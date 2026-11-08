import argparse
import json
from pathlib import Path
import tempfile
import unittest

import websockets

from scripts.bench import benchmark, run_step


class BenchTests(unittest.IsolatedAsyncioTestCase):
    async def test_server_confirmation_and_report(self):
        requests, replies = [], []

        async def server(ws):
            for _ in range(2):
                requests.append(json.loads(await ws.recv()))
                await ws.send(json.dumps(dict(type='agent_step', narration='<Dernière narration>')))
                await ws.send(json.dumps(dict(type='confirm_request', summary='Confirmer ?')))
                replies.append(json.loads(await ws.recv()))
                await ws.send(json.dumps(dict(type='done', ok=True, result='Terminé')))

        async with websockets.serve(server, '127.0.0.1', 0) as listener:
            port = listener.sockets[0].getsockname()[1]
            args = argparse.Namespace(url=f'ws://127.0.0.1:{port}/ws', runs=1, request=['Réserve un dermatologue'], timeout=3)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'report.html'
                self.assertEqual(await benchmark(args, path), 0)
                report = path.read_text(encoding='utf-8')
                self.assertIn('&lt;Dernière narration&gt;', report)
                self.assertIn('elapsed', report)
                self.assertIn('booking', report)
                self.assertIn('cancel', report)
        self.assertEqual(requests, [dict(type='user_text', text='Réserve un dermatologue'),
                                    dict(type='user_text', text='Annule mon prochain rendez-vous')])
        self.assertEqual(replies, [dict(type='confirm', answer='oui')] * 2)

    async def test_failure_exit_and_report(self):
        async def server(ws):
            for _ in range(2):
                await ws.recv()
                await ws.send(json.dumps(dict(type='done', ok=False, result='Aucun créneau')))

        async with websockets.serve(server, '127.0.0.1', 0) as listener:
            port = listener.sockets[0].getsockname()[1]
            args = argparse.Namespace(url=f'ws://127.0.0.1:{port}', runs=1, request=['booking'], timeout=3)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'report.html'
                self.assertEqual(await benchmark(args, path), 1)
                self.assertIn('Aucun créneau', path.read_text(encoding='utf-8'))

    async def test_error_and_closed_connection(self):
        async def server(ws):
            await ws.recv()
            await ws.send(json.dumps(dict(type='error', reason='Erreur navigateur')))

        async with websockets.serve(server, '127.0.0.1', 0) as listener:
            port = listener.sockets[0].getsockname()[1]
            async with websockets.connect(f'ws://127.0.0.1:{port}') as ws:
                row = await run_step(ws, 'test', 3)
                self.assertFalse(row['ok'])
                self.assertEqual(row['error'], 'Erreur navigateur')

    async def test_timeout(self):
        async def server(ws):
            await ws.recv()
            await ws.wait_closed()

        async with websockets.serve(server, '127.0.0.1', 0) as listener:
            port = listener.sockets[0].getsockname()[1]
            async with websockets.connect(f'ws://127.0.0.1:{port}') as ws:
                row = await run_step(ws, 'test', .02)
                self.assertFalse(row['ok'])
                self.assertIn('TimeoutError', row['error'])
