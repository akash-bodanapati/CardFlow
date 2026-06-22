const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const apiClient = {
  createSession: async () => {
    const res = await fetch(`${API_BASE_URL}/sessions/`, { method: 'POST' });
    return res.json();
  },
  getSessions: async () => {
    const res = await fetch(`${API_BASE_URL}/sessions/`);
    return res.json();
  },
  getMessages: async (sessionId) => {
    const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`);
    return res.json();
  },
  sendMessage: async (sessionId, formData) => {
    const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },
  confirmExtraction: async (sessionId, payload) => {
    const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return res.json();
  },
  deleteSession: async (sessionId) => {
    const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    return res.json();
  }
};
