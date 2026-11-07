"""Text-only harness: python -m brainy.agent."""

import argparse
import asyncio
import os

from dotenv import load_dotenv

from .browser import Browser
from .events import AgentError, AgentStep, Done
from .holo import HoloClient
from .loop import WebAgent


async def run(args):
    async def ask(question):
        return await asyncio.to_thread(input, question + " ")

    client = HoloClient(os.getenv("H_API_KEY", ""), args.model)
    async with Browser(headless=args.headless, profile_dir=args.profile_dir) as browser:
        async for event in WebAgent(client, browser, ask).run(args.goal, args.url):
            if isinstance(event, AgentStep):
                print(event.narration, flush=True)
            elif isinstance(event, Done):
                print(event.result, flush=True)
            elif isinstance(event, AgentError):
                print(event.reason, event.suggestion, flush=True)
                return 1
    return 0


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Brainy's controlled H Company web agent (no microphone).")
    parser.add_argument("goal")
    parser.add_argument("--url")
    parser.add_argument("--model", default=os.getenv("H_MODEL") or "holo3-1-35b-a3b")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--profile-dir", help="Optional persistent browser profile; contains private browsing data.")
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("Unable to start. Check H_API_KEY, dependencies and Chromium installation.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
