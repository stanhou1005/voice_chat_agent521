"""
SiliconFlow ASR — SenseVoiceSmall (免费).
OpenAI-compatible endpoint: POST /v1/audio/transcriptions
**语音识别(ASR - Automatic Speech Recognition)**功能
"""

import httpx
from app.config import SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL

ASR_MODEL = "FunAudioLLM/SenseVoiceSmall"


async def recognize(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """
    Send WAV audio bytes to SiliconFlow SenseVoiceSmall, return recognized text.
    SenseVoiceSmall is FREE on SiliconFlow.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{SILICONFLOW_BASE_URL}/audio/transcriptions",
            headers={"Authorization": f"Bearer {SILICONFLOW_API_KEY}"},
            files={"file": (filename, audio_bytes, "audio/wav")},
            data={"model": ASR_MODEL},
        )
        response.raise_for_status()
        return response.json()["text"]
