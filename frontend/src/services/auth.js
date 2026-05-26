const TOKEN_KEY = 'voice_chat_token';
const USERNAME_KEY = 'voice_chat_username';
const ROLE_KEY = 'voice_chat_role';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUsername() {
  return localStorage.getItem(USERNAME_KEY);
}

export function getRole() {
  return localStorage.getItem(ROLE_KEY);
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
  localStorage.setItem(TOKEN_KEY, data.token);
  localStorage.setItem(USERNAME_KEY, data.username);
  localStorage.setItem(ROLE_KEY, data.role || 'user');
  return data;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USERNAME_KEY);
  localStorage.removeItem(ROLE_KEY);
}
