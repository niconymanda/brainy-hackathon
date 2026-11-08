"""Brainy desktop app: python -m brainy.app

Local bridge between the Brainy window (frontend/dist) and the backend:
microphone -> Gladia -> H agent (Playwright Chrome) -> events back to the window.
WebSocket contract: frontend/context/05-interface-back.md.
"""

import argparse
import asyncio
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from websockets.asyncio.server import serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Response

from brainy.agent.browser import Browser
from brainy.agent.forms import DoctolibPrefill, profile_fields
from brainy.agent.events import AgentError, AgentStep, ConfirmRequest, Done, NeedsUser
from brainy.agent.holo import HoloClient
from brainy.agent.route import CHALLENGE_BLOCKED, LOGIN_REQUIRED, book_doctolib, doctolib_url, has_specialty
from brainy.agent.loop import OUT_OF_BUDGET, SECRET_QUESTION, WebAgent

DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
HOME = Path(os.getenv("BRAINY_HOME", Path.home() / ".brainy"))
HISTORY_FILE = HOME / "history.json"
PROFILE_FILE = HOME / "profil.txt"
PROFILE_TEMPLATE = """# Ta fiche Brainy : l'agent s'en sert pour remplir les formulaires sans te poser de questions.
# Elle reste sur cet ordinateur. N'y mets jamais de mot de passe ni de carte bancaire.
# Complete apres les deux-points, enregistre (Ctrl+S) et ferme.
Prénom :
Nom :
Nom de naissance :
Date de naissance :
Ville de naissance :
Pays de naissance :
Sexe :
Adresse :
Téléphone :
E-mail :
"""

SITES = {
    "doctolib": "https://www.doctolib.fr",
    "sncf": "https://www.sncf-connect.com",
    "uber eats": "https://www.ubereats.com/fr",
    "ubereats": "https://www.ubereats.com/fr",
    "leboncoin": "https://www.leboncoin.fr",
    "amazon": "https://www.amazon.fr",
}
YES = re.compile(r"^\W*(oui|yes|ouais|vas-y|go|ok|okay|d'accord|parfait|c'est bon|confirme)\b", re.I)
NO = re.compile(r"^\W*(non|no|stop|arr[êe]t\w*|annule|on s['’]arr[êe]te|laisse tomber)\b", re.I)
DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
          "novembre", "décembre")
FRENCH = ("\nLanguage: write every narration and question in French, as one short spoken sentence "
          "addressed to the user (tutoiement).")
AUTONOMY = ("\nAutonomy: the user is delegating and does not want to be interrupted. The browser is signed in to "
            "the user's own account: treat its profile data (name, birth name, date of birth, address, phone, email) "
            "as correct, keep prefilled fields and continue without asking. Make reasonable choices yourself (first "
            "available slot matching the request, the visit reason closest to the request). Use ask_user only when a "
            "required choice truly cannot be inferred from the request or the account (e.g. which family member). "
            "Never invent personal data that is not in the request, the account or the user's answers (e.g. birth "
            "place, social security number): ask the user for it. "
            "If there is only one option (e.g. a single patient profile), select it. The specialty or category the "
            "user named is settled: never ask about it. Never ask to confirm intermediate steps; use confirm only for "
            "the final irreversible button (e.g. 'Confirmer le rendez-vous', 'Payer').")
OBVIOUS = re.compile(r"^\W*(est-ce que|veux-tu|tu veux|voulez-vous|je confirme|confirmes?-tu|dois-je|je peux|puis-je|"
                     r"peux-tu confirmer|c'est bien|ok pour|je (prends|sélectionne|choisis|continue|valide))|"
                     r"\b(est-(il|elle)|bien)\b", re.I)
OPEN_QUESTION = re.compile(r"\b(quel|quelle|quels|quelles|lequel|laquelle|combien|quand|où|comment|pourquoi)\b", re.I)
CHOICE = re.compile(r"(\w+),? ou (?:un |une |le |la |les |pour |l')?(\w+)", re.I)
AUTO_REPLY = ("Oui. Ne me demande pas de valider les étapes intermédiaires : choisis l'option la plus logique d'après "
              "ma demande et mon compte, et continue jusqu'à la confirmation finale.")
