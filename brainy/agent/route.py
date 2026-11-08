"""Scripted Doctolib booking: search, first matching slot, and public booking funnel."""
import os
import re
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


SPECIALTIES = (
    (r"\b(?:dermatologue|dermato)\b", "dermatologue"),
    (r"\bdentiste\b", "dentiste"),
    (r"\b(?:m[ée]decin(?:e)?\s+g[ée]n[ée]raliste|g[ée]n[ée]raliste|generaliste)\b", "medecin-generaliste"),
    (r"\b(?:ophtalmologue|ophtalmo)\b", "ophtalmologue"),
    (r"\b(?:gyn[ée]cologue|gyn[ée]co)\b", "gynecologue"),
    (r"\b(?:kin[ée]|kine|masseur[-\s]kin[ée]sith[ée]rapeute)\b", "masseur-kinesitherapeute"),
    (r"\b(?:p[ée]diatre|p[ée]diatrie)\b", "pediatre"),
    (r"\borl\b", "orl"),
    (r"\bpsychiatre\b", "psychiatre"),
    (r"\bpsychologue\b", "psychologue"),
    (r"\bost[ée]opathe\b", "osteopathe"),
    (r"\bcardiologue\b", "cardiologue"),
)
SLOT = re.compile(r"^\s*\d{1,2}[:h]\d{2}\s*$")
FINAL = re.compile(r"confirmer le rendez-vous", re.I)
COOKIES = re.compile(r"^\s*(accepter|j'accepte|tout accepter|refuser)\s*$", re.I)
NEXT = re.compile(r"^\s*(?:continuer|suivant|valider|j['’]ai compris|je confirme mon motif)\b", re.I)
CHOICES = re.compile(
    r"(au cabinet|t[ée]l[ée]consultation|premi[eè]re consultation|nouveau patient|"
    r"d[ée]j[àa] consult[ée]|motif|consultation de suivi|^non$|^moi$|moi-m[eê]me|^hugo)",
    re.I,
)
FIRST_VISIT = re.compile(r"premi[eè]re consultation|nouveau patient", re.I)
UNAVAILABLE = re.compile(
    r"prise de rendez-vous en ligne n['’]est (?:malheureusement )?pas disponible|aucune disponibilit[ée] en ligne", re.I)
FOLLOW_UP = re.compile(r"\bsuivi\b|d[ée]j[àa] (?:consult|patient|vu)|contr[ôo]le", re.I)
SHORT_MONTH = re.compile(
    r"(?<!\d)(\d{1,2})(?:er)?\s+(janv|févr|fevr|mars|avr|mai|juin|juil|août|aout|sept|oct|nov|déc|dec)[a-zéû]*\.?(?!\w)", re.I)
SHORT_MONTHS = {"janv": 1, "févr": 2, "fevr": 2, "mars": 3, "avr": 4, "mai": 5, "juin": 6, "juil": 7, "août": 8,
                "aout": 8, "sept": 9, "oct": 10, "nov": 11, "déc": 12, "dec": 12}
