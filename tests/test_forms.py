import unittest

from playwright.async_api import async_playwright

from brainy.agent.forms import DoctolibPrefill, profile_fields

FORM = """<html><body>
<p>Votre nom de naissance est-il ESPOSITO FARESE ?</p>
<label><input type="radio" name="bn" value="yes">Oui</label><label><input type="radio" name="bn" value="no">Non</label>
<div>Lieu de naissance</div><select><option>Né(e) en France</option></select>
<div>Ville de naissance</div><input id="city" oninput="document.getElementById('opts').innerHTML =
 this.value.length > 3 ? '<div role=option onclick=&quot;pick(this)&quot;>Strasbourg (67)</div>' : ''">
<div id="opts"></div>
<div>Adresse</div><input placeholder="Adresse"><input placeholder="Code postal"><input placeholder="Ville">
<p>Avez-vous déjà consulté ce soignant ?</p>
<button onclick="this.dataset.on=1">Oui</button><button id="no" onclick="this.dataset.on=1">Non</button>
<script>function pick(el){document.getElementById('city').value = el.textContent;}</script>
</body></html>"""

PROFILE = "Nom de naissance : ESPOSITO FARESE\nVille de naissance : Strasbourg 67\nAdresse : 26 rue Berzélius, 75017 Paris\n"


class DoctolibPrefillTests(unittest.IsolatedAsyncioTestCase):
    async def test_fills_missing_information(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.route("**/*", lambda route: route.fulfill(body=FORM, content_type="text/html; charset=utf-8"))
            await page.goto("https://www.doctolib.fr/online_booking/checkout")
            prefill = DoctolibPrefill(profile_fields(PROFILE))
            notes = await prefill(page)
            self.assertTrue(await page.locator("input[value=yes]").is_checked())
            self.assertEqual(await page.input_value("#city"), "Strasbourg (67)")
            self.assertEqual(await page.get_by_placeholder("Adresse", exact=True).input_value(), "26 rue Berzélius")
            self.assertEqual(await page.get_by_placeholder("Code postal").input_value(), "75017")
            self.assertEqual(await page.get_by_placeholder("Ville", exact=True).input_value(), "Paris")
            self.assertEqual(await page.get_attribute("#no", "data-on"), "1")
            self.assertIn("ville de naissance", notes[0])
            self.assertEqual(await prefill(page), [])
            await browser.close()

    async def test_ignores_other_pages(self):
        page = type("Page", (), {"url": "https://www.doctolib.fr/dermatologue/paris"})()
        self.assertEqual(await DoctolibPrefill({})(page), [])