BUDGET = ("\nSpeed: book the first available slot on a day the request allows. Never go back to look for a "
          "better time. If nothing matches after checking about 3 practitioners, take the first available slot "
          "anyway and continue to the final confirmation.")
PERSONAL = re.compile(r"naissance|sécu|sécurité sociale|adresse|téléphone|e-mail|email|mot de passe|carte", re.I)
SITE_TIPS = {
    "doctolib": ("\nDoctolib tip: to search, navigate directly to https://www.doctolib.fr/<specialty>/<city> "
                 "(lowercase, hyphens, e.g. https://www.doctolib.fr/dermatologue/paris) instead of the search bar. "
                 "For an arrondissement or postal code, append it to the city: https://www.doctolib.fr/<specialty>/"
                 "<city>-<postal code> (e.g. 9e arrondissement de Paris = https://www.doctolib.fr/dermatologue/"
                 "paris-75009). The results are then already located: do not touch the location or Secteur filters. "
                 "If you use the search bar, pick a suggestion in the dropdown before pressing Rechercher. "
                 "Each result lists its next slots: click directly a slot that fits the request in the results list; "
                 "do not open a practitioner's profile that shows no matching slot. That URL may land on a "
                 "/search page: it already is the results list, so never click Rechercher, never reopen the search "
                 "and never retype the location; scroll down the list, skipping practitioners marked Aucune "
                 "disponibilité en ligne. Only click a slot on a day the "
                 "request allows. For the visit reason, take the first-visit one (e.g. Première consultation) unless "
                 "the request says it is a follow-up; never ask which reason. On the checkout form, fill each "
                 "empty field once, top to bottom, from the user's profile: Ville de naissance is the profile's birth "
                 "city only (type it, then click its suggestion with the department, e.g. 'Strasbourg (67)'), never "
                 "the address city; Adresse is the street only, then Code postal, then Ville = the address city. A "
                 "field already filled or with a green check is done: never retype it. Answer 'Avez-vous déjà "
                 "consulté ce soignant ?' with Non, then scroll to the final button."),
}
STUCK = re.compile(r"^I'm stuck: repeating '(.*)' has no visible effect\.", re.S)


def french_question(text):
    stuck = STUCK.match(text)
    if stuck:
        return (f"Je bloque : « {stuck.group(1)} » ne donne rien. "
                "Je tente autre chose ? Ou fais-le à la main et dis-moi « ok ».")
    if text == OUT_OF_BUDGET:
        return "Ça prend plus de temps que prévu. Je continue, ou on s'arrête là ?"
    return text


def open_choice(question, request):
    """An 'X ou Y' alternative, unless it only restates the request (e.g. 'mardi ou mercredi') or is a final 'ou pas'."""
    said = request.casefold()
    for match in CHOICE.finditer(question):
        first, second = match[1].casefold(), match[2].casefold()
        if second in {"pas", "non"} and not re.search(r"\w", question[match.end():]):
            continue
        if not all(re.search(rf"\b{re.escape(word.removesuffix('s'))}s?\b", said) for word in (first, second)):
            return True
    return False


def obvious_question(question, request=""):
    """Yes/no check-ins the agent should settle itself; open questions, secrets and the budget check go to the user."""
    sentences = re.split(r"(?<=[.!?])\s+", question.strip())
    questions = [s for s in sentences if s.endswith("?")] or sentences[-1:]
    return (bool(OBVIOUS.search(questions[-1])) and not any(OPEN_QUESTION.search(q) for q in questions)
            and not open_choice(question, request)
            and not SECRET_QUESTION.search(question) and question != french_question(OUT_OF_BUDGET))


def read_profile():
    try:
        return PROFILE_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def load_profile():
    lines = read_profile().splitlines()
    facts = [line.strip() for line in lines
             if line.strip() and not line.lstrip().startswith("#") and line.split(":", 1)[-1].strip()]
    if not facts:
        return ""
    return ("\nThe user's profile (use it to fill forms, never ask for it):\n- " + "\n- ".join(facts))


