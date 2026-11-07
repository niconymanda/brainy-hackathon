import unittest
from argparse import Namespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from playwright.async_api import Error

from brainy.agent.browser import Browser
from brainy.agent.__main__ import run
from brainy.agent.events import AgentError, ConfirmRequest, Done, NeedsUser
from brainy.agent.holo import Action, HoloClient, parse_action, parse_click
from brainy.agent.loop import WebAgent


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

    async def test_http_error(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(401))) as http:
            with self.assertRaises(httpx.HTTPStatusError):
                await HoloClient("test-key", http=http).decide(b"png", "test", [])


class BrowserTests(unittest.IsolatedAsyncioTestCase):
    def page_mock(self):
        page = MagicMock()
        page.is_closed.return_value = False
        return page

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
        field.press_sequentially.assert_awaited_once_with("Lyon", delay=65)
        browser.page.wait_for_timeout.assert_awaited_once_with(1000)
        browser.page.keyboard.press.assert_not_called()

    async def test_screenshot_navigation_retry(self):
        browser = Browser(headless=True)
        browser.page = self.page_mock()
        browser.page.wait_for_load_state = AsyncMock()
        browser.page.screenshot = AsyncMock(side_effect=[Error("Execution context was destroyed"), b"png"])
        self.assertEqual(await browser.screenshot(), b"png")
        self.assertEqual(browser.page.screenshot.await_count, 2)

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

        args = Namespace(headless=False, profile_dir=None, model="test", goal="test", url=None)
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

                    args = Namespace(headless=headless, profile_dir=None, model="test", goal="test", url=None)
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
