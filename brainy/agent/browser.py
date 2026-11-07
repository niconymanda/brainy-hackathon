from urllib.parse import urlsplit

from playwright.async_api import Error, async_playwright


class Browser:
    def __init__(self, headless=False, profile_dir=None):
        self.headless = headless
        self.profile_dir = profile_dir
        self.viewport = (1280, 900)

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
            self.page = await self.context.new_page()
            self.page.set_default_timeout(15000)
            return self
        except Exception:
            await self.playwright.stop()
            raise

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
            try:
                await self.page.wait_for_load_state("domcontentloaded")
                return await self.page.screenshot(mask=[self.page.locator('input[type="password"]')])
            except Error as exc:
                if attempt or "Execution context was destroyed" not in str(exc):
                    raise

    async def click(self, x, y):
        await self.page.mouse.click(x, y)

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
