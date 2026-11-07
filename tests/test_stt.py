import asyncio
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import AsyncMock, patch

from brainy.stt import GladiaClient
from brainy.stt.audio import wav_audio


class Socket:
    def __init__(self, error=False):
        self.sent = []
        self.stopped = asyncio.Event()
        self.error = error

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


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, chunks, languages=(), stop=None, error=False):
        async def audio():
            for chunk in chunks:
                yield chunk
            if stop:
                await asyncio.Event().wait()

        socket = Socket(error)
        events = []
        response = unittest.mock.Mock(is_error=False)
        response.json.return_value = {"url": "wss://example.test/live"}
        http = AsyncMock()
        http.__aenter__.return_value = http
        http.post.return_value = response
        with patch("brainy.stt.client.httpx.AsyncClient", return_value=http), patch(
            "brainy.stt.client.connect", return_value=socket,
        ):
            await GladiaClient("test-key", languages).transcribe(audio(), events.append, stop)
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
        async def audio():
            yield b""
        with patch("brainy.stt.client.httpx.AsyncClient", return_value=http):
            with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
                await GladiaClient("test-key").transcribe(audio(), lambda _: None)

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
