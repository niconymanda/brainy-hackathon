"""H Company task handoff from a speech summary and verbatim transcript."""

import asyncio
import json
import math
import os
import sys

from hai_agents import AsyncClient, Client

H_PROMPT_TEMPLATE = """The user wants to perform a task. Here is the summary of what they asked for:

{summary}

Here is what they said, word for word:

{transcript}

Perform this task to complete it.

Rules:
- Use only the details above. If a required detail is missing (for example a date, a departure station, or a passenger name), do not guess. Stop and list the questions to ask the user.
- If no website or app is named, perform a Google Search to identify possibilities. Ask the user if they have a preference.
- Do not complete any purchase, booking, payment, or form submission. Stop on the final confirmation step and report the exact details (price, dates, times, names). Only when the user has given his ok, can you go ahead with the action.
- When you finish, answer with: what you did, the key information you found, and where you stopped.
"""


def build_h_prompt(summary: str, transcript: str = "") -> str:
    return H_PROMPT_TEMPLATE.format(
        summary=summary.strip(), transcript=transcript.strip() or "(not available)",
    )


def _answer(result) -> str:
    if result.error or result.answer is None:
        raise RuntimeError("H returned no answer or reported a failed task.")
    return result.answer if isinstance(result.answer, str) else json.dumps(result.answer, ensure_ascii=False)


def run_h_task(summary: str, transcript: str = "", *, timeout_seconds: float = 600) -> str:
    if not summary.strip():
        raise ValueError("Cannot send an empty task to H.")
    key = os.getenv("H_API_KEY")
    try:
        with (Client(api_key=key) if key else Client()) as client:
            result = client.run_session(
                agent="h/web-surfer-flash", messages=build_h_prompt(summary, transcript),
                timeout_seconds=timeout_seconds, max_time_s=math.ceil(timeout_seconds),
            )
    except Exception:
        raise RuntimeError("H task failed; check H_API_KEY (or HAI_API_KEY), connectivity and agent access.") from None
    return _answer(result)


async def run_h_task_async(summary: str, transcript: str = "", *, timeout_seconds: float = 600) -> str:
    """Keep the session handle so cancellation stops remote work, without a worker thread."""
    if not summary.strip():
        raise ValueError("Cannot send an empty task to H.")
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("H timeout must be a finite positive number of seconds.")
    key = os.getenv("H_API_KEY")
    options = {"timeout": 5, "max_retries": 0}
    if key:
        options["api_key"] = key
    try:
        async with AsyncClient(**options) as client:
            creation = asyncio.create_task(client.start_session(
                agent="h/web-surfer-flash", messages=build_h_prompt(summary, transcript),
                max_time_s=math.ceil(timeout_seconds),
            ))

            async def execute():
                session = await asyncio.shield(creation)
                return await session.wait_for_completion(timeout_seconds=timeout_seconds, wait_for_seconds=1)

            try:
                result = await asyncio.wait_for(execute(), timeout_seconds)
            except BaseException:
                try:
                    session = await asyncio.wait_for(asyncio.shield(creation), timeout=5)
                    await asyncio.wait_for(session.cancel(), timeout=5)
                except Exception:
                    creation.cancel()
                    await asyncio.gather(creation, return_exceptions=True)
                    print("Could not confirm remote H cancellation; its server-side time limit still applies.",
                          file=sys.stderr, flush=True)
                raise
    except asyncio.CancelledError:
        raise
    except asyncio.TimeoutError:
        raise RuntimeError("H task timed out; remote cancellation was attempted.") from None
    except Exception:
        raise RuntimeError("H task failed; check H_API_KEY (or HAI_API_KEY), connectivity and agent access.") from None
    return _answer(result)
