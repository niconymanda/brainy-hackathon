#!/usr/bin/env python3
"""Run one Brainy text request against the local backend and live browser."""
import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from websockets.asyncio.client import connect


ROOT = Path(__file__).resolve().parents[1]


async def run(request, timeout):
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    artifact_dir = ROOT / "artifacts" / timestamp
    shots_dir = artifact_dir / "screenshots"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    shots_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["BRAINY_SHOTS"] = str(shots_dir)
    env["BRAINY_FIXTURE_DIR"] = str(ROOT / "tests" / "fixtures" / "doctolib")
    server_log = (artifact_dir / "server.log").open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "brainy.app", "--no-window", "--hotkey", ""],
        cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
        stdout=server_log, stderr=subprocess.STDOUT,
    )
    log_path = artifact_dir / "events.log"
    started = time.monotonic()
    stop_at_login = os.getenv("E2E_STOP_AT_LOGIN") == "1"
    stop_at_needs_user = os.getenv("E2E_STOP_AT_NEEDS_USER") == "1"
    answer = os.getenv("E2E_ANSWER")
    confirm_yes = os.getenv("E2E_CONFIRM", "non").strip().lower() in {"oui", "yes", "y", "true", "1"}

    def record(handle, event):
        elapsed = time.monotonic() - started
        handle.write(f"{elapsed:8.3f}s {json.dumps(event, ensure_ascii=False)}\n")
        handle.flush()
        print(f"{elapsed:8.3f}s {event}")

    try:
        with log_path.open("w", encoding="utf-8") as events:
            deadline = time.monotonic() + min(timeout, 240)
            websocket = None
            while websocket is None and time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"Backend exited with status {process.returncode}.")
                try:
                    websocket = await connect("ws://127.0.0.1:8765/ws", open_timeout=2)
                except OSError:
                    await asyncio.sleep(0.25)
            if websocket is None:
                raise TimeoutError("Timed out connecting to the Brainy WebSocket.")
            async with websocket:
                request_sent = False
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError(f"Timed out after {timeout} seconds.")
                    raw = await asyncio.wait_for(websocket.recv(), remaining)
                    event = json.loads(raw)
                    record(events, event)
                    kind = event.get("type")
                    if kind == "history":
                        if not request_sent:
                            await websocket.send(json.dumps({"type": "user_text", "text": request}))
                            request_sent = True
                        continue
                    if kind == "login_required" and stop_at_login:
                        selected = event.get("selected_slot") or {}
                        if selected.get("matches_constraint") is True:
                            return 0, artifact_dir
                        print("Reached login without a verified matching slot.", file=sys.stderr)
                        return 1, artifact_dir
                    if kind == "challenge_blocked":
                        return 1, artifact_dir
                    if kind == "needs_user":
                        if stop_at_needs_user:
                            return 0, artifact_dir
                        if answer is not None:
                            await websocket.send(json.dumps({"type": "user_text", "text": answer}))
                    elif kind == "confirm_request":
                        await websocket.send(json.dumps({
                            "type": "confirm", "answer": "oui" if confirm_yes else "non",
                        }))
                    elif kind == "done":
                        return (0 if event.get("ok") is True else 1), artifact_dir
                    elif kind == "error":
                        return 1, artifact_dir
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        server_log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", help="Text request to send to Brainy.")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()
    try:
        code, directory = asyncio.run(run(args.request, args.timeout))
    except (TimeoutError, asyncio.TimeoutError, OSError, RuntimeError) as exc:
        print(f"E2E failed: {exc}", file=sys.stderr)
        return 1
    print(f"Artifacts: {directory}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
