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
