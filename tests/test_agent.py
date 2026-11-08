import unittest
import io
import json
from contextlib import redirect_stderr
from argparse import Namespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from playwright.async_api import Error

from brainy.agent.browser import Browser
from brainy.agent.debug import debug_log
from brainy.agent.__main__ import run
from brainy.agent.events import AgentError, ConfirmRequest, Done, NeedsUser
from brainy.agent.holo import Action, HoloClient, parse_action, parse_click
from brainy.agent.loop import OUT_OF_BUDGET, WRAP_UP, WebAgent


class ParsingTests(unittest.TestCase):
    def test_click_scaling(self):
        self.assertEqual(parse_click("\n\nClick(143, 77)", (1280, 900)), (183.04, 69.3))
        self.assertEqual(parse_click("Click(1000, 1000)", (100, 200)), (99, 199))

    def test_invalid_click(self):
        for value in ("", "Click(-1, 0)", "Click(1001, 1)", "Click(x, y)"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_click(value, (1280, 900))

    def test_action_json(self):
        for wrapper in ("{}", "\n\n{}", "junk ```json\n{}\n``` trailing", "{{bad}} {}"):
            content = wrapper.replace("{}", '{"action":"click","target":"Large radio","narration":"Choose large."}')
            self.assertEqual(parse_action(content).target, "Large radio")

    def test_invalid_action(self):
        for content in ("", "{}", '{"action":"execute"}', '{"action":"click"}',
                        '{"action":"done","text":null}'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_action(content)


class AgentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.browser = AsyncMock()
        self.browser.viewport = (1280, 900)
        self.browser.screenshot.return_value = b"png"
        self.browser.type.return_value = "Test User"
        self.browser.take_recovery_notes.return_value = []
        self.browser.label_at.return_value = ""
        self.browser.page_context.return_value = {"url": "https://example.org/results", "title": "Results",
                                                  "text": "First result: Lyon"}
        self.client = AsyncMock()
        self.client.locate.return_value = (100, 200)
        self.ask = AsyncMock(return_value="non")

    async def collect(self, actions, max_steps=5):
        self.client.decide.side_effect = actions
        return [event async for event in WebAgent(self.client, self.browser, self.ask, max_steps).run("test")]

    async def test_gate_blocks_without_explicit_yes(self):
        for answer in ("non", "", "maybe", "yes please", "no"):
            for target in ("Pay", "Submit order", "Envoyer", "Réserver"):
                self.ask.return_value = answer
                events = await self.collect([Action("click", target=target)])
                self.assertTrue(any(isinstance(e, ConfirmRequest) for e in events))
                self.assertIsInstance(events[-1], Done)
                self.browser.click.assert_not_awaited()

    async def test_gate_allows_oui(self):
        self.ask.return_value = "oui"
        events = await self.collect([Action("click", target="Submit order"), Action("done", text="Submitted")])
        self.browser.click.assert_awaited_once_with(100, 200)
        self.assertEqual(events[-1], Done("Submitted"))

    async def test_label_only_gate_ignores_narration(self):
        self.ask.return_value = "non"
        self.client.decide.side_effect = [
            Action("click", target="Dermatologue", narration="Je confirme la sélection de la catégorie."),
            Action("click", target="Hugo Esposito-Farès", narration="Je réserve pour toi."),
            Action("click", target="Confirmer le rendez-vous", narration="Je finalise."),
        ]
        agent = WebAgent(self.client, self.browser, self.ask, max_steps=5, gate_narration=False)
        events = [event async for event in agent.run("test")]
        self.assertEqual([e.summary for e in events if isinstance(e, ConfirmRequest)], ["Je finalise."])
        self.assertEqual(self.browser.click.await_count, 2)
        self.assertEqual(events[-1], Done("Action skipped: confirmation refused. Nothing was submitted."))

    async def test_gate_reads_clicked_element_label(self):
        self.ask.return_value = "non"
        self.browser.label_at.side_effect = ["Continuer", "Confirmer le rendez-vous"]
        self.client.decide.side_effect = [
            Action("click", target="Continuer button to confirm the time", narration="Je confirme l'heure."),
            Action("click", target="Blue button at the bottom", narration="Je finalise."),
        ]
        agent = WebAgent(self.client, self.browser, self.ask, max_steps=5, gate_narration=False)
        events = [event async for event in agent.run("test")]
        self.assertEqual([e.summary for e in events if isinstance(e, ConfirmRequest)], ["Je finalise."])
        self.assertEqual(self.browser.click.await_count, 1)

    async def test_label_only_gate_keeps_confirm_action(self):
        self.ask.return_value = "non"
        self.client.decide.side_effect = [Action("confirm", target="Continuer", narration="Je termine.")]
        agent = WebAgent(self.client, self.browser, self.ask, max_steps=5, gate_narration=False)
        events = [event async for event in agent.run("test")]
        self.assertTrue(any(isinstance(e, ConfirmRequest) for e in events))
        self.browser.click.assert_not_awaited()

    async def test_confirm_action_and_narration_gate(self):
        for action in (Action("confirm", target="Continue"),
                       Action("click", target="Continue", narration="Confirm booking")):
            events = await self.collect([action])
            self.assertIsInstance(events[-1], Done)
            self.browser.click.assert_not_awaited()

    async def test_max_steps(self):
        events = await self.collect([Action("scroll", text="down")] * 2, max_steps=2)
        self.assertEqual(self.client.decide.await_count, 2)
        self.assertIsInstance(events[-1], AgentError)
        self.assertIn("step limit", events[-1].reason)

    async def run_budget(self, actions, **options):
        self.browser.screenshot.side_effect = (bytes([i]) for i in range(100))
        histories, queue = [], list(actions)
        async def decide(screenshot, goal, history, page_context=None):
            histories.append(list(history))
            return queue.pop(0)
        self.client.decide.side_effect = decide
        agent = WebAgent(self.client, self.browser, self.ask, max_steps=10, **options)
        return [event async for event in agent.run("test")], histories

    async def test_search_budget_nudges_then_asks(self):
        events, histories = await self.run_budget([Action("scroll", text="down")] * 6,
                                                  wrap_up_steps=2, wrap_up_grace=2)
        self.assertNotIn(WRAP_UP, histories[1])
        self.assertIn(WRAP_UP, histories[2])
        self.assertEqual(len(histories), 5)
        self.assertEqual([e.question for e in events if isinstance(e, NeedsUser)], [OUT_OF_BUDGET])
        self.assertEqual(self.browser.scroll.await_count, 4)
        self.assertIsInstance(events[-1], Done)

    async def test_question_after_budget_is_flagged(self):
        self.ask.return_value = "non"
        events, _ = await self.run_budget(
            [Action("scroll", text="down"), Action("ask_user", text="Est-ce que je continue ou pas ?")],
            wrap_up_steps=1, wrap_up_grace=5)
        self.assertEqual([e.after_budget for e in events if isinstance(e, NeedsUser)], [True])

    async def run_goals(self, actions, max_steps=20):
        self.browser.screenshot.side_effect = (bytes([i]) for i in range(100))
        goals, queue = [], list(actions)
        async def decide(screenshot, goal, history, page_context=None):
            goals.append(goal)
            return queue.pop(0)
        self.client.decide.side_effect = decide
        agent = WebAgent(self.client, self.browser, self.ask, max_steps=max_steps)
        return [event async for event in agent.run("test")], goals

    async def test_done_with_question_asks_instead_of_ending(self):
        self.ask.return_value = "Mardi à 13h"
        events, _ = await self.run_goals([Action("done", text="Quel jour et à quelle heure ?"),
                                          Action("done", text="Réservé.")])
        self.assertEqual([e.question for e in events if isinstance(e, NeedsUser)], ["Quel jour et à quelle heure ?"])
        self.assertEqual(events[-1], Done("Réservé."))

    async def test_answers_stay_in_goal(self):
        self.ask.return_value = "Mardi à 13h"
        events, goals = await self.run_goals([Action("ask_user", text="Quel jour ?")]
                                             + [Action("scroll", text="down")] * 10
                                             + [Action("done", text="ok")])
        self.assertNotIn("Mardi", goals[0])
        self.assertIn("Quel jour ? -> Mardi à 13h", goals[-1])
        self.assertEqual(events[-1], Done("ok"))

    async def test_alternating_clicks_are_flagged(self):
        events, histories = await self.run_budget(
            [Action("click", target="Secteur"), Action("click", target="Fermer")] * 3 + [Action("done", text="ok")])
        self.assertFalse(any("already tried" in str(h) for h in histories[4]))
        self.assertTrue(any("already tried click on 'Secteur' 3 times" in str(h) for h in histories[5]))

    async def test_search_budget_resets_after_answer(self):
        self.ask.return_value = "continue"
        events, histories = await self.run_budget(
            [Action("scroll", text="down")] * 2 + [Action("ask_user", text="Mardi ?")]
            + [Action("scroll", text="down")] * 2 + [Action("done", text="ok")],
            wrap_up_seconds=0, wrap_up_grace=5)
        self.assertEqual([h.count(WRAP_UP) for h in histories], [1, 1, 1, 2, 2, 2])
        self.assertIsInstance(events[-1], Done)

    async def test_repeat_warning_after_two_unchanged_actions(self):
        histories = []
        actions = iter([Action("click", target="Rechercher"), Action("click", target="  RECHERCHER "),
                        Action("done")])

        async def decide(screenshot, goal, history, **kwargs):
            histories.append(list(history))
            return next(actions)

        self.client.decide.side_effect = decide
        events = [e async for e in WebAgent(self.client, self.browser, self.ask).run("test")]
        self.assertNotIn("had no visible effect", str(histories[1]))
        self.assertIn("had no visible effect; do not repeat it", str(histories[2]))
        self.assertEqual(self.browser.click.await_count, 2)
        self.assertIsInstance(events[-1], Done)

    async def test_third_unchanged_attempt_is_blocked_then_scrolls_then_asks(self):
        self.ask.return_value = "try scrolling"
        events = await self.collect([Action("click", target="Rechercher")] * 5 + [Action("done")], max_steps=7)
        self.assertEqual(self.browser.click.await_count, 2)
        history = self.client.decide.call_args.args[2]
        self.assertIn("BLOCKED, not executed: 'Rechercher' was already clicked twice", str(history))
        self.browser.scroll.assert_awaited_once_with("down")
        self.assertEqual(sum(isinstance(e, NeedsUser) for e in events), 1)
        self.assertIn("User answered: try scrolling", history)
        self.assertEqual(self.client.locate.await_count, 5)

    async def test_repeat_question_keeps_stop_and_secret_rules(self):
        for target, answer in (("Rechercher", "non"), ("Show PIN", "sensitive answer")):
            with self.subTest(target=target):
                self.setUp()
                self.ask.return_value = answer
                events = await self.collect([Action("click", target=target)] * 5 + [Action("done")], max_steps=7)
                self.assertEqual(self.browser.click.await_count, 2)
                self.assertNotIn("sensitive answer", str(self.client.decide.call_args.args[2]))
                if answer == "non":
                    self.assertEqual(events[-1], Done("Stopped at your request."))
                else:
                    self.assertIn("User has completed the requested manual step", str(self.client.decide.call_args.args[2]))

    async def test_page_change_allows_repeated_actions(self):
        for change in ("url", "text"):
            with self.subTest(change=change):
                self.setUp()
                self.browser.page_context.side_effect = [
                    {"url": f"https://example.org/{i if change == 'url' else 0}", "title": "Results",
                     "text": f"Results {i if change == 'text' else 0}"} for i in range(4)]
                await self.collect([Action("click", target="Next")] * 3 + [Action("done")])
                self.assertEqual(self.browser.click.await_count, 3)
                self.ask.assert_not_awaited()

    async def test_screenshot_noise_is_not_an_effect(self):
        self.browser.screenshot.side_effect = [b"one", b"two", b"three", b"four"]
        await self.collect([Action("click", target="Afficher plus")] * 3 + [Action("done")])
        self.assertEqual(self.browser.click.await_count, 2)
        self.assertIn("BLOCKED", str(self.client.decide.call_args.args[2]))

    def site(self, links, start):
        """Fake site: clicking a label follows links[url][label] (None: no effect); locate returns the label's index."""
        labels = sorted({label for page in links.values() for label in page})
        state = {"url": start}
        self.browser.page_context.side_effect = lambda: {"url": state["url"], "title": "", "text": state["url"]}
        self.client.locate.side_effect = lambda shot, target, viewport: (labels.index(target), 0)
        self.browser.label_at.side_effect = lambda x, y: labels[int(x)]
        clicked = []

        async def click(x, y):
            clicked.append(labels[int(x)])
            state["url"] = links[state["url"]].get(labels[int(x)]) or state["url"]

        async def goto(url):
            state["url"] = links.get("redirects", {}).get(url, url)
        self.browser.click.side_effect = click
        self.browser.goto.side_effect = goto
        return clicked

    async def run_site(self, actions, start=None):
        goals, histories = [], []
        queue = list(actions)

        async def decide(screenshot, goal, history, page_context=None):
            goals.append(goal)
            histories.append(list(history))
            return queue.pop(0)
        self.client.decide.side_effect = decide
        agent = WebAgent(self.client, self.browser, self.ask, max_steps=len(actions))
        events = [e async for e in agent.run("test", start)]
        return events, goals, histories

    RESULTS, BOOKING = "https://d.fr/dermatologue/paris-75009", "https://d.fr/booking?slot=tue"

    async def test_click_that_led_away_is_blocked_after_coming_back(self):
        clicked = self.site({self.RESULTS: {"11:15": self.BOOKING, "11:30": self.BOOKING + "2"},
                             self.BOOKING: {"Étape précédente": self.RESULTS}, self.BOOKING + "2": {}}, self.RESULTS)
        slot, back = Action("click", target="11:15"), Action("click", target="Étape précédente")
        events, goals, histories = await self.run_site(
            [slot, back, slot, Action("click", target="11:30"), Action("done", text="ok")])
        self.assertEqual(clicked, ["11:15", "Étape précédente", "11:30"])
        self.assertIn("BLOCKED, not executed: '11:15' was already clicked on this page earlier in this task: it "
                      "opened /booking?slot=tue and you came back", str(histories[3]))
        self.assertIn("on this page: clicked '11:15' -> opened /booking?slot=tue", goals[2])
        self.assertIn("pages already visited: /dermatologue/paris-75009, /booking?slot=tue", goals[2])
        self.assertLessEqual(self.client.locate.await_count + self.client.decide.await_count, 2 * 5)
        self.assertEqual(events[-1], Done("ok"))

    async def test_cycle_block_scrolls_then_relents_only_once(self):
        clicked = self.site({self.RESULTS: {"11:15": self.BOOKING},
                             self.BOOKING: {"Étape précédente": self.RESULTS}}, self.RESULTS)
        slot, back = Action("click", target="11:15"), Action("click", target="Étape précédente")
        events, goals, histories = await self.run_site(
            [slot, back, slot, slot, slot, back, back, back, slot, slot, Action("done")])
        self.assertEqual(clicked, ["11:15", "Étape précédente", "11:15", "Étape précédente"])
        self.assertEqual(self.browser.scroll.await_count, 3)
        self.assertEqual(str(histories[-1]).count("'11:15' was already clicked"), 4)

    async def test_human_verification_is_left_to_the_user(self):
        clicked = self.site({self.RESULTS: {}}, self.RESULTS)
        self.ask.return_value = "c'est fait"
        events, goals, histories = await self.run_site(
            [Action("click", target="Checkbox 'Verify you are human' (Cloudflare)"), Action("done", text="ok")])
        self.assertEqual(clicked, [])
        self.client.locate.assert_not_awaited()
        self.assertIn("captcha", self.ask.await_args.args[0])

    async def test_click_landing_on_another_day_is_blocked(self):
        clicked = self.site({self.RESULTS: {"11:30": self.BOOKING}}, self.RESULTS)
        page = MagicMock()
        page.evaluate = AsyncMock(side_effect=["11:30 mardi 10 novembre | Dr E", "11:30 lundi 9 novembre | Dr E"])
        self.browser.ensure_page.return_value = page
        self.client.locate.side_effect = None
        self.client.locate.return_value = (0, 0)
        events, goals, histories = await self.run_site(
            [Action("click", target="Créneau du lundi 9 novembre à 11:30"),
             Action("click", target="Créneau 11:30 dans la colonne lundi"), Action("done")])
        self.assertEqual(clicked, ["11:30"])
        self.assertIn("BLOCKED, not executed: the element at that position is '11:30 mardi 10 novembre | Dr E'",
                      str(histories[1]))
        self.assertIn("lundi 9 novembre | Dr E' -> opened /booking?slot=tue", goals[2])

    async def test_cycle_detection_follows_accessible_name_not_visible_text(self):
        clicked = self.site({self.RESULTS: {"11:15": self.BOOKING},
                             self.BOOKING: {"Étape précédente": self.RESULTS}}, self.RESULTS)
        page = MagicMock()
        page.evaluate = AsyncMock(side_effect=["11:15 mardi | Dr A", "Étape précédente", "11:15 lundi | Dr B"])
        self.browser.ensure_page.return_value = page
        slot, back = Action("click", target="11:15"), Action("click", target="Étape précédente")
        events, goals, histories = await self.run_site([slot, back, slot, Action("done")])
        self.assertEqual(clicked, ["11:15", "Étape précédente", "11:15"])
        self.assertIn("clicked '11:15 mardi | Dr A' -> opened /booking?slot=tue", goals[2])

    async def test_navigate_to_current_page_is_blocked(self):
        search = "https://d.fr/search?keyword=dermatologue&location=paris-75009"
        self.site({search: {}, "redirects": {self.RESULTS: search}}, None)
        events, goals, histories = await self.run_site(
            [Action("navigate", url=self.RESULTS), Action("navigate", url=self.RESULTS + "/"),
             Action("navigate", url=search + "#top"), Action("done")], start=self.RESULTS)
        self.assertEqual(self.browser.goto.await_count, 1)
        self.assertEqual(str(histories[1]).count("BLOCKED, not executed: you are already on"), 1)
        self.assertEqual(str(histories[3]).count("BLOCKED, not executed: you are already on"), 3)

    async def test_navigate_back_to_a_visited_page_is_allowed_once(self):
        other, third = "https://d.fr/dermatologue/paris", "https://d.fr/dermatologue/paris-75010"
        self.site({self.RESULTS: {"Autre soignant": other}, other: {}, third: {}}, self.RESULTS)
        home = Action("navigate", url=self.RESULTS)
        events, goals, histories = await self.run_site(
            [Action("click", target="Autre soignant"), home, Action("navigate", url=third), home, home, home,
             Action("done")], start=self.RESULTS)
        self.assertEqual([c.args[0] for c in self.browser.goto.await_args_list],
                         [self.RESULTS, self.RESULTS, third, self.RESULTS])
        self.assertIn("you already went to /dermatologue/paris-75009 earlier", str(histories[4]))
        self.browser.scroll.assert_awaited_once_with("down")

    async def test_no_effect_note_then_block_counts_rewordings(self):
        clicked = self.site({self.RESULTS: {"Rechercher": None}}, self.RESULTS)
        page = MagicMock()
        page.evaluate = AsyncMock(return_value="Rechercher")
        self.browser.ensure_page.return_value = page
        self.client.locate.side_effect = None
        self.client.locate.return_value = (0, 0)
        events, goals, histories = await self.run_site(
            [Action("click", target="Rechercher"), Action("click", target="Bouton Rechercher bleu"),
             Action("click", target="Search button"), Action("done")])
        self.assertEqual(clicked, ["Rechercher", "Rechercher"])
        self.assertIn("neither the URL nor the page text changed", str(histories[1]))
        self.assertIn("had no visible effect; do not repeat it", str(histories[2]))
        self.assertIn("on this page: clicked 'Rechercher' -> had no effect", goals[2])
        self.assertIn("BLOCKED", str(histories[3]))

    async def test_page_context_forwarded_to_decide(self):
        await self.collect([Action("done")])
        self.assertEqual(self.client.decide.call_args.kwargs["page_context"], self.browser.page_context.return_value)

    async def test_empty_budget(self):
        events = await self.collect([], max_steps=0)
        self.assertIsInstance(events[-1], AgentError)
        self.client.decide.assert_not_awaited()

    async def test_api_and_browser_errors_are_safe(self):
        self.client.decide.side_effect = RuntimeError("secret transport data")
        events = [e async for e in WebAgent(self.client, self.browser, self.ask).run("test")]
        self.assertIsInstance(events[-1], AgentError)
        self.assertNotIn("secret", str(events))
        self.browser.goto.side_effect = RuntimeError("secret URL")
        events = [e async for e in WebAgent(self.client, self.browser, self.ask).run("test", "https://example.org")]
        self.assertIsInstance(events[-1], AgentError)
        self.assertNotIn("secret", str(events))

    async def test_error_categories(self):
        cases = (("screenshot", "screenshot", None),
                 ("decide", "model call", None),
                 ("locate", "model call", Action("click", target="Link")),
                 ("click", "click", Action("click", target="Link")),
                 ("type", "type", Action("type", target="Name", text="Test")),
                 ("goto", "navigate", Action("navigate", url="https://example.org")))
        for method, category, action in cases:
            with self.subTest(method=method):
                self.setUp()
                owner = self.client if method in {"decide", "locate"} else self.browser
                getattr(owner, method).side_effect = ValueError("secret URL headers page content")
                if method != "decide":
                    self.client.decide.return_value = action or Action("done")
                events = [e async for e in WebAgent(self.client, self.browser, self.ask).run("test")]
                self.assertEqual(events[-1].reason, f"The web agent could not complete {category} (ValueError).")
                self.assertNotIn("secret", str(events))

    async def test_type_and_user_manual_step(self):
        self.ask.return_value = "private answer"
        events = await self.collect([Action("type", target="Name", text="Test User"),
                                     Action("ask_user", text="Enter your password manually"), Action("done")])
        self.browser.type.assert_awaited_once_with("Test User")
        self.browser.press.assert_not_awaited()
        self.assertTrue(any(isinstance(e, NeedsUser) for e in events))
        self.assertNotIn("private answer", str(self.client.decide.call_args))

    async def test_recovery_note_reaches_model(self):
        self.browser.take_recovery_notes.return_value = ["Tab reopened; inspect current state."]
        await self.collect([Action("done")])
        self.assertIn("Tab reopened", str(self.client.decide.call_args.args[2]))

    async def test_debug_exception_is_local_and_opt_in(self):
        for debug in (False, True):
            with self.subTest(debug=debug):
                self.client.api_key = "private-api-key"
                self.client.decide.side_effect = ValueError("broken response private-api-key")
                output = io.StringIO()
                with redirect_stderr(output):
                    events = [e async for e in WebAgent(self.client, self.browser, self.ask, debug=debug).run("test")]
                self.assertNotIn("private-api-key", output.getvalue())
                self.assertNotIn("broken response", events[-1].reason)
                if debug:
                    self.assertIn("builtins.ValueError: broken response [redacted]", output.getvalue())
                else:
                    self.assertEqual(output.getvalue(), "")

    async def test_type_missed_field(self):
        self.browser.type.return_value = None
        await self.collect([Action("type", target="Search", text="Lyon"), Action("done")])
        self.assertEqual(self.client.locate.await_count, 2)
        history = self.client.decide.call_args.args[2]
        self.assertIn("not editable", history[0])
        self.assertIn("retry missed", history[1])
        self.assertNotIn("executed", str(history))

    async def test_type_retry_and_readback(self):
        self.browser.type.side_effect = [None, "Lyon"]
        await self.collect([Action("type", target="Search", text="Lyon"), Action("done")])
        history = self.client.decide.call_args.args[2]
        self.assertIn("Field now contains 'Lyon'", history[1])
        self.assertIn("click the matching suggestion", history[1])

    async def test_type_empty_readback(self):
        self.browser.type.return_value = ""
        await self.collect([Action("type", target="Search", text="Lyon"), Action("done")])
        self.assertIn("Field empty", self.client.decide.call_args.args[2][0])

    async def test_follow_up_answer_forwarded(self):
        for answer in ("8:10", ""):
            with self.subTest(answer=answer):
                self.ask.return_value = answer
                await self.collect([Action("ask_user", text="Which train: 7:04 or 8:10?"), Action("done")])
                self.assertIn("User answered: " + answer, self.client.decide.call_args.args[2])

    async def test_secret_answers_not_forwarded(self):
        for question in ("Password?", "Votre mot de passe ?", "Card number?", "Numéro de carte ?",
                         "CVV?", "CVC?", "Security code?", "PIN?", "IBAN?", "OTP?", "SMS code?"):
            with self.subTest(question=question):
                self.ask.return_value = "sensitive answer"
                await self.collect([Action("ask_user", text=question), Action("done")])
                history = self.client.decide.call_args.args[2]
                self.assertEqual(history, ["User has completed the requested manual step; inspect the screenshot."])
                self.assertNotIn("sensitive answer", str(history))

    async def test_follow_up_stop_answers(self):
        for answer in ("stop", "non", "no", " NO "):
            with self.subTest(answer=answer):
                self.ask.return_value = answer
                self.client.decide.reset_mock()
                events = await self.collect([Action("ask_user", text="Which train?"), Action("done")])
                self.assertEqual(events[-1], Done("Stopped at your request."))
                self.assertEqual(self.client.decide.await_count, 1)


class HTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_page_context_in_prompt(self):
        client = HoloClient("test-key")
        client._chat = AsyncMock(return_value='{"action":"done"}')
        context = {"url": "https://example.org/results", "title": "Search results", "text": "First result: Lyon"}
        await client.decide(b"png", "search", [], page_context=context)
        prompt = client._chat.call_args.args[1]
        self.assertIn(json.dumps(context), prompt)
        self.assertIn("current sub-step is already satisfied", prompt)
    async def test_malformed_action_retried(self):
        client = HoloClient("test-key")
        client._chat = AsyncMock(side_effect=['{"action":"type"}',
                                             '{"action":"type","target":"Name","text":"Test"}'])
        self.assertEqual((await client.decide(b"png", "test", [])).target, "Name")
        self.assertEqual(client._chat.await_count, 2)

    async def test_invalid_action_retry_exhausted(self):
        client = HoloClient("test-key")
        client._chat = AsyncMock(return_value="")
        with self.assertRaises(ValueError):
            await client.decide(b"png", "test", [])
        self.assertEqual(client._chat.await_count, 2)

    async def test_http_contract(self):
        requests = []

        def respond(request):
            requests.append(request)
            content = '\n\n{"action":"done","text":"Finished"}' if len(requests) == 1 else "Click(500, 250)"
            return httpx.Response(200, json={"choices": [{"message": {"content": content, "reasoning": "ignored"}}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            client = HoloClient("test-key", http=http)
            self.assertEqual((await client.decide(b"png", "test", [])).text, "Finished")
            self.assertEqual(await client.locate(b"png", "Name", (1000, 800)), (500, 200))
        self.assertEqual(requests[0].headers["authorization"], "Bearer test-key")
        self.assertIn(b"data:image/png;base64,", requests[0].content)
        self.assertIn(b"Localize an element on the GUI image", requests[1].content)

    async def test_http_retries_busy_api(self):
        codes = iter([503, 429, 200])

        def respond(_):
            code = next(codes)
            return httpx.Response(code, json={"choices": [{"message": {"content": '{"action":"done"}'}}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            with patch("brainy.agent.holo.asyncio.sleep", AsyncMock()):
                self.assertEqual((await HoloClient("test-key", http=http).decide(b"png", "test", [])).action, "done")

    async def test_http_waits_out_rate_limit(self):
        codes = iter([429, 429, 429, 429, 200])

        def respond(_):
            return httpx.Response(next(codes), json={"choices": [{"message": {"content": '{"action":"done"}'}}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            with patch("brainy.agent.holo.asyncio.sleep", AsyncMock()):
                self.assertEqual((await HoloClient("test-key", http=http).decide(b"png", "test", [])).action, "done")

    async def test_throttle_stays_under_rpm(self):
        clock = [0.0]

        async def sleep(seconds):
            clock[0] += seconds

        client = HoloClient("test-key")
        client.rpm = 2
        with patch("brainy.agent.holo.time.monotonic", lambda: clock[0]), \
                patch("brainy.agent.holo.asyncio.sleep", sleep):
            for _ in range(3):
                await client._throttle()
        self.assertGreaterEqual(clock[0], 60)

    async def test_locate_retries_empty_content_with_thinking(self):
        replies = iter([None, "Click(500, 250)"])

        def respond(_):
            return httpx.Response(200, json={"choices": [{"message": {"content": next(replies)}}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            self.assertEqual(await HoloClient("test-key", http=http).locate(b"png", "OK", (1000, 800)), (500, 200))

    async def test_http_error(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(401))) as http:
            with self.assertRaises(httpx.HTTPStatusError):
                await HoloClient("test-key", http=http).decide(b"png", "test", [])


class BrowserTests(unittest.IsolatedAsyncioTestCase):
    def page_mock(self):
        page = MagicMock()
        page.is_closed.return_value = False
        return page

    async def test_page_context_uses_truncated_body_text_not_input_values(self):
        browser = Browser()
        browser.page = self.page_mock()
        browser.page.url = "https://example.org/results"
        browser.page.title = AsyncMock(return_value="Results")
        browser.page.evaluate = AsyncMock(return_value="First result: Lyon")
        self.assertEqual(await browser.page_context(), {"url": "https://example.org/results", "title": "Results",
                                                        "text": "First result: Lyon"})
        script = browser.page.evaluate.call_args.args[0]
        self.assertIn("innerText", script)
        self.assertIn("3000", script)
        self.assertNotIn(".value", script)

    async def test_reopen_last_url_and_limit_two_per_run(self):
        browser = Browser()
        browser.browser = MagicMock()
        browser.browser.is_connected.return_value = True
        browser.context = MagicMock()
        original = self.page_mock()
        original.url = "https://example.org/results"
        browser.page = original
        self.assertIs(browser.page, original)
        original.is_closed.return_value = True
        reopened = []

        async def new_page():
            page = self.page_mock()
            page.url = "about:blank"
            page.goto = AsyncMock()
            reopened.append(page)
            return page

        browser.context.new_page = AsyncMock(side_effect=new_page)
        for _ in range(2):
            page = await browser.ensure_page()
            page.goto.assert_awaited_once_with("https://example.org/results", wait_until="domcontentloaded")
            page.is_closed.return_value = True
        with self.assertRaisesRegex(RuntimeError, "recovery limit"):
            await browser.ensure_page()
        self.assertEqual(browser.context.new_page.await_count, 2)
        notes = await browser.take_recovery_notes()
        self.assertEqual(len(notes), 2)
        self.assertIn("Do not repeat a submission", notes[0])
        self.assertEqual(await browser.take_recovery_notes(), [])
        await browser.start_run()
        await browser.ensure_page()
        self.assertEqual(browser.context.new_page.await_count, 3)

    async def test_crash_reopens_and_disconnected_browser_does_not(self):
        browser = Browser()
        browser.browser = MagicMock()
        browser.context = MagicMock()
        old, new = self.page_mock(), self.page_mock()
        old.url = "https://example.org/search"
        new.url = "about:blank"
        new.goto = AsyncMock()
        browser.page = old
        self.assertIs(browser.page, old)
        browser._on_crash(old)
        browser.context.new_page = AsyncMock(return_value=new)
        self.assertIs(await browser.ensure_page(), new)
        new.goto.assert_awaited_once_with("https://example.org/search", wait_until="domcontentloaded")
        new.is_closed.return_value = True
        browser.browser.is_connected.return_value = False
        with self.assertRaisesRegex(RuntimeError, "Browser or context is closed"):
            await browser.ensure_page()
        self.assertEqual(browser.context.new_page.await_count, 1)

    async def test_debug_lifecycle_is_opt_in(self):
        for debug in (False, True):
            browser = Browser(debug=debug)
            page = self.page_mock()
            page.url = "https://example.org/search?token=private"
            output = io.StringIO()
            with redirect_stderr(output):
                browser._track_page(page)
                callbacks = dict(page.on.call_args_list[i].args for i in range(3))
                callbacks["framenavigated"](page.main_frame)
                callbacks["crash"]()
                callbacks["close"]()
            if debug:
                for event in ("opened", "navigated", "crashed", "closed"):
                    self.assertIn("Page " + event, output.getvalue())
                self.assertNotIn("private", output.getvalue())
            else:
                self.assertEqual(output.getvalue(), "")

    async def test_newest_open_page_and_closed_page_fallback(self):
        browser = Browser()
        first, second, third = (self.page_mock() for _ in range(3))
        browser._track_page(first)
        browser._track_page(second)
        browser._track_page(third)
        self.assertIs(browser.page, third)
        third.is_closed.return_value = True
        self.assertIs(browser.page, second)
        second.is_closed.return_value = True
        self.assertIs(browser.page, first)
        first.is_closed.return_value = True
        with self.assertRaises(RuntimeError):
            browser.page

    async def test_click_follows_popup_and_waits_for_load(self):
        browser = Browser()
        original, popup = self.page_mock(), self.page_mock()
        browser._track_page(original)
        popup.wait_for_load_state = AsyncMock()
        original.mouse.click = AsyncMock(side_effect=lambda *args: browser._track_page(popup))
        await browser.click(10, 20)
        self.assertIs(browser.page, popup)
        original.mouse.click.assert_awaited_once_with(10, 20)
        popup.wait_for_load_state.assert_awaited_once_with("domcontentloaded", timeout=5000)

    async def test_load_wait_is_best_effort(self):
        browser = Browser()
        browser.page = self.page_mock()
        browser.page.wait_for_load_state = AsyncMock(side_effect=Error("Timed out"))
        await browser._wait_for_page()

    async def test_screenshot_falls_back_when_page_closes(self):
        browser = Browser()
        first, popup = self.page_mock(), self.page_mock()
        browser._track_page(first)
        browser._track_page(popup)
        first.wait_for_load_state = AsyncMock()
        first.screenshot = AsyncMock(return_value=b"first page")
        popup.wait_for_load_state = AsyncMock()

        async def close_popup(**kwargs):
            popup.is_closed.return_value = True
            raise Error("Page closed")

        popup.screenshot = AsyncMock(side_effect=close_popup)
        self.assertEqual(await browser.screenshot(), b"first page")

    async def test_type_does_not_touch_noneditable_focus(self):
        browser = Browser()
        browser.page = self.page_mock()
        browser.page.evaluate = AsyncMock(return_value=False)
        self.assertIsNone(await browser.type("Lyon"))
        browser.page.locator.assert_not_called()
        browser.page.keyboard.insert_text.assert_not_called()

    async def test_type_clears_types_slowly_and_reads_value(self):
        browser = Browser()
        browser.page = self.page_mock()
        browser.page.evaluate = AsyncMock(side_effect=[True, "Lyon"])
        browser.page.wait_for_timeout = AsyncMock()
        field = browser.page.locator.return_value
        field.fill = AsyncMock()
        field.press_sequentially = AsyncMock()
        self.assertEqual(await browser.type("Lyon"), "Lyon")
        browser.page.locator.assert_called_once_with(":focus")
        field.fill.assert_awaited_once_with("")
        field.press_sequentially.assert_awaited_once_with("Lyon", delay=25)
        browser.page.wait_for_timeout.assert_awaited_once_with(1000)
        browser.page.keyboard.press.assert_not_called()

    async def test_screenshot_navigation_retry(self):
        browser = Browser(headless=True)
        browser.page = self.page_mock()
        browser.page.wait_for_load_state = AsyncMock()
        browser.page.screenshot = AsyncMock(side_effect=[Error("Execution context was destroyed"), b"png"])
        self.assertEqual(await browser.screenshot(), b"png")
        self.assertEqual(browser.page.screenshot.await_count, 2)

    async def test_screenshot_retries_transient_error(self):
        browser = Browser(headless=True)
        browser.page = self.page_mock()
        browser.page.wait_for_load_state = AsyncMock()
        browser.page.screenshot = AsyncMock(side_effect=[Error("Timeout 30000ms exceeded"), Error("Protocol error"), b"png"])
        with patch("brainy.agent.browser.asyncio.sleep", AsyncMock()):
            self.assertEqual(await browser.screenshot(), b"png")
        self.assertEqual(browser.page.screenshot.await_count, 3)

    async def test_screenshot_other_error(self):
        browser = Browser(headless=True)
        browser.page = self.page_mock()
        browser.page.wait_for_load_state = AsyncMock()
        browser.page.screenshot = AsyncMock(side_effect=Error("Disconnected"))
        with self.assertRaises(Error):
            await browser.screenshot()
        self.assertEqual(browser.page.screenshot.await_count, 1)

    async def test_invalid_navigation(self):
        browser = Browser()
        for url in ("file:///etc/passwd", "https://user:password@example.org", "javascript:alert(1)", ""):
            with self.subTest(url=url), self.assertRaises(ValueError):
                await browser.goto(url)


class CLITests(unittest.IsolatedAsyncioTestCase):
    async def test_ctrl_c_at_close_prompt_exits_and_closes(self):
        async def events(*args):
            yield Done("Finished")

        args = Namespace(headless=False, profile_dir=None, model="test", goal="test", url=None, debug=False, channel=None)
        with patch("brainy.agent.__main__.Browser") as browser, \
                patch("brainy.agent.__main__.HoloClient"), \
                patch("brainy.agent.__main__.WebAgent") as agent, \
                patch("builtins.input", side_effect=KeyboardInterrupt), patch("builtins.print"):
            browser.return_value.__aenter__ = AsyncMock()
            browser.return_value.__aexit__ = AsyncMock(return_value=False)
            agent.return_value.run = events
            with self.assertRaises(KeyboardInterrupt):
                await run(args)
            browser.return_value.__aexit__.assert_awaited_once()

    async def test_headed_waits_on_completion_or_error_headless_does_not(self):
        for headless in (False, True):
            for event in (Done("Finished"), AgentError("Failure", "Retry"),
                          AgentError("The step limit was reached.", "Retry")):
                with self.subTest(headless=headless, event=event):
                    async def events(*args):
                        yield event

                    args = Namespace(headless=headless, profile_dir=None, model="test", goal="test", url=None, debug=False, channel=None)
                    with patch("brainy.agent.__main__.Browser") as browser, \
                            patch("brainy.agent.__main__.HoloClient"), \
                            patch("brainy.agent.__main__.WebAgent") as agent, \
                            patch("builtins.input", return_value="") as prompt, patch("builtins.print"):
                        browser.return_value.__aenter__ = AsyncMock()
                        browser.return_value.__aexit__ = AsyncMock(return_value=False)
                        agent.return_value.run = events
                        self.assertEqual(await run(args), 1 if isinstance(event, AgentError) else 0)
                        if headless:
                            prompt.assert_not_called()
                        else:
                            prompt.assert_called_once_with("Press Enter to close the browser. ")
                        browser.return_value.__aexit__.assert_awaited_once()

    async def test_channel_and_debug_forwarded(self):
        async def events(*args):
            yield Done("Finished")

        args = Namespace(headless=True, profile_dir="profile", model="test", goal="test", url=None,
                         debug=True, channel="chrome")
        with patch("brainy.agent.__main__.Browser") as browser, \
                patch("brainy.agent.__main__.HoloClient"), \
                patch("brainy.agent.__main__.WebAgent") as agent, patch("builtins.print"):
            browser.return_value.__aenter__ = AsyncMock()
            browser.return_value.__aexit__ = AsyncMock(return_value=False)
            agent.return_value.run = events
            await run(args)
            browser.assert_called_once_with(headless=True, profile_dir="profile", channel="chrome", debug=True)
            self.assertTrue(agent.call_args.kwargs["debug"])


class DebugTests(unittest.TestCase):
    def test_credentials_and_headers_are_redacted(self):
        output = io.StringIO()
        with redirect_stderr(output), patch.dict("os.environ", {"H_API_KEY": "private-key"}):
            debug_log("ValueError: private-key\nHeaders: sensitive\nAuthorization: Bearer sensitive\n"
                      "https://user:password@example.org/path?token=sensitive")
        self.assertNotIn("private-key", output.getvalue())
        self.assertNotIn("sensitive", output.getvalue())
        self.assertNotIn("password", output.getvalue())
