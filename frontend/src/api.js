// Zentrale API-Anbindung. In Produktion via VITE_API_URL auf die Railway-Backend-URL setzen.
const BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

const TOKEN_KEY = "vesti_token";

export const auth = {
  get token() {
    return localStorage.getItem(TOKEN_KEY);
  },
  set(token) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
  },
};

function authHeaders(extra = {}) {
  const t = auth.token;
  return t ? { ...extra, Authorization: `Bearer ${t}` } : extra;
}

async function handle(res) {
  if (res.status === 401) {
    auth.clear();
    window.dispatchEvent(new Event("vesti-unauthorized"));
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  // ---- Auth ----
  async register(payload) {
    return handle(
      await fetch(`${BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  },

  async login(payload) {
    return handle(
      await fetch(`${BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  },

  async me() {
    return handle(await fetch(`${BASE}/api/auth/me`, { headers: authHeaders() }));
  },

  // ---- Meta ----
  async getMeta() {
    return handle(await fetch(`${BASE}/api/meta`));
  },

  // ---- Items ----
  async listItems() {
    return handle(await fetch(`${BASE}/api/items`, { headers: authHeaders() }));
  },

  async analyze(file) {
    const form = new FormData();
    form.append("file", file);
    return handle(
      await fetch(`${BASE}/api/analyze`, {
        method: "POST",
        headers: authHeaders(),
        body: form,
      })
    );
  },

  async createItem(payload) {
    return handle(
      await fetch(`${BASE}/api/items`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async deleteItem(id) {
    return handle(
      await fetch(`${BASE}/api/items/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async recommend(payload) {
    return handle(
      await fetch(`${BASE}/api/recommend`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },
};
