import asyncio
from urllib.parse import urlsplit

from playwright.async_api import Error, async_playwright

from .debug import debug_log


class Browser:
    def __init__(self, headless=False, profile_dir=None, channel=None, debug=False):
        self.headless = headless
        self.profile_dir = profile_dir
        self.channel = channel
        self.debug = debug
        self.viewport = (1280, 900)
        self._pages = []
        self._page_opened = asyncio.Event()
        self._crashed = set()
        self._last_url = None
        self._context_closed = False
        self._recoveries = 0
        self._recovery_notes = []

    @property
    def page(self):
        for page in reversed(self._pages):
            if not page.is_closed() and page not in self._crashed:
                self._remember_url(page)
                return page
        raise RuntimeError("No open browser page")

    @page.setter
    def page(self, page):
        if page not in self._pages:
            self._pages.append(page)
            page.set_default_timeout(15000)
            page.on("close", lambda: self._lifecycle("closed", page))
            page.on("crash", lambda: self._on_crash(page))
            page.on("framenavigated", lambda frame: self._on_navigation(page, frame))
            self._lifecycle("opened", page)
            self._page_opened.set()

    def _remember_url(self, page):
        if isinstance(page.url, str) and page.url.startswith(("http://", "https://")):
            self._last_url = page.url

    def _lifecycle(self, event, page):
        if self.debug:
            debug_log(f"Page {event}: {page.url}")

    def _on_crash(self, page):
        self._crashed.add(page)
        self._lifecycle("crashed", page)

    def _on_navigation(self, page, frame):
        if frame == page.main_frame:
            if self._pages and page == self._pages[-1]:
                self._remember_url(page)
            self._lifecycle("navigated", page)

    async def start_run(self):
        self._recoveries = 0
        self._recovery_notes.clear()

    async def take_recovery_notes(self):
        notes, self._recovery_notes = self._recovery_notes, []
        return notes

    async def ensure_page(self):
        try:
            return self.page
        except RuntimeError:
            if self._context_closed or (self.browser and not self.browser.is_connected()):
                raise RuntimeError("Browser or context is closed") from None
            if self._recoveries >= 2 or not self._last_url:
                raise RuntimeError("Tab recovery limit reached or no previous URL") from None
            self._recoveries += 1
            url = self._last_url
            self.page = await self.context.new_page()
            await self.goto(url)
            self._recovery_notes.append("The browser tab closed or crashed and was reopened at its last URL. "
                                        "Inspect the screenshot; previous form state may be lost. Do not repeat a submission.")
            if self.debug:
                debug_log(f"Tab recovered ({self._recoveries}/2): {url}")
            return self.page

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        try:
            options = {"headless": self.headless}
            if self.channel:
                options["channel"] = self.channel
            if not self.headless:
                options["args"] = ["--disable-blink-features=AutomationControlled"]
            viewport = {"width": self.viewport[0], "height": self.viewport[1]}
            if self.profile_dir:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    self.profile_dir, viewport=viewport, **options)
                self.browser = None
            else:
                self.browser = await self.playwright.chromium.launch(**options)
                self.context = await self.browser.new_context(viewport=viewport)
            self.context.on("page", self._track_page)
            self.context.on("close", lambda _: setattr(self, "_context_closed", True))
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
            page = await self.ensure_page()
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
                return
            except Error:
                if page is await self.ensure_page():
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
            page = await self.ensure_page()
            try:
                await page.wait_for_load_state("domcontentloaded")
                return await page.screenshot(mask=[page.locator('input[type="password"]')])
            except Error as exc:
                if attempt or (not page.is_closed() and page not in self._crashed and "Execution context was destroyed" not in str(exc)):
                    raise

    async def page_context(self):
        page = await self.ensure_page()
        return {"url": page.url, "title": await page.title(),
                "text": await page.evaluate("() => (document.body?.innerText || '').slice(0, 1500)")}

    async def click(self, x, y):
        self._page_opened.clear()
        page = await self.ensure_page()
        try:
            await page.mouse.click(x, y)
        except Error:
            if not page.is_closed() and page not in self._crashed:
                raise
            await self.ensure_page()
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
