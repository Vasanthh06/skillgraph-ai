import type { Profile, ProfileUpdate, TokenResponse, User } from "../types";

// Same-origin by default: in development Vite proxies "/api" to the backend (see vite.config.ts),
// and in production the reverse proxy / static host does the same. This works on any host —
// unlike "http://localhost:8000", which only worked when the browser happened to run on the same
// machine as the backend. Set VITE_API_URL only for a genuinely separate API origin
// (e.g. "https://api.example.com", no trailing slash; the backend also serves the un-prefixed routes).
export const API_URL: string = import.meta.env.VITE_API_URL ?? "/api";
// Session JWT persists only in the server-set HttpOnly cookie, never Web Storage.
let memoryToken: string | null = null;
export const tokenStore = {
  get: () => memoryToken,
  set: (_t: string) => { memoryToken = "cookie-session"; },
  clear: () => { memoryToken = null; },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// FastAPI returns `detail` as a string, or a list of validation errors.
function readDetail(body: unknown, fallback: string): string {
  const d = (body as { detail?: unknown } | null)?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((e: { msg?: string; loc?: string[] }) => `${(e.loc ?? []).slice(1).join(".")}: ${(e.msg ?? "").replace(/^Value error, /, "")}`)
      .join("\n");
  }
  return fallback;
}

let onUnauthorized: (() => void) | null = null;
export const setUnauthorizedHandler = (fn: () => void) => { onUnauthorized = fn; };

async function request<T>(path: string, init: RequestInit = {}, auth = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && init.body) headers.set("Content-Type", "application/json");
  const token = tokenStore.get();
  headers.set("X-Requested-With", "SkillGraph");

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers, credentials: "same-origin" });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check that the backend is running.");
  }
  // Only let a 401 end the session if it was OUR current token that failed. A late response
  // for a request sent with an OLD token (e.g. the startup /auth/me check racing a fresh
  // login) must not clear the brand-new session it knows nothing about.
  if (res.status === 401 && auth && token && tokenStore.get() === token) onUnauthorized?.();
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, readDetail(body, `Request failed (${res.status})`));
  return body as T;
}

export const http = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body: body === undefined ? undefined : JSON.stringify(body) }),
  upload: <T>(path: string, file: File) => { const fd = new FormData(); fd.append("file", file); return request<T>(path, { method: "POST", body: fd }); },
};

export const api = {
  register: (d: { full_name: string; email: string; password: string; confirm_password: string }) =>
    request<TokenResponse>("/auth/register", { method: "POST", body: JSON.stringify(d) }, false),
  login: (d: { email: string; password: string }) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(d) }, false),
  me: () => request<User>("/auth/me"),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  profile: () => request<Profile>("/profile"),
  updateProfile: (d: ProfileUpdate) => request<Profile>("/profile", { method: "PUT", body: JSON.stringify(d) }),
  uploadPhoto: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<Profile>("/profile/photo", { method: "POST", body: fd });
  },
};
