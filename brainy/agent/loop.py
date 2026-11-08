import hashlib
import os
import re
import sys
import time
from urllib.parse import urlsplit

from .events import AgentError, AgentStep, ConfirmRequest, Done, NeedsUser
from .debug import debug_log


RISKY = re.compile(r"pay|payer|submit|envoyer|valider|book|réserver|confirm|acheter|order|commander", re.I)
WRAP_UP = ("Search budget used up: stop searching now. Use ask_user to propose the best option seen so far "
           "(say which constraint it does not meet, if any), or say nothing suitable was found and offer to keep looking. "
           "If you are already completing a booking that matches the request, ignore this and continue.")
OUT_OF_BUDGET = "This is taking longer than expected. Should I keep going, or stop here?"
SECRET_QUESTION = re.compile(r"\b(?:password|mot\s+de\s+passe|card|carte|cvv|cvc|code|pin|iban|otp|sms)\b", re.I)
HUMAN_CHECK = re.compile(r"captcha|cloudflare|verify you are human|je suis humain|vérifiez que vous|"
                         r"not a robot|pas un robot", re.I)
WEEKDAY = re.compile(r"\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|"
                     r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
DATE = re.compile(r"\b(\d{1,2})(?:er)?\.?\s+(janv|févr|fevr|mars|avr|mai|juin|juil|août|aout|sept|oct|nov|déc|dec|"
                  r"jan|feb|mar|apr|may|jun|jul|aug|sep|dec)", re.I)
FORCED_SCROLL = "Brainy scrolled down instead so that other options are visible."
# Accessible name of the element under a click: Doctolib slot buttons only show "11:15" but are
# labelled by their date, so this tells two "11:15" slots on different days apart.
ELEMENT_NAME = """([x, y]) => {
  const hit = document.elementFromPoint(x, y);
  const el = hit && (hit.closest('button, a, [role="button"], [role="radio"], [role="option"], input, select, textarea, label') || hit);
  if (!el || el.type === 'password') return '';
  const clean = s => (s || '').replace(/\\s+/g, ' ').trim();
  const ids = (el.getAttribute('aria-labelledby') || '').split(/\\s+/).filter(Boolean);
  let name = clean([...new Set(ids)].map(id => document.getElementById(id)?.innerText || '').join(' '));
  if (!name && /^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName))
    name = clean(el.getAttribute('aria-label') || el.placeholder || el.name || el.id);
  if (!name) name = clean(el.getAttribute('aria-label') || el.innerText || el.value || el.title);
  const card = el.closest('article, li, [class*="card"], [class*="Card"]');
  const head = card && card !== el ? clean(card.querySelector('h1, h2, h3, h4')?.innerText) : '';
  return (head && !name.includes(head) ? name + ' | ' + head : name).slice(0, 160);
}"""


def _url_key(url):
    parts = urlsplit(url or "")
    route = parts.fragment if parts.fragment.startswith(("/", "!/")) else ""
    return parts._replace(fragment=route, path=parts.path.rstrip("/") or "/").geturl()


def _short(url):
    parts = urlsplit(url)
    return (parts.path + ("?" + parts.query if parts.query else "") +
            ("#" + parts.fragment if parts.fragment else ""))[:100]


def _fold(text):
    return " ".join(str(text).casefold().split())


HUMAN_CHECK_QUESTION = ("Le site affiche une vérification « humain » (captcha). Je ne la passe pas à ta place : "
                        "fais-la dans la fenêtre du navigateur et dis-moi quand c'est bon.")


def _days(text):
    text = text.casefold()
    return set(WEEKDAY.findall(text)), {(int(d), m[:3]) for d, m in DATE.findall(text)}


def _other_day(target, name):
    """The model asked for a slot on one day but the element under the click is labelled with another."""
    (wanted, wanted_dates), (found, found_dates) = _days(target), _days(name)
    return bool(wanted and found and not wanted & found) or bool(
        wanted_dates and found_dates and not wanted_dates & found_dates)


class TaskMemory:
    """What this task already did: pages visited, navigations, and the outcome of each click per page."""

    def __init__(self):
        self.visited = []
        self.navigations = {}
        self.aliases = {}
        self.clicks = {}
        self.labels = {}
        self.order = []

    def visit(self, url):
        if url not in self.visited:
            self.visited.append(url)

    def same_page(self, url, target):
        return target in {url, self.aliases.get(url)}

    def record(self, element, label, outcome):
        self.clicks.setdefault(element, []).append(outcome)
        self.labels[element] = label
        if element in self.order:
            self.order.remove(element)
        self.order.append(element)

    def forget(self, element):
        self.clicks.pop(element, None)
        self.labels.pop(element, None)
        if element in self.order:
            self.order.remove(element)

    def forget_no_effect(self, url):
        """A form field changed: clicks that did nothing on this page (e.g. Search) may work now."""
        for element in [e for e in self.order if e[0] == url and self.clicks[e][-1][0] == "none"]:
            self.forget(element)

    def no_effect_count(self, element):
        return sum(o[0] == "none" for o in self.clicks.get(element, []))

    def led_to(self, element):
        return next((o[1] for o in reversed(self.clicks.get(element, [])) if o[0] == "moved"), None)

    def prompt(self, url):
        lines = []
        for element in sorted(self.order[-12:], key=lambda e: e[0] != url):
            page, _ = element
            outcome = self.clicks[element][-1]
            result = {"moved": lambda: "opened " + _short(outcome[1]), "none": lambda: "had no effect",
                      "changed": lambda: "updated the page"}[outcome[0]]()
            where = "this page" if page == url else _short(page)
            label = " ".join(self.labels[element].split())[:80].replace("'", "’")
            lines.append(f"on {where}: clicked '{label}' -> {result}")
        if len(self.visited) > 1:
            lines.append("pages already visited: " + ", ".join(_short(u) for u in self.visited[-6:]))
        if not lines:
            return ""
        return ("\nAlready tried in this task (do not repeat a click that led somewhere you came back from or "
                "had no effect; choose another element, slot or option):\n- " + "\n- ".join(lines))


class Laps:
    """Per-phase timings on stderr when BRAINY_TIMING is set."""

    def __init__(self):
        self.on = bool(os.getenv("BRAINY_TIMING"))
        self.last = time.monotonic()

    def __call__(self, label):
        now = time.monotonic()
        if self.on:
            print(f"[timing] {label}: {now - self.last:.2f}s", file=sys.stderr, flush=True)
        self.last = now


class WebAgent:
    def __init__(self, client, browser, ask, max_steps=25, debug=False,
                 wrap_up_steps=None, wrap_up_seconds=None, wrap_up_grace=6, gate_narration=True,
                 prefill=None):
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
        self.prefill = prefill

    def _needs_confirmation(self, action):
        if not self.gate_narration:
            # Clicks are gated after locating, on the clicked element's own label (see _label_is_risky).
            return action.action == "confirm"
        return action.action == "confirm" or (
            action.action == "click" and RISKY.search(action.target + " " + action.narration))

    @staticmethod
    def _label_is_risky(action, label):
        """Gate on the text of the element under the click: "Continuer" is not risky, "Confirmer le RDV" is.
        The model's target description ("Continuer to confirm the time") is only a fallback."""
        return bool(RISKY.search(label or action.target))

    async def _element(self, x, y):
        """(visible label, accessible name) of the element under the click; empty strings when unknown."""
        try:
            label = await self.browser.label_at(x, y)
        except Exception:
            label = ""
        try:
            name = await (await self.browser.ensure_page()).evaluate(ELEMENT_NAME, [x, y])
        except Exception:
            name = ""
        return (label.strip() if isinstance(label, str) else "", name.strip() if isinstance(name, str) else "")

    def _over_budget(self, steps, started):
        return ((self.wrap_up_steps is not None and steps >= self.wrap_up_steps) or
                (self.wrap_up_seconds is not None and time.monotonic() - started >= self.wrap_up_seconds))

    async def run(self, goal, start_url=None):
        history = []
        memory = TaskMemory()
        pending = None
        blocks, relented = {}, set()
        step = "navigate"
        budget_steps, budget_start, nudged_at = 0, time.monotonic(), None
        facts, recent = [], []
        lap = Laps()

        def block(reason, note):
            """Refuse a repeated action. Every second refusal also scrolls, so the model sees other options."""
            blocks[reason] = blocks.get(reason, 0) + 1
            history.append("BLOCKED, not executed: " + note)
            return blocks[reason] % 2 == 0

        try:
            await self.browser.start_run()
            if start_url:
                await self.browser.goto(start_url)
                pending = ("navigate", _url_key(start_url), "", None, None)
            for _ in range(self.max_steps):
                lap("between steps")
                if self.prefill:
                    step = "prefill"
                    try:
                        history.extend(await self.prefill(await self.browser.ensure_page()))
                    except Exception:
                        pass
                    lap("prefill")
                step = "screenshot"
                screenshot = await self.browser.screenshot()
                lap("screenshot")
                step = "page context"
                page_context = await self.browser.page_context()
                lap("page context")
                url = _url_key(page_context["url"])
                # Screenshots differ after almost any click (hover, focus ring); URL and page text tell real effects.
                text_hash = hashlib.sha256(str(page_context.get("text", "")).encode()).digest()
                memory.visit(url)
                history.extend(await self.browser.take_recovery_notes())
                if pending:
                    kind, element, label, before_url, before_hash = pending
                    pending = None
                    if kind == "navigate":
                        if url != element:
                            memory.aliases[url] = element
                    elif url != before_url:
                        memory.record(element, label, ("moved", url))
                    elif text_hash == before_hash:
                        memory.record(element, label, ("none",))
                        if memory.no_effect_count(element) >= 2:
                            history.append(f"Your last click on '{label}' had no visible effect; do not repeat it, "
                                           "try a different approach (e.g. results may already be shown, scroll, "
                                           "choose a suggestion first, or ask the user).")
                        else:
                            history.append(f"After your click on '{label}' neither the URL nor the page text changed: "
                                           "check the screenshot; if nothing was selected or opened, it had no effect.")
                    else:
                        memory.record(element, label, ("changed",))
                if nudged_at is None and self._over_budget(budget_steps, budget_start):
                    history.append(WRAP_UP)
                    nudged_at = budget_steps
                budget_steps += 1
                step = "model call"
                known = ("\nThe user already answered (settled, never ask again):\n- " + "\n- ".join(facts)) if facts else ""
                action = await self.client.decide(screenshot, goal + known + memory.prompt(url), history,
                                                  page_context=page_context)
                lap(f"decide ({action.action})")
                key = (action.action, _fold(action.target))
                recent = (recent + [key])[-6:]
                if action.action in {"click", "type"} and recent.count(key) >= 3:
                    history.append(f"You already tried {action.action} on '{action.target}' {recent.count(key)} times "
                                   "recently without progress: stop doing it and continue with what is visible.")
                yield AgentStep(action.narration, action.action)
                question = None
                if action.action == "done":
                    result = action.text or action.narration
                    if "?" not in result:
                        yield Done(result)
                        return
                    question = result
                if action.action == "ask_user":
                    question = action.text or action.narration
                elif action.action in {"click", "confirm", "type"} and HUMAN_CHECK.search(action.target):
                    question = HUMAN_CHECK_QUESTION
                elif question is None and nudged_at is not None and budget_steps - nudged_at > self.wrap_up_grace:
                    question = OUT_OF_BUDGET
                stuck = None
                if action.action in {"click", "confirm"} and question is None:
                    step = "model call"
                    x, y = await self.client.locate(screenshot, action.target, self.browser.viewport)
                    lap("locate")
                    label, name = await self._element(x, y)
                    element = (url, _fold(name or label or action.target))
                    shown = name or label or action.target
                    led_to = memory.led_to(element)
                    if _other_day(action.target, name):
                        # Grounding picked the neighbouring day column; clicking it starts a wrong-day booking.
                        history.append(f"BLOCKED, not executed: the element at that position is '{name}', not "
                                       f"'{action.target}'. Describe the wanted element more precisely (e.g. the "
                                       "slot in the column under its day header) or scroll.")
                        continue
                    if memory.no_effect_count(element) >= 2:
                        if blocks.get(("none", element), 0) >= 2:
                            stuck = shown
                            question = (f"I'm stuck: repeating '{action.target}' has no visible effect. "
                                        "Should I try a different approach, or can you do it manually and reply ok?")
                        else:
                            if block(("none", element), f"'{shown}' was already clicked twice on this page with no "
                                     "effect (it may be disabled or need another field first). Do something else."):
                                await self.browser.scroll("down")
                                history.append(FORCED_SCROLL)
                            continue
                    elif led_to and not memory.same_page(led_to, url):
                        # Insisting twice gets the click through once; a cycle never gets a second pass.
                        if blocks.get(("moved", element), 0) < 2 or element in relented:
                            if block(("moved", element), f"'{shown}' was already clicked on this page earlier in "
                                     f"this task: it opened {_short(led_to)} and you came back. Clicking it again "
                                     "repeats the same path. Choose a different slot, practitioner or option, or "
                                     "fix the choice on the next page instead of coming back."):
                                await self.browser.scroll("down")
                                history.append(FORCED_SCROLL)
                            continue
                        relented.add(element)
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
                        if action.action in {"ask_user", "done"}:
                            facts.append(f"{question} -> {answer}")
                    if stuck is not None:
                        blocks.pop(("none", element), None)
                        memory.forget(element)
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
                    target = _url_key(action.url)
                    if memory.same_page(url, target):
                        history.append(f"BLOCKED, not executed: you are already on {_short(target)}; reloading it "
                                       "changes nothing. Use what is shown: scroll, or click a result.")
                        continue
                    if memory.navigations.get(target, 0) >= 1:
                        if blocks.get(("navigate", target), 0) < 2:
                            if block(("navigate", target), f"you already went to {_short(target)} earlier in this "
                                     "task; going back there repeats work already done. Continue from the current "
                                     "page."):
                                await self.browser.scroll("down")
                                history.append(FORCED_SCROLL)
                            continue
                        blocks.pop(("navigate", target))
                    step = "navigate"
                    memory.navigations[target] = memory.navigations.get(target, 0) + 1
                    await self.browser.goto(action.url)
                    lap("navigate")
                    pending = ("navigate", target, "", url, text_hash)
                elif action.action in {"click", "confirm"}:
                    if not self.gate_narration and action.action == "click" and self._label_is_risky(action, label):
                        summary = action.narration or action.target
                        yield ConfirmRequest(summary)
                        step = "confirmation"
                        if (await self.ask(summary + " Proceed? (yes/oui or no/non)")).strip().casefold() not in {"yes", "oui"}:
                            yield Done("Action skipped: confirmation refused. Nothing was submitted.")
                            return
                        budget_steps, budget_start, nudged_at = 0, time.monotonic(), None
                    step = "click"
                    await self.browser.click(x, y)
                    lap("click")
                    pending = ("click", element, shown, url, text_hash)
                elif action.action == "type":
                    step = "model call"
                    x, y = await self.client.locate(screenshot, action.target, self.browser.viewport)
                    lap("locate")
                    step = "click"
                    await self.browser.click(x, y)
                    lap("click")
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
                    memory.forget_no_effect(url)
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
