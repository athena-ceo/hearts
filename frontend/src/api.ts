// Copyright (c) 2026 Athena Decisions Systems SAS.
import type { DealReview, NewTable, Opponent, Player, TableInfo } from "./types";

const API = import.meta.env.VITE_API_BASE ?? "/api";

// --- identity ---------------------------------------------------------------
const TOKEN_KEY = "hearts.token";

export function authToken(): string | null { return localStorage.getItem(TOKEN_KEY); }
export function setAuthToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t); else localStorage.removeItem(TOKEN_KEY);
}

let signedOut: () => void = () => {};
/** Called when the server stops accepting the stored token. */
export function onSignedOut(listener: () => void) { signedOut = listener; }

export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}

async function jfetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = authToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["X-Hearts-Token"] = token;
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* ignore */ }
    if (res.status === 401 && token) {
      setAuthToken(null);
      signedOut();
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return jfetch<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) });
}

/** The address of a table's live connection, on the same host as the API. */
export function tableSocketUrl(tableId: string, token: string): string {
  const url = new URL(`${API}/tables/${tableId}/ws`, window.location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("token", token);
  return url.toString();
}

interface Session { player: Player; token: string; }

export const api = {
  register: (name: string, password: string, code: string) =>
    post<Session>("/auth/register", { name, password, code }),
  login: (name: string, password: string) => post<Session>("/auth/login", { name, password }),
  logout: () => post<{ ok: boolean }>("/auth/logout"),
  me: () => jfetch<{ player: Player }>("/auth/me"),

  opponents: () => jfetch<{ opponents: Opponent[] }>("/opponents"),
  tables: () => jfetch<{ tables: TableInfo[] }>("/tables"),
  table: (id: string) => jfetch<TableInfo>(`/tables/${id}`),
  createTable: (table: NewTable) => post<TableInfo>("/tables", table),
  join: (id: string, seat?: number) => post<TableInfo>(`/tables/${id}/join`, seat ? { seat } : {}),
  fill: (id: string) => post<TableInfo>(`/tables/${id}/fill`),
  review: (id: string, number: number) => jfetch<DealReview>(`/tables/${id}/deals/${number}/review`),
};
