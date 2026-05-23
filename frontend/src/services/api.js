const BASE = '/api';

export async function getSessions(limit = 50, offset = 0) {
  const res = await fetch(`${BASE}/sessions?limit=${limit}&offset=${offset}`);
  return res.json();
}

export async function getSessionMessages(sessionId) {
  const res = await fetch(`${BASE}/sessions/${sessionId}/messages`);
  return res.json();
}

export async function deleteSession(sessionId) {
  await fetch(`${BASE}/sessions/${sessionId}`, { method: 'DELETE' });
}

export async function getSettings() {
  const res = await fetch(`${BASE}/settings`);
  return res.json();
}

export async function updateSettings(data) {
  const res = await fetch(`${BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}
