import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchSearch, fetchSnapshot, fetchWatchlist, patchWatchlist } from "./api";
import type { HistoryRow, SearchHit, SnapshotResponse, WatchlistEntry } from "./types";

function wrCellBg(wr: number | null): string {
  if (wr == null) return "transparent";
  const t = (wr + 100) / 100;
  const r = Math.round(30 + t * 120);
  const g = Math.round(80 + (1 - t) * 40);
  const b = Math.round(140 + (1 - t) * 40);
  return `rgba(${r}, ${g}, ${b}, 0.35)`;
}

function fmtVol(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1e8) return `${(n / 1e8).toFixed(2)} 億`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)} 萬`;
  return String(n);
}

type Universe = "tw50" | "watchlist";
type SortKey = "symbol" | "williams_r" | "williams_r_desc";

function useDebounced<T>(value: T, delay: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}

export function Dashboard() {
  const [universe, setUniverse] = useState<Universe>("tw50");
  const [period, setPeriod] = useState(14);
  const [sort, setSort] = useState<SortKey>("williams_r");
  const [recent, setRecent] = useState(30);
  const [data, setData] = useState<SnapshotResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const [wlEntries, setWlEntries] = useState<WatchlistEntry[]>([]);
  const [searchQ, setSearchQ] = useState("");
  const debouncedSearch = useDebounced(searchQ.trim(), 400);
  const [searchHits, setSearchHits] = useState<SearchHit[]>([]);
  const [searchBusy, setSearchBusy] = useState(false);
  const [wlFeedback, setWlFeedback] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const p = new URLSearchParams({
        universe,
        period: String(period),
        sort,
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
  }, [universe, period, sort, recent]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void (async () => {
      try {
        const w = await fetchWatchlist();
        setWlEntries(w.entries);
      } catch {
        setWlEntries([]);
      }
    })();
  }, []);

  useEffect(() => {
    if (debouncedSearch.length < 1) {
      setSearchHits([]);
      return;
    }
    let cancelled = false;
    setSearchBusy(true);
    setSearchHits([]);
    void fetchSearch(debouncedSearch, 14)
      .then((r) => {
        if (!cancelled) setSearchHits(r.results);
      })
      .catch(() => {
        if (!cancelled) setSearchHits([]);
      })
      .finally(() => {
        if (!cancelled) setSearchBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedSearch]);

  const applyWatchlistPatch = useCallback(
    async (patch: { add?: string[]; remove?: string[] }) => {
      setWlFeedback(null);
      try {
        const r = await patchWatchlist(patch);
        setWlEntries(r.entries);
        const parts: string[] = [];
        if (r.added?.length) parts.push(`已加入：${r.added.join(", ")}`);
        if (r.removed?.length) parts.push(`已移除：${r.removed.join(", ")}`);
        if (r.skipped?.length)
          parts.push(
            `略過：${r.skipped.map((s) => `${s.symbol}（${s.reason}）`).join("；")}`
          );
        setWlFeedback(parts.length ? parts.join(" · ") : null);
        if (universe === "watchlist") void load();
      } catch (e) {
        setWlFeedback(e instanceof Error ? e.message : String(e));
      }
    },
    [universe, load]
  );

  const barData = useMemo(() => {
    if (!data) return [];
    return [...data.snapshot]
      .filter((r) => r.williams_r != null)
      .sort((a, b) => a.williams_r! - b.williams_r!)
      .map((r) => ({
        symbol: r.symbol.replace(".TW", "").replace(".TWO", ""),
        fullSymbol: r.symbol,
        williams_r: r.williams_r!,
      }));
  }, [data]);

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

  const barHeight = Math.max(320, barData.length * 18);

  const onBarClick = (state: { payload?: { fullSymbol?: string } }) => {
    const sym = state?.payload?.fullSymbol;
    if (sym) setSelected(sym);
  };

  return (
    <div
      style={{
        minHeight: "100%",
        padding: "1.25rem",
        maxWidth: 1400,
        margin: "0 auto",
      }}
    >
      <header
        style={{
          marginBottom: "1.25rem",
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: "1.35rem", fontWeight: 600 }}>
            WillR Dashboard
          </h1>
          <p className="muted" style={{ margin: "0.25rem 0 0" }}>
            台股 Williams %R（Yahoo）· 點列或長條檢視走勢
          </p>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.35rem",
            alignItems: "flex-end",
          }}
        >
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "0.5rem",
              alignItems: "center",
              justifyContent: "flex-end",
            }}
          >
          <label className="muted">
            底下圖表／表格要用哪份名單{" "}
            <select
              value={universe}
              onChange={(e) => setUniverse(e.target.value as Universe)}
            >
              <option value="tw50">台灣 50（固定 50 檔）</option>
              <option value="watchlist">自選股（watchlist.txt）</option>
            </select>
          </label>
          <label className="muted">
            週期{" "}
            <input
              type="number"
              min={2}
              max={120}
              value={period}
              onChange={(e) => setPeriod(Number(e.target.value) || 14)}
            />
          </label>
          <label className="muted">
            排序{" "}
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
            >
              <option value="williams_r">WR 低→高</option>
              <option value="williams_r_desc">WR 高→低</option>
              <option value="symbol">代號</option>
            </select>
          </label>
          <label className="muted">
            歷史天數{" "}
            <input
              type="number"
              min={5}
              max={250}
              value={recent}
              onChange={(e) => setRecent(Number(e.target.value) || 30)}
            />
          </label>
          <button
            type="button"
            className="primary"
            disabled={loading}
            onClick={() => void load()}
          >
            {loading ? "載入中…" : "重新整理"}
          </button>
          </div>
          <p
            className="muted"
            style={{ margin: 0, fontSize: "0.8125rem", textAlign: "right", maxWidth: "28rem" }}
          >
            {universe === "tw50"
              ? "目前下方長條圖、線圖、表格＝「台灣 50」成分。與自選股區塊無直接關聯。"
              : "目前下方長條圖、線圖、表格＝「自選股」檔案內的股票。編輯自選股後可按重新整理。"}
          </p>
        </div>
      </header>

      <section className="panel watchlist-panel">
        <div className="muted" style={{ fontWeight: 500 }}>
          編輯自選股（存成專案根目錄 <code>watchlist.txt</code>）
        </div>
        <p className="muted" style={{ margin: "0.35rem 0 0.5rem", fontSize: "0.8125rem" }}>
          這裡只是在維護你的股票清單。要讓<strong>下面整區圖表與表格</strong>改顯示這些股票，請把上方「底下圖表／表格要用哪份名單」改成<strong>自選股</strong>。
        </p>
        <div className="watchlist-chips">
          {wlEntries.length === 0 ? (
            <span className="muted">尚無項目，請用下方搜尋加入。</span>
          ) : (
            wlEntries.map((e) => (
              <span key={e.yahoo} className="chip">
                {e.yahoo}
                <button
                  type="button"
                  title="移除"
                  onClick={() => void applyWatchlistPatch({ remove: [e.yahoo] })}
                >
                  ×
                </button>
              </span>
            ))
          )}
        </div>
        <div className="search-row" style={{ flexDirection: "column", alignItems: "stretch" }}>
          <input
            type="text"
            placeholder="搜尋：代號（2330）或英文簡稱（例：Mediatek）— 中文名 Yahoo 常無結果"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
          />
          {debouncedSearch.length > 0 && (
            <ul className="search-drop">
              {searchBusy && (
                <li className="muted" style={{ justifyContent: "center" }}>
                  搜尋中…
                </li>
              )}
              {!searchBusy &&
                searchHits.map((h) => (
                  <li key={h.symbol}>
                    <div>
                      <strong>{h.symbol}</strong>
                      {h.name ? (
                        <div className="muted" style={{ fontSize: "0.75rem" }}>
                          {h.name}
                          {h.exchange ? ` · ${h.exchange}` : ""}
                        </div>
                      ) : null}
                    </div>
                    <button
                      type="button"
                      className="mini primary"
                      onClick={() => void applyWatchlistPatch({ add: [h.symbol] })}
                    >
                      加入
                    </button>
                  </li>
                ))}
              {!searchBusy && searchHits.length === 0 && (
                <li className="muted" style={{ justifyContent: "center" }}>
                  無符合的 .TW / .TWO 結果
                </li>
              )}
            </ul>
          )}
        </div>
        {wlFeedback ? <div className="feedback-line">{wlFeedback}</div> : null}
      </section>

      {err && (
        <div
          className="panel"
          style={{
            marginBottom: "1rem",
            borderColor: "var(--negative)",
            color: "var(--negative)",
          }}
        >
          {err}
        </div>
      )}

      <div className="charts-grid">
        <div className="panel" style={{ minHeight: 360 }}>
          <div className="muted" style={{ marginBottom: "0.5rem" }}>
            Williams %R（橫軸 -100…0；長條圖由低至高排列）
          </div>
          {barData.length === 0 ? (
            <div className="muted" style={{ padding: "2rem", textAlign: "center" }}>
              無有效 %R 資料
            </div>
          ) : (
            <div style={{ height: Math.min(barHeight, 520), overflowY: "auto" }}>
              <ResponsiveContainer width="100%" height={barHeight}>
                <BarChart
                  data={barData}
                  layout="vertical"
                  margin={{ left: 4, right: 16, top: 8, bottom: 8 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#30363d"
                    horizontal={false}
                  />
                  <XAxis
                    type="number"
                    domain={[-100, 0]}
                    tick={{ fill: "#8b949e", fontSize: 11 }}
                  />
                  <YAxis
                    type="category"
                    dataKey="symbol"
                    width={44}
                    tick={{ fill: "#8b949e", fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#161b22",
                      border: "1px solid #30363d",
                    }}
                    formatter={(v: number) => [`${v.toFixed(2)}`, "%R"]}
                  />
                  <Bar
                    dataKey="williams_r"
                    radius={[0, 4, 4, 0]}
                    fill="#58a6ff"
                    onClick={onBarClick}
                    cursor="pointer"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div
          className="panel"
          style={{
            minHeight: 360,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div className="muted" style={{ marginBottom: "0.5rem" }}>
            已選 {selected ?? "—"} · 收盤與 %R
          </div>
          <div style={{ flex: 1, minHeight: 300 }}>
            {composedData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={composedData}
                  margin={{ left: 4, right: 8, top: 8, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                  <XAxis dataKey="date" tick={{ fill: "#8b949e", fontSize: 10 }} />
                  <YAxis
                    yAxisId="l"
                    domain={["auto", "auto"]}
                    tick={{ fill: "#8b949e", fontSize: 10 }}
                  />
                  <YAxis
                    yAxisId="r"
                    orientation="right"
                    domain={[-100, 0]}
                    tick={{ fill: "#8b949e", fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#161b22",
                      border: "1px solid #30363d",
                    }}
                  />
                  <Legend />
                  <Line
                    yAxisId="l"
                    type="monotone"
                    dataKey="close"
                    name="收盤"
                    stroke="#f0883e"
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    yAxisId="r"
                    type="monotone"
                    dataKey="williams_r"
                    name="%R"
                    stroke="#58a6ff"
                    dot={false}
                    strokeWidth={2}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div
                className="muted"
                style={{ padding: "2rem", textAlign: "center" }}
              >
                無歷史資料或未選股
              </div>
            )}
          </div>
        </div>
      </div>

      <div
        className="panel"
        style={{ padding: 0, overflow: "hidden", marginTop: "1rem" }}
      >
        <div className="scroll-y" style={{ maxHeight: 480 }}>
          <table className="data-grid">
            <thead>
              <tr>
                <th>代號</th>
                <th>日</th>
                <th className="num">開</th>
                <th className="num">高</th>
                <th className="num">低</th>
                <th className="num">收</th>
                <th className="num">量</th>
                <th className="num">漲跌</th>
                <th className="num">Williams %R</th>
                <th>註</th>
              </tr>
            </thead>
            <tbody>
              {(data?.snapshot ?? []).map((row) => (
                <tr
                  key={row.symbol}
                  className={row.symbol === selected ? "selected" : ""}
                  onClick={() => setSelected(row.symbol)}
                >
                  <td>{row.symbol}</td>
                  <td>{row.as_of ?? "—"}</td>
                  <td className="num">{row.open ?? "—"}</td>
                  <td className="num">{row.high ?? "—"}</td>
                  <td className="num">{row.low ?? "—"}</td>
                  <td className="num">{row.close ?? "—"}</td>
                  <td className="num">{fmtVol(row.volume)}</td>
                  <td
                    className={`num ${
                      row.day_pct.startsWith("+")
                        ? "tag-up"
                        : row.day_pct.startsWith("-")
                          ? "tag-down"
                          : ""
                    }`}
                  >
                    {row.day_pct || "—"}
                  </td>
                  <td
                    className="num"
                    style={{ background: wrCellBg(row.williams_r) }}
                  >
                    {row.williams_r ?? "—"}
                  </td>
                  <td className="muted">{row.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="muted" style={{ marginTop: "1rem", fontSize: "0.75rem" }}>
        資料來源 Yahoo。啟動方式見專案 <code>README.md</code>。
      </p>
    </div>
  );
}
