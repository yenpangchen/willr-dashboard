# WillR · 台股 Williams %R

從 **Yahoo Finance** 拉取台股日線，計算 **Williams %R（威廉指標）**，並提供：

- 命令列工具 `fetch_williams.py`
- **FastAPI** 後端（給網頁與跨域情境使用）
- **React** 儀表板（表格 + 圖表）

> 報價與 K 線來源為 Yahoo，正確性與延遲請自行斟酌。本專案不提供投資建議。

**版控**：請勿提交 `.env`、憑證或 API 金鑰；可自行複製 [`.env.example`](./.env.example) 為 `.env` 並只在本機使用。`.gitignore` 已排除常見敏感檔與 `node_modules`、`.venv`、`dashboard/dist`。

---

## 環境需求

- Python **3.9+**（建議專用虛擬環境）
- **Node.js 18+**（僅在你要跑 React 儀表板時需要）

---

## 快速開始（Python）

### 1. 建立虛擬環境並安裝依賴

```bash
cd willr
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. 命令列：自訂清單（`watchlist.txt`）

```bash
.venv/bin/python fetch_williams.py --universe watchlist
```

`watchlist.txt` 一行一檔；可只寫數字（會自動加 `.TW`），上櫃請寫完整代號（例如 `6488.TWO`）。

### 3. 命令列：台灣 50 成分（`tw50_constituents.txt`）

```bash
.venv/bin/python fetch_williams.py --universe tw50 --sort williams_r --recent 5
```

- `--period 14`：威廉迴天數（預設 14）
- `--sort`：`symbol` | `williams_r` | `williams_r_desc`
- `--recent N`：多印每檔最近 N 個交易日的 OHLCV + %R

成分代號檔需隨 **FTSE／TWSE 公告** 手動更新；詳見檔案內註解。

---

## 後端 API（FastAPI）

在**專案根目錄**執行（務必設定 `PYTHONPATH`，讓 `willr_core` 可被匯入）：

```bash
cd willr
PYTHONPATH=. .venv/bin/uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/health` | 健康檢查 |
| GET | `/api/snapshot` | 快照 JSON（表格 + 可選歷史序列） |
| GET | `/api/search?q=…` | Yahoo 搜尋，僅回傳 `.TW` / `.TWO`（代號可直接試 `.TW` / `.TWO`） |
| GET | `/api/watchlist` | 讀取 `watchlist.txt` 項目 |
| POST | `/api/watchlist` | JSON `{ "add": ["2454.TW"], "remove": ["2330"] }` 更新檔案 |

### `/api/snapshot` 查詢參數

| 參數 | 預設 | 說明 |
|------|------|------|
| `universe` | `tw50` | `tw50` 或 `watchlist` |
| `period` | `14` | 威廉 %R 天數（2～120） |
| `sort` | `symbol` | `symbol` / `williams_r` / `williams_r_desc` |
| `recent` | `30` | 每檔附帶最近幾個**交易日**的歷史（0～250，供圖表用） |
| `workers` | `10` | 並行請求 Yahoo 的執行緒數（1～32） |

範例：

```bash
curl -s "http://127.0.0.1:8000/api/snapshot?universe=tw50&period=14&sort=williams_r&recent=30"
```

---

## React 儀表板

### 1. 安裝前端依賴

```bash
cd willr/dashboard
npm install
```

### 2. 啟動開發伺服器

**請先**在另一終端機啟動 API（`http://127.0.0.1:8000`），再執行：

```bash
npm run dev
```

瀏覽器開 **http://localhost:5173**。開發模式下 Vite 會把 `/api` **proxy** 到 `127.0.0.1:8000`。

### 3. 正式打包

```bash
npm run build
```

輸出在 `dashboard/dist/`（可刪除後再建，已列於 `.gitignore`）。若靜態網站與 API 不同網域，需自行設定 CORS 或改 API 基底網址。

### 儀表板可做什麼

- 切換 **台灣 50** / **watchlist**
- **自選股**：搜尋（代號或英文簡稱）後加入／自 chips 移除，會寫入專案根目錄 `watchlist.txt`
- 調整週期、排序、歷史天數並 **重新整理**
- **橫條圖**：各股 %R；點長條可選股
- **線圖**：選中股票的收盤與 %R
- **表格**：熱力底色、列點選選股

> Yahoo 搜尋對**中文公司名**經常無結果，建議用**股票代號**或**英文**關鍵字。

---

## 專案結構（重點）

```
willr/
├── willr_core.py           # 共用資料邏輯（Yahoo + %R + JSON）
├── fetch_williams.py       # CLI
├── watchlist.txt
├── tw50_constituents.txt   # 台灣 50 代號（手動維護）
├── api/main.py             # FastAPI
├── dashboard/              # Vite + React
└── requirements.txt
```

---

## 部署（同一台機器：一個網址）

最簡單：**FastAPI 同時提供 `/api` 與打包後的靜態網頁**，瀏覽器只連一個 port 即可（無需 Vite dev、也無需另開靜態伺服器）。

### 1. 建置前端

```bash
cd willr/dashboard
npm ci   # 或 npm install
npm run build
```

完成後會出現目錄 `willr/dashboard/dist/`。

### 2. 啟動服務（專案根目錄）

```bash
cd willr
PYTHONPATH=. .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
```

- 本機或同一區網：**http://你的 IP:8000**  
- API 仍為 **`http://…:8000/api/...`**；OpenAPI 文件：**http://…:8000/docs**

若 `dashboard/dist` 不存在，程式只會提供 API（與以前一樣）。

### 3. 環境變數（選用）

| 變數 | 說明 |
|------|------|
| `WILLR_STATIC_DIR` | 靜態檔目錄，預設為專案內 `dashboard/dist` |
| `WILLR_CORS_ORIGINS` | 逗號分隔的來源網址；**前端與 API 不同網域**時必設，例如 `https://app.example.com,https://www.example.com` |

### 4. 前端與 API 不同網域（進階）

1. 後端照樣跑，並設定 `WILLR_CORS_ORIGINS` 為**前端網址**。  
2. 建置前端時指定 API 根網址（**不要**結尾斜線）：

```bash
cd willr/dashboard
VITE_API_BASE=https://api.example.com npm run build
```

此時瀏覽器會對 `https://api.example.com/api/...` 發請求，靜態檔可放在任意 CDN／主機。

> 伺服器需能連外取得 **Yahoo** 報價；`watchlist.txt`、路徑請確認行程有**寫入權限**。

---

## 常見問題

**為什麼一定要有後端，不能瀏覽器直接打 Yahoo？**  
瀏覽器會碰到 **CORS** 與來源限制，且把大量請求放在前端也不穩定，故由 Python 集中抓取。

**Yahoo 上 0050 的持股清單不完整怎麼辦？**  
完整 50 檔以 `tw50_constituents.txt` 為準；ETF 在 Yahoo 上常只顯示前幾大持股。

**終端機出現 `urllib3` / OpenSSL 警告？**  
多半仍可正常抓資料；若異常再考慮升級 Python 或環境。

---

## 授權與免責

程式碼依你本機專案用途使用即可。市場資料與指標解讀請自行負責，本專案不構成投資或稅務建議。
