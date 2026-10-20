// src/api.js
// One place for every call to the backend.
// The API address comes from an environment variable, so the same code works
// locally (http://localhost:8000) and in production (your Render URL).

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function getToken() {
  return localStorage.getItem("token");
}

// request("/auth/me") or request("/attempts", { method: "POST", body: {...} })
export async function request(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    // The login endpoint expects form data (OAuth2 standard), not JSON
    payload = new URLSearchParams(form);
  } else if (body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`${API_URL}${path}`, { method, headers, body: payload });
  const data = await res.json().catch(() => null);

  if (!res.ok) {
    // FastAPI puts the error message in "detail" (a string, or a list for 422s)
    const detail = data?.detail;
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : detail;
    const error = new Error(message || `Request failed (${res.status})`);
    error.status = res.status;
    throw error;
  }
  return data;
}
