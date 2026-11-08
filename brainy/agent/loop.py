import hashlib
import re
import asyncio

from playwright.async_api import Error

from .events import AgentError, AgentStep, ConfirmRequest, Done, NeedsUser
from .debug import debug_log
from .browser import SECRET_QUESTION, SecretFieldError, normalize_choice


RISKY = re.compile(r"pay|payer|submit|envoyer|valider|book|réserver|confirm|acheter|order|commander", re.I)
DIRECT_CHOICE_BUDGET = 3


class WebAgent:
    def __init__(self, client, browser, ask, max_steps=25, debug=False, choices=None, pending_actions=None):
        self.client = client
        self.browser = browser
        self.ask = ask
        self.max_steps = max_steps
        self.debug = debug
        self.pending_actions = (list(pending_actions) if pending_actions is not None else
                                [("choose", text) for text in choices or []])

    async def _locate(self, screenshot, target):
        if self.debug:
            debug_log("Thinking (Holo grounding)...")
        return await self.client.locate(screenshot, target, self.browser.viewport)

    async def run(self, goal, start_url=None):
        history = []
        queue = self.pending_actions.copy()
        pending = None
        unavailable_choice = None
        last_key = None
        unchanged_count = 0
        step = "navigate"
        try:
            await self.browser.start_run()
            if start_url:
                await self.browser.goto(start_url)
            for _ in range(self.max_steps):
                history.extend(await self.browser.take_recovery_notes())
                if queue and queue[0][0] == "fill":
                    _, field, text = queue[0]
                    step = "type"
                    try:
                        element = await asyncio.wait_for(self.browser.find_fill(field), timeout=3)
                        value = await asyncio.wait_for(self.browser.fill_field(element, text), timeout=5) if element is not None else None
                    except SecretFieldError:
                        warning = "Skipped secret-like fill field; complete it manually."
                        yield AgentStep(warning, "fill")
                        history.append(warning)
                        queue.pop(0)
                        continue
                    except (Error, asyncio.TimeoutError):
                        value = None
                        history.append("Direct fill unavailable during page loading; inspect the current page.")
                    if value is not None:
                        yield AgentStep(f"Typing {text}.", "type")
                        history.append(f"Filled {field!r} directly; field now contains {value!r}. "
                                       "Choose a matching autocomplete suggestion before searching.")
                        queue.pop(0)
                        pending = last_key = None
                        unchanged_count = 0
                        continue
                if (queue and queue[0][0] == "choose" and not RISKY.search(queue[0][1]) and
                        unavailable_choice != queue[0]):
                    step = "select_text"
                    selected = False
                    deadline = asyncio.get_running_loop().time() + DIRECT_CHOICE_BUDGET
                    for text in queue[0][1].split("|"):
                        remaining = deadline - asyncio.get_running_loop().time()
                        if remaining <= 0:
                            break
                        try:
                            element = await asyncio.wait_for(self.browser.find_choice(text.strip()), timeout=remaining)
                        except (Error, asyncio.TimeoutError):
                            element = None
                        if element is not None:
                            try:
                                result = await asyncio.wait_for(self.browser.select_choice(element, text.strip()), timeout=5)
                            except (Error, asyncio.TimeoutError):
                                result = None
                            if result is not None:
                                yield AgentStep(f"Selecting {text.strip()}.", "select_text")
                                history.extend([f"Selected {text.strip()} directly", result])
                                queue.pop(0)
                                unavailable_choice = None
                                pending = last_key = None
                                unchanged_count = 0
                                selected = True
                                break
                    if selected:
                        continue
                    unavailable_choice = queue[0]
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
                step = "model call"
                if self.debug:
                    debug_log("Thinking (Holo)...")
                action = await self.client.decide(screenshot, goal, history, page_context=page_context)
                if self.debug:
                    debug_log(f"Holo action: {action.action}")
                target = action.text if action.action == "select_text" else action.target
                key = (action.action, " ".join(target.casefold().split()))
                yield AgentStep(action.narration, action.action)
                if action.action == "done":
                    yield Done(action.text or action.narration)
                    return
                question = None
                if key == last_key and unchanged_count >= 2 and action.action != "scroll":
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
                        x, y = await self._locate(screenshot, action.text)
                        step = "click"
                        await self.browser.click(x, y)
                        result = f"Clicked {action.text!r} using grounding; inspect next screenshot for selection state."
                    history.append(result)
                    for index, item in enumerate(queue):
                        if item[0] == "choose" and any(normalize_choice(choice) == normalize_choice(action.text)
                                                       for choice in item[1].split("|")):
                            queue.pop(index)
                            break
                elif action.action in {"click", "confirm", "type"}:
                    step = "model call"
                    x, y = await self._locate(screenshot, action.target)
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
                            x, y = await self._locate(screenshot, action.target)
                            step = "click"
                            await self.browser.click(x, y)
                            step = "type"
                            value = await self.browser.type(action.text)
                        if value is None:
                            history.append("Typing retry missed the field; no text entered. Re-locate the editable field.")
                            continue
                        history.append(("Field now contains " + repr(value) if value else "Field empty") +
                                       ". If a suggestion list appeared, click the matching suggestion before searching.")
                        if queue and queue[0][0] == "fill" and normalize_choice(queue[0][2]) == normalize_choice(action.text):
                            queue.pop(0)
                elif action.action == "scroll":
                    step = "scroll"
                    result = await self.browser.scroll(action.text)
                    if isinstance(result, str):
                        history.append(result)
                unavailable_choice = None
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
