import { useReducer, useCallback, useEffect, useRef } from 'react';
import { AppContext, appReducer, initialState } from './context/AppContext';
import Sidebar from './components/Sidebar';
import ChatPanel from './components/ChatPanel';
import SettingsModal from './components/SettingsModal';

// ── WebSocket pool: keeps connections alive across session switches ──
const wsPoolRef = { current: {} }; // { sessionId: WebSocket }

function _ensureWS(sessionId, dispatch) {
  if (wsPoolRef.current[sessionId]) {
    return wsPoolRef.current[sessionId];
  }

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${location.host}/ws/${sessionId}`;
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

  // Auto-create session on first load
  useEffect(() => {
    if (!state.currentSessionId) {
      const id = crypto.randomUUID();
      dispatch({ type: 'NEW_SESSION', sessionId: id });
      _ensureWS(id, dispatch);
    }
  }, []);

  // Ensure WebSocket exists for current session
  useEffect(() => {
    if (state.currentSessionId) {
      _ensureWS(state.currentSessionId, dispatch);
    }
  }, [state.currentSessionId]);

  const openSettings = useCallback(() => dispatch({ type: 'TOGGLE_SETTINGS', open: true }), []);
  const closeSettings = useCallback(() => dispatch({ type: 'TOGGLE_SETTINGS', open: false }), []);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      <div className="app-container">
        <Sidebar onOpenSettings={openSettings} />
        <ChatPanel onOpenSettings={openSettings} />
        <SettingsModal isOpen={state.settingsModalOpen} onClose={closeSettings} />
      </div>
    </AppContext.Provider>
  );
}