def open_profile():
    """Create the profile file from the template if needed and open it in a text editor."""
    HOME.mkdir(parents=True, exist_ok=True)
    if not PROFILE_FILE.exists():
        PROFILE_FILE.write_text(PROFILE_TEMPLATE, encoding="utf-8")
        PROFILE_FILE.chmod(0o600)
    print(f"Fiche profil : {PROFILE_FILE}")
    try:
        if sys.platform == "win32":
            os.startfile(PROFILE_FILE)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-t", str(PROFILE_FILE)], check=False)
        else:
            subprocess.run(["xdg-open", str(PROFILE_FILE)], check=False)
    except OSError:
        print("Ouvre ce fichier dans un éditeur de texte.")


def brainy_goal(request, now=None):
    now = now or datetime.now()
    today = f"{DAYS[now.weekday()]} {now.day} {MONTHS[now.month - 1]} {now.year}"
    return (f"The user asked (spoken and transcribed, may contain small transcription errors):\n{request}\n\n"
            f"Today is {today}. Resolve relative dates yourself (e.g. 'mardi' = the next Tuesday, 'tous les "
            "mardis' = any Tuesday). Everything stated in the request is settled: never ask about it again. Times "
            "like 'vers 13h' or 'l'après-midi' are soft hints: the first available slot on an allowed day is fine. If a required "
            "detail is truly missing, use ask_user; never use done to ask a question. Use done only when the task "
            "is complete, with a short summary of what was done. If it cannot be done, use ask_user to say why and "
            "propose the closest alternative.")


def site_tips(text):
    lowered = text.lower()
    return "".join(tip for name, tip in SITE_TIPS.items() if name in lowered)


SILENCE_SECONDS = float(os.getenv("BRAINY_SILENCE", "2.0"))
MAX_LISTEN_SECONDS = 60


def start_url_for(text):
    lowered = text.lower()
    return next((url for name, url in SITES.items() if name in lowered), None)


def load_history():
    try:
        return json.loads(HISTORY_FILE.read_text())
    except (OSError, ValueError):
        return []


def save_history(items):
    HOME.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(items[:50], ensure_ascii=False, indent=1))


def french_done(result):
    if result.startswith("Stopped at your request"):
        return False, "D'accord, j'arrête là."
    if result.startswith("Action skipped"):
        return False, "D'accord, je n'ai rien validé."
    return True, result


def french_error(error):
    if "step limit" in error.reason:
        return "J'ai fait beaucoup d'étapes sans terminer.", "Essaie une demande plus simple, ou termine à la main."
    return "Je n'ai pas réussi à terminer.", "Vérifie la connexion et réessaie."


class BrainyApp:
    """Shared state: one browser and one agent run at a time."""

    def __init__(self, args):
        self.args = args
        self.browser = None
        self.browser_lock = asyncio.Lock()
        self.history = load_history()
        self.agent_task = None
        self.sessions = set()

    def broadcast(self, **event):
        for session in self.sessions:
            session.emit(**event)

    async def get_browser(self):
        async with self.browser_lock:
            if self.browser is not None and not self.browser._context_closed:
                return self.browser
            HOME.mkdir(parents=True, exist_ok=True)
            profile = str(HOME / "chrome-profile")
            for channel in (self.args.channel, None) if self.args.channel else (None,):
                try:
                    self.browser = await Browser(
                        headless=False, profile_dir=profile, channel=channel,
                    ).__aenter__()
                    return self.browser
                except Exception as exc:
                    print(f"Browser launch failed (channel={channel}): {type(exc).__name__}", file=sys.stderr)
            raise RuntimeError("Unable to launch a browser")

    async def warm_up(self):
        """Open the agent's browser as soon as Brainy starts, so the first request does not wait for it."""
        try:
            await self.get_browser()
        except Exception as exc:
            print(f"Browser warm-up failed: {type(exc).__name__}", file=sys.stderr)

    async def close(self):
        if self.browser is not None:
            await self.browser.__aexit__(None, None, None)


