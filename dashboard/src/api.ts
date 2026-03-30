import type { SnapshotResponse } from "./types";

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
