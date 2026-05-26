import { getToken } from './auth';

const BASE = '/api';

function authHeaders() {
  const token = getToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export async function getSessions(limit = 50, offset = 0) {
  const res = await fetch(`${BASE}/sessions?limit=${limit}&offset=${offset}`, {
    headers: authHeaders(),
  });
  return res.json();
}

export async function getSessionMessages(sessionId) {
  const res = await fetch(`${BASE}/sessions/${sessionId}/messages`, {
    headers: authHeaders(),
  });
  return res.json();
}

export async function deleteSession(sessionId) {
  await fetch(`${BASE}/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
}

export async function getSettings() {
  const res = await fetch(`${BASE}/settings`, {
    headers: authHeaders(),
  });
  return res.json();
}

export async function updateSettings(data) {
  const res = await fetch(`${BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function getUsers() {
  const res = await fetch(`${BASE}/auth/users`, {
    headers: authHeaders(),
  });
  return res.json();
}

export async function createUser(username, password, role = 'user') {
  const res = await fetch(`${BASE}/auth/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ username, password, role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed' }));
    throw new Error(err.detail || 'Failed');
  }
  return res.json();
}

export async function deleteUser(userId) {
  const res = await fetch(`${BASE}/auth/users/${userId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed' }));
    throw new Error(err.detail || 'Failed');
  }
}
