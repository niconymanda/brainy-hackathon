"""PCM audio sources; PortAudio is loaded only when microphone access is needed."""

import asyncio
import sys
import wave


async def wav_audio(path):
    with wave.open(str(path), "rb") as source:
        if (source.getframerate(), source.getnchannels(), source.getsampwidth()) != (16000, 1, 2):
            raise ValueError("WAV must be uncompressed 16 kHz, mono, 16-bit PCM.")
        while chunk := source.readframes(1600):
            yield chunk
            await asyncio.sleep(len(chunk) / 32000)


async def microphone_audio(device=None):
    import sounddevice as sd

    loop = asyncio.get_running_loop()
    queue = asyncio.Queue(maxsize=20)

    def enqueue(chunk, status):
        if queue.full():
            queue.get_nowait()
            queue.put_nowait(RuntimeError("Microphone buffer overflow; audio could not be streamed fast enough."))
        else:
            queue.put_nowait(RuntimeError(f"Microphone capture error: {status}") if status else chunk)

    def callback(indata, frames, time, status):
        chunk = bytes(indata)
        if sys.byteorder != "little":
            from array import array
            samples = array("h", chunk)
            samples.byteswap()
            chunk = samples.tobytes()
        loop.call_soon_threadsafe(enqueue, chunk, status)

    with sd.RawInputStream(
        samplerate=16000, channels=1, dtype="int16", blocksize=1600,
        device=device, callback=callback,
    ):
        while True:
            chunk = await queue.get()
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk
