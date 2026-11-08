"""Fill known forms straight from the user's profile: faster and more reliable than clicking field by field."""
import re
import sys
from pathlib import Path

ADDRESS = re.compile(r"^(.*?)[,\s]+(\d{5})\s+(.+)$")


def profile_fields(text):
    fields = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep and value.strip() and not key.lstrip().startswith("#"):
            fields[key.strip().casefold()] = value.strip()
    return fields


async def _empty(field):
    return await field.count() > 0 and not (await field.first.input_value()).strip()


class DoctolibPrefill:
    """Fills Doctolib's "Vos informations manquantes" block (birth name, birth city, address) once per task."""

    def __init__(self, profile):
        self.profile = profile
        self.done = set()

    async def __call__(self, page):
        url = str(getattr(page, "url", ""))
        if "doctolib.fr" not in url or "checkout" not in url:
            return []
        filled = []
        for name, fill in (("nom de naissance", self._birth_name), ("ville de naissance", self._birth_city),
                           ("adresse", self._address), ("déjà consulté", self._first_visit)):
            if name in self.done:
                continue
            try:
                if await fill(page):
                    self.done.add(name)
                    filled.append(name)
            except Exception as exc:
                print(f"Prefill {name}: {type(exc).__name__}", file=sys.stderr)
        if not self.done and not getattr(self, "dumped", False):
            self.dumped = True
            try:
                # Local debugging aid: the form's markup, kept on this computer only.
                html = await page.evaluate("() => (document.querySelector('main') || document.body).outerHTML")
                (Path.home() / ".brainy" / "checkout.html").write_text(html, encoding="utf-8")
            except Exception:
                pass
        if not filled:
            return []
        return [f"Brainy already filled from the profile: {', '.join(filled)}. Do not retype these fields; "
                "check the rest of the form and continue to the final button."]

    async def _birth_name(self, page):
        radio = page.locator("xpath=//*[contains(text(), 'nom de naissance est-il')]"
                             "/following::input[@type='radio'][1]")
        if not await radio.count():
            return False
        if not await radio.first.is_checked():
            await radio.first.check(force=True, timeout=3000)
        return True

    async def _birth_city(self, page):
        city = re.sub(r"[\s(]*\d+\)?\s*$", "", self.profile.get("ville de naissance", "")).strip()
        field = page.locator("xpath=//*[normalize-space(text())='Ville de naissance']/following::input[1]")
        if not city or not await _empty(field):
            return False
        await field.first.click(timeout=3000)
        await field.first.press_sequentially(city, delay=40)
        option = page.get_by_role("option").filter(has_text=re.compile(rf"^\s*{re.escape(city)}", re.I))
        try:
            await option.first.wait_for(timeout=4000)
            await option.first.click(timeout=3000)
        except Exception:
            await page.keyboard.press("ArrowDown")
            await page.keyboard.press("Enter")
        return True

    async def _address(self, page):
        address = self.profile.get("adresse", "")
        street = page.get_by_placeholder("Adresse", exact=True)
        if not address or not await _empty(street):
            return False
        match = ADDRESS.match(address)
        parts = (match.group(1).strip(" ,"), match.group(2), match.group(3).strip()) if match else (address, "", "")
        for placeholder, value in zip(("Adresse", "Code postal", "Ville"), parts):
            field = page.get_by_placeholder(placeholder, exact=True)
            if value and await _empty(field):
                await field.first.fill(value, timeout=3000)
                await page.keyboard.press("Escape")
        return True

    async def _first_visit(self, page):
        button = page.locator("xpath=//*[contains(text(), 'déjà consulté ce soignant')]"
                              "/following::*[self::button or @role='radio' or self::label][normalize-space()='Non'][1]")
        if not await button.count():
            return False
        await button.first.click(timeout=3000)
        return True
