const TOKEN_KEY = 'voice_chat_token';
const USERNAME_KEY = 'voice_chat_username';
const ROLE_KEY = 'voice_chat_role';

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function getUsername() {
  return sessionStorage.getItem(USERNAME_KEY);
}

export function getRole() {
  return sessionStorage.getItem(ROLE_KEY);
}

export function isAdmin() {
  return getRole() === 'admin';
}

export function isAuthenticated() {
  return !!getToken();
}

export async function login(username, password) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(err.detail || 'Login failed');
  }
  const data = await res.json();
  sessionStorage.setItem(TOKEN_KEY, data.token);
  sessionStorage.setItem(USERNAME_KEY, data.username);
  sessionStorage.setItem(ROLE_KEY, data.role || 'user');
  return data;
}

export function logout() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USERNAME_KEY);
  sessionStorage.removeItem(ROLE_KEY);
}
