import argparse
import asyncio
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from websockets.asyncio.client import connect

import brainy.app as app_module
from brainy.agent.holo import Action


class FakeBrowser:
    viewport = (1280, 900)

    def __init__(self):
        self.visited = []
        self.clicks = 0

    async def start_run(self):
        pass

    async def take_recovery_notes(self):
        return []

    async def goto(self, url):
        self.visited.append(url)

    async def screenshot(self):
        return f"shot{self.clicks}".encode()

    async def page_context(self):
        return {"url": self.visited[-1] if self.visited else "about:blank", "title": "", "text": ""}

    async def click(self, x, y):
        self.clicks += 1

    async def type(self, text):
        return text

    async def scroll(self, direction):
        pass


class FakeHolo:
    script = [
        Action("click", target="Dermatologue", narration="Je cherche un dermatologue."),
        Action("confirm", target="Réserver", narration="Je réserve samedi 21 à 10h30 ?"),
        Action("done", text="Rendez-vous réservé samedi 21 à 10h30."),
    ]

    def __init__(self, api_key, model):
        self.steps = iter(self.script)

    async def decide(self, screenshot, goal, history, page_context=None):
        FakeHolo.goal, FakeHolo.history = goal, list(history)
        return next(self.steps)

    async def locate(self, screenshot, description, viewport):
        return 10, 10


class AppTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.browser = FakeBrowser()
        patches = [
            patch.object(app_module, "HISTORY_FILE", Path(self.tmp.name) / "history.json"),
            patch.object(app_module, "PROFILE_FILE", Path(self.tmp.name) / "profil.txt"),
            patch.object(app_module, "HoloClient", FakeHolo),
            patch.object(app_module.BrainyApp, "get_browser", self.fake_browser),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        args = argparse.Namespace(port=8799, language=["fr"], device=None, channel=None,
                                  model="m", max_steps=10)
        self.ready = asyncio.Event()
        self.server = asyncio.create_task(app_module.serve_app(args, self.ready))
        await asyncio.wait_for(self.ready.wait(), 5)

    async def fake_browser(self, _app=None):
        return self.browser

    async def asyncTearDown(self):
        self.server.cancel()
        await asyncio.gather(self.server, return_exceptions=True)
        self.tmp.cleanup()

    async def recv_until(self, ws, kind):
        events = []
        while True:
            event = json.loads(await asyncio.wait_for(ws.recv(), 5))
            events.append(event)
            if event["type"] == kind:
                return events

    async def test_text_request_confirm_and_done(self):
        async with connect("ws://127.0.0.1:8799/ws") as ws:
            self.assertEqual(json.loads(await ws.recv())["type"], "history")
            await ws.send(json.dumps({"type": "user_text", "text": "Un dermato sur Doctolib samedi"}))
            events = await self.recv_until(ws, "confirm_request")
            kinds = [e["type"] for e in events]
            self.assertEqual(kinds[0], "say")
            self.assertIn("agent_step", kinds)
            self.assertEqual(self.browser.visited, ["https://www.doctolib.fr"])
            self.assertIn("profile data", FakeHolo.goal)
            self.assertIn("Never invent personal data", FakeHolo.goal)
            self.assertEqual(self.browser.clicks, 1)
            await ws.send(json.dumps({"type": "confirm", "answer": "oui"}))
            events = await self.recv_until(ws, "history")
            done = next(e for e in events if e["type"] == "done")
            self.assertTrue(done["ok"])
            self.assertIn("10h30", done["result"])
            self.assertEqual(events[-1]["items"][0]["status"], "Terminé")
            self.assertEqual(self.browser.clicks, 2)

    async def test_obvious_question_answered_without_user(self):
        script = [Action("ask_user", text="Est-ce que je prends le rendez-vous pour toi ?"),
                  Action("done", text="Fini.")]
        with patch.object(FakeHolo, "script", script):
            async with connect("ws://127.0.0.1:8799/ws") as ws:
                await ws.recv()
                await ws.send(json.dumps({"type": "user_text", "text": "Un dermato"}))
                events = await self.recv_until(ws, "done")
        self.assertNotIn("needs_user", [e["type"] for e in events])
        self.assertTrue(events[-1]["ok"])

    async def test_mic_click_answers_a_question(self):
        class FakeGladia:
            def __init__(self, *args):
                pass

            async def transcribe(self, audio, on_transcript, stop):
                on_transcript(type("T", (), {"text": "Pour Léo", "is_final": True})())
                await stop.wait()

        script = [Action("ask_user", text="Pour Léo ou pour Inès ?"), Action("done", text="Fini.")]
        with patch.object(FakeHolo, "script", script), patch.object(app_module, "SILENCE_SECONDS", 0.1), \
                patch("brainy.stt.client.GladiaClient", FakeGladia), \
                patch("brainy.stt.audio.microphone_audio", lambda device: None):
            async with connect("ws://127.0.0.1:8799/ws") as ws:
                await ws.recv()
                await ws.send(json.dumps({"type": "user_text", "text": "Un dentiste"}))
                await self.recv_until(ws, "needs_user")
                await ws.send(json.dumps({"type": "start_listening"}))
                events = await self.recv_until(ws, "done")
        kinds = [e["type"] for e in events]
        self.assertLess(kinds.index("listening"), kinds.index("transcript"))
        self.assertTrue(events[-1]["ok"])
        self.assertIn("Pour Léo", json.dumps(FakeHolo.history, ensure_ascii=False))

    async def test_question_after_budget_goes_to_user(self):
        script = [Action("scroll", text="down"), Action("ask_user", text="Est-ce que je continue ou pas ?"),
                  Action("done", text="Fini.")]
        with patch.object(FakeHolo, "script", script), \
                patch("brainy.agent.loop.WebAgent._over_budget", lambda *a: True):
            async with connect("ws://127.0.0.1:8799/ws") as ws:
                await ws.recv()
                await ws.send(json.dumps({"type": "user_text", "text": "Un dermato"}))
                events = await self.recv_until(ws, "needs_user")
        self.assertEqual(events[-1]["question"], "Est-ce que je continue ou pas ?")

    async def test_open_answer_starting_with_non_continues(self):
        script = [Action("ask_user", text="Quel jour ?"), Action("done", text="Fini.")]
        with patch.object(FakeHolo, "script", script):
            async with connect("ws://127.0.0.1:8799/ws") as ws:
                await ws.recv()
                await ws.send(json.dumps({"type": "user_text", "text": "Un dermato"}))
                await self.recv_until(ws, "needs_user")
                await ws.send(json.dumps({"type": "user_text", "text": "Non, plutôt lundi"}))
                events = await self.recv_until(ws, "done")
        self.assertTrue(events[-1]["ok"])
        self.assertIn("User answered: Non, plutôt lundi", FakeHolo.history)

    async def test_refused_confirmation_clicks_nothing(self):
        async with connect("ws://127.0.0.1:8799/ws") as ws:
            await ws.recv()
            await ws.send(json.dumps({"type": "user_text", "text": "Un dermato"}))
            await self.recv_until(ws, "confirm_request")
            await ws.send(json.dumps({"type": "user_text", "text": "Non merci"}))
            events = await self.recv_until(ws, "done")
            self.assertFalse(events[-1]["ok"])
            self.assertEqual(self.browser.clicks, 1)

    async def test_voice_request_auto_stops_after_silence(self):
        async def transcribe(self_client, audio, callback, stop):
            from brainy.stt import Transcript
            callback(Transcript("Un dermato", False, "1"))
            callback(Transcript("Un dermato samedi", True, "1"))
            await stop.wait()

        async def no_audio(device=None):
            yield b""

        with patch("brainy.stt.client.GladiaClient.transcribe", transcribe), \
                patch("brainy.stt.audio.microphone_audio", no_audio), \
                patch.object(app_module, "SILENCE_SECONDS", 0.3), \
                patch.dict("os.environ", {"GLADIA_API_KEY": "k"}):
            async with connect("ws://127.0.0.1:8799/ws") as ws:
                await ws.recv()
                await ws.send(json.dumps({"type": "start_listening"}))
                events = await self.recv_until(ws, "say")
                kinds = [e["type"] for e in events]
                self.assertEqual(kinds[0], "listening")
                self.assertEqual(events[-2], {"type": "transcript", "text": "Un dermato samedi", "final": True})

    async def test_static_fallback(self):
        response = app_module.static_response("/../../etc/passwd")
        self.assertIn(response.status_code, (200, 500))
        self.assertNotIn(b"root:", response.body)


class HelperTests(unittest.TestCase):
    def test_start_url(self):
        self.assertEqual(app_module.start_url_for("Prends-moi un RDV sur Doctolib"), "https://www.doctolib.fr")
        self.assertIsNone(app_module.start_url_for("Réserve un restaurant"))

    async def test_profile_reaches_the_goal(self):
        (Path(self.tmp.name) / "profil.txt").write_text(
            app_module.PROFILE_TEMPLATE.replace("Ville de naissance :", "Ville de naissance : Lyon"), encoding="utf-8")
        async with connect("ws://127.0.0.1:8799/ws") as ws:
            await ws.recv()
            await ws.send(json.dumps({"type": "user_text", "text": "Un dermato sur Doctolib samedi"}))
            await self.recv_until(ws, "confirm_request")
            self.assertIn("never ask for it):\n- Ville de naissance : Lyon", FakeHolo.goal)
            self.assertNotIn("Prénom", FakeHolo.goal)
            self.assertNotIn("carte bancaire", FakeHolo.goal)
            await ws.send(json.dumps({"type": "confirm", "answer": "non"}))
            await self.recv_until(ws, "done")

    def test_goal_carries_request_and_date(self):
        goal = app_module.brainy_goal("Un dermato mardi vers 13h", datetime(2026, 11, 7))
        self.assertIn("Un dermato mardi vers 13h", goal)
        self.assertIn("Today is samedi 7 novembre 2026", goal)
        self.assertIn("never use done to ask", goal)
        self.assertNotIn("complete or impossible", goal)
        self.assertNotIn("list the questions", goal)

    def test_obvious_questions(self):
        for q in ("Est-ce que tu veux bien que je prenne le rendez-vous pour toi ?",
                  "Je confirme la sélection de la catégorie dermatologue ?",
                  "Ton nom de naissance est-il Esposito-Farès ?", "Est-ce que je continue ou pas ?",
                  "Je cherche un dermatologue. Je vise un créneau vers 13h. "
                  "Veux-tu que je prenne la première option disponible ?"):
            self.assertTrue(app_module.obvious_question(q), q)
        request = "Un dermatologue un mardi ou un mercredi vers 13h"
        self.assertTrue(app_module.obvious_question(
            "Je vise un mardi ou un mercredi. Veux-tu que je prenne la première option ?", request))
        self.assertTrue(app_module.obvious_question("Est-ce que je continue ? Je vais cliquer sur Suivant."))
        self.assertFalse(app_module.obvious_question(
            "Il y a Léo ou Inès. Est-ce que je réserve pour Léo ?", request))
        for q in ("Quel âge a le patient ?", "Peux-tu entrer ton mot de passe ?",
                  "Pour Léo ou pour Inès ?", "Est-ce que je réserve pour Léo ou pour Inès ?",
                  "Est-ce que je choisis un billet remboursable ou non remboursable ?",
                  "Je cherche un mardi ou un mercredi. Est-ce que je prends le Dr Martin ou le Dr Durand ?",
                  app_module.french_question(app_module.OUT_OF_BUDGET)):
            self.assertFalse(app_module.obvious_question(q), q)

    def test_yes_no(self):
        self.assertTrue(app_module.YES.search("Oui, parfait, merci !"))
        self.assertFalse(app_module.YES.search("Non"))
        self.assertTrue(app_module.NO.search("non merci"))
        for text in ("On s'arrête là.", "arrêter", "Laisse tomber"):
            self.assertTrue(app_module.NO.search(text), text)


class FrenchTests(unittest.TestCase):
    def test_stuck_question_is_translated(self):
        self.assertIn("Je continue", app_module.french_question(app_module.OUT_OF_BUDGET))
        q = app_module.french_question("I'm stuck: repeating 'Bouton Rechercher' has no visible effect. Should I try?")
        self.assertIn("Je bloque", q)
        self.assertIn("Bouton Rechercher", q)

    def test_doctolib_tip_only_for_doctolib(self):
        self.assertIn("doctolib.fr/dermatologue/paris", app_module.site_tips("Cherche sur Doctolib"))
        self.assertEqual(app_module.site_tips("Commande une pizza"), "")


class LoginTests(unittest.TestCase):
    def test_login_opens_url_and_waits_for_close(self):
        class FakeBrowser:
            _context_closed = False
            visited = None

            async def goto(self, url):
                self.visited = url
                self._context_closed = True

            async def __aexit__(self, *exc):
                pass

        fake = FakeBrowser()
        args = argparse.Namespace(login="https://www.doctolib.fr/sessions/new", channel=None)

        async def get_browser(self):
            self.browser = fake
            return fake

        with patch.object(app_module.BrainyApp, "get_browser", get_browser):
            asyncio.run(app_module.login(args))
        self.assertEqual(fake.visited, "https://www.doctolib.fr/sessions/new")
