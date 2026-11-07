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
from brainy.agent.events import AgentError, AgentStep, ConfirmRequest, Done, NeedsUser
from brainy.agent.holo import HoloClient
from brainy.agent.loop import WebAgent
from brainy.h_task import build_h_prompt

DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
HOME = Path(os.getenv("BRAINY_HOME", Path.home() / ".brainy"))
HISTORY_FILE = HOME / "history.json"

SITES = {
    "doctolib": "https://www.doctolib.fr",
    "sncf": "https://www.sncf-connect.com",
    "uber eats": "https://www.ubereats.com/fr",
    "ubereats": "https://www.ubereats.com/fr",
    "leboncoin": "https://www.leboncoin.fr",
    "amazon": "https://www.amazon.fr",
}
YES = re.compile(r"^\W*(oui|yes|ouais|vas-y|go|ok|okay|d'accord|parfait|c'est bon|confirme)\b", re.I)
NO = re.compile(r"^\W*(non|no|stop|arrête|annule)\b", re.I)
FRENCH = ("\nLanguage: write every narration and question in French, as one short spoken sentence "
          "addressed to the user (tutoiement).")
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
        self.history = load_history()
        self.agent_task = None

    async def get_browser(self):
        if self.browser is not None and not self.browser._context_closed:
            return self.browser
        HOME.mkdir(parents=True, exist_ok=True)
        profile = str(HOME / "chrome-profile")
        for channel in (self.args.channel, None) if self.args.channel else (None,):
            try:
                self.browser = await Browser(headless=False, profile_dir=profile, channel=channel).__aenter__()
                return self.browser
            except Exception as exc:
                print(f"Browser launch failed (channel={channel}): {type(exc).__name__}", file=sys.stderr)
        raise RuntimeError("Unable to launch a browser")

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

    def emit(self, **event):
        self.outbox.put_nowait(event)

    async def pump(self):
        while True:
            event = await self.outbox.get()
            await self.ws.send(json.dumps(event, ensure_ascii=False))

    async def run(self):
        pump = asyncio.create_task(self.pump())
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
            if self.stop:
                self.stop.set()
            if self.answer and not self.answer.done():
                self.answer.set_result("non")
            pump.cancel()

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
        try:
            client = GladiaClient(os.getenv("GLADIA_API_KEY", ""), self.app.args.language)
            await client.transcribe(microphone_audio(self.app.args.device), on_transcript, self.stop)
        except Exception as exc:
            print(f"Listening failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            self.emit(type="error", reason="Je n'arrive pas à t'entendre.",
                      suggestion="Vérifie le micro et la clé Gladia, ou écris ta demande au clavier.")
            return
        finally:
            watchdog.cancel()
        await self.on_text(" ".join([*finals, partial]).strip())

    async def on_text(self, text):
        if not text:
            self.emit(type="error", reason="Je n'ai rien entendu.", suggestion="Appuie sur H et parle-moi.")
            return
        if self.answer and not self.answer.done():
            self.reply("oui" if YES.search(text) else "non" if NO.search(text) else text)
            return
        if self.app.agent_task and not self.app.agent_task.done():
            self.emit(type="say", text="Je suis encore sur la demande précédente.")
            return
        self.app.agent_task = asyncio.create_task(self.run_agent(text))

    async def ask(self, question):
        self.answer = asyncio.get_running_loop().create_future()
        try:
            return await self.answer
        finally:
            self.answer = None

    async def run_agent(self, request):
        self.emit(type="say", text="C'est noté, je m'en occupe.")
        title = request if len(request) <= 48 else request[:47].rstrip() + "…"
        status, tone = "Arrêté", "wait"
        try:
            key = os.getenv("H_API_KEY") or os.getenv("HCOMPANY_API_KEY", "")
            client = HoloClient(key, self.app.args.model)
            browser = await self.app.get_browser()
            goal = build_h_prompt(request, request) + FRENCH
            agent = WebAgent(client, browser, self.ask, max_steps=self.app.args.max_steps)
            async for event in agent.run(goal, start_url_for(request)):
                if isinstance(event, AgentStep):
                    if event.action not in {"done", "ask_user", "confirm"}:
                        self.emit(type="agent_step", narration=event.narration, action=event.action)
                elif isinstance(event, NeedsUser):
                    self.emit(type="needs_user", question=event.question)
                elif isinstance(event, ConfirmRequest):
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


async def serve_app(args, ready):
    app = BrainyApp(args)

    def process_request(connection, request):
        if request.path.split("?", 1)[0] == "/ws":
            return None
        return static_response(request.path)

    async def handler(ws):
        await Session(app, ws).run()

    async with serve(handler, "127.0.0.1", args.port, process_request=process_request, max_size=2**20):
        ready.set()
        try:
            await asyncio.Future()
        finally:
            await app.close()


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Brainy desktop app (window + local bridge).")
    parser.add_argument("--port", type=int, default=int(os.getenv("BRAINY_PORT", "8765")))
    parser.add_argument("--no-window", action="store_true", help="Only run the server; open the URL in a browser.")
    parser.add_argument("--language", action="append", default=None, metavar="CODE",
                        help="Gladia language code, repeatable (default: fr).")
    parser.add_argument("--device", help="Microphone device index or name.")
    parser.add_argument("--channel", default=os.getenv("BRAINY_BROWSER_CHANNEL", "chrome"),
                        help="Installed browser for the agent (chrome, msedge); falls back to bundled Chromium.")
    parser.add_argument("--model", default=os.getenv("H_MODEL") or "holo3-1-35b-a3b")
    parser.add_argument("--max-steps", type=int, default=40)
    args = parser.parse_args()
    args.language = args.language or ["fr"]
    if args.device and args.device.isdecimal():
        args.device = int(args.device)

    ready = threading.Event()
    server = threading.Thread(target=lambda: asyncio.run(serve_app(args, ready)), daemon=True)
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
            return 0
        return 0

    import webview

    screen = webview.screens[0] if webview.screens else None
    width, height = 360, 560
    x = screen.width - width - 24 if screen else None
    webview.create_window("Brainy", url, width=width, height=height, x=x, y=60 if screen else None,
                          on_top=True, resizable=False, background_color="#FFFFFF")
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
