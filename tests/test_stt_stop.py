"""Exercise the CLI's real SIGINT handler against a loopback WebSocket."""

import asyncio
import io
import json
import signal
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from unittest.mock import patch

import httpx
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from brainy.stt.__main__ import main


class StopTests(unittest.TestCase):
    def exercise(self, ws_summary=True, *, force=False, force_poll=False, stall=False, responses=None,
                 result_timeout=120):
        requests = []
        stopped = []

        async def server(socket):
            async for message in socket:
                if isinstance(message, bytes):
                    signal.raise_signal(signal.SIGINT)
                elif json.loads(message)["type"] == "stop_recording":
                    stopped.append(True)
                    if force:
                        signal.raise_signal(signal.SIGINT)
                    if stall or force:
                        await socket.wait_closed()
                        return
                    await socket.send(json.dumps({"type": "transcript", "data": {
                        "id": "1", "is_final": True, "utterance": {"text": "Bonjour"},
                    }}))
                    if ws_summary:
                        await socket.send(json.dumps({"type": "post_summarization",
                                                      "data": {"results": "WS summary"}}))
                    await socket.close()

        async def microphone(device):
            yield b"\x00\x00" * 1600
            await asyncio.Event().wait()

        def http(request):
            requests.append(request)
            if request.method == "POST":
                return httpx.Response(201, json={"id": "session-123", "url": "wss://fake.test/live"})
            if force_poll:
                signal.raise_signal(signal.SIGINT)
                return httpx.Response(200, json={"status": "processing"})
            if responses:
                response = responses.pop(0) if len(responses) > 1 else responses[0]
                return httpx.Response(200, json=response)
            return httpx.Response(200, json={
                "status": "done", "result": {"summarization": {"results": "GET summary"}},
            })

        original_client = httpx.AsyncClient
        original_run = asyncio.run

        async def run_with_server(coroutine):
            async with serve(server, "127.0.0.1", 0) as listener:
                port = listener.sockets[0].getsockname()[1]
                with patch("brainy.stt.client.connect", side_effect=lambda *a, **kw: connect(
                    f"ws://127.0.0.1:{port}", **kw,
                )):
                    return await coroutine

        stdout, stderr = io.StringIO(), io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(patch("brainy.stt.client.POST_STOP_TIMEOUT", 0.05))
            stack.enter_context(patch("brainy.stt.client.RESULT_TIMEOUT", result_timeout))
            stack.enter_context(patch.dict("os.environ", {"GLADIA_API_KEY": "test-key"}))
            with patch("sys.argv", ["brainy.stt", "--summary", "bullet_points"]):
                with patch("brainy.stt.__main__.microphone_audio", microphone):
                    with patch("brainy.stt.client.httpx.AsyncClient", side_effect=lambda **kw: original_client(
                        transport=httpx.MockTransport(http), **kw,
                    )):
                        with patch("brainy.stt.__main__.asyncio.run", side_effect=lambda coro: original_run(
                            run_with_server(coro),
                        )):
                            with redirect_stdout(stdout), redirect_stderr(stderr):
                                code = main()
        self.assertEqual(stopped, [True])
        self.assertEqual(code, 130 if force or force_poll else 0)
        if not stall and not force:
            self.assertIn("Bonjour", stdout.getvalue())
        self.assertIn("Stopping… waiting for final transcripts and summary", stderr.getvalue())
        return stdout.getvalue(), stderr.getvalue(), requests

    def test_ctrl_c_keeps_ws_summary(self):
        stdout, _, requests = self.exercise()
        self.assertIn("Summary:\nWS summary", stdout)
        self.assertEqual([request.method for request in requests], ["POST"])

    def test_ctrl_c_fetches_missing_ws_summary(self):
        stdout, _, requests = self.exercise(ws_summary=False)
        self.assertIn("Summary:\nGET summary", stdout)
        self.assertEqual([request.method for request in requests], ["POST", "GET"])
        self.assertEqual(str(requests[-1].url), "https://api.gladia.io/v2/live/session-123")
        self.assertEqual(requests[-1].headers["x-gladia-key"], "test-key")

    def test_ctrl_c_polls_until_done(self):
        stdout, _, requests = self.exercise(ws_summary=False, responses=[
            {"status": "queued"}, {"status": "processing"},
            {"status": "done", "result": {"summarization": {"results": "Delayed summary"}}},
        ])
        self.assertIn("Summary:\nDelayed summary", stdout)
        self.assertEqual(len(requests), 4)

    def test_post_stop_ws_timeout_uses_get(self):
        stdout, _, _ = self.exercise(stall=True)
        self.assertIn("Summary:\nGET summary", stdout)

    def test_second_ctrl_c_exits_without_summary(self):
        stdout, stderr, requests = self.exercise(force=True)
        self.assertNotIn("Summary:", stdout)
        self.assertIn("Quitting without remaining results.", stderr)
        self.assertEqual(len(requests), 1)

    def test_get_timeout_is_reported(self):
        _, stderr, _ = self.exercise(ws_summary=False, responses=[{"status": "processing"}],
                                     result_timeout=0.02)
        self.assertIn("Summarization failed: Timed out", stderr)

    def test_second_ctrl_c_during_polling(self):
        _, stderr, requests = self.exercise(ws_summary=False, force_poll=True)
        self.assertIn("Quitting without remaining results.", stderr)
        self.assertEqual(len(requests), 2)

    def test_terminal_get_results(self):
        for response, expected in (
            ({"status": "error", "error": "Job failed"}, "Job failed"),
            ({"status": "done", "result": {}}, "without a summary"),
            ({"status": "done", "result": {"summarization": {
                "error": "Addon failed", "results": None,
            }}}, "Addon failed"),
            ({"status": "done", "result": {"summarization": {"results": ""}}}, None),
        ):
            with self.subTest(response=response):
                stdout, stderr, _ = self.exercise(ws_summary=False, responses=[response])
                if expected:
                    self.assertIn(expected, stderr)
                else:
                    self.assertIn("Summary:\n", stdout)
                    self.assertNotIn("Summarization failed", stderr)


if __name__ == "__main__":
    unittest.main()
