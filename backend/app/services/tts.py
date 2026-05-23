"""
SiliconFlow TTS — CosyVoice2-0.5B.
OpenAI-compatible endpoint: POST /v1/audio/speech
Returns MP3 audio bytes.
"""

import httpx
from app.config import SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL

TTS_MODEL = "FunAudioLLM/CosyVoice2-0.5B"
TTS_VOICE = "FunAudioLLM/CosyVoice2-0.5B:alex"  # default voice


async def synthesize(text: str, voice: str = TTS_VOICE) -> bytes:
    """
    Convert text to speech using SiliconFlow CosyVoice2.
    Returns MP3 audio bytes.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{SILICONFLOW_BASE_URL}/audio/speech",
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": TTS_MODEL,
                "input": text,
                "voice": voice,
                "response_format": "mp3",
            },
        )
        response.raise_for_status()
        return response.content  # raw MP3 bytes
