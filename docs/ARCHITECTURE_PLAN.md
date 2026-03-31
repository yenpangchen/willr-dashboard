# WillR Architecture Plan

This document tracks architecture decisions and implementation progress.

## Product Direction

- Scope: TW50 Williams %R dashboard (no custom watchlist/search in UI).
- Data flow target: ingest once daily, API reads from DB/cache.
- Infra target:
  - DB: SQLite (current phase)
  - Worker: external worker (next phase)
  - Cache: Redis (next phase)

## Phases

### Phase A (done)

- [x] Define architecture folders (`config`, `db`, `repository`, `services`, `jobs`).
- [x] Introduce app settings module.
- [x] Introduce SQLite models and initialization.
- [x] Introduce repository layer for snapshot/history reads and upserts.
- [x] Introduce service layer:
  - read from DB first
  - fallback to live Yahoo compute when DB empty
- [x] Add ingestion job skeleton to populate DB (manual run).
- [x] Keep current API contract for frontend compatibility.
- [x] Rewrite README to remove machine-specific absolute paths.

### Phase B (adjusted)

- [~] Move API to DB-first mode. (Temporary live fallback re-enabled for production stability)
- [x] Schedule daily ingestion via external worker.
- [x] Persist job runs / ingestion metrics.
- [x] Add `/api/meta` for data freshness and job status.

### Phase C (done)

- [x] Add Redis cache around snapshot endpoint.
- [x] Add cache invalidation after ingestion.
- [x] Add alerting / retries / structured logging.

## Notes

- Temporary decision (A-mode): API uses DB first with live fallback when DB empty/unavailable.
- Target steady state: DB-only mode after persistent worker + storage is fully stable.
- External worker execution model: run `jobs/daily_ingest.py` on scheduler (cron/GitHub Actions/VM worker).

