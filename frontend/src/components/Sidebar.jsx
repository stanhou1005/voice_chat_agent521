import { useContext, useCallback, useEffect } from 'react';
import { AppContext } from '../context/AppContext';
import { _ensureWS } from '../App';
import { getUsername } from '../services/auth';
import { generateUUID } from '../utils/uuid';
import * as api from '../services/api';

const REFRESH_INTERVAL = 5000;

export default function Sidebar({ onOpenSettings, onLogout }) {
  const { state, dispatch } = useContext(AppContext);
  const { sessions, currentSessionId } = state;

  // Load sessions on mount
  useEffect(() => {
    _fetchSessions();
    const interval = setInterval(_fetchSessions, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, []);

  // Refresh after each turn completes
  useEffect(() => {
    _fetchSessions();
  }, [state.status]);

  async function _fetchSessions() {
    try {
      const data = await api.getSessions();
      dispatch({ type: 'SET_SESSIONS', sessions: data.sessions || [] });
    } catch (e) {
      // server not ready yet, ignore
    }
  }

  const newChat = useCallback(() => {
    const id = generateUUID();
    dispatch({ type: 'NEW_SESSION', sessionId: id });
    _ensureWS(id, dispatch);
  }, [dispatch]);

  const selectSession = useCallback(
    async (id) => {
      _ensureWS(id, dispatch);
      try {
        const data = await api.getSessionMessages(id);
        dispatch({ type: 'SELECT_SESSION', sessionId: id, messages: data.messages || [] });
      } catch {
        dispatch({ type: 'SELECT_SESSION', sessionId: id, messages: [] });
      }
    },
    [dispatch]
  );

  return (
    <aside className="sidebar">
      <div className="sidebar-user">
        <span className="sidebar-username">{getUsername()}</span>
      </div>

      <button className="btn-new-chat" onClick={newChat}>
        + 新建会话
      </button>

      <div className="session-list">
        <h3 className="session-list-title">历史会话</h3>
        {sessions.map((s) => (
          <div
            key={s.thread_id}
            className={`session-item ${s.thread_id === currentSessionId ? 'active' : ''}`}
            onClick={() => selectSession(s.thread_id)}
          >
            <span className="session-title">{s.title || '新会话'}</span>
            <span className="session-time">{_formatTime(s.last_active_at)}</span>
          </div>
        ))}
        {sessions.length === 0 && (
          <p className="session-empty">暂无历史会话</p>
        )}
      </div>

      <div className="sidebar-footer">
        <button className="btn-logout" onClick={onLogout}>退出登录</button>
      </div>
    </aside>
  );
}

function _formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
  return d.toLocaleDateString('zh-CN');
}
