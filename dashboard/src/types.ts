export type SnapshotRow = {
  symbol: string;
  name: string;
  as_of: string | null;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  day_pct: string;
  williams_r: number | null;
  note: string;
};

export type HistoryRow = {
  symbol: string;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  williams_r: number | null;
};

export type SnapshotResponse = {
  universe: string;
  period: number;
  sort: string;
  recent_sessions: number;
  snapshot: SnapshotRow[];
  history: HistoryRow[];
};

export type SearchHit = {
  symbol: string;
  name: string;
  exchange: string;
  quote_type: string;
};

export type WatchlistEntry = {
  line: string;
  yahoo: string;
};

export type WatchlistPatchResponse = {
  entries: WatchlistEntry[];
  added?: string[];
  skipped?: { symbol: string; reason: string }[];
  removed?: string[];
};
