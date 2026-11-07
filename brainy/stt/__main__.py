"""Run with python -m brainy.stt."""

import argparse
import asyncio
import os
import re
import signal
import sys
import wave

from dotenv import load_dotenv

from brainy.h_task import build_h_prompt

from .audio import microphone_audio, wav_audio
from .client import GladiaClient, validate_duration


class TranscriptPrinter:
    def __init__(self):
        self.width = 0

    def __call__(self, transcript):
        if not sys.stdout.isatty():
            if transcript.is_final:
                print(transcript.text, flush=True)
            return
        text = transcript.text
        print("\r" + text.ljust(self.width), end="\n" if transcript.is_final else "", flush=True)
        self.width = 0 if transcript.is_final else len(text)

    def finish(self):
        if self.width:
            print("\r" + " " * self.width + "\r", end="", flush=True)


def build_h_prompt_from_results(final_utterances, summaries):
    transcript = "\n".join(final_utterances).strip()
    summary = next((item.results.strip() for item in reversed(summaries)
                    if not item.error and item.results and item.results.strip()), "")
    summary = summary or transcript
    if not summary:
        raise ValueError("No summary or final transcript available; cannot build an H prompt.")
    return build_h_prompt(summary, transcript)


async def run(args):
    h_prompt = getattr(args, "h_prompt", False)
    client = GladiaClient(
        os.getenv("GLADIA_API_KEY", ""), args.language or (),
        summary_type=args.summary or ("bullet_points" if h_prompt else None), endpointing=args.endpointing,
        maximum_duration_without_endpointing=args.max_utterance,
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    forced = False

    def interrupt():
        nonlocal forced
        if not stop.is_set():
            stop.set()
            print(
                "Stopping… waiting for final transcripts and summary "
                "(press Ctrl+C again to quit without them)",
                file=sys.stderr, flush=True,
            )
        elif not forced:
            forced = True
            print("Quitting without remaining results.", file=sys.stderr, flush=True)
            task.cancel()

    previous = signal.signal(signal.SIGINT, lambda *_: loop.call_soon_threadsafe(interrupt))
    printer = TranscriptPrinter()
    audio = wav_audio(args.file) if args.file else microphone_audio(args.device)
    summaries = []
    final_utterances = []

    def on_transcript(transcript):
        if transcript.is_final:
            final_utterances.append(transcript.text)
        printer(transcript)

    try:
        await client.transcribe(audio, on_transcript, stop, on_summary=summaries.append)
    except asyncio.CancelledError:
        if not forced:
            raise
        return 130
    finally:
        await audio.aclose()
        signal.signal(signal.SIGINT, previous)
        printer.finish()
        for summary in summaries:
            if summary.error:
                print(f"Summarization failed: {summary.error}", file=sys.stderr)
            elif summary.results is not None:
                print(f"Summary:\n{summary.results}", flush=True)
    if h_prompt:
        prompt = build_h_prompt_from_results(final_utterances, summaries)
        print(f"H prompt:\n{prompt}", flush=True)
        return prompt


def duration_type(minimum, maximum):
    def parse(value):
        try:
            return validate_duration(float(value), minimum, maximum)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from None
    return parse


def add_audio_arguments(parser, *, summary_default=None):
    parser.add_argument("--language", action="append", metavar="CODE",
                        help="ISO language code; repeat for code switching (e.g. fr and en). Default: auto-detect.")
    parser.add_argument("--summary", choices=("general", "bullet_points", "concise"), default=summary_default,
                        help=f"Print a post-session summary (default: {summary_default or 'disabled'}).")
    parser.add_argument("--endpointing", type=duration_type(0.01, 10), metavar="SECONDS",
                        help="Silence ending an utterance: 0.01–10 seconds (API default: 0.05).")
    parser.add_argument("--max-utterance", type=duration_type(5, 60), metavar="SECONDS",
                        help="Utterance duration cap without silence: 5–60 seconds (API default: 5).")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--device", help="Microphone device index or name (default: system input).")
    source.add_argument("--file", metavar="PATH.wav", help="Stream a 16 kHz mono 16-bit PCM WAV in real time.")


def error_message(exc):
    # Transport exceptions can contain the signed session URL; never print it.
    if isinstance(exc, ModuleNotFoundError):
        message = f"Missing Python package '{exc.name}'. Run: pip install -r requirements.txt"
    elif isinstance(exc, (ValueError, RuntimeError, OSError, wave.Error)):
        message = str(exc)
    else:
        message = f"{type(exc).__name__}: check connectivity, audio device and Gladia configuration."
    return re.sub(r"(?i)wss?://[^\s\"'<>]+", "[REDACTED URL]", message)


def main():
    parser = argparse.ArgumentParser(description="Stream microphone or WAV audio to Gladia live STT.")
    add_audio_arguments(parser)
    parser.add_argument("--list-devices", action="store_true", help="List audio devices without an API key.")
    parser.add_argument("--h-prompt", action="store_true",
                        help="Print a prompt for a future H agent without calling H (enables summarization).")
    args = parser.parse_args()
    load_dotenv()
    try:
        if args.list_devices:
            import sounddevice as sd
            devices = sd.query_devices()
            print(devices if len(devices) else "No audio devices found.")
            return 0
        if args.device and args.device.isdecimal():
            args.device = int(args.device)
        result = asyncio.run(run(args))
        return result if isinstance(result, int) else 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Error: {error_message(exc)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
