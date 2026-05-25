import { useContext, useRef, useEffect, useCallback, useState } from 'react';
import { AppContext } from '../context/AppContext';
import Message from './Message';
import Thinking from './Thinking';
import useWebSocket from '../hooks/useWebSocket';
import useRecorder, { _arrayBufferToBase64 } from '../hooks/useRecorder';

export default function ChatPanel({ onOpenSettings, onLogout }) {
  const { state, dispatch } = useContext(AppContext);
  const { currentSessionId, error } = state;
  // Per-session state (isolated from other tabs)
  const sessionState = state.sessionStates[currentSessionId] || { messages: [], status: 'idle', statusText: '' };
  const { messages, status } = sessionState;
  const scrollRef = useRef(null);
  const recorder = useRecorder();
  const [silenceCountdown, setSilenceCountdown] = useState(null);

  useWebSocket(currentSessionId);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  // Error auto-dismiss
  useEffect(() => {
    if (error) {
      const t = setTimeout(() => dispatch({ type: 'CLEAR_ERROR' }), 5000);
      return () => clearTimeout(t);
    }
  }, [error, dispatch]);

  // Keyboard shortcut: Space to toggle recording (when not in input)
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.code === 'Space') {
        e.preventDefault();
        if (status === 'idle') _start();
        else if (status === 'recording') _stop();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [status]);

  const _start = useCallback(async () => {
    if (status !== 'idle') return;
    if (!window.__wsSend) {
      dispatch({ type: 'ERROR', sessionId: currentSessionId, message:'WebSocket 未连接，请刷新页面' });
      return;
    }
    setSilenceCountdown(null);
    dispatch({ type: 'SET_STATUS', status: 'recording', sessionId: currentSessionId });
    try {
      await recorder.startRecording(
      // onFinish: called when silence timeout or manual stop
      (wavBytes, duration) => {
        if (wavBytes && wavBytes.byteLength > 0) {
          dispatch({ type: 'SET_STATUS', status: 'processing', sessionId: currentSessionId });
          dispatch({ type: 'APPEND_USER_MESSAGE', text: '识别中…', sessionId: currentSessionId });
          const b64 = _arrayBufferToBase64(wavBytes);
          window.__wsSend(JSON.stringify({ type: 'audio', data: b64, timestamp: Date.now() }));
        } else {
          dispatch({ type: 'SET_STATUS', status: 'idle', sessionId: currentSessionId });
          if (duration < 1.0) {
            dispatch({ type: 'ERROR', sessionId: currentSessionId, message:'录音时间太短，请重新说话' });
          }
        }
        setSilenceCountdown(null);
      },
      // onSilenceTick: remaining seconds of silence
      (remaining) => setSilenceCountdown(remaining),
    );
    } catch (err) {
      console.error('Recorder start failed:', err);
      dispatch({ type: 'SET_STATUS', status: 'idle', sessionId: currentSessionId });
      dispatch({ type: 'ERROR', sessionId: currentSessionId, message:'麦克风启动失败，请检查权限' });
    }
  }, [status, recorder, dispatch]);

  const _stop = useCallback(() => {
    recorder.stopRecording();
  }, [recorder]);

  const statusLabel = {
    idle: '就绪 — 按空格键或点击开始说话',
    recording: silenceCountdown ? `聆听中… 静音 ${silenceCountdown}s 后自动结束` : '正在聆听… 点击结束',
    processing: '处理中…',
  }[status];

  return (
    <main className="chat-panel">
      <header className="chat-header">
        <span className="status-indicator" data-status={status}>
          {statusLabel}
        </span>
        <div className="header-actions">
          <button className="btn-settings" onClick={onOpenSettings} title="设置">
            ⚙
          </button>
          <button className="btn-settings" onClick={onLogout} title="退出登录">
            ↩
          </button>
        </div>
      </header>

      {error && (
        <div className="error-banner" onClick={() => dispatch({ type: 'CLEAR_ERROR' })}>
          {error}
        </div>
      )}

      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 && status === 'idle' && (
          <p className="chat-placeholder">按空格键或点击下方按钮开始说话…</p>
        )}
        {messages.map((msg, i) =>
          msg.text === 'thinking' ? (
            <Thinking key={`thinking-${i}`} />
          ) : (
            <Message key={i} role={msg.role} text={msg.text} />
          )
        )}
      </div>

      {/* Record button area */}
      <div className="record-bar">
        {status === 'idle' && (
          <button className="btn-record btn-record-start" onClick={_start}>
            🎤 开始说话
          </button>
        )}
        {status === 'recording' && (
          <button className="btn-record btn-record-stop" onClick={_stop}>
            ⏹ 结束说话
          </button>
        )}
        {status === 'processing' && (
          <div className="record-bar-processing">处理中…</div>
        )}
      </div>
    </main>
  );
}
