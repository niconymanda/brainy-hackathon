"""Fake Brainy backend to test the frontend live mode (pip install websockets).

python3 scripts/mock_ws.py  then open http://localhost:5173/?ws=ws://localhost:8765
"""
import asyncio
import json

import websockets


async def handler(ws):
    async def send(**event):
        await ws.send(json.dumps(event))

    async for raw in ws:
        msg = json.loads(raw)
        if msg["type"] == "start_listening":
            await send(type="listening")
            text = "Réserve-moi un dermato samedi"
            for i in range(1, len(text) + 1, 3):
                await send(type="transcript", text=text[:i], final=False)
                await asyncio.sleep(0.05)
            await send(type="transcript", text=text, final=True)
            await send(type="say", text="Je m'en occupe.")
            for step in ["J'ouvre Doctolib", "Je cherche un dermatologue", "Samedi 21 à 10h30 est libre"]:
                await asyncio.sleep(1.2)
                await send(type="agent_step", narration=step, action="click")
            await send(type="confirm_request", summary="Dermato samedi 21 à 10h30 avec le Dr Martin")
        elif msg["type"] == "confirm":
            if msg["answer"] == "oui":
                await send(type="agent_step", narration="Je réserve", action="click")
                await asyncio.sleep(1.5)
                await send(type="done", result="Rendez-vous réservé samedi 21 à 10h30.")
                await send(type="history", items=[
                    {"title": "Dermato · Sarah", "when": "Sam. 21 nov., 10h30", "status": "Réservé", "tone": "paid", "isNew": True},
                ])
            else:
                await send(type="idle")
        elif msg["type"] == "user_text":
            await send(type="say", text=f"Bien reçu : {msg['text']}")


async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("mock backend on ws://localhost:8765")
        await asyncio.Future()


asyncio.run(main())
