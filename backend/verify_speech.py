"""
Verify SiliconFlow ASR + TTS API connectivity.
Run with: python verify_speech.py
Requires SILICONFLOW_API_KEY in .env
"""

import asyncio
import sys
import os
import base64
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from app.services.asr import recognize
from app.services.tts import synthesize

# A tiny valid WAV file (16kHz, 16-bit, mono) with ~1 second of near-silence
# Generated programmatically to avoid needing a real audio file
def _make_test_wav() -> bytes:
    import struct
    sample_rate = 16000
    duration = 1.0
    num_samples = int(sample_rate * duration)
    buf = bytearray()
    # RIFF header
    buf += b"RIFF"
    buf += struct.pack("<I", 36 + num_samples * 2)
    buf += b"WAVE"
    # fmt chunk
    buf += b"fmt "
    buf += struct.pack("<I", 16)  # chunk size
    buf += struct.pack("<H", 1)   # PCM
    buf += struct.pack("<H", 1)   # mono
    buf += struct.pack("<I", sample_rate)
    buf += struct.pack("<I", sample_rate * 2)
    buf += struct.pack("<H", 2)   # block align
    buf += struct.pack("<H", 16)  # bits per sample
    # data chunk
    buf += b"data"
    buf += struct.pack("<I", num_samples * 2)
    for _ in range(num_samples):
        buf += struct.pack("<h", 0)  # silence
    return bytes(buf)


async def main():
    print("=" * 50)
    print("SiliconFlow Speech API Verification")
    print("=" * 50)

    api_key = os.getenv("SILICONFLOW_API_KEY", "")
    if not api_key:
        # Try loading from .env
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent / ".env")
        api_key = os.getenv("SILICONFLOW_API_KEY", "")

    if not api_key:
        print("\n⚠ SILICONFLOW_API_KEY not set in .env, skipping")
        return

    # 1. ASR test
    print("\n[1/2] Testing ASR (SenseVoiceSmall)...")
    print("  Sending test WAV (1s silence)...")
    try:
        text = await recognize(_make_test_wav(), "test.wav")
        print(f"  ✓ ASR response: '{text}'")
        print("  ✓ ASR API is working!")
    except Exception as e:
        print(f"  ✗ ASR failed: {e}")

    # 2. TTS test
    print("\n[2/2] Testing TTS (CosyVoice2)...")
    test_text = "你好，这是一个语音合成测试。"
    print(f"  Sending: '{test_text}'")
    try:
        audio = await synthesize(test_text)
        print(f"  ✓ TTS returned {len(audio)} bytes of MP3 audio")
        # Save sample
        out = Path(__file__).resolve().parent / "test_tts_output.mp3"
        out.write_bytes(audio)
        print(f"  ✓ Saved to {out}")
        print("  ✓ TTS API is working!")
    except Exception as e:
        print(f"  ✗ TTS failed: {e}")

    print("\n" + "=" * 50)
    print("Verification complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
