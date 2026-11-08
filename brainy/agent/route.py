"""Scripted Doctolib booking: search, first slot, first visit, checkout, final confirmation. No model calls."""
import re

SPECIALTIES = {
    "dermato": "dermatologue",
    "dentist": "dentiste",
    "généraliste": "medecin-generaliste",
    "generaliste": "medecin-generaliste",
    "ophtalmo": "ophtalmologue",
    "kiné": "masseur-kinesitherapeute",
    "kine": "masseur-kinesitherapeute",
    "gynéco": "gynecologue",
    "gyneco": "gynecologue",
}
SLOT = re.compile(r"^\s*\d{1,2}[:h]\d{2}\s*$")
FINAL = re.compile(r"confirmer le rendez-vous", re.I)
COOKIES = re.compile(r"^\s*(accepter|j'accepte|tout accepter|refuser)\s*$", re.I)
NEXT = re.compile(r"^\s*(continuer|suivant|valider|j'ai compris|je confirme mon motif)\s*$", re.I)
CHOICES = re.compile(r"^\s*(au cabinet|premi[eè]re consultation[^\n]*|nouveau patient[^\n]*|non|moi|moi-m[eê]me|hugo[^\n]*)\s*$", re.I)
CONFIRMED = re.compile(r"rendez-vous (est )?confirmé|réservation confirmée|votre rendez-vous a été", re.I)

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
    if (c.checked || !(c.required || c.closest('form')) || !(visible(c) || (c.labels && c.labels[0] && visible(c.labels[0])))) continue;
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


def doctolib_url(request):
    lowered = request.lower()
    specialty = next((slug for key, slug in SPECIALTIES.items() if key in lowered), None)
    if not specialty or "doctolib" not in lowered and not any(k in lowered for k in SPECIALTIES):
        return None
    arrondissement = re.search(r"\b(\d{1,2})\s*(?:e|ème|eme)\b", lowered)
    city = f"paris-750{int(arrondissement.group(1)):02d}" if arrondissement and 1 <= int(arrondissement.group(1)) <= 20 else "paris"
    return f"https://www.doctolib.fr/{specialty}/{city}"


async def _click_first(page, locator, tried):
    for element in (await locator.all())[:60]:
        try:
            if not await element.is_visible():
                continue
            text = (await element.inner_text()).strip()
            key = (page.url, text)
            if key in tried:
                continue
            tried.add(key)
            await element.scroll_into_view_if_needed(timeout=2000)
            await element.click(timeout=3000)
            return text or True
        except Exception:
            continue
    return None


async def book_doctolib(page, url, say, confirm, max_steps=40):
    """Returns (ok, message), or None when the route gets stuck so the model agent can take over."""
    say("J'ouvre Doctolib sur les dermatologues du quartier." if "dermato" in url else "J'ouvre Doctolib.")
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2500)
    tried, idle = set(), 0
    for _ in range(max_steps):
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
            acted = await _click_first(page, page.locator("button, label, [role=button], [role=radio], [role=option]").filter(has_text=CHOICES), tried)
            if acted:
                say(f"Je choisis « {str(acted).splitlines()[0]} ».")
        if not acted:
            acted = await _click_first(page, page.locator("button, a, [role=button]").filter(has_text=SLOT), tried)
            if acted:
                say(f"Je prends le premier créneau disponible, à {str(acted).replace(':', 'h')}.")
        if not acted:
            acted = await _click_first(page, page.locator("button").filter(has_text=NEXT), tried)
            if acted:
                say("Je continue.")
        if acted:
            idle = 0
            await page.wait_for_timeout(1800)
            continue
        idle += 1
        if idle > 15:
            return None
        await page.mouse.wheel(0, 700)
        await page.wait_for_timeout(900)
    return None