CONFIRMED = re.compile(r"rendez-vous (est )?confirmé|réservation confirmée|votre rendez-vous a été", re.I)
LOGIN_URL = re.compile(r"/(?:sessions/new|login|connexion|authentication)(?:/|$)", re.I)
MONTHS = {
    name: number for number, name in enumerate(
        ("janvier", "février", "mars", "avril", "mai", "juin", "juillet",
         "août", "septembre", "octobre", "novembre", "décembre"), 1)
}
WEEKDAYS = {
    name: number for number, name in enumerate(
        ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"))
}
WEEKDAY_NAMES = tuple(WEEKDAYS)
MONTH_NAMES = tuple(MONTHS)
LOGIN_REQUIRED = "login_required"
CHALLENGE_BLOCKED = "challenge_blocked"

# Answer each unanswered radio group: first-visit reason, else "Non", else the first option.
SETTLE_FORM = """() => {
  const label = r => (r.labels && r.labels[0] ? r.labels[0].innerText : r.closest('label')?.innerText || r.value || '').trim();
  const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
  const groups = {};
  let acted = 0;
  for (const r of document.querySelectorAll('input[type=radio]')) if (visible(r) || (r.labels && r.labels[0] && visible(r.labels[0]))) (groups[r.name || r.id] ||= []).push(r);
  for (const radios of Object.values(groups)) {
    if (radios.some(r => r.checked)) continue;
    const pick = radios.find(r => /premi[eè]re consultation|nouveau patient/i.test(label(r)))
      || radios.find(r => /^non\\b/i.test(label(r))) || radios[0];
    const target = pick.labels && pick.labels[0] && visible(pick.labels[0]) ? pick.labels[0] : pick;
    target.click(); acted++;
  }
  for (const c of document.querySelectorAll('input[type=checkbox]')) {
    if (c.checked || !(c.required || c.closest('form')) || !(visible(c) || (c.labels && visible(c.labels[0])))) continue;
    const target = c.labels && c.labels[0] && visible(c.labels[0]) ? c.labels[0] : c;
    target.click(); acted++;
  }
  for (const s of document.querySelectorAll('select')) {
    if (s.value || !visible(s)) continue;
    const opts = [...s.options].filter(o => o.value);
    const pick = opts.find(o => /premi[eè]re/i.test(o.text)) || opts[0];
    if (pick) { s.value = pick.value; s.dispatchEvent(new Event('change', {bubbles: true})); acted++; }
  }
  return acted;
}"""


@dataclass
class DayConstraint:
    exact_dates: set[date] = field(default_factory=set)
    weekdays: set[int] = field(default_factory=set)
    periods: list[tuple[date, date]] = field(default_factory=list)

    def matches(self, value):
        if self.exact_dates and value not in self.exact_dates:
            return False
        if self.weekdays and value.weekday() not in self.weekdays:
            return False
        if self.periods and not any(start <= value <= end for start, end in self.periods):
            return False
        return True


def has_specialty(request):
    return any(re.search(pattern, request, re.I) for pattern, _ in SPECIALTIES)


def doctolib_url(request):
    lowered = request.lower()
    specialty = next((slug for pattern, slug in SPECIALTIES if re.search(pattern, lowered, re.I)), None)
    if not specialty:
        return None
    arrondissement = re.search(r"\b(\d{1,2})\s*(?:e|ème|eme)\b", lowered)
    number = int(arrondissement.group(1)) if arrondissement else 0
    city = f"paris-750{number:02d}" if 1 <= number <= 20 else "paris"
    return f"https://www.doctolib.fr/{specialty}/{city}"


def parse_day_constraint(request, today=None):
    today = today or date.today()
    text = request.lower()
    constraint = DayConstraint()

    dates = re.search(
        r"\b(?:le\s+)?(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|"
        r"septembre|octobre|novembre|décembre)(?:\s+(\d{4}))?\b", text)
    if dates:
        day, month = int(dates.group(1)), MONTHS[dates.group(2)]
        year = int(dates.group(3)) if dates.group(3) else today.year
        if not dates.group(3) and (month, day) < (today.month, today.day):
            year += 1
        try:
            constraint.exact_dates.add(date(year, month, day))
        except ValueError:
            pass
    else:
        numeric_day = re.search(r"\ble\s+(\d{1,2})(?!\s*(?:e|ème|eme)\b)\b", text)
        if numeric_day:
            day = int(numeric_day.group(1))
            year, month = today.year, today.month
            try:
                target = date(year, month, day)
                if target < today:
                    month += 1
                    if month > 12:
                        month, year = 1, year + 1
                    target = date(year, month, day)
                constraint.exact_dates.add(target)
            except ValueError:
                pass

    relative_dates = set()
    if re.search(r"\baujourd['’]hui\b", text):
        relative_dates.add(today)
    if re.search(r"\bdemain\b", text):
        relative_dates.add(today + timedelta(days=1))
    constraint.exact_dates.update(relative_dates)

    named_days = {weekday for name, weekday in WEEKDAYS.items()
                  if re.search(rf"\b{re.escape(name)}\b", text)}
    constraint.weekdays.update(named_days)

    if re.search(r"\bcette semaine\b", text):
        days_left = (6 - today.weekday()) % 7
        if days_left == 0:
            days_left = 7
        constraint.periods.append((today, today + timedelta(days=days_left)))
    if re.search(r"\bla semaine prochaine\b", text):
        next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
        constraint.periods.append((next_monday, next_monday + timedelta(days=6)))
    return constraint if constraint.exact_dates or constraint.weekdays or constraint.periods else None


def _date_from_text(text, today):
    for match in re.finditer(r"\b(20\d{2})-(\d{2})-(\d{2})", text):
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            continue
    match = SHORT_MONTH.search(text)
    if match:
        day, month = int(match.group(1)), SHORT_MONTHS[match.group(2).lower()]
        year = today.year + (1 if (month, day) < (today.month, today.day) else 0)
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def _slot_date(metadata, today):
    href = metadata.get("href", "")
    selected = parse_qs(urlsplit(unquote(href)).query).get("selected_slot", [])
    values = [*selected, metadata.get("labelled", ""), metadata.get("attributes", ""), metadata.get("context", "")]
    for value in values:
        match = re.search(r"20\d{2}-\d{2}-\d{2}", value or "")
        if match:
            try:
                return date.fromisoformat(match.group())
            except ValueError:
                pass
        parsed = _date_from_text(value or "", today)
        if parsed:
            return parsed
    return None


async def _click_first(page, locator, tried):
    for element in (await locator.all())[:60]:
        try:
            if not await element.is_visible():
                continue
            text = (await element.inner_text()).strip()
            key = (page.url, text)
            if key in tried:
                continue
            await element.scroll_into_view_if_needed(timeout=2000)
            await element.click(timeout=3000)
            tried.add(key)
            return text or True
        except Exception:
            continue
    return None


async def _slot_metadata(element):
    return await element.evaluate("""e => {
      const parts = [];
      const attrs = [];
      let node = e;
      for (let i = 0; node && i < 7; i++, node = node.parentElement) {
        const text = (node.innerText || '').trim();
        if (text) parts.push(text.slice(0, 800));
        for (const name of ['datetime', 'aria-label', 'data-date', 'data-slot', 'data-testid']) {
          const value = node.getAttribute(name);
          if (value) attrs.push(value);
        }
      }
      const labelled = (e.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean)
        .map(id => document.getElementById(id)).filter(n => n && n !== e).map(n => n.innerText || '').join(' ');
      return {text: (e.innerText || e.value || '').trim(), href: e.getAttribute('href') || '', labelled,
        context: parts.join('\\n'), attributes: attrs.join(' ')};
    }""")


async def _slot_candidates(page):
    locator = page.locator("a, button, [role=button]").filter(has_text=SLOT)
    candidates = []
    for element in (await locator.all())[:100]:
        try:
            if not await element.is_visible():
                continue
            data = await _slot_metadata(element)
            if data["text"]:
                candidates.append((element, data))
        except Exception:
            continue
    return candidates


def _slot_narration(slot_date, time_text):
    slot_time = time_text.replace(":", "h")
    if slot_date is None:
        return f"Je prends le créneau disponible à {slot_time}."
    day = WEEKDAY_NAMES[slot_date.weekday()]
    month = MONTH_NAMES[slot_date.month - 1]
    return f"Je prends le créneau du {day} {slot_date.day} {month} à {slot_time}."


async def _click_slot(page, constraint, tried, today, preferred=None):
    candidates = await _slot_candidates(page)
    fallback = None
    for element, metadata in candidates:
        text = metadata["text"]
        key = (page.url, text, metadata["href"])
        if key in tried:
            continue
        if fallback is None:
            fallback = metadata
        if preferred and not (
            (preferred.get("href") and preferred["href"] == metadata["href"])
            or (not preferred.get("href") and preferred["text"] == text)
        ):
            continue
        slot_date = _slot_date(metadata, today)
        if constraint and not preferred and (
            slot_date is None or not constraint.matches(slot_date)
        ):
            continue
        try:
            await element.scroll_into_view_if_needed(timeout=2000)
            await element.click(timeout=3000)
            tried.add(key)
            slot_date = _slot_date(metadata, today)
            page._brainy_selected_slot = {
                "date": slot_date.isoformat() if slot_date else None,
                "matches_constraint": not constraint or bool(slot_date and constraint.matches(slot_date)),
            }
            return text, metadata, len(candidates), fallback
        except Exception:
            continue
    return None, None, len(candidates), fallback


async def _at_bottom(page):
    return await page.evaluate(
        "() => ({bottom: window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 8, "
        "height: document.documentElement.scrollHeight})")


async def _login_wall(page):
    if LOGIN_URL.search(urlsplit(page.url).path):
        return True
    try:
        return await page.evaluate("""() => {
          const password = document.querySelector('input[type="password"]');
          const email = document.querySelector('input[type="email"], input[autocomplete="username"]');
          const text = (document.body?.innerText || '').toLowerCase();
          return !!password || (!!email && /connectez-vous|se connecter|connexion/.test(text));
        }""")
    except Exception:
        return False


async def _challenge_page(page):
    try:
        return await page.evaluate("""() => {
          const text = (document.body?.innerText || '').toLowerCase();
          const challengeFrame = [...document.querySelectorAll('iframe')].some(frame =>
            /challenges\\.cloudflare\\.com/.test(frame.src || ''));
          return challengeFrame || /verify you are human|vérifier que vous êtes bien humain|challenge-platform/.test(text);
        }""")
    except Exception:
        return False


async def _capture_fixture(page, captured, on_page=None):
    if urlsplit(page.url).hostname not in {"doctolib.fr", "www.doctolib.fr"}:
        return
    try:
        is_login = await _login_wall(page)
        is_challenge = await _challenge_page(page)
        text = (await page.locator("body").inner_text()).lower()
        if is_challenge:
            name = "human-verification"
        elif is_login:
            name = "login"
        elif re.search(r"d[ée]j[àa] consult[ée]|nouveau patient", text):
            name = "patient-status"
        elif re.search(r"mode de consultation|au cabinet|t[ée]l[ée]consultation", text):
            name = "consultation-mode"
        elif re.search(r"motif|raison de la consultation|premi[eè]re consultation", text):
            name = "visit-reason"
        elif re.search(r"continuer|j['’]ai compris", text):
            name = "information-notice"
        elif "/booking" in page.url:
            name = "booking"
        elif re.search(r"\b\d{1,2}[:h]\d{2}\b", text):
            name = "results"
        else:
            name = "results"
        if name not in captured:
            captured.add(name)
            if on_page:
                on_page(name, urlsplit(page.url).path)
        if name == "human-verification":
            return
        directory = os.getenv("BRAINY_FIXTURE_DIR")
        if not directory:
            return
        path = Path(directory) / f"{name}.html"
        if path.exists():
            return
        html = await page.evaluate("""() => {
          const body = document.body.cloneNode(true);
          body.querySelectorAll('script, noscript, iframe, input[type=hidden]').forEach(e => e.remove());
          body.querySelectorAll('input, textarea').forEach(e => {
            e.removeAttribute('value');
            e.value = '';
            e.textContent = '';
          });
          body.querySelectorAll('*').forEach(e => {
            for (const attribute of [...e.attributes]) {
              if (attribute.name.toLowerCase().startsWith('on')) e.removeAttribute(attribute.name);
            }
          });
          return '<!doctype html><html><head><meta charset="utf-8"></head>' +
            '<body>' + body.innerHTML + '</body></html>';
        }""")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        captured.add(name)
    except Exception:
        return


async def book_doctolib(page, url, say, confirm, max_steps=60, request="", on_page=None):
    """Returns (ok, message), including LOGIN_REQUIRED at the public login wall."""
    say("J'ouvre Doctolib sur les dermatologues du quartier." if "dermato" in url else "J'ouvre Doctolib.")
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2500)
    tried, idle = set(), 0
    first_visit = bool(FIRST_VISIT.search(request)) or not FOLLOW_UP.search(request)
    constraint = parse_day_constraint(request)
    slot_started = None
    first_slot = None
    same_bottom = 0
    previous_height = None
    previous_count = 0
    today = date.today()
    captured = set()

    for _ in range(max_steps):
        await _capture_fixture(page, captured, on_page)
        if await _challenge_page(page):
            say("Doctolib demande une vérification humaine ; je m'arrête là.")
            return False, CHALLENGE_BLOCKED
        if await _login_wall(page):
            say("Doctolib demande de te connecter.")
            return False, LOGIN_REQUIRED

        if "/booking" in page.url and UNAVAILABLE.search(await page.locator("body").inner_text()):
            # Another motive would change the visit type; another practitioner keeps the request intact.
            say("Ce rendez-vous n'est pas réservable en ligne ; je cherche un autre créneau.")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            continue

        final = page.locator("button").filter(has_text=FINAL)
        if await final.count() and await final.first.is_visible():
            if await page.evaluate(SETTLE_FORM):
                say("Je remplis les dernières questions du formulaire.")
                await page.wait_for_timeout(800)
            summary = (await page.locator("main").first.inner_text())[:600] if await page.locator("main").count() else ""
            when = re.search(r"(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)[^\n•]*[•\n ]+\d{1,2}h\d{2}", summary, re.I)
            if not await confirm(f"Je confirme le rendez-vous{' du ' + when.group(0).replace(chr(10), ' ') if when else ''} ?"):
                return False, "D'accord, je n'ai rien réservé."
            await final.first.scroll_into_view_if_needed()
            await final.first.click()
            say("Je confirme le rendez-vous.")
            for _ in range(20):
                await page.wait_for_timeout(1000)
                if CONFIRMED.search(await page.locator("body").inner_text()):
                    return True, "C'est réservé ! Ton rendez-vous est confirmé sur Doctolib."
                if not await final.count():
                    return True, "C'est réservé ! Le rendez-vous est dans ton compte Doctolib."
            return None

        acted = await _click_first(page, page.locator("button").filter(has_text=COOKIES), tried)
        if not acted and await page.evaluate(SETTLE_FORM):
            acted = "form"
            say("Je choisis la première consultation pour toi.")
        if not acted and "/booking" in page.url:
            choices = "button, a, label, [role=button], [role=radio], [role=option]"
            acted = first_visit and await _click_first(page, page.locator(choices).filter(has_text=FIRST_VISIT), tried)
            acted = acted or await _click_first(
                page, page.locator("button, a, label, [role=button], [role=radio], [role=option]").filter(has_text=CHOICES),
                tried)
            if acted:
                say(f"Je choisis « {str(acted).splitlines()[0]} ».")
        if not acted:
            clicked, metadata, count, fallback = await _click_slot(page, constraint, tried, today)
            if fallback and first_slot is None:
                first_slot = fallback
            if count and slot_started is None:
                slot_started = time.monotonic()
            if clicked:
                selected_date = _slot_date(metadata, today)
                say(_slot_narration(selected_date, clicked))
                acted = clicked
            elif constraint and first_slot and slot_started:
                bottom = await _at_bottom(page)
                if count > previous_count or bottom["height"] != previous_height:
                    same_bottom = 0
                elif bottom["bottom"]:
                    same_bottom += 1
                previous_count, previous_height = count, bottom["height"]
                elapsed = time.monotonic() - slot_started
                if elapsed >= 40 or same_bottom >= 3:
                    clicked, metadata, _, _ = await _click_slot(page, None, tried, today, preferred=first_slot)
                    if not clicked:
                        clicked, metadata, _, _ = await _click_slot(page, None, tried, today)
                    if clicked:
                        page._brainy_selected_slot["matches_constraint"] = False
                        say("Aucun créneau ne correspond au jour demandé ; je prends le premier disponible.")
                        acted = clicked
                if not acted:
                    idle += 1
                    await page.mouse.wheel(0, 900)
                    await page.wait_for_timeout(900)
                    continue
        if not acted:
            acted = await _click_first(page, page.locator("button").filter(has_text=NEXT), tried)
            if acted:
                say("Je continue.")
        if acted:
            idle = 0
            await page.wait_for_timeout(1800)
            continue
        idle += 1
        if idle > 30:
            return None
        await page.mouse.wheel(0, 700)
        await page.wait_for_timeout(900)
    return None