class Session:
    """One connected Brainy window."""

    def __init__(self, app, ws):
        self.app = app
        self.ws = ws
        self.outbox = asyncio.Queue()
        self.listen_task = None
        self.stop = None
        self.answer = None
        self.auto_reply = None
        self.confirming = False
        self.shot_count = 0
        self.shot_tasks = set()

    def emit(self, **event):
        self.outbox.put_nowait(event)
        if event.get("type") == "agent_step" and os.getenv("BRAINY_SHOTS"):
            self.shot_count += 1
            task = asyncio.create_task(self._save_screenshot(self.shot_count))
            self.shot_tasks.add(task)
            task.add_done_callback(self.shot_tasks.discard)

    async def _save_screenshot(self, number):
        try:
            browser = self.app.browser
            if browser is None:
                return
            directory = Path(os.environ["BRAINY_SHOTS"])
            directory.mkdir(parents=True, exist_ok=True)
            image = await browser.screenshot()
            await asyncio.to_thread((directory / f"step-{number:03d}.jpg").write_bytes, image)
        except Exception as exc:
            print(f"Screenshot failed: {type(exc).__name__}", file=sys.stderr)

    async def pump(self):
        while True:
            event = await self.outbox.get()
            await self.ws.send(json.dumps(event, ensure_ascii=False))

    async def run(self):
        pump = asyncio.create_task(self.pump())
        self.app.sessions.add(self)
        self.emit(type="history", items=self.app.history)
        try:
            async for raw in self.ws:
                try:
                    await self.handle(json.loads(raw))
                except (ValueError, KeyError, TypeError):
                    continue
        except ConnectionClosed:
            pass
        finally:
            self.app.sessions.discard(self)
            if self.stop:
                self.stop.set()
            if self.answer and not self.answer.done():
                self.answer.set_result("non")
            pump.cancel()
            if self.shot_tasks:
                await asyncio.gather(*self.shot_tasks, return_exceptions=True)

    async def handle(self, msg):
        kind = msg.get("type")
        if kind == "start_listening":
            if self.listen_task and not self.listen_task.done():
                return
            self.stop = asyncio.Event()
            self.listen_task = asyncio.create_task(self.listen())
        elif kind == "stop_listening":
            if self.stop:
                self.stop.set()
        elif kind == "user_text":
            await self.on_text(str(msg["text"]))
        elif kind == "confirm":
            self.reply("oui" if msg.get("answer") == "oui" else "non")

    def reply(self, text):
        if self.answer and not self.answer.done():
            self.answer.set_result(text)
            return True
        return False

    async def listen(self):
        from brainy.stt.audio import microphone_audio
        from brainy.stt.client import GladiaClient

        self.emit(type="listening")
        finals, partial = [], ""
        last = time.monotonic()
        started = last

        def on_transcript(t):
            nonlocal partial, last
            last = time.monotonic()
            if t.is_final:
                finals.append(t.text.strip())
                partial = ""
            else:
                partial = t.text.strip()
            self.emit(type="transcript", text=" ".join([*finals, partial]).strip(), final=t.is_final)

        async def auto_stop():
            while not self.stop.is_set():
                await asyncio.sleep(0.2)
                now = time.monotonic()
                if (finals and not partial and now - last > SILENCE_SECONDS) or now - started > MAX_LISTEN_SECONDS:
                    self.stop.set()

        watchdog = asyncio.create_task(auto_stop())
        audio_queue = asyncio.Queue()

        async def capture_audio():
            try:
                async for chunk in microphone_audio(self.app.args.device):
                    await audio_queue.put(chunk)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await audio_queue.put(exc)
            finally:
                await audio_queue.put(None)

        async def buffered_audio():
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    return
                if isinstance(chunk, Exception):
                    raise chunk
                yield chunk

        capture_task = asyncio.create_task(capture_audio())
        try:
            await asyncio.sleep(0)
            client = GladiaClient(os.getenv("GLADIA_API_KEY", ""), self.app.args.language)
            await client.transcribe(buffered_audio(), on_transcript, self.stop)
        except Exception as exc:
            print(f"Listening failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            self.emit(type="error", reason="Je n'arrive pas à t'entendre.",
                      suggestion="Vérifie le micro et la clé Gladia, ou écris ta demande au clavier.")
            return
        finally:
            watchdog.cancel()
            capture_task.cancel()
            await asyncio.gather(capture_task, return_exceptions=True)
        await self.on_text(" ".join([*finals, partial]).strip())

    async def on_text(self, text):
        if not text:
            self.emit(type="error", reason="Je n'ai rien entendu.", suggestion="Appuie sur H et parle-moi.")
            return
        if self.answer and not self.answer.done():
            # An open answer like "non, plutôt lundi à 13h" is passed on as is, not read as "stop".
            match = YES.match(text) or NO.match(text)
            if match and (self.confirming or not re.search(r"\w", re.sub(r"merci( beaucoup)?", "", text[match.end():], flags=re.I))):
                text = "oui" if YES.match(text) else "non"
            self.reply(text)
            return
        if self.app.agent_task and not self.app.agent_task.done():
            self.emit(type="say", text="Je suis encore sur la demande précédente.")
            return
        self.app.agent_task = asyncio.create_task(self.run_agent(text))

    async def ask(self, question):
        if self.auto_reply:
            reply, self.auto_reply = self.auto_reply, None
            return reply
        self.answer = asyncio.get_running_loop().create_future()
        try:
            return await self.answer
        finally:
            self.answer = None

    def _say(self, text):
        self.emit(type="agent_step", narration=text, action="route")

    def _route_page(self, page_type, path):
        self.emit(type="route_page", page_type=page_type, path=path)

    async def _confirm(self, summary):
        self.confirming = True
        self.emit(type="confirm_request", summary=summary)
        try:
            return bool(YES.match(await self.ask(summary) or ""))
        finally:
            self.confirming = False

    async def run_agent(self, request):
        self.emit(type="say", text="C'est noté, je m'en occupe.")
        title = request if len(request) <= 48 else request[:47].rstrip() + "…"
        status, tone = "Arrêté", "wait"
        try:
            route = doctolib_url(request) if not os.getenv("BRAINY_NO_ROUTE") else None
            medical_booking = bool(re.search(
                r"\b(?:rdv|rendez[\s-]?vous|r[ée]serv(?:e|er|ation)|doctolib|m[ée]decin|docteur|arrondissement)\b"
                r"|\b\d{1,2}\s*(?:e|ème|eme)\b", request, re.I))
            while medical_booking and not has_specialty(request):
                self.emit(type="needs_user",
                          question="Quel type de médecin ? Par exemple dermatologue ou dentiste.")
                answer = await self.ask("Quel type de médecin ? Par exemple dermatologue ou dentiste.")
                if not answer:
                    break
                request = f"{request} {answer}"
                route = doctolib_url(request)
            if medical_booking and not route:
                if has_specialty(request):
                    self.emit(type="error", reason="Je ne trouve pas la recherche Doctolib demandée.",
                              suggestion="Précise la spécialité ou la ville.")
                return
            key = os.getenv("H_API_KEY") or os.getenv("HCOMPANY_API_KEY", "")
            client = HoloClient(key, self.app.args.model)
            browser = await self.app.get_browser()
            if route:
                try:
                    booked = await book_doctolib(await browser.ensure_page(), route, self._say, self._confirm,
                                                 request=request, on_page=self._route_page)
                except Exception as exc:
                    print(f"Route failed: {type(exc).__name__}: {exc}", file=sys.stderr)
                    booked = None
                if booked:
                    ok, result = booked
                    if result == LOGIN_REQUIRED:
                        self.emit(type="login_required", url=browser.page.url,
                                  selected_slot=getattr(browser.page, "_brainy_selected_slot", None))
                        result = "Connexion Doctolib requise pour continuer."
                    elif result == CHALLENGE_BLOCKED:
                        self.emit(type="challenge_blocked", url=browser.page.url)
                        result = "Vérification humaine requise par Doctolib."
                    if ok:
                        status, tone = "Terminé", "paid"
                    self.emit(type="done", result=result, ok=ok)
                    return
                self.emit(type="agent_step", narration="Je continue sur la page.", action="auto")
            goal = brainy_goal(request) + load_profile() + FRENCH + AUTONOMY + BUDGET + site_tips(request)
            args = self.app.args
            agent = WebAgent(client, browser, self.ask, max_steps=args.max_steps,
                             wrap_up_steps=getattr(args, "search_steps", None),
                             wrap_up_seconds=getattr(args, "search_seconds", None), wrap_up_grace=15,
                             gate_narration=False, prefill=DoctolibPrefill(profile_fields(read_profile())))
            async for event in agent.run(goal, start_url_for(request)):
                if isinstance(event, AgentStep):
                    if event.action not in {"done", "ask_user", "confirm"}:
                        self.emit(type="agent_step", narration=event.narration or "Je continue.", action=event.action)
                elif isinstance(event, NeedsUser):
                    self.confirming = False
                    question = french_question(event.question)
                    # Hackathon demo: the agent settles every question itself, except secrets and personal data.
                    if not SECRET_QUESTION.search(question) and not PERSONAL.search(question):
                        self.auto_reply = AUTO_REPLY
                        self.emit(type="agent_step", narration="Je choisis l'option évidente et je continue.",
                                  action="auto")
                    else:
                        self.emit(type="needs_user", question=question)
                elif isinstance(event, ConfirmRequest):
                    self.confirming = True
                    self.emit(type="confirm_request", summary=event.summary)
                elif isinstance(event, Done):
                    ok, result = french_done(event.result)
                    if ok:
                        status, tone = "Terminé", "paid"
                    self.emit(type="done", result=result, ok=ok)
                elif isinstance(event, AgentError):
                    print(f"Agent error: {event.reason} {event.suggestion}", file=sys.stderr)
                    reason, suggestion = french_error(event)
                    status, tone = "Échec", "wait"
                    self.emit(type="error", reason=reason, suggestion=suggestion)
        except Exception as exc:
            print(f"Agent failed: {type(exc).__name__}", file=sys.stderr)
            status, tone = "Échec", "wait"
            self.emit(type="error", reason="L'agent n'a pas pu démarrer.",
                      suggestion="Vérifie la clé H Company et le navigateur.")
        finally:
            when = datetime.now().strftime("%d/%m, %Hh%M")
            self.app.history.insert(0, {"title": title, "when": when, "status": status, "tone": tone, "isNew": True})
            save_history([{**item, "isNew": False} for item in self.app.history])
            self.emit(type="history", items=self.app.history)


