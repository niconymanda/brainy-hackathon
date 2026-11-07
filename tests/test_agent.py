import unittest
from unittest.mock import AsyncMock, MagicMock

import httpx
from playwright.async_api import Error

from brainy.agent.browser import Browser
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

    async def test_type_and_user_manual_step(self):
        self.ask.return_value = "private answer"
        events = await self.collect([Action("type", target="Name", text="Test User"),
                                     Action("ask_user", text="Complete the manual step"), Action("done")])
        self.browser.type.assert_awaited_once_with("Test User")
        self.browser.press.assert_awaited_once_with("ControlOrMeta+A")
        self.assertTrue(any(isinstance(e, NeedsUser) for e in events))
        self.assertNotIn("private answer", str(self.client.decide.call_args))


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
    async def test_screenshot_navigation_retry(self):
        browser = Browser(headless=True)
        browser.page = MagicMock()
        browser.page.wait_for_load_state = AsyncMock()
        browser.page.screenshot = AsyncMock(side_effect=[Error("Execution context was destroyed"), b"png"])
        self.assertEqual(await browser.screenshot(), b"png")
        self.assertEqual(browser.page.screenshot.await_count, 2)

    async def test_screenshot_other_error(self):
        browser = Browser(headless=True)
        browser.page = MagicMock()
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
