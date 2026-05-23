import { useContext, useCallback } from 'react';
import { AppContext } from '../context/AppContext';

export default function Thinking() {
  const { state, dispatch } = useContext(AppContext);
  const sessionState = state.sessionStates[state.currentSessionId] || {};
  const statusText = sessionState.statusText || '正在思考…';

  const cancel = useCallback(() => {
    window.__wsCancel?.();
    dispatch({ type: 'CANCELLED' });
  }, [dispatch]);

  return (
    <div className="thinking-container">
      <span className="thinking-dots">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </span>
      <span className="thinking-text">{statusText}</span>
      <button className="btn-cancel" onClick={cancel}>终止</button>
    </div>
  );
}
