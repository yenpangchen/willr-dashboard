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

### Phase A (current)

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

### Phase B (next)

- [ ] Move API to DB-only mode.
- [ ] Schedule daily ingestion via external worker.
- [ ] Persist job runs / ingestion metrics.
- [ ] Add `/api/meta` for data freshness and job status.

### Phase C (next)

- [ ] Add Redis cache around snapshot endpoint.
- [ ] Add cache invalidation after ingestion.
- [ ] Add alerting / retries / structured logging.

## Notes

- In Phase A, fallback-to-live avoids service interruption while DB bootstrap is incomplete.
- In production mode later, fallback should be disabled to keep predictable latency/cost.

