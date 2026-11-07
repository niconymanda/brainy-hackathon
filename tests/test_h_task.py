import argparse
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import AsyncMock, patch

from brainy.h_task import H_PROMPT_TEMPLATE, build_h_prompt
from brainy.stt import Summary, Transcript
from brainy.stt.__main__ import build_h_prompt_from_results, main, run


class PromptTests(unittest.TestCase):
    def test_summary_and_transcript(self):
        prompt = build_h_prompt("  Book a train  ", "  Paris to Lyon {tomorrow}  ")
        self.assertIn("\n\nBook a train\n\n", prompt)
        self.assertNotIn("Paris to Lyon", prompt)
        self.assertIn("Only when the user has given his ok, can you go ahead with the action.", prompt)
        self.assertIn("{summary}", H_PROMPT_TEMPLATE)

    def test_empty_transcript(self):
        for transcript in ("", " \n "):
            self.assertEqual(build_h_prompt("Task", transcript), build_h_prompt("Task"))

    def test_latest_usable_summary(self):
        summaries = [Summary(results="Old"), Summary(results="Latest"),
                     Summary(results=" "), Summary(results="Failed", error="Addon failed")]
        self.assertEqual(build_h_prompt_from_results(["Paris", "to Lyon"], summaries),
                         build_h_prompt("Latest", "Paris\nto Lyon"))

    def test_summary_without_transcript(self):
        self.assertEqual(build_h_prompt_from_results([], [Summary(results="Task")]),
                         build_h_prompt("Task"))

    def test_missing_failed_or_empty_summary_falls_back(self):
        for summaries in ([], [Summary(error="Addon failed")], [Summary(results="  ")]):
            with self.subTest(summaries=summaries):
                self.assertEqual(build_h_prompt_from_results(["Paris", "to Lyon"], summaries),
                                 build_h_prompt("Paris\nto Lyon", "Paris\nto Lyon"))

    def test_empty_results(self):
        with self.assertRaisesRegex(ValueError, "cannot build an H prompt"):
            build_h_prompt_from_results(["  "], [Summary(error="Addon failed")])

    def test_main_returns_success_for_prompt_string(self):
        with patch("sys.argv", ["brainy.stt", "--h-prompt"]):
            with patch("brainy.stt.__main__.run", new=AsyncMock(return_value="Prompt")) as runner:
                self.assertEqual(main(), 0)
        self.assertTrue(runner.call_args.args[0].h_prompt)


class HandoffTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, summaries=(), texts=("Paris", "to Lyon"), enabled=True, summary_type=None):
        args = argparse.Namespace(
            summary=summary_type, language=None, endpointing=None, max_utterance=None,
            file="unused.wav", device=None, h_prompt=enabled,
        )

        async def transcribe(audio, callback, stop, on_summary):
            callback(Transcript("Ignored partial", False, "0"))
            for index, text in enumerate(texts):
                callback(Transcript(text, True, str(index)))
            for summary in summaries:
                on_summary(summary)

        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("brainy.stt.__main__.GladiaClient") as gladia:
            gladia.return_value.transcribe = AsyncMock(side_effect=transcribe)
            with redirect_stdout(stdout), redirect_stderr(stderr):
                prompt = await run(args)
        self.assertEqual(gladia.call_args.kwargs["summary_type"],
                         summary_type or ("bullet_points" if enabled else None))
        return prompt, stdout.getvalue(), stderr.getvalue()

    async def test_prints_and_returns_prompt(self):
        prompt, stdout, _ = await self.exercise([Summary(results="Train to Lyon")])
        self.assertEqual(prompt, build_h_prompt("Train to Lyon", "Paris\nto Lyon"))
        self.assertIn(f"H prompt:\n{prompt}", stdout)
        self.assertNotIn("Ignored partial", prompt)
        self.assertNotIn("H answer:", stdout)

    async def test_missing_failed_or_empty_summary_falls_back(self):
        for summaries in ([], [Summary(error="Addon failed")], [Summary(results=" ")]):
            with self.subTest(summaries=summaries):
                prompt, _, _ = await self.exercise(summaries)
                self.assertEqual(prompt, build_h_prompt("Paris\nto Lyon", "Paris\nto Lyon"))

    async def test_explicit_summary_type_is_preserved(self):
        await self.exercise([Summary(results="Task")], summary_type="concise")

    async def test_no_flag_leaves_prompt_disabled(self):
        prompt, stdout, _ = await self.exercise(enabled=False)
        self.assertIsNone(prompt)
        self.assertNotIn("H prompt:", stdout)

    async def test_empty_speech_does_not_build_prompt(self):
        with self.assertRaisesRegex(ValueError, "cannot build an H prompt"):
            await self.exercise(texts=())


if __name__ == "__main__":
    unittest.main()
