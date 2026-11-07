"""Gladia v2 live protocol, independent of microphone and terminal UI."""

import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator, Callable, Sequence
from dataclasses import dataclass
from typing import Literal
from urllib.parse import quote, quote_plus

import httpx
from websockets.asyncio.client import connect


@dataclass(frozen=True)
class Transcript:
    text: str
    is_final: bool
    utterance_id: str
    language: str | None = None


SummaryType = Literal["general", "bullet_points", "concise"]


@dataclass(frozen=True)
class Summary:
    results: str | None = None
    error: str | None = None


def validate_duration(value: float, minimum: float, maximum: float) -> float:
    if not minimum <= value <= maximum:
        raise ValueError(f"Must be between {minimum:g} and {maximum:g} seconds.")
    return value


class GladiaClient:
    """Stream 16 kHz mono signed 16-bit little-endian PCM to a sync callback.

    Set stop to finish gracefully; callbacks must not block the event loop.
    Each call creates a new paid Gladia session. No automatic retries are made.
    """

    def __init__(
        self, api_key: str, languages: Sequence[str] = (), *,
        summary_type: SummaryType | None = None,
        endpointing: float | None = None,
        maximum_duration_without_endpointing: float | None = None,
    ):
        if not api_key.strip():
            raise ValueError("Set GLADIA_API_KEY in the environment or .env file.")
        self.api_key = api_key
        self.languages = list(languages)
        if summary_type not in (None, "general", "bullet_points", "concise"):
            raise ValueError("Summary type must be general, bullet_points or concise.")
        self.summary_type = summary_type
        self.endpointing = None if endpointing is None else validate_duration(endpointing, 0.01, 10)
        self.maximum_duration_without_endpointing = (
            None if maximum_duration_without_endpointing is None
            else validate_duration(maximum_duration_without_endpointing, 5, 60)
        )

    def _safe_error(self, detail: str) -> str:
        detail = detail.replace("\\/", "/")
        for secret in (self.api_key, json.dumps(self.api_key)[1:-1],
                       quote(self.api_key, safe=""), quote_plus(self.api_key)):
            detail = detail.replace(secret, "[REDACTED]")
        detail = re.sub(r"(?i)wss?://[^\s\"'<>]+", "[REDACTED URL]", detail)
        detail = " ".join(detail.split())
        return detail[:500] + ("…" if len(detail) > 500 else "")

    async def transcribe(
        self,
        audio: AsyncGenerator[bytes, None],
        on_transcript: Callable[[Transcript], None],
        stop: asyncio.Event | None = None,
        on_summary: Callable[[Summary], None] | None = None,
    ) -> None:
        config = {
            "encoding": "wav/pcm", "sample_rate": 16000,
            "bit_depth": 16, "channels": 1,
            "language_config": {
                "languages": self.languages,
                "code_switching": len(self.languages) > 1,
            },
            "messages_config": {
                "receive_partial_transcripts": True,
                "receive_final_transcripts": True,
            },
        }
        if self.summary_type is not None:
            config["post_processing"] = {
                "summarization": True,
                "summarization_config": {"type": self.summary_type},
            }
            config["messages_config"]["receive_post_processing_events"] = True
        if self.endpointing is not None:
            config["endpointing"] = self.endpointing
        if self.maximum_duration_without_endpointing is not None:
            config["maximum_duration_without_endpointing"] = self.maximum_duration_without_endpointing
        async with httpx.AsyncClient(timeout=20) as http:
            response = await http.post(
                "https://api.gladia.io/v2/live",
                headers={"x-gladia-key": self.api_key}, json=config,
            )
            if response.is_error:
                detail = self._safe_error(response.text)
                raise RuntimeError(
                    f"Gladia session initialization failed (HTTP {response.status_code}): "
                    f"{detail or 'No error details returned.'}"
                )
            url = response.json().get("url")
            if not isinstance(url, str) or not url.startswith("wss://"):
                raise RuntimeError("Gladia returned no secure WebSocket URL.")

        async with connect(url, open_timeout=20, close_timeout=5) as socket:
            async def send():
                try:
                    async for chunk in audio:
                        if chunk:
                            await socket.send(chunk)
                finally:
                    await audio.aclose()
                    await socket.send(json.dumps({"type": "stop_recording"}))

            async def receive():
                async for raw in socket:
                    message = json.loads(raw)
                    if message.get("type") == "post_summarization":
                        error = message.get("error")
                        data = message.get("data") or {}
                        summary = Summary(
                            results=data.get("results"),
                            error=self._safe_error(json.dumps(error)) if error else None,
                        )
                        if on_summary is not None:
                            on_summary(summary)
                        elif summary.error:
                            logging.getLogger(__name__).warning("Gladia summarization failed: %s", summary.error)
                        continue
                    if message.get("type") == "error" or message.get("error"):
                        raise RuntimeError("Gladia reported a streaming error.")
                    if message.get("type") == "transcript":
                        data = message["data"]
                        utterance = data["utterance"]
                        on_transcript(Transcript(
                            utterance["text"], data["is_final"], data["id"],
                            utterance.get("language"),
                        ))

            sender = asyncio.create_task(send())
            receiver = asyncio.create_task(receive())
            stopper = asyncio.create_task((stop or asyncio.Event()).wait())
            try:
                done, _ = await asyncio.wait(
                    [sender, receiver, stopper], return_when=asyncio.FIRST_COMPLETED,
                )
                if receiver in done:
                    await receiver
                    if not sender.done():
                        raise RuntimeError("Gladia closed the stream before audio finished.")
                if stopper in done and not sender.done():
                    sender.cancel()
                result = await asyncio.gather(sender, return_exceptions=True)
                if isinstance(result[0], Exception):
                    raise result[0]
                try:
                    await asyncio.wait_for(receiver, timeout=30)
                except asyncio.TimeoutError:
                    raise RuntimeError("Timed out waiting for Gladia's final transcripts.") from None
            finally:
                for task in (sender, receiver, stopper):
                    task.cancel()
                await asyncio.gather(sender, receiver, stopper, return_exceptions=True)
