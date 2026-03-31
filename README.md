# WillR · Taiwan 50 Williams %R

WillR provides a TW50 Williams %R dashboard and API.

- Frontend: React dashboard (range filters + table + trend chart)
- Backend: FastAPI (`/api/snapshot`)
- Data source: Yahoo Finance

> For research only. Not investment advice.

## Current Product Scope

- Universe is fixed to **TW50** (`tw50_constituents.txt`)
- Two configurable %R ranges on the dashboard (defaults):
  - `-100 ~ -90`
  - `-10 ~ 0`
- Snapshot includes symbol, name, OHLC, volume, day change, and Williams %R
- Click a row to view recent close + %R trend

## Architecture (Phase A)

This repository is being migrated to a product-style architecture.

- `config/`: settings and environment config
- `db/`: SQLite engine and schema
- `repository/`: data access layer
- `services/`: use-case orchestration
- `jobs/`: ingestion jobs (manual/external worker)
- `api/`: HTTP layer

Phase tracking document: `docs/ARCHITECTURE_PLAN.md`

## Requirements

- Python 3.9+
- Node.js 18+

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

```bash
cd dashboard
npm install
cd ..
```

## Local Development

### Run API

```bash
PYTHONPATH=. .venv/bin/uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### Run frontend

```bash
cd dashboard
npm run dev
```

Open `http://localhost:5173`.

## API

### `GET /api/health`

Health check.

### `GET /api/snapshot`

Returns TW50 snapshot and recent history.

Query params:

- `period` (default `14`)
- `sort` (`symbol` / `williams_r` / `williams_r_desc`)
- `recent` (default `60`)
- `workers` (default `10`)

Example:

```bash
curl -s "http://127.0.0.1:8000/api/snapshot?period=14&sort=symbol&recent=60"
```

## Daily Ingestion Job (Phase A bootstrap)

Run manually to initialize/populate SQLite:

```bash
PYTHONPATH=. .venv/bin/python jobs/daily_ingest.py
```

This writes into `data/willr.db`.

## CLI

```bash
PYTHONPATH=. .venv/bin/python fetch_williams.py --universe tw50 --period 14 --recent 5
```

## Vercel Deploy

Included:

- `vercel.json`
- `scripts/vercel-build.sh` (builds dashboard and copies assets to `api/static`)

Deploy from repo root.

## Project Structure

```text
.
├── api/
├── config/
├── db/
├── repository/
├── services/
├── jobs/
├── dashboard/
├── docs/
├── tw50_constituents.txt
├── fetch_williams.py
├── willr_core.py
├── requirements.txt
└── vercel.json
```
