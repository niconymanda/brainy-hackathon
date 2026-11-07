import asyncio
import io
import os
import signal
import subprocess
import sys
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from unittest.mock import AsyncMock, patch

from brainy.__main__ import main
from brainy.agent.__main__ import ask
from brainy.agent.events import AgentError, AgentStep, Done
from brainy.h_task import build_h_prompt
from brainy.stt import Summary, Transcript


class PipelineTests(unittest.TestCase):
    def exercise(self, texts=("Find trains", "to Lyon"), summary="Train task", keys=None,
                 interrupt=None, error=None, event=None):
        async def audio():
            yield b""

        async def transcribe(audio, callback, stop, on_summary):
            if error:
                raise error
            callback(Transcript("partial", False, "0"))
            for index, text in enumerate(texts):
                callback(Transcript(text, True, str(index)))
            if interrupt in ("stop", "force"):
                signal.raise_signal(signal.SIGINT)
                await stop.wait()
                if interrupt == "force":
                    signal.raise_signal(signal.SIGINT)
                    await asyncio.Event().wait()
            if summary is not None:
                on_summary(Summary(results=summary))

        async def events(goal, url):
            if interrupt == "agent":
                signal.raise_signal(signal.SIGINT)
            yield AgentStep("Searching", "navigate")
            yield event or Done("Finished")

        stdout, stderr = io.StringIO(), io.StringIO()
        previous = signal.getsignal(signal.SIGINT)
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, keys if keys is not None else
                                           {"GLADIA_API_KEY": "gladia-key", "H_API_KEY": "h-key"}, clear=True))
            stack.enter_context(patch("brainy.__main__.load_dotenv"))
            stack.enter_context(patch("sys.argv", ["brainy", "--headless", "--url", "https://example.org",
                                                   "--model", "test-model", "--device", "2"]))
            gladia = stack.enter_context(patch("brainy.stt.__main__.GladiaClient"))
            gladia.return_value.transcribe = AsyncMock(side_effect=transcribe)
            mic = stack.enter_context(patch("brainy.stt.__main__.microphone_audio", side_effect=lambda _: audio()))
            browser = stack.enter_context(patch("brainy.agent.__main__.Browser"))
            holo = stack.enter_context(patch("brainy.agent.__main__.HoloClient"))
            agent = stack.enter_context(patch("brainy.agent.__main__.WebAgent"))
            agent.return_value.run.side_effect = events
            stack.enter_context(redirect_stdout(stdout))
            stack.enter_context(redirect_stderr(stderr))
            code = main()
        self.assertEqual(signal.getsignal(signal.SIGINT), previous)
        return code, stdout.getvalue(), stderr.getvalue(), gladia, mic, browser, holo, agent

    def test_speech_prompt_reaches_agent_with_url(self):
        code, stdout, _, gladia, mic, browser, holo, agent = self.exercise(interrupt="stop")
        self.assertEqual(code, 0)
        gladia.assert_called_once_with("gladia-key", (), summary_type="bullet_points", endpointing=None,
                                      maximum_duration_without_endpointing=None)
        mic.assert_called_once_with(2)
        browser.assert_called_once_with(headless=True, profile_dir=None, channel=None, debug=False)
        holo.assert_called_once_with("h-key", "test-model")
        agent.return_value.run.assert_called_once_with(build_h_prompt("Train task", "Find trains\nto Lyon"),
                                                      "https://example.org")
        self.assertIn("Searching\nFinished", stdout)
        browser.return_value.__aexit__.assert_awaited_once()

    def test_transcript_fallback(self):
        code, _, _, _, _, _, _, agent = self.exercise(summary=None)
        self.assertEqual(code, 0)
        self.assertEqual(agent.return_value.run.call_args.args[0], build_h_prompt("Find trains\nto Lyon"))

    def test_empty_speech_never_launches_browser(self):
        code, _, stderr, _, _, browser, _, agent = self.exercise(texts=(), summary=None)
        self.assertEqual(code, 1)
        self.assertIn("No summary or final transcript available", stderr)
        browser.assert_not_called()
        agent.assert_not_called()

    def test_missing_keys_fail_before_transcription(self):
        for keys, missing in (({"GLADIA_API_KEY": "key"}, "H_API_KEY"),
                              ({"H_API_KEY": "key"}, "GLADIA_API_KEY")):
            with self.subTest(missing=missing):
                code, _, stderr, gladia, mic, browser, _, _ = self.exercise(keys=keys)
                self.assertEqual(code, 1)
                self.assertIn(f"Set {missing}", stderr)
                gladia.assert_not_called()
                mic.assert_not_called()
                browser.assert_not_called()

    def test_agent_error_status(self):
        code, stdout, _, *_ = self.exercise(event=AgentError("Failure", "Retry"))
        self.assertEqual(code, 1)
        self.assertIn("Failure Retry", stdout)

    def test_interrupt_in_agent_exits_cleanly(self):
        code, _, stderr, _, _, browser, _, _ = self.exercise(interrupt="agent")
        self.assertEqual(code, 130)
        self.assertNotIn("Traceback", stderr)
        browser.return_value.__aexit__.assert_awaited_once()

    def test_second_recording_interrupt_does_not_launch_agent(self):
        code, _, _, _, _, browser, _, _ = self.exercise(interrupt="force")
        self.assertEqual(code, 130)
        browser.assert_not_called()

    def test_signed_url_never_printed_on_stt_failure(self):
        for error in (RuntimeError("Failed wss://example.org/session?secret=signed-token"),
                      Exception("wss://example.org/session?secret=signed-token")):
            with self.subTest(error=type(error)):
                code, stdout, stderr, _, _, browser, _, _ = self.exercise(error=error)
                self.assertEqual(code, 1)
                self.assertNotIn("signed-token", stdout + stderr)
                self.assertNotIn("wss://", stdout + stderr)
                browser.assert_not_called()

    def test_interrupt_during_typed_input_does_not_wait_for_thread(self):
        program = '''
import asyncio
import os
import signal
import threading
from unittest.mock import patch
from brainy.agent.__main__ import ask

def blocked_input(prompt):
    os.kill(os.getpid(), signal.SIGINT)
    threading.Event().wait()

with patch("builtins.input", side_effect=blocked_input):
    try:
        asyncio.run(ask("Question?"))
    except KeyboardInterrupt:
        raise SystemExit(130)
'''
        result = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 130, result.stderr)
        self.assertNotIn("Traceback", result.stderr)


class TypedInputTests(unittest.IsolatedAsyncioTestCase):
    async def test_typed_answer(self):
        with patch("builtins.input", return_value="oui") as prompt:
            self.assertEqual(await ask("Confirm?"), "oui")
        prompt.assert_called_once_with("Confirm? ")

    async def test_empty_answer(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(await ask("Question?"), "")

    async def test_input_error(self):
        with patch("builtins.input", side_effect=EOFError):
            with self.assertRaises(EOFError):
                await ask("Question?")
