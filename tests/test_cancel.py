import unittest

from playwright.async_api import async_playwright

from brainy.agent.cancel import cancel_doctolib


FIXTURE = """<html><body><main>
<h1>Rendez-vous à venir</h1><section aria-label="Rendez-vous à venir" role="region">
<article><button onclick="document.querySelector('#detail').hidden=false">12 décembre 2030 à 10h30 — Dr Martin</button></article>
</section><div id="detail" hidden><h2>Dr Martin — dermatologue</h2><p>12 décembre 2030 à 10h30</p>
<button onclick="document.querySelector('#modal').showModal()">Annuler le rendez-vous</button></div>
<dialog id="modal"><p>Voulez-vous annuler ?</p><button onclick="cancelAppointment()">Confirmer l'annulation</button></dialog>
<script>function cancelAppointment(){document.querySelector('main').innerHTML='<h1>Rendez-vous annulé</h1>';}</script>
</main></body></html>"""


class CancelTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        self.page = await self.browser.new_page()

    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()

    async def route(self, body=FIXTURE, answer=True):
        await self.page.route('**/*', lambda route: route.fulfill(body=body, content_type='text/html; charset=utf-8'))
        self.summaries = []

        async def confirm(summary):
            self.summaries.append(summary)
            return answer

        return await cancel_doctolib(self.page, lambda text: None, confirm)

    async def test_confirmed_cancellation(self):
        result = await self.route()
        self.assertTrue(result[0])
        self.assertIn('Dr Martin', self.summaries[0])
        self.assertIn('12 décembre 2030 à 10h30', self.summaries[0])
        self.assertIn('Rendez-vous annulé', await self.page.locator('main').inner_text())

    async def test_declined_cancellation(self):
        result = await self.route(answer=False)
        self.assertFalse(result[0])
        self.assertEqual(await self.page.get_by_text('Rendez-vous annulé').count(), 0)
        self.assertTrue(await self.page.locator('#detail').is_visible())

    async def test_public_help_flow(self):
        body = FIXTURE.replace('Annuler le rendez-vous', 'Annuler le RDV').replace(
            '<p>Voulez-vous annuler ?</p>',
            '<button onclick="this.hidden=true;document.querySelector(\'select\').hidden=false">Continuer</button>'
            '<select hidden><option value="">Motif</option><option value="other">Autre</option></select>')
        self.assertTrue((await self.route(body))[0])

    async def test_empty_appointments(self):
        self.assertIsNone(await self.route('<main><h1>Rendez-vous à venir</h1><p>Aucun rendez-vous</p></main>'))
        self.assertEqual(self.summaries, [])

    async def test_missing_cancel_control(self):
        self.assertIsNone(await self.route(FIXTURE.replace('Annuler le rendez-vous', 'Indisponible')))
        self.assertEqual(self.summaries, [])

    async def test_submission_not_verified(self):
        body = FIXTURE.replace("document.querySelector('main').innerHTML='<h1>Rendez-vous annulé</h1>';", "document.querySelector('#modal').close();")
        result = await self.route(body)
        self.assertFalse(result[0])
        self.assertIn('vérifier', result[1])

    async def test_old_cancelled_appointment_does_not_verify_failed_cancellation(self):
        body = FIXTURE.replace('<main>', '<aside>Rendez-vous annulé — Dr Dupont — 1 janvier 2020 à 09h00</aside><main>').replace(
            "document.querySelector('main').innerHTML='<h1>Rendez-vous annulé</h1>';",
            "document.querySelector('#modal').close();")
        result = await self.route(body)
        self.assertFalse(result[0])
        self.assertIn('vérifier', result[1])
        self.assertTrue(await self.page.locator('#detail').is_visible())
