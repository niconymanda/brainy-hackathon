import re

from .events import AgentError, AgentStep, ConfirmRequest, Done, NeedsUser


RISKY = re.compile(r"pay|payer|submit|envoyer|valider|book|réserver|confirm|acheter|order|commander", re.I)


class WebAgent:
    def __init__(self, client, browser, ask, max_steps=25):
        self.client = client
        self.browser = browser
        self.ask = ask
        self.max_steps = max_steps

    async def run(self, goal, start_url=None):
        history = []
        try:
            if start_url:
                await self.browser.goto(start_url)
            for _ in range(self.max_steps):
                screenshot = await self.browser.screenshot()
                action = await self.client.decide(screenshot, goal, history)
                yield AgentStep(action.narration, action.action)
                if action.action == "done":
                    yield Done(action.text or action.narration)
                    return
                if action.action == "ask_user":
                    question = action.text or action.narration
                    yield NeedsUser(question)
                    answer = await self.ask(question)
                    # Answers can contain secrets: never send them back to the model.
                    if answer.strip().casefold() in {"stop", "non", "no"}:
                        yield Done("Stopped at your request.")
                        return
                    history.append("User has completed the requested manual step; inspect the screenshot.")
                    continue
                if action.action == "confirm" or (
                    action.action == "click" and RISKY.search(action.target + " " + action.narration)
                ):
                    summary = action.narration or action.target
                    question = summary + " Proceed? (yes/oui or no/non)"
                    yield ConfirmRequest(summary)
                    if (await self.ask(question)).strip().casefold() not in {"yes", "oui"}:
                        yield Done("Action skipped: confirmation refused. Nothing was submitted.")
                        return
                if action.action == "navigate":
                    await self.browser.goto(action.url)
                elif action.action in {"click", "confirm", "type"}:
                    x, y = await self.client.locate(screenshot, action.target, self.browser.viewport)
                    await self.browser.click(x, y)
                    if action.action == "type":
                        await self.browser.press("ControlOrMeta+A")
                        await self.browser.type(action.text)
                elif action.action == "scroll":
                    await self.browser.scroll(action.text)
                history.append({"action": action.action, "target": action.target,
                                "result": "executed; inspect current screenshot to verify"})
            yield AgentError("The step limit was reached.", "Try a smaller task or continue manually.")
        except Exception:
            # API/browser exceptions may contain URLs, headers or page data.
            yield AgentError("The web agent could not complete this step.",
                             "Check connectivity and H API configuration, or continue manually.")
