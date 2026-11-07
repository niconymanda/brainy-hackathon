"""Speak a task, then hand its prompt to the local web agent: python -m brainy."""

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

from .agent import __main__ as agent
from .stt import __main__ as stt


async def run(args):
    for name in ("GLADIA_API_KEY", "H_API_KEY"):
        if not os.getenv(name, "").strip():
            print(f"Error: Set {name} in the environment or .env file.", file=sys.stderr)
            return 1
    args.h_prompt = True
    if args.device and args.device.isdecimal():
        args.device = int(args.device)
    try:
        prompt = await stt.run(args)
    except Exception as exc:
        print(f"Error: {stt.error_message(exc)}", file=sys.stderr)
        return 1
    if isinstance(prompt, int):
        return prompt
    try:
        return await agent.run_goal(prompt, args)
    except Exception as exc:
        agent.startup_error(exc, args)
        return 1


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Speak a task with Gladia, then run Brainy's local H web agent.")
    stt.add_audio_arguments(parser, summary_default="bullet_points")
    agent.add_agent_arguments(parser)
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
