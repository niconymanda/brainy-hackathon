import asyncio
import functools
import http.server
import shutil
import tempfile
import threading
import unittest
from datetime import date, timedelta
from pathlib import Path

from brainy.agent.route import LOGIN_REQUIRED, book_doctolib

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

FIXTURES = Path(__file__).parent / "fixtures" / "route"
DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
MONTHS = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")


def column(index, day, slots):
    buttons = "".join(
        f'<span class="sr-only" id="s{index}-{n}-sub">Rendez-vous assuré par un remplaçant : Dr. B</span>'
        f'<a href="/booking/motives.html" id="s{index}-{n}" aria-labelledby="s{index}-{n} d{index} s{index}-{n}-sub">'
        f'{slot}</a>' for n, slot in enumerate(slots)) or "<span>—</span>"
    return (f'<div class="column"><div id="d{index}" style="display:flex;flex-direction:column"><span>{DAYS[day.weekday()]}</span>'
            f'<span>{day.day} {MONTHS[day.month - 1]}</span></div>{buttons}</div>')


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipIf(async_playwright is None, "playwright not installed")
class RouteFixtureTests(unittest.TestCase):
    """Doctolib-like pages: abbreviated column dates, a follow-up motive listed first, an unavailable motive."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        shutil.copytree(FIXTURES, self.root, dirs_exist_ok=True)
        today = date.today()
        monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
        tuesday_before = monday - timedelta(days=6)
        columns = column(0, tuesday_before, ["11:30"]) + column(1, monday - timedelta(days=1), []) + \
            column(2, monday, ["14:00"])
        (self.root / "results.html").write_text(
            f'<!doctype html><meta charset="utf-8"><h2>Dr B</h2><div class="slots">{columns}</div>', encoding="utf-8")
        self.monday = monday
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=self.root))
        self.server = server
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        shutil.rmtree(self.root, ignore_errors=True)

    async def book(self, request):
        said, visited = [], []
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            page.on("framenavigated", lambda frame: frame == page.main_frame and visited.append(frame.url))
            result = await book_doctolib(page, self.base + "/results.html", said.append,
                                         lambda question: asyncio.sleep(0, False), max_steps=20, request=request)
            selected = getattr(page, "_brainy_selected_slot", None)
            await browser.close()
        return result, said, visited, selected

    def test_requested_weekday_first_visit_then_another_motive_when_unavailable(self):
        result, said, visited, selected = asyncio.run(self.book("Je veux un dermatologue dans le 9e lundi"))
        self.assertEqual(result, (False, LOGIN_REQUIRED))
        self.assertEqual(selected, {"date": self.monday.isoformat(), "matches_constraint": True})
        self.assertIn("Je choisis « Première consultation de dermatologie ».", said)
        self.assertIn("Ce motif n'est pas réservable en ligne ; j'en choisis un autre.", said)
        self.assertIn("Je choisis « Consultation de suivi de dermatologie ».", said)
        paths = [u.split(self.base)[1] for u in visited if u.startswith(self.base)]
        self.assertEqual(paths, ["/results.html", "/booking/motives.html", "/booking/unavailable.html",
                                 "/booking/motives.html", "/sessions/new/"])


if __name__ == "__main__":
    unittest.main()
