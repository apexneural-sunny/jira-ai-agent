"""
modules/transcriber.py — Voice transcription: transcribe_voice(path) -> str
"""
import logging

from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)
_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


async def transcribe_voice(path: str) -> str:
    """Transcribe an audio file at *path* using OpenAI Whisper. Returns transcript text."""
    try:
        with open(path, "rb") as audio_file:
            response = await _client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
        return response.text
    except Exception as e:
        logger.error("transcribe_voice failed: %s", e)
        raise
