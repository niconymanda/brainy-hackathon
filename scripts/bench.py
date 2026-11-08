"""Book/cancel benchmark against an already running Brainy bridge."""
import argparse
import asyncio
import html
import json
from pathlib import Path
import time

import websockets


DEFAULT_REQUEST = 'Réserve-moi un dermatologue dans le 9e, le premier créneau disponible cette semaine'


async def connect(url, retry_seconds=120):
    deadline = time.monotonic() + retry_seconds
    while True:
        try:
            return await websockets.connect(url, open_timeout=min(10, max(.1, deadline - time.monotonic())))
        except (OSError, TimeoutError, websockets.exceptions.WebSocketException):
            if time.monotonic() >= deadline:
                raise
            await asyncio.sleep(min(2, deadline - time.monotonic()))


async def run_step(ws, request, timeout):
    start = time.monotonic()
    row = dict(request=request, ok=False, duration=0, narration='', error='', events=[])
    try:
        await ws.send(json.dumps({'type': 'user_text', 'text': request}, ensure_ascii=False))
        while True:
            remaining = timeout - (time.monotonic() - start)
            event = json.loads(await asyncio.wait_for(ws.recv(), timeout=max(0, remaining)))
            row['events'].append({'elapsed': round(time.monotonic() - start, 3), 'event': event})
            kind = event.get('type')
            if kind == 'agent_step':
                row['narration'] = event.get('narration', '')
            elif kind == 'confirm_request':
                await ws.send(json.dumps({'type': 'confirm', 'answer': 'oui'}))
            elif kind == 'done':
                row['ok'] = event.get('ok') is True
                if not row['ok']:
                    row['error'] = event.get('result', 'Échec sans explication')
                break
            elif kind == 'error':
                row['error'] = event.get('reason', 'Erreur')
                break
    except Exception as exc:
        row['error'] = f'{type(exc).__name__}: {exc}'
    row['duration'] = round(time.monotonic() - start, 3)
    return row


def write_report(rows, path):
    escape = lambda value: html.escape(str(value))
    body = []
    for row in rows:
        body.append('<tr>' + ''.join(f'<td>{escape(row[key])}</td>' for key in
                    ('run', 'phase', 'request', 'ok', 'duration', 'narration', 'error')) + '</tr>')
        body.append('<tr><td colspan="7"><details><summary>Événements horodatés</summary><pre>' +
                    escape(json.dumps(row['events'], ensure_ascii=False, indent=2)) + '</pre></details></td></tr>')
    path.write_text('<!doctype html><html lang="fr"><meta charset="utf-8"><title>Brainy benchmark</title>'
                    '<style>body{font-family:system-ui;margin:2em}table{border-collapse:collapse;width:100%}'
                    'td,th{border:1px solid #aaa;padding:.5em}pre{white-space:pre-wrap}</style>'
                    '<h1>Brainy benchmark</h1><table><tr><th>Run</th><th>Phase</th><th>Demande</th>'
                    '<th>Succès</th><th>Durée (s)</th><th>Dernière narration</th><th>Erreur</th></tr>' +
                    ''.join(body) + '</table></html>', encoding='utf-8')


async def benchmark(args, report_path=None):
    rows = []
    ws = None
    try:
        ws = await connect(args.url)
        for run in range(1, args.runs + 1):
            for phase, request in [('booking', args.request[(run - 1) % len(args.request)]),
                                   ('cancel', 'Annule mon prochain rendez-vous')]:
                row = await run_step(ws, request, args.timeout)
                row.update(run=run, phase=phase)
                rows.append(row)
                print(f"Run {run} {phase}: {'OK' if row['ok'] else 'FAIL'} ({row['duration']}s) {row['error']}", flush=True)
                # An unterminated operation may still emit done: never reuse that connection.
                if row['error'].startswith(('TimeoutError', 'ConnectionClosed', 'JSONDecodeError')):
                    return 1
    except Exception as exc:
        rows.append(dict(run=0, phase='connection', request='', ok=False, duration=0,
                         narration='', error=f'{type(exc).__name__}: {exc}', events=[]))
    finally:
        if ws is not None:
            await ws.close()
        write_report(rows, report_path or Path(__file__).with_name('bench-report.html'))
    return int(not rows or any(not row['ok'] for row in rows))


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('must be positive')
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=positive_int, default=3)
    parser.add_argument('--url', default='ws://127.0.0.1:8765/ws')
    parser.add_argument('--request', action='append')
    parser.add_argument('--timeout', type=positive_int, default=300, help='seconds per booking/cancellation')
    args = parser.parse_args()
    args.request = args.request or [DEFAULT_REQUEST]
    return asyncio.run(benchmark(args))


if __name__ == '__main__':
    raise SystemExit(main())
