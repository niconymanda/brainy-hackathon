import re

from .events import AgentError, AgentStep, ConfirmRequest, Done, NeedsUser
from .debug import debug_log


RISKY = re.compile(r"pay|payer|submit|envoyer|valider|book|réserver|confirm|acheter|order|commander", re.I)
SECRET_QUESTION = re.compile(r"\b(?:password|mot\s+de\s+passe|card|carte|cvv|cvc|code|pin|iban|otp|sms)\b", re.I)


class WebAgent:
    def __init__(self, client, browser, ask, max_steps=25, debug=False):
        self.client = client
        self.browser = browser
        self.ask = ask
        self.max_steps = max_steps
        self.debug = debug

    async def run(self, goal, start_url=None):
        history = []
        step = "navigate"
        try:
            await self.browser.start_run()
            if start_url:
                await self.browser.goto(start_url)
            for _ in range(self.max_steps):
                step = "screenshot"
                screenshot = await self.browser.screenshot()
                history.extend(await self.browser.take_recovery_notes())
                step = "model call"
                action = await self.client.decide(screenshot, goal, history)
                yield AgentStep(action.narration, action.action)
                if action.action == "done":
                    yield Done(action.text or action.narration)
                    return
                if action.action == "ask_user":
                    question = action.text or action.narration
                    yield NeedsUser(question)
                    step = "user answer"
                    answer = await self.ask(question)
                    if answer.strip().casefold() in {"stop", "non", "no"}:
                        yield Done("Stopped at your request.")
                        return
                    if SECRET_QUESTION.search(question):
                        history.append("User has completed the requested manual step; inspect the screenshot.")
                    else:
                        history.append("User answered: " + answer)
                    continue
                if action.action == "confirm" or (
                    action.action == "click" and RISKY.search(action.target + " " + action.narration)
                ):
                    summary = action.narration or action.target
                    question = summary + " Proceed? (yes/oui or no/non)"
                    yield ConfirmRequest(summary)
                    step = "confirmation"
                    if (await self.ask(question)).strip().casefold() not in {"yes", "oui"}:
                        yield Done("Action skipped: confirmation refused. Nothing was submitted.")
                        return
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
            yield AgentError("The step limit was reached.", "Try a smaller task or continue manually.")
        except Exception as exc:
            if self.debug:
                debug_log(f"{step}: {type(exc).__module__}.{type(exc).__name__}: {exc}",
                          secrets=(getattr(self.client, "api_key", ""),))
            # API/browser exceptions may contain URLs, headers or page data.
            yield AgentError(f"The web agent could not complete {step} ({type(exc).__name__}).",
                             "Check connectivity and H API configuration, or continue manually.")
