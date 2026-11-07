import asyncio
import argparse
import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import AsyncMock, patch

import httpx

from brainy.stt import GladiaClient, Summary
from brainy.stt.audio import wav_audio
from brainy.stt.__main__ import duration_type, run


class Socket:
    def __init__(self, error=False, summary=None):
        self.sent = []
        self.stopped = asyncio.Event()
        self.error = error
        self.summary = summary

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def send(self, data):
        self.sent.append(data)
        if isinstance(data, str):
            self.stopped.set()

    async def __aiter__(self):
        await self.stopped.wait()
        if self.error:
            yield json.dumps({"type": "error"})
            return
        for final in (False, True):
            yield json.dumps({"type": "transcript", "data": {
                "id": "1", "is_final": final,
                "utterance": {"text": "Bonjour", "language": "fr"},
            }})
        if self.summary is not None:
            yield json.dumps({"type": "post_summarization", **self.summary})
            yield json.dumps({"type": "end_session"})


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, chunks, languages=(), stop=None, error=False,
                       summary=None, on_summary=None, **options):
        async def audio():
            for chunk in chunks:
                yield chunk
            if stop:
                await asyncio.Event().wait()

        socket = Socket(error, summary)
        events = []
        response = unittest.mock.Mock(is_error=False)
        response.json.return_value = {"url": "wss://example.test/live"}
        http = AsyncMock()
        http.__aenter__.return_value = http
        http.post.return_value = response
        with patch("brainy.stt.client.httpx.AsyncClient", return_value=http), patch(
            "brainy.stt.client.connect", return_value=socket,
        ):
            await GladiaClient("test-key", languages, **options).transcribe(
                audio(), events.append, stop, on_summary=on_summary,
            )
        return socket, events, http.post.call_args

    async def test_audio_and_transcripts(self):
        socket, events, call = await self.exercise([b"\x00\x00"], ["fr", "en"])
        self.assertEqual(socket.sent, [b"\x00\x00", '{"type": "stop_recording"}'])
        self.assertEqual([event.is_final for event in events], [False, True])
        self.assertEqual(events[-1].language, "fr")
        self.assertEqual(call.kwargs["headers"], {"x-gladia-key": "test-key"})
        self.assertTrue(call.kwargs["json"]["language_config"]["code_switching"])

    async def test_empty_audio_auto_detection(self):
        socket, _, call = await self.exercise([])
        self.assertEqual(len(socket.sent), 1)
        self.assertEqual(call.kwargs["json"]["language_config"], {
            "languages": [], "code_switching": False,
        })
        for key in ("post_processing", "endpointing", "maximum_duration_without_endpointing"):
            self.assertNotIn(key, call.kwargs["json"])
        self.assertNotIn("receive_post_processing_events", call.kwargs["json"]["messages_config"])

    async def test_summary_after_stop(self):
        for summary_type in ("general", "bullet_points", "concise"):
            summaries = []
            socket, events, call = await self.exercise(
                [], summary={"data": {"results": "Résumé"}}, on_summary=summaries.append,
                summary_type=summary_type, endpointing=0.5,
                maximum_duration_without_endpointing=9,
            )
            config = call.kwargs["json"]
            self.assertEqual(config["post_processing"], {
                "summarization": True, "summarization_config": {"type": summary_type},
            })
            self.assertTrue(config["messages_config"]["receive_post_processing_events"])
            self.assertEqual(config["endpointing"], 0.5)
            self.assertEqual(config["maximum_duration_without_endpointing"], 9)
            self.assertTrue(socket.stopped.is_set())
            self.assertTrue(events[-1].is_final)
            self.assertEqual(summaries[0].results, "Résumé")
            self.assertIsNone(summaries[0].error)

    async def test_empty_summary(self):
        summaries = []
        await self.exercise([], summary={"data": {"results": ""}}, on_summary=summaries.append)
        self.assertEqual(summaries[0].results, "")

    async def test_summary_failure_does_not_abort(self):
        summaries = []
        payload = {"data": None, "error": {"message": "Addon unavailable"}}
        _, events, _ = await self.exercise([], summary=payload, on_summary=summaries.append)
        self.assertTrue(events[-1].is_final)
        self.assertIn("Addon unavailable", summaries[0].error)
        self.assertIsNone(summaries[0].results)
        with self.assertLogs("brainy.stt.client", level="WARNING") as logs:
            await self.exercise([], summary=payload)
        self.assertIn("Addon unavailable", logs.output[0])

    async def test_cli_prints_summary_and_addon_failure(self):
        args = argparse.Namespace(language=None, summary="concise", endpointing=0.5,
                                  max_utterance=9, file="sample.wav", device=None)
        async def transcribe(audio, callback, stop, on_summary):
            on_summary(Summary(results="A short summary"))
            on_summary(Summary(error="Addon failed"))
        client = unittest.mock.Mock()
        client.transcribe = AsyncMock(side_effect=transcribe)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("brainy.stt.__main__.GladiaClient", return_value=client) as factory:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                await run(args)
        self.assertEqual(stdout.getvalue(), "Summary:\nA short summary\n")
        self.assertEqual(stderr.getvalue(), "Summarization failed: Addon failed\n")
        self.assertEqual(factory.call_args.kwargs, {
            "summary_type": "concise", "endpointing": 0.5,
            "maximum_duration_without_endpointing": 9,
        })

    def test_option_validation(self):
        for name, low, high in (("endpointing", 0.01, 10),
                                ("maximum_duration_without_endpointing", 5, 60)):
            for value in (low, high):
                GladiaClient("test-key", **{name: value})
                self.assertEqual(duration_type(low, high)(str(value)), value)
            for value in (low - 0.01, high + 0.01, float("nan"), float("inf")):
                with self.assertRaises(ValueError):
                    GladiaClient("test-key", **{name: value})
                with self.assertRaises(argparse.ArgumentTypeError):
                    duration_type(low, high)(str(value))
        with self.assertRaises(ValueError):
            GladiaClient("test-key", summary_type="invalid")

    async def test_stop_drains_final_transcripts(self):
        stop = asyncio.Event()
        stop.set()
        socket, events, _ = await self.exercise([b"00"], stop=stop)
        self.assertTrue(socket.stopped.is_set())
        self.assertTrue(events[-1].is_final)

    async def test_server_error(self):
        with self.assertRaisesRegex(RuntimeError, "streaming error"):
            await self.exercise([], error=True)

    async def test_init_error(self):
        http = AsyncMock()
        http.__aenter__.return_value = http
        http.post.return_value.status_code = 401
        http.post.return_value.is_error = True
        http.post.return_value.text = "Invalid endpointing"
        async def audio():
            yield b""
        with patch("brainy.stt.client.httpx.AsyncClient", return_value=http):
            with self.assertRaisesRegex(RuntimeError, "HTTP 401.*Invalid endpointing"):
                await GladiaClient("test-key").transcribe(audio(), lambda _: None)

    async def test_init_error_redaction_and_truncation(self):
        http = AsyncMock()
        http.__aenter__.return_value = http
        http.post.return_value = httpx.Response(422, json={
            "message": "Invalid value test-key wss://example.test/live?token=secret " + "x" * 1000,
        })
        async def audio():
            yield b""
        with patch("brainy.stt.client.httpx.AsyncClient", return_value=http):
            with self.assertRaises(RuntimeError) as caught:
                await GladiaClient("test-key").transcribe(audio(), lambda _: None)
        message = str(caught.exception)
        self.assertIn("Invalid value", message)
        self.assertNotIn("test-key", message)
        self.assertNotIn("wss://", message)
        self.assertNotIn("token=secret", message)
        self.assertLess(len(message), 600)

    def test_error_sanitizer(self):
        client = GladiaClient('secret"key')
        for text in ('secret"key', r'secret\"key', 'secret%22key',
                     r'wss:\/\/example.test/live?token=abc', 'ws://example.test/live'):
            safe = client._safe_error(text)
            self.assertIn("REDACTED", safe)
            self.assertNotIn("example.test", safe)

    async def test_summary_fetch_http_error_and_missing_id(self):
        client = GladiaClient("test-key")
        self.assertIn("no session id", (await client._get_summary(None)).error)
        http = AsyncMock()
        http.__aenter__.return_value = http
        http.get.return_value = httpx.Response(401, text="Invalid test-key wss://example.test/live")
        with patch("brainy.stt.client.httpx.AsyncClient", return_value=http):
            summary = await client._get_summary("session-123")
        self.assertIn("HTTP 401", summary.error)
        self.assertNotIn("test-key", summary.error)
        self.assertNotIn("example.test", summary.error)

    async def test_summary_fetch_retries_with_backoff(self):
        http = AsyncMock()
        http.__aenter__.return_value = http
        http.get.side_effect = [
            httpx.Response(503), httpx.ConnectError("offline"),
            httpx.Response(200, json={"status": "done", "result": {
                "summarization": {"results": "Recovered summary"},
            }}),
        ]
        with patch("brainy.stt.client.httpx.AsyncClient", return_value=http):
            with patch("brainy.stt.client.asyncio.sleep", new_callable=AsyncMock) as sleep:
                summary = await GladiaClient("test-key")._get_summary("session-123")
        self.assertEqual(summary.results, "Recovered summary")
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2])

    def test_missing_key(self):
        with self.assertRaisesRegex(ValueError, "GLADIA_API_KEY"):
            GladiaClient("")

    async def test_wav_validation_and_empty_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.wav"
            for rate in (8000, 16000):
                with wave.open(str(path), "wb") as output:
                    output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
                if rate == 8000:
                    with self.assertRaisesRegex(ValueError, "16 kHz"):
                        _ = [chunk async for chunk in wav_audio(path)]
                else:
                    self.assertEqual([chunk async for chunk in wav_audio(path)], [])


if __name__ == "__main__":
    unittest.main()
