"""Run with python -m brainy.stt."""

import argparse
import asyncio
import os
import signal
import sys
import wave

from dotenv import load_dotenv

from .audio import microphone_audio, wav_audio
from .client import GladiaClient


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


async def run(args):
    client = GladiaClient(os.getenv("GLADIA_API_KEY", ""), args.language or ())
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    previous = signal.signal(signal.SIGINT, lambda *_: loop.call_soon_threadsafe(stop.set))
    printer = TranscriptPrinter()
    audio = wav_audio(args.file) if args.file else microphone_audio(args.device)
    try:
        await client.transcribe(audio, printer, stop)
    finally:
        await audio.aclose()
        signal.signal(signal.SIGINT, previous)
        printer.finish()


def main():
    parser = argparse.ArgumentParser(description="Stream microphone or WAV audio to Gladia live STT.")
    parser.add_argument("--language", action="append", metavar="CODE",
                        help="ISO language code; repeat for code switching (e.g. fr and en). Default: auto-detect.")
    parser.add_argument("--list-devices", action="store_true", help="List audio devices without an API key.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--device", help="Microphone device index or name (default: system input).")
    source.add_argument("--file", metavar="PATH.wav", help="Stream a 16 kHz mono 16-bit PCM WAV in real time.")
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
        asyncio.run(run(args))
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        # Transport exceptions can contain the signed session URL; never print it.
        if isinstance(exc, ModuleNotFoundError):
            message = f"Missing Python package '{exc.name}'. Run: pip install -r requirements.txt"
        elif isinstance(exc, (ValueError, RuntimeError, OSError, wave.Error)):
            message = str(exc)
        else:
            message = f"{type(exc).__name__}: check connectivity, audio device and Gladia configuration."
        print(f"Error: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
