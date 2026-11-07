"""Text-only harness: python -m brainy.agent."""

import argparse
import asyncio
import os
import signal

from dotenv import load_dotenv

from .browser import Browser
from .debug import debug_log
from .events import AgentError, AgentStep, Done
from .holo import HoloClient
from .loop import WebAgent


async def run(args):
    async def ask(question):
        return await asyncio.to_thread(input, question + " ")

    client = HoloClient(os.getenv("H_API_KEY", ""), args.model)
    async with Browser(headless=args.headless, profile_dir=args.profile_dir,
                       channel=args.channel, debug=args.debug) as browser:
        status = 0
        async for event in WebAgent(client, browser, ask, debug=args.debug).run(args.goal, args.url):
            if isinstance(event, AgentStep):
                print(event.narration, flush=True)
            elif isinstance(event, Done):
                print(event.result, flush=True)
            elif isinstance(event, AgentError):
                print(event.reason, event.suggestion, flush=True)
                status = 1
        if not args.headless:
            previous = signal.signal(signal.SIGINT, signal.default_int_handler)
            try:
                input("Press Enter to close the browser. ")
            except EOFError:
                pass
            finally:
                signal.signal(signal.SIGINT, previous)
    return status


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Brainy's controlled H Company web agent (no microphone).")
    parser.add_argument("goal")
    parser.add_argument("--url")
    parser.add_argument("--model", default=os.getenv("H_MODEL") or "holo3-1-35b-a3b")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--channel", help="Installed browser channel, e.g. chrome or msedge (default: bundled Chromium).")
    parser.add_argument("--debug", action="store_true", help="Local exception and page lifecycle diagnostics on stderr.")
    parser.add_argument("--profile-dir", help="Optional persistent browser profile; contains private browsing data.")
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        if args.debug:
            debug_log(f"startup: {type(exc).__module__}.{type(exc).__name__}: {exc}")
        print("Unable to start. Check H_API_KEY, dependencies and Chromium installation.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
