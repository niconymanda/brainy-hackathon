"""Deterministic, explicitly confirmed cancellation of the next Doctolib appointment."""
import re
import sys

from playwright.async_api import TimeoutError as PlaywrightTimeoutError


CANCEL = re.compile(r"^annuler (?:le|mon|ce) (?:rendez-vous|rdv)$", re.I)
FINAL = re.compile(r"^(?:confirmer l['’]annulation|oui,? annuler|annuler (?:le|mon|ce) (?:rendez-vous|rdv))$", re.I)
CANCELLED = re.compile(r"(?:rendez-vous (?:a (?:bien )?été |est )?annulé|annulation (?:est )?confirmée)", re.I)
UPCOMING = re.compile(r"(?:à venir|prochains rendez-vous)", re.I)
OPEN = re.compile(r"(?:voir|détails|gérer|rendez-vous|\d{1,2}[:h]\d{2})", re.I)


def _log(message):
    print(f"[cancel] {message}", file=sys.stderr, flush=True)


async def _find(scope, pattern):
    for locator in (scope.get_by_role("tab", name=pattern), scope.get_by_role("button", name=pattern),
                    scope.get_by_role("link", name=pattern), scope.get_by_text(pattern)):
        for element in (await locator.all())[:50]:
            if await element.is_visible():
                return element
    return None


async def cancel_doctolib(page, say, confirm):
    """Return (ok, French message), or None if the expected UI is unavailable."""
    submitted = False
    try:
        _log("Opening account appointments")
        say("J'ouvre tes prochains rendez-vous sur Doctolib.")
        await page.goto("https://www.doctolib.fr/account/appointments", wait_until="domcontentloaded")
        # Wait for the account's client-rendered appointment list.
        try:
            await page.get_by_text(UPCOMING).first.wait_for(timeout=10000)
        except PlaywrightTimeoutError:
            _log("Upcoming appointments heading unavailable")
            return None
        tab = await _find(page, re.compile(r"^(?:à venir|rendez-vous à venir|prochains rendez-vous)$", re.I))
        if tab and await tab.get_attribute("role") == "tab":
            await tab.click()
            _log("Selected upcoming appointments tab")
        # Prefer a labelled upcoming region; otherwise a dated appointment card.
        region = page.get_by_role("region", name=UPCOMING)
        scope = region.first if await region.count() else page.locator("main").first
        if not await scope.count():
            scope = page.locator("body")
        cards = scope.locator("article, [role=listitem], li").filter(has_text=re.compile(r"\d{1,2}[:h]\d{2}", re.I))
        card = None
        for candidate in await cards.all():
            if await candidate.is_visible() and not re.search(r"annulé|passé", await candidate.inner_text(), re.I):
                card = candidate
                break
        opener = await _find(card if card is not None else scope, OPEN)
        if opener is None:
            _log("No upcoming appointment control found")
            return None
        await opener.click(timeout=3000)
        _log("Opened first upcoming appointment")
        cancel = await _find(page, CANCEL)
        if cancel is None:
            _log("Cancellation control unavailable")
            return None
        selected_detail = (await cancel.evaluate_handle("""el => {
            for (let node = el.parentElement; node && node.tagName !== 'BODY'; node = node.parentElement) {
                if (/\\d{1,2}[:h]\\d{2}/i.test(node.innerText)) return node;
            }
            return null;
        }""")).as_element()
        detail_was_cancelled = bool(selected_detail and CANCELLED.search(await selected_detail.inner_text()))
        detail = page.locator("main").first
        summary = (await (detail if await detail.count() else page.locator("body")).inner_text()).strip()
        if not re.search(r"\d{1,2}[:h]\d{2}", summary):
            _log("Appointment time unavailable; refusing cancellation")
            return None
        await cancel.click(timeout=3000)
        _log("Opened cancellation dialog")
        say("Je prépare l'annulation de ce rendez-vous.")
        if not await confirm(f"Veux-tu annuler ce rendez-vous ?\n{summary[:2000]}"):
            _log("User declined cancellation")
            return False, "D'accord, je n'ai pas annulé ton rendez-vous."
        _log("User approved cancellation")
        dialog = page.get_by_role("dialog")
        scope = dialog.last if await dialog.count() else page
        # The public help flow includes Continuer and an optional cancellation reason.
        onward = await _find(scope, re.compile(r"^continuer$", re.I))
        if onward:
            await onward.click(timeout=3000)
            _log("Continued cancellation dialog")
        for select in await scope.get_by_role("combobox").all():
            if await select.is_visible() and await select.evaluate("el => el.tagName === 'SELECT'"):
                for option in await select.locator("option").all():
                    if re.fullmatch(r"autre(?: raison| motif)?", (await option.inner_text()).strip(), re.I):
                        await select.select_option(value=await option.get_attribute("value"))
                        _log("Selected neutral Other reason")
                        break
        final = await _find(scope, FINAL)
        if final is None:
            _log("Final cancellation control unavailable")
            return None
        cancelled_markers = page.get_by_text(CANCELLED)
        previous_cancelled = sum([await marker.is_visible() for marker in await cancelled_markers.all()])
        await final.click(timeout=3000)
        submitted = True
        _log("Submitted cancellation")
        for _ in range(20):
            current_cancelled = sum([await marker.is_visible() for marker in await cancelled_markers.all()])
            if current_cancelled > previous_cancelled:
                break
            if selected_detail and not detail_was_cancelled and await selected_detail.evaluate('el => el.isConnected'):
                if CANCELLED.search(await selected_detail.inner_text()):
                    _log("Selected appointment detail now shows cancellation")
                    break
            await page.wait_for_timeout(500)
        else:
            raise PlaywrightTimeoutError("No new cancellation confirmation appeared")
        _log("Verified cancelled appointment state")
        say("Le rendez-vous est maintenant annulé.")
        return True, "Ton rendez-vous est bien annulé sur Doctolib."
    except Exception as exc:
        _log(f"Stopped: {type(exc).__name__}: {exc}")
        if submitted:
            return False, "L'annulation a été envoyée, mais je n'ai pas pu vérifier son résultat. Vérifie ton compte Doctolib."
        return None
