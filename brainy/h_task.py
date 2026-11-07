"""H Company task handoff from a speech summary and verbatim transcript."""

import json
import os

from hai_agents import Client

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


def run_h_task(summary: str, transcript: str = "") -> str:
    if not summary.strip():
        raise ValueError("Cannot send an empty task to H.")
    key = os.getenv("H_API_KEY")
    try:
        with (Client(api_key=key) if key else Client()) as client:
            result = client.run_session(
                agent="h/web-surfer-flash", messages=build_h_prompt(summary, transcript),
            )
    except Exception:
        raise RuntimeError("H task failed; check H_API_KEY (or HAI_API_KEY), connectivity and agent access.") from None
    if result.error or result.answer is None:
        raise RuntimeError("H returned no answer or reported a failed task.")
    return result.answer if isinstance(result.answer, str) else json.dumps(result.answer, ensure_ascii=False)
