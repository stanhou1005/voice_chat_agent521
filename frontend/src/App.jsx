import { useReducer, useCallback, useEffect, useRef } from 'react';
import { AppContext, appReducer, initialState } from './context/AppContext';
import Sidebar from './components/Sidebar';
import ChatPanel from './components/ChatPanel';
import SettingsModal from './components/SettingsModal';
import LoginPage from './components/LoginPage';
import { getToken, isAuthenticated, getUsername, logout } from './services/auth';

// ── WebSocket pool: keeps connections alive across session switches ──
const wsPoolRef = { current: {} }; // { sessionId: WebSocket }

function _ensureWS(sessionId, dispatch) {
  if (wsPoolRef.current[sessionId]) {
    return wsPoolRef.current[sessionId];
  }

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const token = getToken();
  const wsUrl = `${protocol}//${location.host}/ws/${sessionId}?token=${encodeURIComponent(token || '')}`;
  const ws = new WebSocket(wsUrl);
  console.log(`[WS-Pool] Connecting to ${sessionId}`);

  ws.onopen = () => console.log(`[WS-Pool] ${sessionId} connected`);
  ws.onclose = () => {
    console.log(`[WS-Pool] ${sessionId} closed`);
    delete wsPoolRef.current[sessionId];
  };
  ws.onerror = () => console.error(`[WS-Pool] ${sessionId} error`);

  wsPoolRef.current[sessionId] = ws;
  return ws;
}

function _closeWS(sessionId) {
  const ws = wsPoolRef.current[sessionId];
  if (ws) {
    ws.close();
    delete wsPoolRef.current[sessionId];
  }
}

export { _ensureWS, _closeWS, wsPoolRef };

export default function App() {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Check existing auth on mount
  useEffect(() => {
    if (isAuthenticated()) {
      dispatch({ type: 'SET_AUTH', username: getUsername() });
    }
  }, []);

  // Auto-create session on first load (only when authenticated)
  useEffect(() => {
    if (state.isAuthenticated && !state.currentSessionId) {
      const id = crypto.randomUUID();
      dispatch({ type: 'NEW_SESSION', sessionId: id });
      _ensureWS(id, dispatch);
    }
  }, [state.isAuthenticated]);

  // Ensure WebSocket exists for current session
  useEffect(() => {
    if (state.currentSessionId) {
      _ensureWS(state.currentSessionId, dispatch);
    }
  }, [state.currentSessionId]);

  const openSettings = useCallback(() => dispatch({ type: 'TOGGLE_SETTINGS', open: true }), []);
  const closeSettings = useCallback(() => dispatch({ type: 'TOGGLE_SETTINGS', open: false }), []);

  const handleLogin = useCallback((username) => {
    dispatch({ type: 'SET_AUTH', username });
  }, []);

  const handleLogout = useCallback(() => {
    logout();
    // Close all WebSocket connections
    Object.keys(wsPoolRef.current).forEach((id) => _closeWS(id));
    dispatch({ type: 'LOGOUT' });
  }, []);

  if (!state.isAuthenticated) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      <div className="app-container">
        <Sidebar onOpenSettings={openSettings} onLogout={handleLogout} />
        <ChatPanel onOpenSettings={openSettings} onLogout={handleLogout} />
        <SettingsModal isOpen={state.settingsModalOpen} onClose={closeSettings} />
      </div>
    </AppContext.Provider>
  );
}
