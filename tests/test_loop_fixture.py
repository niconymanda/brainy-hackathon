"""WebAgent's anti-loop rules against real Chromium on local Doctolib-like pages (skipped without Chromium)."""
import functools
import http.server
import os
import threading
import unittest

from brainy.agent.browser import Browser
from brainy.agent.events import Done
from brainy.agent.holo import Action
from brainy.agent.loop import ELEMENT_NAME, WebAgent

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "loop")


class ScriptedModel:
    """Replays the failures seen on doctolib.fr; locate() finds the element by CSS selector, like grounding would."""

    def __init__(self, browser, script):
        self.browser = browser
        self.script = list(script)
        self.goals, self.histories, self.calls = [], [], 0

    async def decide(self, screenshot, goal, history, page_context=None):
        self.calls += 1
        self.goals.append(goal)
        self.histories.append(list(history))
        return self.script.pop(0)[0]

    async def locate(self, screenshot, description, viewport):
        self.calls += 1
        selector = next(selector for action, selector in self.done_script if action.target == description)
        box = await self.browser.page.locator(selector).bounding_box()
        return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


class LoopFixtureTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        handler = functools.partial(Quiet, directory=FIXTURES)
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}/"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    async def asyncSetUp(self):
        self.browser = Browser(headless=True)
        try:
            await self.browser.__aenter__()
        except Exception as exc:
            self.skipTest(f"Chromium unavailable: {type(exc).__name__}")
        self.clicked, self.questions = [], []
        click = self.browser.click

        async def logged_click(x, y):
            self.clicked.append(await self.browser.label_at(x, y))
            await click(x, y)
        self.browser.click = logged_click

    async def asyncTearDown(self):
        await self.browser.__aexit__(None, None, None)

    async def run_script(self, script):
        model = ScriptedModel(self.browser, script)
        model.done_script = list(script)
        agent = WebAgent(model, self.browser, self.ask, max_steps=len(script), gate_narration=False)
        events = [e async for e in agent.run("test", self.base + "results.html")]
        return model, events

    async def ask(self, question):
        self.questions.append(question)
        return "oui"

    async def test_slot_name_includes_its_day_and_practitioner(self):
        await self.browser.goto(self.base + "results.html")
        page = self.browser.page
        names = []
        for selector in ("#slot-a-tue", "#slot-b-mon", "#search"):
            box = await page.locator(selector).bounding_box()
            names.append(await page.evaluate(ELEMENT_NAME, [box["x"] + 5, box["y"] + 5]))
        self.assertEqual(names, ["11:15 mardi 10 novembre | Dr Alice Martin", "11:15 lundi 9 novembre | Dr Bruno Petit",
                                 "Rechercher"])

    async def test_observed_doctolib_loops_are_broken(self):
        tue, mon = Action("click", target="11:15 mardi"), Action("click", target="11:15 lundi")
        search, back = Action("click", target="Rechercher"), Action("click", target="Étape précédente")
        final = Action("click", target="Bouton Confirmer")
        script = [(search, "#search"), (search, "#search"), (search, "#search"),
                  (tue, "#slot-a-tue"), (back, "#back"), (tue, "#slot-a-tue"), (mon, "#slot-b-mon"),
                  (final, "#final"), (final, "#final"), (final, "#final"), (Action("done", text="Login page"), "")]
        model, events = await self.run_script(script)
        self.assertEqual(self.clicked, ["Rechercher", "Rechercher", "11:15", "Étape précédente", "11:15",
                                        "Confirmer le rendez-vous", "Confirmer le rendez-vous"])
        self.assertIn("2026-11-09", self.browser.page.url)
        blocked = [h for h in model.histories[-1] if isinstance(h, str) and h.startswith("BLOCKED")]
        self.assertEqual(len(blocked), 3)
        self.assertIn("'Rechercher' was already clicked twice", blocked[0])
        self.assertIn("'11:15 mardi 10 novembre | Dr Alice Martin' was already clicked", blocked[1])
        self.assertIn("opened /booking.html?slot=2026-11-10", blocked[1])
        self.assertIn("'Confirmer le rendez-vous' was already clicked twice", blocked[2])
        self.assertIn("on this page: clicked 'Confirmer le rendez-vous' -> had no effect", model.goals[-1])
        self.assertEqual(len(self.questions), 2, "the blocked third final click must not ask again")
        self.assertEqual(events[-1], Done("Login page"))
        self.assertLessEqual(model.calls, 2 * len(script))

