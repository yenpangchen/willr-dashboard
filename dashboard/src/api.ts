import type {
  SearchHit,
  SnapshotResponse,
  WatchlistEntry,
  WatchlistPatchResponse,
} from "./types";

/** Empty = same origin (e.g. FastAPI serves / + /api). Set at build: VITE_API_BASE=https://api.example.com */
const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${p}`;
}

export async function fetchSnapshot(params: URLSearchParams): Promise<SnapshotResponse> {
  const res = await fetch(`${apiUrl("/api/snapshot")}?${params.toString()}`);
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json();
}

export async function fetchSearch(q: string, limit = 12): Promise<{ results: SearchHit[] }> {
  const p = new URLSearchParams({ q, limit: String(limit) });
  const res = await fetch(`${apiUrl("/api/search")}?${p}`);
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json();
}

export async function fetchWatchlist(): Promise<{ entries: WatchlistEntry[] }> {
  const res = await fetch(apiUrl("/api/watchlist"));
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json();
}

export async function patchWatchlist(body: {
  add?: string[];
  remove?: string[];
}): Promise<WatchlistPatchResponse> {
  const res = await fetch(apiUrl("/api/watchlist"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json();
}
