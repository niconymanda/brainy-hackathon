import asyncio
from urllib.parse import urlsplit

from playwright.async_api import Error, async_playwright


class Browser:
    def __init__(self, headless=False, profile_dir=None):
        self.headless = headless
        self.profile_dir = profile_dir
        self.viewport = (1280, 900)
        self._pages = []
        self._page_opened = asyncio.Event()

    @property
    def page(self):
        for page in reversed(self._pages):
            if not page.is_closed():
                return page
        raise RuntimeError("No open browser page")

    @page.setter
    def page(self, page):
        if page not in self._pages:
            self._pages.append(page)
            page.set_default_timeout(15000)
            self._page_opened.set()

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        try:
            options = {"headless": self.headless}
            viewport = {"width": self.viewport[0], "height": self.viewport[1]}
            if self.profile_dir:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    self.profile_dir, viewport=viewport, **options)
                self.browser = None
            else:
                self.browser = await self.playwright.chromium.launch(**options)
                self.context = await self.browser.new_context(viewport=viewport)
            self.context.on("page", self._track_page)
            for page in self.context.pages:
                self._track_page(page)
            self.page = await self.context.new_page()
            return self
        except Exception:
            await self.playwright.stop()
            raise

    def _track_page(self, page):
        self.page = page

    async def _wait_for_page(self):
        for _ in range(2):
            page = self.page
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
                return
            except Error:
                if page is self.page:
                    return

    async def __aexit__(self, *args):
        try:
            await self.context.close()
            if self.browser:
                await self.browser.close()
        finally:
            await self.playwright.stop()

    async def goto(self, url):
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ValueError("Only HTTP(S) URLs without credentials are allowed")
        await self.page.goto(url, wait_until="domcontentloaded")

    async def screenshot(self):
        # Mask password fields before any image leaves the machine.
        for attempt in range(2):
            page = self.page
            try:
                await page.wait_for_load_state("domcontentloaded")
                return await page.screenshot(mask=[page.locator('input[type="password"]')])
            except Error as exc:
                if attempt or (not page.is_closed() and "Execution context was destroyed" not in str(exc)):
                    raise

    async def click(self, x, y):
        self._page_opened.clear()
        await self.page.mouse.click(x, y)
        try:
            await asyncio.wait_for(self._page_opened.wait(), timeout=0.5)
        except asyncio.TimeoutError:
            pass
        await self._wait_for_page()

    async def type(self, text):
        editable = await self.page.evaluate("""() => {
            const el = document.activeElement;
            return !!el && !el.disabled && !el.readOnly &&
                (el.isContentEditable || el.tagName === 'TEXTAREA' ||
                 (el.tagName === 'INPUT' &&
                  ['text', 'search', 'email', 'url', 'tel', 'password', 'number'].includes(el.type)));
        }""")
        if not editable:
            return None
        field = self.page.locator(":focus")
        await field.fill("")
        await field.press_sequentially(text, delay=65)
        await self.page.wait_for_timeout(1000)
        return await self.page.evaluate("""() => {
            const el = document.activeElement;
            if (!el) return '';
            if (el.type === 'password') return '[redacted]';
            return el.isContentEditable ? el.textContent : (el.value || '');
        }""")

    async def press(self, key):
        await self.page.keyboard.press(key)

    async def scroll(self, direction):
        await self.page.mouse.wheel(0, -600 if direction == "up" else 600)
