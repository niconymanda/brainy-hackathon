import hashlib
import re

from .events import AgentError, AgentStep, ConfirmRequest, Done, NeedsUser
from .debug import debug_log
from .browser import normalize_choice


RISKY = re.compile(r"pay|payer|submit|envoyer|valider|book|réserver|confirm|acheter|order|commander", re.I)
SECRET_QUESTION = re.compile(r"\b(?:password|mot\s+de\s+passe|card|carte|cvv|cvc|code|pin|iban|otp|sms)\b", re.I)


class WebAgent:
    def __init__(self, client, browser, ask, max_steps=25, debug=False, choices=None):
        self.client = client
        self.browser = browser
        self.ask = ask
        self.max_steps = max_steps
        self.debug = debug
        self.choices = list(choices or [])

    async def run(self, goal, start_url=None):
        history = []
        choices = self.choices.copy()
        pending = None
        last_key = None
        unchanged_count = 0
        step = "navigate"
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
                    if key[0] == "select_text":
                        history.append(f"select_text on '{target}': " +
                                       ("page changed" if before != signature else "no visible page change"))
                    if unchanged_count >= 2:
                        history.append(f"Your last {key[0]} on '{target}' had no visible effect; do not repeat it, "
                                       "try a different approach (e.g. results may already be shown, scroll, "
                                       "choose a suggestion first, or ask the user).")
                if choices and not RISKY.search(choices[0]):
                    text = choices[0]
                    step = "select_text"
                    element = await self.browser.find_choice(text)
                    if element is not None:
                        result = await self.browser.select_choice(element, text)
                        if result is not None:
                            yield AgentStep(f"Selecting {text}.", "select_text")
                            history.extend([f"Selected {text} directly", result])
                            choices.pop(0)
                            pending = (("select_text", " ".join(text.casefold().split())), signature, text)
                            continue
                step = "model call"
                action = await self.client.decide(screenshot, goal, history, page_context=page_context)
                target = action.text if action.action == "select_text" else action.target
                key = (action.action, " ".join(target.casefold().split()))
                yield AgentStep(action.narration, action.action)
                if action.action == "done":
                    yield Done(action.text or action.narration)
                    return
                question = None
                if key == last_key and unchanged_count >= 2:
                    question = (f"I'm stuck: repeating '{target}' has no visible effect. "
                                "Should I try a different approach, or can you do it manually and reply ok?")
                elif action.action == "ask_user":
                    question = action.text or action.narration
                if question is not None:
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
                    last_key = None
                    unchanged_count = 0
                    continue
                if action.action == "confirm" or (
                    action.action in {"click", "select_text"} and RISKY.search(target + " " + action.narration)
                ):
                    summary = action.narration or target
                    question = summary + " Proceed? (yes/oui or no/non)"
                    yield ConfirmRequest(summary)
                    step = "confirmation"
                    if (await self.ask(question)).strip().casefold() not in {"yes", "oui"}:
                        yield Done("Action skipped: confirmation refused. Nothing was submitted.")
                        return
                if action.action == "navigate":
                    step = "navigate"
                    await self.browser.goto(action.url)
                elif action.action == "select_text":
                    step = "select_text"
                    result = await self.browser.select_text(action.text)
                    if result is None:
                        step = "model call"
                        x, y = await self.client.locate(screenshot, action.text, self.browser.viewport)
                        step = "click"
                        await self.browser.click(x, y)
                        result = f"Clicked {action.text!r} using grounding; inspect next screenshot for selection state."
                    history.append(result)
                    for index, choice in enumerate(choices):
                        if normalize_choice(choice) == normalize_choice(action.text):
                            choices.pop(index)
                            break
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
                history.append({"action": action.action, "target": target,
                                "result": "executed; inspect current screenshot to verify"})
                pending = (key, signature, target)
            yield AgentError("The step limit was reached.", "Try a smaller task or continue manually.")
        except Exception as exc:
            if self.debug:
                debug_log(f"{step}: {type(exc).__module__}.{type(exc).__name__}: {exc}",
                          secrets=(getattr(self.client, "api_key", ""),))
            # API/browser exceptions may contain URLs, headers or page data.
            yield AgentError(f"The web agent could not complete {step} ({type(exc).__name__}).",
                             "Check connectivity and H API configuration, or continue manually.")
