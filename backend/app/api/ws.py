"""
WebSocket endpoint for voice chat sessions.
"""

import json
import logging
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.graph import run_agent
from app.agent.nodes import CancelledError
from app.core.auth import verify_token
from app.db.langgraph import get_checkpointer, get_store, STORE_NAMESPACE
from app.services.asr import recognize
from app.services.tts import synthesize
from app.utils.cancellation import create_cancel_event, set_cancel_event, clear_cancel_event, remove_cancel_event

logger = logging.getLogger("voice_chat.ws")
router = APIRouter()


async def _upsert_session(thread_id: str, user_text: str, user_id: str):
    """Create or update session metadata in LangGraph Store (long-term memory)."""
    from datetime import datetime, timezone
    store = get_store()

    existing = await store.aget(STORE_NAMESPACE, thread_id)

    if existing:
        value = existing.value
        value["last_active_at"] = datetime.now(timezone.utc).isoformat()
        value["message_count"] = value.get("message_count", 0) + 2
    else:
        value = {
            "thread_id": thread_id,
            "title": user_text[:50] if user_text else "新会话",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_active_at": datetime.now(timezone.utc).isoformat(),
            "message_count": 2,
            "user_id": user_id,
        }

    await store.aput(STORE_NAMESPACE, thread_id, value)


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str, token: str = ""):
    try:
        payload = verify_token(token)
    except Exception:
        await ws.close(code=4001, reason="Authentication failed")
        return

    user_id = payload.get("sub", "")
    await ws.accept()
    create_cancel_event(session_id)
    logger.info(f"[{session_id}] WebSocket connected (user: {payload.get('username')})")

    checkpointer = get_checkpointer()

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            if msg["type"] == "ping":
                await ws.send_json({"type": "pong"})

            elif msg["type"] == "audio":
                data_len = len(msg.get("data", ""))
                logger.info(f"[{session_id}] Received audio: {data_len} base64 chars")

                try:
                    # Reset cancel flag from any previous turn
                    clear_cancel_event(session_id)

                    # 1. Decode
                    audio_bytes = base64.b64decode(msg["data"])
                    logger.info(f"[{session_id}] Decoded audio: {len(audio_bytes)} bytes")

                    # 2. ASR
                    await ws.send_json({"type": "status", "phase": "asr", "text": "正在识别语音…"})
                    logger.info(f"[{session_id}] Calling ASR...")
                    text = await recognize(audio_bytes)
                    logger.info(f"[{session_id}] ASR result: '{text}'")
                    await ws.send_json({"type": "asr_result", "text": text, "is_final": True})

                    # Skip if ASR returned nothing
                    if not text or not text.strip():
                        logger.info(f"[{session_id}] ASR returned empty, skipping")
                        await ws.send_json({"type": "error", "message": "未检测到语音内容，请重新说话"})
                        continue

                    # 3. Create session metadata on first message
                    await _upsert_session(session_id, text, user_id)

                    # 4. Thinking + agent
                    await ws.send_json({"type": "thinking", "status": "start"})

                    async def on_status(phase: str, status_text: str):
                        await ws.send_json({"type": "status", "phase": phase, "text": status_text})

                    logger.info(f"[{session_id}] Running agent for: '{text}'")
                    try:
                        bot_text = await run_agent(checkpointer, session_id, text, on_status=on_status)
                    except CancelledError:
                        logger.info(f"[{session_id}] Cancelled by user")
                        await ws.send_json({"type": "cancelled"})
                        await ws.send_json({"type": "thinking", "status": "stop"})
                        clear_cancel_event(session_id)  # reset for next turn
                        continue
                    logger.info(f"[{session_id}] Agent reply: '{bot_text[:80]}...'")

                    # 5. Bot text
                    await ws.send_json({"type": "bot_text", "text": bot_text})
                    await ws.send_json({"type": "thinking", "status": "stop"})

                    # 6. TTS
                    await ws.send_json({"type": "status", "phase": "tts", "text": "正在合成语音…"})
                    logger.info(f"[{session_id}] Calling TTS...")
                    audio_data = await synthesize(bot_text)
                    audio_b64 = base64.b64encode(audio_data).decode()
                    await ws.send_json({"type": "bot_audio", "data": audio_b64})
                    logger.info(f"[{session_id}] TTS done: {len(audio_data)} bytes MP3")

                except Exception as e:
                    logger.exception(f"[{session_id}] Processing error: {e}")
                    await ws.send_json({
                        "type": "error",
                        "message": f"处理失败: {str(e)[:200]}"
                    })
                    await ws.send_json({"type": "thinking", "status": "stop"})

            elif msg["type"] == "cancel":
                logger.info(f"[{session_id}] Cancel requested")
                set_cancel_event(session_id)

    except WebSocketDisconnect:
        logger.info(f"[{session_id}] WebSocket disconnected")
        set_cancel_event(session_id)
    except Exception as e:
        logger.exception(f"[{session_id}] WebSocket error: {e}")
    finally:
        remove_cancel_event(session_id)
