import hashlib
import re
import time

from .events import AgentError, AgentStep, ConfirmRequest, Done, NeedsUser
from .debug import debug_log


RISKY = re.compile(r"pay|payer|submit|envoyer|valider|book|réserver|confirm|acheter|order|commander", re.I)
WRAP_UP = ("Search budget used up: stop searching now. Use ask_user to propose the best option seen so far "
           "(say which constraint it does not meet, if any), or say nothing suitable was found and offer to keep looking. "
           "If you are already completing a booking that matches the request, ignore this and continue.")
OUT_OF_BUDGET = "This is taking longer than expected. Should I keep going, or stop here?"
SECRET_QUESTION = re.compile(r"\b(?:password|mot\s+de\s+passe|card|carte|cvv|cvc|code|pin|iban|otp|sms)\b", re.I)


class WebAgent:
    def __init__(self, client, browser, ask, max_steps=25, debug=False,
                 wrap_up_steps=None, wrap_up_seconds=None, wrap_up_grace=6, gate_narration=True):
        """wrap_up_*: after this many steps/seconds without user input, tell the model to stop searching
        and propose the best option; if it still has not asked after wrap_up_grace steps, ask the user."""
        self.client = client
        self.browser = browser
        self.ask = ask
        self.max_steps = max_steps
        self.debug = debug
        self.wrap_up_steps = wrap_up_steps
        self.wrap_up_seconds = wrap_up_seconds
        self.wrap_up_grace = wrap_up_grace
        self.gate_narration = gate_narration

    def _needs_confirmation(self, action):
        if not self.gate_narration:
            # Clicks are gated on the element's label only: narrations like "je confirme la sélection" are not risky.
            return action.action == "confirm" or (action.action == "click" and bool(RISKY.search(action.target)))
        return action.action == "confirm" or (
            action.action == "click" and RISKY.search(action.target + " " + action.narration))

    def _over_budget(self, steps, started):
        return ((self.wrap_up_steps is not None and steps >= self.wrap_up_steps) or
                (self.wrap_up_seconds is not None and time.monotonic() - started >= self.wrap_up_seconds))

    async def run(self, goal, start_url=None):
        history = []
        pending = None
        last_key = None
        unchanged_count = 0
        step = "navigate"
        budget_steps, budget_start, nudged_at = 0, time.monotonic(), None
        try:
            await self.browser.start_run()
            if start_url:
                await self.browser.goto(start_url)
            for _ in range(self.max_steps):
                step = "screenshot"
                screenshot = await self.browser.screenshot()
                step = "page context"
                page_context = await self.browser.page_context()
                signature = (page_context["url"], hashlib.sha256(screenshot).digest())
                history.extend(await self.browser.take_recovery_notes())
                if pending:
                    key, before, target = pending
                    if before == signature:
                        unchanged_count = unchanged_count + 1 if key == last_key else 1
                    else:
                        unchanged_count = 0
                    last_key = key
                    pending = None
                    if unchanged_count >= 2:
                        history.append(f"Your last {key[0]} on '{target}' had no visible effect; do not repeat it, "
                                       "try a different approach (e.g. results may already be shown, scroll, "
                                       "choose a suggestion first, or ask the user).")
                if nudged_at is None and self._over_budget(budget_steps, budget_start):
                    history.append(WRAP_UP)
                    nudged_at = budget_steps
                budget_steps += 1
                step = "model call"
                action = await self.client.decide(screenshot, goal, history, page_context=page_context)
                key = (action.action, " ".join(action.target.casefold().split()))
                yield AgentStep(action.narration, action.action)
                if action.action == "done":
                    yield Done(action.text or action.narration)
                    return
                question = None
                if key == last_key and unchanged_count >= 2:
                    question = (f"I'm stuck: repeating '{action.target}' has no visible effect. "
                                "Should I try a different approach, or can you do it manually and reply ok?")
                elif action.action == "ask_user":
                    question = action.text or action.narration
                elif nudged_at is not None and budget_steps - nudged_at > self.wrap_up_grace:
                    question = OUT_OF_BUDGET
                if question is not None:
                    yield NeedsUser(question, after_budget=nudged_at is not None)
                    step = "user answer"
                    answer = await self.ask(question)
                    if answer.strip().casefold() in {"stop", "non", "no"}:
                        yield Done("Stopped at your request.")
                        return
                    if SECRET_QUESTION.search(question):
                        history.append("User has completed the requested manual step; inspect the screenshot.")
                    else:
                        history.append("User answered: " + answer)
                    last_key = None
                    unchanged_count = 0
                    budget_steps, budget_start, nudged_at = 0, time.monotonic(), None
                    continue
                if self._needs_confirmation(action):
                    summary = action.narration or action.target
                    question = summary + " Proceed? (yes/oui or no/non)"
                    yield ConfirmRequest(summary)
                    step = "confirmation"
                    if (await self.ask(question)).strip().casefold() not in {"yes", "oui"}:
                        yield Done("Action skipped: confirmation refused. Nothing was submitted.")
                        return
                    budget_steps, budget_start, nudged_at = 0, time.monotonic(), None
                if action.action == "navigate":
                    step = "navigate"
                    await self.browser.goto(action.url)
                elif action.action in {"click", "confirm", "type"}:
                    step = "model call"
                    x, y = await self.client.locate(screenshot, action.target, self.browser.viewport)
                    step = "click"
                    await self.browser.click(x, y)
                    if action.action == "type":
                        step = "type"
                        value = await self.browser.type(action.text)
                        if value is None:
                            history.append("Typing click missed the field: focused element is not editable; no text entered.")
                            step = "screenshot"
                            screenshot = await self.browser.screenshot()
                            step = "model call"
                            x, y = await self.client.locate(screenshot, action.target, self.browser.viewport)
                            step = "click"
                            await self.browser.click(x, y)
                            step = "type"
                            value = await self.browser.type(action.text)
                        if value is None:
                            history.append("Typing retry missed the field; no text entered. Re-locate the editable field.")
                            continue
                        history.append(("Field now contains " + repr(value) if value else "Field empty") +
                                       ". If a suggestion list appeared, click the matching suggestion before searching.")
                elif action.action == "scroll":
                    step = "scroll"
                    await self.browser.scroll(action.text)
                history.append({"action": action.action, "target": action.target,
                                "result": "executed; inspect current screenshot to verify"})
                pending = (key, signature, action.target)
            yield AgentError("The step limit was reached.", "Try a smaller task or continue manually.")
        except Exception as exc:
            if self.debug:
                debug_log(f"{step}: {type(exc).__module__}.{type(exc).__name__}: {exc}",
                          secrets=(getattr(self.client, "api_key", ""),))
            # API/browser exceptions may contain URLs, headers or page data.
            yield AgentError(f"The web agent could not complete {step} ({type(exc).__name__}).",
                             "Check connectivity and H API configuration, or continue manually.")
