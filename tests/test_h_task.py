import argparse
import asyncio
import io
import signal
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import AsyncMock, Mock, patch

from brainy.h_task import H_PROMPT_TEMPLATE, build_h_prompt, run_h_task, run_h_task_async
from brainy.stt import Summary, Transcript
from brainy.stt.__main__ import main, run


class PromptTests(unittest.TestCase):
    def test_summary_and_transcript(self):
        prompt = build_h_prompt("  Book a train  ", "  Paris to Lyon {tomorrow}  ")
        self.assertIn("\n\nBook a train\n\n", prompt)
        self.assertIn("Here is what they said, word for word:\n\nParis to Lyon {tomorrow}", prompt)
        self.assertIn("Only when the user has given his ok, can you go ahead with the action.", prompt)
        self.assertIn("{summary}", H_PROMPT_TEMPLATE)

    def test_empty_transcript(self):
        self.assertIn("(not available)", build_h_prompt("Task", " \n "))

    def test_sdk_call_and_key_alias(self):
        with patch.dict("os.environ", {"H_API_KEY": "test-key"}):
            with patch("brainy.h_task.Client") as factory:
                client = factory.return_value.__enter__.return_value
                client.run_session.return_value = Mock(answer="Stopped before booking", error=None)
                self.assertEqual(run_h_task("Task", "Words"), "Stopped before booking")
        factory.assert_called_once_with(api_key="test-key")
        client.run_session.assert_called_once_with(
            agent="h/web-surfer-flash", messages=build_h_prompt("Task", "Words"),
            timeout_seconds=600, max_time_s=600,
        )
        factory.return_value.__exit__.assert_called_once()

    def test_native_sdk_credentials_and_structured_answer(self):
        with patch.dict("os.environ", {}, clear=True), patch("brainy.h_task.Client") as factory:
            factory.return_value.__enter__.return_value.run_session.return_value = Mock(
                answer={"result": "Done"}, error=None,
            )
            self.assertEqual(run_h_task("Task"), '{"result": "Done"}')
            factory.assert_called_once_with()

    def test_empty_task_and_failed_sdk(self):
        with patch("brainy.h_task.Client") as factory:
            with self.assertRaisesRegex(ValueError, "empty task"):
                run_h_task(" ")
            factory.assert_not_called()
            factory.side_effect = RuntimeError("secret-key")
            with self.assertRaisesRegex(RuntimeError, "H task failed") as caught:
                run_h_task("Task")
            self.assertNotIn("secret-key", str(caught.exception))

    def test_missing_answer(self):
        with patch("brainy.h_task.Client") as factory:
            factory.return_value.__enter__.return_value.run_session.return_value = Mock(answer=None, error=None)
            with self.assertRaisesRegex(RuntimeError, "no answer"):
                run_h_task("Task")

    def test_dry_run_requires_handoff(self):
        with patch("sys.argv", ["brainy.stt", "--dry-run"]), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main()
        self.assertEqual(caught.exception.code, 2)


class HandoffTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, summary=None, dry_run=False, texts=("Paris", "to Lyon"), interrupt=False):
        args = argparse.Namespace(
            summary=None, language=None, endpointing=None, max_utterance=None,
            file="unused.wav", device=None, send_to_h=True, dry_run=dry_run,
        )

        async def transcribe(audio, callback, stop, on_summary):
            callback(Transcript("Ignored partial", False, "0"))
            for index, text in enumerate(texts):
                callback(Transcript(text, True, str(index)))
            if summary is not None:
                on_summary(summary)

        loops = []
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("brainy.stt.__main__.GladiaClient") as gladia:
            gladia.return_value.transcribe = AsyncMock(side_effect=transcribe)
            with patch("brainy.h_task.AsyncClient") as h_client:
                client = h_client.return_value.__aenter__.return_value
                session = Mock(cancel=AsyncMock())
                client.start_session = AsyncMock(return_value=session)

                async def answer(**kwargs):
                    loops.append(asyncio.get_running_loop())
                    if interrupt:
                        signal.raise_signal(signal.SIGINT)
                        await asyncio.Event().wait()
                    return Mock(answer="Stopped at confirmation", error=None)

                session.wait_for_completion = AsyncMock(side_effect=answer)
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    code = await run(args)
                if interrupt:
                    self.assertEqual(code, 130)
                    session.cancel.assert_awaited_once()
                    self.assertIn("Cancelling the H task", stderr.getvalue())
                else:
                    session.cancel.assert_not_called()
        self.assertEqual(gladia.call_args.kwargs["summary_type"], "bullet_points")
        return stdout.getvalue(), stderr.getvalue(), client, loops

    async def test_summary_handoff_uses_async_sdk(self):
        stdout, _, client, loops = await self.exercise(Summary(results="Train to Lyon"))
        self.assertIn("H prompt:", stdout)
        self.assertIn("H answer:\nStopped at confirmation", stdout)
        client.start_session.assert_called_once_with(
            agent="h/web-surfer-flash", messages=build_h_prompt("Train to Lyon", "Paris\nto Lyon"),
            max_time_s=600,
        )
        self.assertIs(loops[0], asyncio.get_running_loop())

    async def test_ctrl_c_cancels_remote_h_session_promptly(self):
        stdout, _, _, _ = await asyncio.wait_for(
            self.exercise(Summary(results="Task"), interrupt=True), timeout=1,
        )
        self.assertNotIn("H answer:", stdout)

    async def test_missing_failed_or_empty_summary_falls_back(self):
        for summary in (None, Summary(error="Addon failed"), Summary(results="  ")):
            with self.subTest(summary=summary):
                _, stderr, client, _ = await self.exercise(summary)
                self.assertIn("using the final transcript", stderr)
                self.assertEqual(client.start_session.call_args.kwargs["messages"],
                                 build_h_prompt("Paris\nto Lyon", "Paris\nto Lyon"))

    async def test_dry_run_never_calls_h(self):
        stdout, _, client, threads = await self.exercise(Summary(results="Task"), dry_run=True)
        self.assertIn("H prompt:", stdout)
        self.assertNotIn("H answer:", stdout)
        client.start_session.assert_not_called()
        self.assertEqual(threads, [])

    async def test_empty_speech_does_not_send(self):
        with self.assertRaisesRegex(ValueError, "nothing to send"):
            await self.exercise(texts=())

    async def test_h_timeout_cancels_remote_session(self):
        with patch("brainy.h_task.AsyncClient") as factory:
            client = factory.return_value.__aenter__.return_value
            session = Mock(cancel=AsyncMock())
            async def wait(**kwargs):
                await asyncio.Event().wait()
            session.wait_for_completion = AsyncMock(side_effect=wait)
            client.start_session = AsyncMock(return_value=session)
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                await run_h_task_async("Task", timeout_seconds=0.01)
            session.cancel.assert_awaited_once()
            self.assertEqual(client.start_session.call_args.kwargs["max_time_s"], 1)

    async def test_cancel_during_creation_still_cancels_remote_session(self):
        started = asyncio.Event()
        release = asyncio.Event()
        session = Mock(cancel=AsyncMock())

        async def create(**kwargs):
            started.set()
            await release.wait()
            return session

        with patch("brainy.h_task.AsyncClient") as factory:
            factory.return_value.__aenter__.return_value.start_session = AsyncMock(side_effect=create)
            task = asyncio.create_task(run_h_task_async("Task"))
            await started.wait()
            task.cancel()
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=1)
            session.cancel.assert_awaited_once()

    async def test_failed_remote_cancel_is_reported_safely(self):
        started = asyncio.Event()
        async def wait(**kwargs):
            started.set()
            await asyncio.Event().wait()

        session = Mock(cancel=AsyncMock(side_effect=RuntimeError("secret-key")),
                       wait_for_completion=AsyncMock(side_effect=wait))
        with patch("brainy.h_task.AsyncClient") as factory:
            factory.return_value.__aenter__.return_value.start_session = AsyncMock(return_value=session)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                task = asyncio.create_task(run_h_task_async("Task"))
                await started.wait()
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(task, timeout=1)
            self.assertIn("Could not confirm remote H cancellation", stderr.getvalue())
            self.assertNotIn("secret-key", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
