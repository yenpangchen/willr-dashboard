# WillR · 台股 Williams %R

使用 **Yahoo Finance** 日線資料，計算台灣 50 成分股的 **Williams %R**，並提供：

- CLI：`fetch_williams.py`
- FastAPI：`/api/snapshot`
- React 儀表板：區間篩選 + 表格 + 走勢圖

> 本專案僅供研究，不構成投資建議。

---

## 主要功能（目前版本）

- 只看 **台灣 50**（`tw50_constituents.txt`）
- 儀表板可設定兩個 %R 區間（預設）：
  - `-100 ~ -90`
  - `-10 ~ 0`
- 顯示每檔：代號、名稱、OHLC、成交量、日漲跌、%R
- 點選股票可看最近 N 日「收盤 + %R」線圖

---

## 環境需求

- Python 3.9+
- Node.js 18+

---

## 安裝

```bash
cd willr
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

前端依賴：

```bash
cd dashboard
npm install
```

---

## 本機開發

### 1) 啟動 API

```bash
cd /Users/ypchen/development/willr
PYTHONPATH=. .venv/bin/uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 2) 啟動前端

```bash
cd /Users/ypchen/development/willr/dashboard
npm run dev
```

打開：`http://localhost:5173`

---

## API

### `GET /api/health`
健康檢查。

### `GET /api/snapshot`
回傳台灣 50 快照 + 歷史序列。

Query params:

- `period`：%R 週期（預設 `14`）
- `sort`：`symbol` / `williams_r` / `williams_r_desc`（預設 `symbol`）
- `recent`：每檔回傳最近幾個交易日（預設 `60`）
- `workers`：並行抓價數（預設 `10`）

範例：

```bash
curl -s "http://127.0.0.1:8000/api/snapshot?period=14&sort=symbol&recent=60"
```

---

## CLI

```bash
cd /Users/ypchen/development/willr
.venv/bin/python fetch_williams.py --universe tw50 --period 14 --recent 5
```

---

## 部署（Vercel）

已內建：

- `vercel.json`
- `scripts/vercel-build.sh`（建置前端並複製到 `api/static`）

重點：

- Root directory 用 repo 根目錄
- 部署後：
  - 前端：`/`
  - API：`/api/health`, `/api/snapshot`

---

## 專案結構

```text
willr/
├── api/main.py
├── dashboard/
├── tw50_constituents.txt
├── fetch_williams.py
├── willr_core.py
├── requirements.txt
└── vercel.json
```
