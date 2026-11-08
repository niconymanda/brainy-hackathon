"""ElevenLabs text-to-speech for the voice Brainy speaks with."""

import os

import httpx

API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice}"
DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL = "eleven_flash_v2_5"


def api_key():
    return os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVEN_API_KEY", "")


async def synthesize(text):
    """Returns MP3 bytes for `text`; raises on a missing key or an API error."""
    key = api_key()
    if not key:
        raise ValueError("Set ELEVENLABS_API_KEY in the environment or .env file.")
    voice = os.getenv("ELEVENLABS_VOICE_ID") or DEFAULT_VOICE
    body = {"text": text, "model_id": os.getenv("ELEVENLABS_MODEL") or DEFAULT_MODEL}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(API_URL.format(voice=voice), params={"output_format": "mp3_44100_128"},
                                     headers={"xi-api-key": key}, json=body)
        response.raise_for_status()
        return response.content
