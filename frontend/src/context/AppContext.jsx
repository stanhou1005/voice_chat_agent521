import { createContext } from 'react';

export const AppContext = createContext(null);

const _emptySession = () => ({
  messages: [],
  status: 'idle',
  statusText: '',
});

export const initialState = {
  isAuthenticated: false,
  username: null,
  currentSessionId: null,
  sessions: [],
  // Per-session state: { [sessionId]: { messages, status, statusText } }
  sessionStates: {},
  settingsModalOpen: false,
  error: null,
};

export function appReducer(state, action) {
  const sid = action.sessionId || state.currentSessionId;

  switch (action.type) {

    // ── Session-level actions (use sessionId to target) ──

    case 'SET_SESSIONS':
      return { ...state, sessions: action.sessions };

    case 'SELECT_SESSION': {
      const states = { ...state.sessionStates };
      if (!states[action.sessionId]) {
        states[action.sessionId] = _emptySession();
      }
      if (action.messages) {
        states[action.sessionId] = {
          ...states[action.sessionId],
          messages: action.messages,
        };
      }
      return { ...state, currentSessionId: action.sessionId, sessionStates: states };
    }

    case 'NEW_SESSION': {
      const states = { ...state.sessionStates, [action.sessionId]: _emptySession() };
      return { ...state, currentSessionId: action.sessionId, sessionStates: states };
    }

    case 'SET_STATUS': {
      if (!state.sessionStates[sid]) return state;
      return {
        ...state,
        sessionStates: {
          ...state.sessionStates,
          [sid]: { ...state.sessionStates[sid], status: action.status },
        },
      };
    }

    case 'SET_STATUS_TEXT': {
      if (!state.sessionStates[sid]) return state;
      return {
        ...state,
        sessionStates: {
          ...state.sessionStates,
          [sid]: { ...state.sessionStates[sid], statusText: action.text },
        },
      };
    }

    case 'APPEND_USER_MESSAGE': {
      if (!state.sessionStates[sid]) return state;
      const ss = state.sessionStates[sid];
      return {
        ...state,
        sessionStates: {
          ...state.sessionStates,
          [sid]: { ...ss, messages: [...ss.messages, { role: 'user', text: action.text }] },
        },
      };
    }

    case 'UPDATE_LAST_USER_MESSAGE': {
      if (!state.sessionStates[sid]) return state;
      const ss = state.sessionStates[sid];
      const msgs = [...ss.messages];
      const lastUserIdx = msgs.reduce((found, m, i) => m.role === 'user' ? i : found, -1);
      if (lastUserIdx >= 0) {
        msgs[lastUserIdx] = { ...msgs[lastUserIdx], text: action.text };
      }
      return {
        ...state,
        sessionStates: { ...state.sessionStates, [sid]: { ...ss, messages: msgs } },
      };
    }

    case 'SET_THINKING': {
      if (!state.sessionStates[sid]) return state;
      const ss = state.sessionStates[sid];
      const msgs = action.status === 'start'
        ? [...ss.messages, { role: 'system', text: 'thinking' }]
        : ss.messages.filter(m => m.text !== 'thinking');
      return {
        ...state,
        sessionStates: {
          ...state.sessionStates,
          [sid]: {
            ...ss,
            messages: msgs,
            statusText: action.status === 'start' ? '正在思考…' : '',
          },
        },
      };
    }

    case 'APPEND_BOT_MESSAGE': {
      if (!state.sessionStates[sid]) return state;
      const ss = state.sessionStates[sid];
      return {
        ...state,
        sessionStates: {
          ...state.sessionStates,
          [sid]: {
            ...ss,
            messages: ss.messages.filter(m => m.text !== 'thinking').concat({ role: 'assistant', text: action.text }),
          },
        },
      };
    }

    case 'REMOVE_LAST_USER_PLACEHOLDER': {
      if (!state.sessionStates[sid]) return state;
      const ss = state.sessionStates[sid];
      const msgs = [...ss.messages];
      const lastUserIdx = msgs.reduce((found, m, i) => m.role === 'user' ? i : found, -1);
      if (lastUserIdx >= 0) msgs.splice(lastUserIdx, 1);
      return {
        ...state,
        sessionStates: { ...state.sessionStates, [sid]: { ...ss, messages: msgs, status: 'idle', statusText: '' } },
      };
    }

    case 'CANCELLED': {
      if (!state.sessionStates[sid]) return state;
      const ss = state.sessionStates[sid];
      return {
        ...state,
        sessionStates: {
          ...state.sessionStates,
          [sid]: {
            ...ss,
            status: 'idle',
            messages: ss.messages.filter(m => m.text !== 'thinking' && m.text !== '识别中…'),
          },
        },
      };
    }

    case 'ERROR': {
      // ERROR can be global or per-session
      const targetSid = action.sessionId || sid;
      if (!state.sessionStates[targetSid]) return { ...state, error: action.message };
      const ess = state.sessionStates[targetSid];
      return {
        ...state,
        error: action.message,
        sessionStates: {
          ...state.sessionStates,
          [targetSid]: {
            ...ess,
            status: 'idle',
            messages: ess.messages.filter(m => m.text !== 'thinking' && m.text !== '识别中…'),
          },
        },
      };
    }

    case 'CLEAR_PENDING': {
      if (!state.sessionStates[sid]) return state;
      const pss = state.sessionStates[sid];
      return {
        ...state,
        sessionStates: {
          ...state.sessionStates,
          [sid]: { ...pss, status: 'idle', messages: pss.messages.filter(m => m.text !== 'thinking' && m.text !== '识别中…') },
        },
      };
    }

    // ── Global actions ──

    case 'CLEAR_ERROR':
      return { ...state, error: null };

    case 'TOGGLE_SETTINGS':
      return { ...state, settingsModalOpen: action.open };

    case 'SET_AUTH':
      return { ...state, isAuthenticated: true, username: action.username };

    case 'LOGOUT':
      return {
        ...initialState,
        isAuthenticated: false,
        username: null,
      };

    default:
      return state;
  }
}
