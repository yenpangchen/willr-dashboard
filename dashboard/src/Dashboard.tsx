import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchSnapshot } from "./api";
import type { HistoryRow, SnapshotResponse, SnapshotRow } from "./types";

function wrCellBg(wr: number | null): string {
  if (wr == null) return "transparent";
  const t = (wr + 100) / 100;
  const r = Math.round(30 + t * 120);
  const g = Math.round(80 + (1 - t) * 40);
  const b = Math.round(140 + (1 - t) * 40);
  return `rgba(${r}, ${g}, ${b}, 0.35)`;
}

function fmtVol(n: number | null): string {
  if (n == null) return "-";
  if (n >= 1e8) return `${(n / 1e8).toFixed(2)} 億`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)} 萬`;
  return String(n);
}

function inRange(wr: number | null, lo: number, hi: number): boolean {
  if (wr == null) return false;
  const min = Math.min(lo, hi);
  const max = Math.max(lo, hi);
  return wr >= min && wr <= max;
}

export function Dashboard() {
  const [period, setPeriod] = useState(14);
  const [recent, setRecent] = useState(60);
  const [data, setData] = useState<SnapshotResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  // Default intervals requested by user.
  const [rangeLowLo, setRangeLowLo] = useState(-100);
  const [rangeLowHi, setRangeLowHi] = useState(-90);
  const [rangeHighLo, setRangeHighLo] = useState(-10);
  const [rangeHighHi, setRangeHighHi] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const p = new URLSearchParams({
        period: String(period),
        sort: "symbol",
        recent: String(recent),
      });
      const res = await fetchSnapshot(p);
      setData(res);
      const first =
        res.snapshot.find((r) => r.williams_r != null)?.symbol ??
        res.snapshot[0]?.symbol ??
        null;
      setSelected((prev) =>
        prev && res.snapshot.some((s) => s.symbol === prev) ? prev : first
      );
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [period, recent]);

  useEffect(() => {
    void load();
  }, [load]);

  const snapshot = data?.snapshot ?? [];

  const lowRows = useMemo(
    () => snapshot.filter((r) => inRange(r.williams_r, rangeLowLo, rangeLowHi)),
    [snapshot, rangeLowLo, rangeLowHi]
  );

  const highRows = useMemo(
    () => snapshot.filter((r) => inRange(r.williams_r, rangeHighLo, rangeHighHi)),
    [snapshot, rangeHighLo, rangeHighHi]
  );

  const historyForSelected: HistoryRow[] = useMemo(() => {
    if (!data || !selected) return [];
    return data.history.filter((h) => h.symbol === selected);
  }, [data, selected]);

  const composedData = useMemo(
    () =>
      historyForSelected.map((h) => ({
        date: h.date.slice(5),
        close: h.close,
        williams_r: h.williams_r,
      })),
    [historyForSelected]
  );

  const renderRangeTable = (title: string, rows: SnapshotRow[]) => (
    <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
      <div style={{ padding: "0.75rem 1rem", borderBottom: "1px solid var(--border)" }}>
        <strong>{title}</strong>
        <span className="muted" style={{ marginLeft: "0.5rem" }}>共 {rows.length} 檔</span>
      </div>
      <div className="scroll-y" style={{ maxHeight: 300 }}>
        <table className="data-grid">
          <thead>
            <tr>
              <th>代號</th>
              <th>名稱</th>
              <th className="num">%R</th>
              <th className="num">收</th>
              <th className="num">漲跌</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={`${title}-${row.symbol}`}
                className={row.symbol === selected ? "selected" : ""}
                onClick={() => setSelected(row.symbol)}
              >
                <td>{row.symbol}</td>
                <td
                  className="muted"
                  style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                  title={row.name || ""}
                >
                  {row.name || "-"}
                </td>
                <td className="num" style={{ background: wrCellBg(row.williams_r) }}>
                  {row.williams_r ?? "-"}
                </td>
                <td className="num">{row.close ?? "-"}</td>
                <td className={`num ${row.day_pct.startsWith("+") ? "tag-up" : row.day_pct.startsWith("-") ? "tag-down" : ""}`}>
                  {row.day_pct || "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div style={{ minHeight: "100%", padding: "1.25rem", maxWidth: 1400, margin: "0 auto" }}>
      <header
        style={{
          marginBottom: "1rem",
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: "1.35rem", fontWeight: 600 }}>WillR Dashboard</h1>
          <p className="muted" style={{ margin: "0.25rem 0 0" }}>
            台灣 50 Williams %R（Yahoo）
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
          <label className="muted">
            週期 <input type="number" min={2} max={120} value={period} onChange={(e) => setPeriod(Number(e.target.value) || 14)} />
          </label>
          <label className="muted">
            歷史天數 <input type="number" min={10} max={250} value={recent} onChange={(e) => setRecent(Number(e.target.value) || 60)} />
          </label>
          <button type="button" className="primary" disabled={loading} onClick={() => void load()}>
            {loading ? "載入中..." : "重新整理"}
          </button>
        </div>
      </header>

      <section className="panel" style={{ marginBottom: "1rem" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", alignItems: "center" }}>
          <strong>區間設定</strong>
          <label className="muted">
            低檔區間
            <input type="number" value={rangeLowLo} onChange={(e) => setRangeLowLo(Number(e.target.value) || -100)} style={{ marginLeft: 6 }} />
            <span style={{ margin: "0 6px" }}>~</span>
            <input type="number" value={rangeLowHi} onChange={(e) => setRangeLowHi(Number(e.target.value) || -90)} />
          </label>
          <label className="muted">
            高檔區間
            <input type="number" value={rangeHighLo} onChange={(e) => setRangeHighLo(Number(e.target.value) || -10)} style={{ marginLeft: 6 }} />
            <span style={{ margin: "0 6px" }}>~</span>
            <input type="number" value={rangeHighHi} onChange={(e) => setRangeHighHi(Number(e.target.value) || 0)} />
          </label>
          <span className="muted">預設：-100~-90、-10~0</span>
        </div>
      </section>

      {err && (
        <div className="panel" style={{ marginBottom: "1rem", borderColor: "var(--negative)", color: "var(--negative)" }}>
          {err}
        </div>
      )}

      <div className="grid-two" style={{ marginBottom: "1rem" }}>
        {renderRangeTable(`低檔區間 (${Math.min(rangeLowLo, rangeLowHi)} ~ ${Math.max(rangeLowLo, rangeLowHi)})`, lowRows)}
        {renderRangeTable(`高檔區間 (${Math.min(rangeHighLo, rangeHighHi)} ~ ${Math.max(rangeHighLo, rangeHighHi)})`, highRows)}
      </div>

      <div className="panel" style={{ minHeight: 360, marginBottom: "1rem" }}>
        <div className="muted" style={{ marginBottom: "0.5rem" }}>
          已選 {selected ?? "-"} · 收盤與 %R
        </div>
        <div style={{ height: 320 }}>
          {composedData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={composedData} margin={{ left: 4, right: 8, top: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                <XAxis dataKey="date" tick={{ fill: "#8b949e", fontSize: 10 }} />
                <YAxis yAxisId="l" domain={["auto", "auto"]} tick={{ fill: "#8b949e", fontSize: 10 }} />
                <YAxis yAxisId="r" orientation="right" domain={[-100, 0]} tick={{ fill: "#8b949e", fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #30363d" }} />
                <Legend />
                <Line yAxisId="l" type="monotone" dataKey="close" name="收盤" stroke="#f0883e" dot={false} strokeWidth={2} />
                <Line yAxisId="r" type="monotone" dataKey="williams_r" name="%R" stroke="#58a6ff" dot={false} strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="muted" style={{ padding: "2rem", textAlign: "center" }}>無歷史資料或未選股</div>
          )}
        </div>
      </div>

      <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
        <div className="scroll-y" style={{ maxHeight: 500 }}>
          <table className="data-grid">
            <thead>
              <tr>
                <th>代號</th>
                <th>名稱</th>
                <th>日</th>
                <th className="num">開</th>
                <th className="num">高</th>
                <th className="num">低</th>
                <th className="num">收</th>
                <th className="num">量</th>
                <th className="num">漲跌</th>
                <th className="num">%R</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.map((row) => (
                <tr key={row.symbol} className={row.symbol === selected ? "selected" : ""} onClick={() => setSelected(row.symbol)}>
                  <td>{row.symbol}</td>
                  <td className="muted" style={{ maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={row.name || ""}>{row.name || "-"}</td>
                  <td>{row.as_of ?? "-"}</td>
                  <td className="num">{row.open ?? "-"}</td>
                  <td className="num">{row.high ?? "-"}</td>
                  <td className="num">{row.low ?? "-"}</td>
                  <td className="num">{row.close ?? "-"}</td>
                  <td className="num">{fmtVol(row.volume)}</td>
                  <td className={`num ${row.day_pct.startsWith("+") ? "tag-up" : row.day_pct.startsWith("-") ? "tag-down" : ""}`}>{row.day_pct || "-"}</td>
                  <td className="num" style={{ background: wrCellBg(row.williams_r) }}>{row.williams_r ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
