"""H Company task handoff from a speech summary and verbatim transcript."""

H_PROMPT_TEMPLATE = """The user wants to perform a task. Here is the summary of what they asked for:

{summary}

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