def static_response(path):
    rel = path.split("?", 1)[0].lstrip("/") or "index.html"
    file = (DIST / rel).resolve()
    if not file.is_relative_to(DIST.resolve()) or not file.is_file():
        file = DIST / "index.html"
    if not file.is_file():
        body = b"frontend/dist is missing: run `npm install && npm run build` in frontend/"
        return Response(500, "Internal Server Error", Headers([("Content-Type", "text/plain")]), body)
    body = file.read_bytes()
    headers = Headers([
        ("Content-Type", mimetypes.guess_type(file.name)[0] or "application/octet-stream"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-cache"),
    ])
    return Response(200, "OK", headers, body)


async def login(args):
    """Open the agent's browser profile so the user can sign in once; cookies persist for later runs."""
    app = BrainyApp(args)
    browser = await app.get_browser()
    await browser.goto(args.login)
    print("Connecte-toi dans la fenêtre du navigateur, puis ferme-la.")
    while not browser._context_closed:
        await asyncio.sleep(1)
    await app.close()


def start_hotkey(combo, loop, app):
    """Global shortcut (works when Brainy is in the background). macOS asks for Accessibility access."""
    try:
        from pynput import keyboard

        def pressed():
            loop.call_soon_threadsafe(lambda: app.broadcast(type="hotkey"))

        listener = keyboard.GlobalHotKeys({combo: pressed})
        listener.daemon = True
        listener.start()
    except Exception as exc:
        print(f"Global hotkey disabled ({type(exc).__name__}); use H in the Brainy window.", file=sys.stderr)


async def serve_app(args, ready, shutdown=None):
    app = BrainyApp(args)
    warm_up = asyncio.create_task(app.warm_up())
    if getattr(args, "hotkey", ""):
        start_hotkey(args.hotkey, asyncio.get_running_loop(), app)

    def process_request(connection, request):
        if request.path.split("?", 1)[0] == "/ws":
            return None
        return static_response(request.path)

    async def handler(ws):
        await Session(app, ws).run()

    async with serve(handler, "127.0.0.1", args.port, process_request=process_request, max_size=2**20):
        ready.set()
        try:
            if shutdown is None:
                await asyncio.Future()
            else:
                await asyncio.to_thread(shutdown.wait)
        finally:
            warm_up.cancel()
            await asyncio.gather(warm_up, return_exceptions=True)
            await app.close()


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Brainy desktop app (window + local bridge).")
    parser.add_argument("--port", type=int, default=int(os.getenv("BRAINY_PORT", "8765")))
    parser.add_argument("--no-window", action="store_true", help="Only run the server; open the URL in a browser.")
    parser.add_argument("--language", action="append", default=None, metavar="CODE",
                        help="Gladia language code, repeatable (default: fr).")
    parser.add_argument("--device", help="Microphone device index or name.")
    parser.add_argument("--hotkey", default=os.getenv("BRAINY_HOTKEY", "<ctrl>+<alt>+h"),
                        help="Global shortcut (pynput syntax); empty to disable.")
    parser.add_argument("--channel", default=os.getenv("BRAINY_BROWSER_CHANNEL",
                                                       "msedge" if sys.platform == "win32" else "chrome"),
                        help="Installed browser for the agent (chrome, msedge); falls back to bundled Chromium.")
    parser.add_argument("--model", default=os.getenv("H_MODEL") or "holo4-35b-a3b")
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--search-steps", type=int, default=int(os.getenv("BRAINY_SEARCH_STEPS", "25")),
                        help="Steps without user input before Brainy stops searching and proposes the best option.")
    parser.add_argument("--search-seconds", type=float, default=float(os.getenv("BRAINY_SEARCH_SECONDS", "240")),
                        help="Same limit in seconds.")
    parser.add_argument("--login", metavar="URL", nargs="?", const="https://www.doctolib.fr/sessions/new",
                        help="Only open the agent's browser to sign in to a site once (default: Doctolib).")
    parser.add_argument("--profile", action="store_true",
                        help="Open the profile file (birth date, address...) the agent uses to fill forms.")
    args = parser.parse_args()
    args.language = args.language or ["fr"]
    if args.device and args.device.isdecimal():
        args.device = int(args.device)

    if args.login:
        asyncio.run(login(args))
        return 0
    if args.profile:
        open_profile()
        return 0

    ready = threading.Event()
    shutdown = threading.Event()
    server = threading.Thread(target=lambda: asyncio.run(serve_app(args, ready, shutdown)), daemon=True)
    server.start()
    if not ready.wait(10):
        print("Server failed to start (port already in use?)", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{args.port}/?app&ws=ws://127.0.0.1:{args.port}/ws"
    if args.no_window:
        print(f"Brainy is running: {url}")
        try:
            server.join()
        except KeyboardInterrupt:
            shutdown.set()
            server.join(timeout=10)
            return 0
        return 0

    import webview

    screen = webview.screens[0] if webview.screens else None
    width, height = 360, 560
    x = y = None
    if screen and screen.width > width + 24 and screen.height > height + 60:
        x, y = screen.width - width - 24, 60
    webview.create_window("Brainy", url, width=width, height=height, x=x, y=y,
                          on_top=True, resizable=False, background_color="#FFFFFF")
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
