import asyncio
import re
import unicodedata
from uuid import uuid4
from urllib.parse import urlsplit

from playwright.async_api import Error, TimeoutError as PlaywrightTimeoutError, async_playwright

from .debug import debug_log


SECRET_QUESTION = re.compile(r"\b(?:password|mot\s+de\s+passe|card|carte|cvv|cvc|code|pin|iban|otp|sms)\b", re.I)


class SecretFieldError(ValueError):
    pass


def is_secret_field(text):
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text).replace("_", " ")
    return bool(SECRET_QUESTION.search(normalize_choice(text)))


def normalize_choice(text):
    text = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


DIRECT_LOOKUP = r"""({mode, target, marker}) => {
    const normalize = text => text.normalize('NFKD').toLowerCase().replace(/ß/g, 'ss')
        .replace(/ς/g, 'σ').replace(/\p{M}/gu, '').replace(/\s+/g, ' ').trim();
    const visible = el => {
        if (!el || !el.getClientRects().length) return false;
        const style = getComputedStyle(el);
        return style.visibility !== 'hidden' && style.visibility !== 'collapse' &&
            (el.getBoundingClientRect().width > 0 && el.getBoundingClientRect().height > 0);
    };
    const enabled = el => !el.matches(':disabled') && el.getAttribute('aria-disabled') !== 'true';
    const metadata = el => ({type: el.type || '', autocomplete: el.getAttribute('autocomplete') || '',
        labels: [el.getAttribute('placeholder') || '', el.getAttribute('aria-label') || '',
                 ...Array.from(el.labels || []).map(label => label.innerText), el.getAttribute('name') || '']});
    const mark = (el, rank, meta) => {
        el.setAttribute('data-brainy-direct', marker);
        return {rank, metadata: meta};
    };
    if (mode === 'fill') {
        for (const el of document.querySelectorAll('input, textarea, [role="combobox"][contenteditable="true"]')) {
            if (!visible(el) || !enabled(el) || el.readOnly) continue;
            const meta = metadata(el);
            if (!meta.labels.some(label => normalize(label).includes(target))) continue;
            if (!['', 'text', 'search', 'email', 'url', 'tel', 'number', 'textarea', 'password'].includes(meta.type)) continue;
            return mark(el, 0, meta);
        }
        return null;
    }
    const groups = [
        'input[type="radio"], [role="radio"]', 'option, [role="option"]',
        'input[type="checkbox"], [role="checkbox"]', 'button, input[type="button"], input[type="submit"], [role="button"]',
        'a[href], [role="link"]', '[role="menuitem"]', '[role="tab"]',
        'label', '[onclick], [tabindex], select'
    ];
    const text = el => {
        if (el.tagName === 'INPUT') {
            if (['button', 'submit'].includes(el.type)) return el.value;
            return Array.from(el.labels || []).filter(visible).map(label => label.innerText).join(' ');
        }
        return el.innerText;
    };
    for (let rank = 0; rank < groups.length; rank++) {
        for (const el of document.querySelectorAll(groups[rank])) {
            if (el.hasAttribute('aria-pressed')) continue;
            const control = el.tagName === 'OPTION' ? el.closest('select') : el;
            if (!enabled(el) || !visible(control)) continue;
            if (normalize(text(el)) === target) return mark(el, rank, null);
        }
    }
    return null;
}"""


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
            page.set_default_timeout(5000)
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
                await page.wait_for_load_state("domcontentloaded", timeout=2500)
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
        await self.page.goto(url, wait_until="domcontentloaded", timeout=5000)

    async def screenshot(self):
        # Mask password fields before any image leaves the machine.
        for attempt in range(2):
            page = await self.ensure_page()
            try:
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=2500)
                except PlaywrightTimeoutError:
                    pass
                return await asyncio.wait_for(page.screenshot(mask=[page.locator('input[type="password"]')],
                                                              timeout=4000), timeout=5)
            except Error as exc:
                if attempt or (not page.is_closed() and page not in self._crashed and "Execution context was destroyed" not in str(exc)):
                    raise

    async def page_context(self):
        page = await self.ensure_page()
        async def read():
            return {"url": page.url, "title": await page.title(),
                    "text": await page.evaluate("() => (document.body?.innerText || '').slice(0, 1500)")}
        try:
            return await asyncio.wait_for(read(), timeout=3)
        except (Error, asyncio.TimeoutError):
            return {"url": page.url, "title": "", "text": "Page context temporarily unavailable during loading."}

    async def click(self, x, y):
        self._page_opened.clear()
        page = await self.ensure_page()
        try:
            await page.mouse.click(x, y)
        except Error:
            if not page.is_closed() and page not in self._crashed:
                raise
            await self.ensure_page()
        # Page events are delivered while Playwright resolves the click. Yield once
        # for an event already queued, without imposing a fixed no-popup delay.
        await asyncio.sleep(0)
        if self._page_opened.is_set():
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
        await field.press_sequentially(text, delay=25)
        await self.page.wait_for_timeout(450)
        return await self.page.evaluate("""() => {
            const el = document.activeElement;
            if (!el) return '';
            if (el.type === 'password') return '[redacted]';
            return el.isContentEditable ? el.textContent : (el.value || '');
        }""")

    async def find_choice(self, text):
        if not normalize_choice(text):
            return None
        return await self._find_direct("choose", text)

    async def _find_direct(self, mode, text):
        try:
            return await asyncio.wait_for(self._lookup_direct(mode, text), timeout=2)
        except (Error, asyncio.TimeoutError) as exc:
            if self.debug:
                debug_log(f"Direct lookup deferred to Holo ({type(exc).__name__}).")
            return None

    async def _lookup_direct(self, mode, text):
        page = await self.ensure_page()
        marker = uuid4().hex
        best = None
        for frame in page.frames:
            result = await frame.evaluate(DIRECT_LOOKUP, {"mode": mode, "target": normalize_choice(text), "marker": marker})
            if result is not None and (best is None or result["rank"] < best[0]):
                if mode == "fill":
                    self._check_fill_secret(result["metadata"])
                best = (result["rank"], frame.locator(f'[data-brainy-direct="{marker}"]'))
                if result["rank"] == 0:
                    break
        return best[1] if best else None

    async def find_fill(self, field):
        if is_secret_field(field):
            raise SecretFieldError()
        field = normalize_choice(field)
        if not field:
            return None
        return await self._find_direct("fill", field)

    async def _fill_metadata(self, element):
        return await element.evaluate("""el => ({
            type: el.type || '', autocomplete: el.getAttribute('autocomplete') || '',
            labels: [el.getAttribute('placeholder') || '', el.getAttribute('aria-label') || '',
                     ...Array.from(el.labels || []).map(label => label.innerText), el.getAttribute('name') || '']
        })""", timeout=300)

    def _check_fill_secret(self, metadata):
        if (metadata["type"] == "password" or
                any(is_secret_field(label) for label in metadata["labels"]) or
                metadata.get("autocomplete", "").startswith(("cc-", "one-time-code"))):
            raise SecretFieldError()

    async def fill_field(self, element, text):
        if not await self._direct_click(element):
            return None
        try:
            if not await element.evaluate("el => el === el.ownerDocument.activeElement", timeout=300):
                return None
            self._check_fill_secret(await self._fill_metadata(self.page.locator(":focus")))
        except PlaywrightTimeoutError:
            return None
        return await self.type(text)

    async def _direct_click(self, element):
        page = await self.ensure_page()
        started, loaded = asyncio.Event(), asyncio.Event()
        def on_request(request):
            if request.is_navigation_request() and request.frame == page.main_frame:
                started.set()
        def on_load():
            loaded.set()
        page.on("request", on_request)
        page.on("domcontentloaded", on_load)
        try:
            result = await self._click_direct_element(element)
            if result:
                try:
                    await asyncio.wait_for(started.wait(), timeout=0.15)
                    await asyncio.wait_for(loaded.wait(), timeout=2.5)
                except asyncio.TimeoutError:
                    pass
            return result
        finally:
            page.remove_listener("request", on_request)
            page.remove_listener("domcontentloaded", on_load)

    async def _click_direct_element(self, element):
        try:
            await element.click(timeout=500, no_wait_after=True)
            return True
        except PlaywrightTimeoutError:
            try:
                box = await element.bounding_box(timeout=300)
                if box:
                    await self.page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    return True
            except PlaywrightTimeoutError:
                pass
            return False

    async def select_choice(self, element, text):
        try:
            return await self._select_first_visible(element, text, exact=True, fast=True)
        except PlaywrightTimeoutError:
            return None

    async def select_text(self, text, exact=False, find_only=False):
        try:
            return await asyncio.wait_for(self._resolve_text(text, exact, find_only), timeout=5)
        except (Error, asyncio.TimeoutError):
            return None

    async def _resolve_text(self, text, exact=False, find_only=False):
        page = await self.ensure_page()
        name = re.compile(".*" if exact else re.escape(text), re.I)
        options = {"exact": True, "find_only": find_only} if exact else {}
        frames = page.frames
        for role in ("radio", "option", "checkbox", "button", "link", "menuitem", "tab"):
            for frame in frames:
                matches = frame.get_by_role(role, name=name, include_hidden=role == "option")
                result = await self._select_first_visible(matches, text, **options)
                if result is not None:
                    return result
        for method in ("get_by_label", "get_by_text"):
            for frame in frames:
                result = await self._select_first_visible(getattr(frame, method)(name), text, **options)
                if result is not None:
                    return result
        return None

    async def _select_first_visible(self, matches, text, exact=False, find_only=False, fast=False):
        for index in range(await matches.count()):
            element = matches.nth(index)
            kind = await element.evaluate("el => ({tag: el.tagName, type: el.type, role: el.getAttribute('role')})",
                                          timeout=300 if fast else 15000)
            if exact:
                label = await element.evaluate("""el => {
                    const control = el.closest('button, a[href], input, select, option, label, [role="radio"], [role="option"], [role="checkbox"], [role="button"], [role="link"], [role="menuitem"], [role="tab"], [onclick], [tabindex]');
                    if (!control || control.disabled) return null;
                    if (control.tagName === 'INPUT') {
                        if (['button', 'submit'].includes(control.type)) return control.value;
                        return Array.from(control.labels || []).filter(label => label.getClientRects().length)
                            .map(label => label.innerText).join(' ');
                    }
                    return control.innerText;
                }""", timeout=300 if fast else 15000)
                if label is None or normalize_choice(label) != normalize_choice(text):
                    continue
            if kind["tag"] == "OPTION":
                select = element.locator("xpath=ancestor::select[1]")
                if not await select.is_visible():
                    continue
                if find_only:
                    return element
                await select.scroll_into_view_if_needed(**({"timeout": 500} if fast else {}))
                await select.select_option(label=await element.evaluate("el => el.label", timeout=300 if fast else 15000),
                                           **({"timeout": 500} if fast else {}))
            else:
                if not await element.is_visible():
                    continue
                if find_only:
                    return element
                if not fast:
                    await element.scroll_into_view_if_needed()
                if kind.get("type") in {"radio", "checkbox"} or kind.get("role") in {"radio", "checkbox"}:
                    if fast:
                        try:
                            await element.check(timeout=500, no_wait_after=True)
                        except PlaywrightTimeoutError:
                            if not await self._direct_click(element):
                                return None
                    else:
                        await element.check()
                elif kind["tag"] == "SELECT":
                    await element.select_option(label=text, **({"timeout": 500} if fast else {}))
                else:
                    if fast:
                        if not await self._direct_click(element):
                            return None
                    else:
                        await element.click()
            if not fast:
                await self._wait_for_page()
            try:
                state = await element.evaluate("""el => {
                    const control = el.control || el.querySelector('input[type="radio"], input[type="checkbox"]') || el;
                    const state = {};
                    if (typeof control.checked === 'boolean') state.checked = control.checked;
                    for (const attr of ['aria-checked', 'aria-selected']) {
                        if (control.hasAttribute(attr)) state[attr] = control.getAttribute(attr);
                    }
                    if (control.tagName === 'OPTION') state.selected = control.selected;
                    return state;
                }""", timeout=300 if fast else 15000)
            except Error:
                state = {}
            if fast and (state.get("checked") is False or state.get("aria-checked") == "false"):
                return None
            details = ", ".join(f"{key}={str(value).lower()}" for key, value in state.items())
            return f"Selected {text!r}: " + (details or "clicked; inspect next screenshot for page change")

    async def press(self, key):
        await self.page.keyboard.press(key)

    async def scroll(self, direction):
        page = await self.ensure_page()
        viewport_delta = """() => {
            let target = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
            while (target && !(target.clientHeight > 0 && target.scrollHeight > target.clientHeight &&
                    /auto|scroll/.test(getComputedStyle(target).overflowY))) target = target.parentElement;
            target ||= document.scrollingElement;
            const rect = target.getBoundingClientRect();
            const visibleHeight = Math.min(rect.bottom, innerHeight) - Math.max(rect.top, 0);
            return Math.max(1, Math.round(Math.min(target.clientHeight, visibleHeight) * 0.8));
        }"""
        state = """() => [window.scrollX, window.scrollY, ...Array.from(document.querySelectorAll('*'))
            .filter(el => el.scrollHeight > el.clientHeight && el.clientHeight > 0)
            .map(el => el.scrollTop)]"""
        async def perform():
            delta = await page.evaluate(viewport_delta)
            if direction == "up":
                delta = -delta
            before = await page.evaluate(state)
            await page.mouse.move(self.viewport[0] / 2, self.viewport[1] / 2)
            await page.mouse.wheel(0, delta)
            await page.wait_for_timeout(100)
            if before != await page.evaluate(state):
                return "Scrolled the content under the viewport center."
            moved = await page.evaluate("""delta => {
                const candidates = [document.scrollingElement, ...document.querySelectorAll('*')]
                    .filter(el => el && el.clientHeight > 0 && el.scrollHeight > el.clientHeight &&
                        (el === document.scrollingElement || /auto|scroll/.test(getComputedStyle(el).overflowY)))
                    .filter(el => { const r = el.getBoundingClientRect();
                        return r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth; });
                candidates.sort((a,b) => b.clientWidth*b.clientHeight - a.clientWidth*a.clientHeight);
                for (const el of candidates) {
                    const before = el.scrollTop;
                    const rect = el.getBoundingClientRect();
                    const visibleHeight = Math.min(rect.bottom, innerHeight) - Math.max(rect.top, 0);
                    el.scrollTop += Math.sign(delta) * Math.max(1, Math.round(Math.min(el.clientHeight, visibleHeight) * 0.8));
                    if (el.scrollTop !== before) return true;
                }
                return false;
            }""", delta)
            return "Scrolled an inner scroll container." if moved else "Scroll had no effect; try another direction or approach."
        return await asyncio.wait_for(perform(), timeout=3)
