import { useEffect, useRef, useContext } from 'react';
import { AppContext } from '../context/AppContext';
import { _ensureWS, _closeWS, wsPoolRef } from '../App';

const PROCESSING_TIMEOUT = 120_000; // 2 min timeout for complex multi-step questions

export default function useWebSocket(sessionId) {
  const { dispatch } = useContext(AppContext);
  const timeoutRef = useRef(null);
  const pingRef = useRef(null);
  const audioRef = useRef(null);  // currently playing Audio

  useEffect(() => {
    if (!sessionId) return;

    const ws = _ensureWS(sessionId, dispatch);

    // Attach message handler (reattach on session switch)
    const handler = (event) => {
      const msg = JSON.parse(event.data);
      console.log('[WS] ←', msg.type, msg.type === 'asr_result' ? `"${msg.text}"` : '');

      if (timeoutRef.current && msg.type !== 'pong') {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }

      switch (msg.type) {
        case 'asr_result':
          if (msg.text && msg.text.trim()) {
            dispatch({ type: 'UPDATE_LAST_USER_MESSAGE', text: msg.text, sessionId });
          } else {
            dispatch({ type: 'REMOVE_LAST_USER_PLACEHOLDER', sessionId });
          }
          break;
        case 'status':
          dispatch({ type: 'SET_STATUS_TEXT', text: msg.text, sessionId });
          break;
        case 'thinking':
          dispatch({ type: 'SET_THINKING', status: msg.status, sessionId });
          if (msg.status === 'start') {
            timeoutRef.current = setTimeout(() => {
              console.error('[WS] Processing timeout!');
              dispatch({ type: 'ERROR', message: '处理超时，请重试', sessionId });
            }, PROCESSING_TIMEOUT);
          }
          break;
        case 'bot_text':
          dispatch({ type: 'APPEND_BOT_MESSAGE', text: msg.text, sessionId });
          break;
        case 'bot_audio':
          try { _playAudio(msg.data, audioRef); } catch (e) { console.error('[WS] Audio play failed:', e); }
          setTimeout(() => dispatch({ type: 'SET_STATUS', status: 'idle', sessionId }), 500);
          break;
        case 'cancelled':
          dispatch({ type: 'CANCELLED', sessionId });
          break;
        case 'error':
          dispatch({ type: 'ERROR', message: msg.message, sessionId });
          break;
        case 'pong':
          break;
      }
    };

    ws.addEventListener('message', handler);

    // Heartbeat
    if (ws.readyState === WebSocket.OPEN) {
      _startPing();
    } else {
      ws.addEventListener('open', _startPing, { once: true });
    }

    function _startPing() {
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);
    }

    // Expose send/cancel/stopAudio for the CURRENT session
    window.__wsSend = (data) => {
      if (ws.readyState === WebSocket.OPEN) {
        console.log('[WS] →', JSON.parse(data).type);
        ws.send(data);
      } else {
        console.warn('[WS] Cannot send, state:', ws.readyState);
        dispatch({ type: 'ERROR', message: 'WebSocket 未连接，请刷新页面' });
      }
    };
    window.__wsCancel = () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'cancel' }));
      }
    };
    window.__stopAudio = () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };

    return () => {
      ws.removeEventListener('message', handler);
      clearInterval(pingRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      window.__stopAudio?.();
      // NOTE: do NOT close the WebSocket — other components may still use it
    };
  }, [sessionId, dispatch]);
}

function _playAudio(base64Data, audioRef) {
  if (audioRef.current) {
    audioRef.current.pause();
    audioRef.current = null;
  }
  const blob = _base64ToBlob(base64Data, 'audio/mp3');
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.onended = () => { URL.revokeObjectURL(url); audioRef.current = null; };
  audioRef.current = audio;
  audio.play().catch(console.error);
}

function _base64ToBlob(base64, mimeType) {
  const byteChars = atob(base64);
  const byteArrays = [];
  for (let offset = 0; offset < byteChars.length; offset += 512) {
    const slice = byteChars.slice(offset, offset + 512);
    const byteNumbers = new Array(slice.length);
    for (let i = 0; i < slice.length; i++) {
      byteNumbers[i] = slice.charCodeAt(i);
    }
    byteArrays.push(new Uint8Array(byteNumbers));
  }
  return new Blob(byteArrays, { type: mimeType });
}
