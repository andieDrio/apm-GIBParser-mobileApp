# Architecture

## Locked stack

- Mobile: Native Android, Kotlin, Jetpack Compose
- Backend: FastAPI/Python
- Initial persistence: SQLite
- PDF: ReportLab backend-side
- Transport: HTTPS/TLS
- Group-IB: backend-only

## Processing

Mobile -> FastAPI -> Group-IB -> validate -> normalize -> history/classify -> assess -> PDF -> mobile.

Architecture gates A1-A8 are locked. A6 establishes the implementation foundation.

## A7 — SQLite Persistence & Durable History

The mobile backend persists authoritative execution state in SQLite. The persistence model contains:

```text
runs
reports
compromise_history
provider_records
observations
report_records
assessments
data_quality
```

`runs.idempotency_key` is unique so repeated requests can resolve to the same run. `compromise_history` is unique on `(provider, compromise_identity)`, and `report_records` is unique on `(run_id, provider, compromise_identity)`. These constraints are database-enforced rather than application-only checks.

History upserts preserve earliest provider timeline values, update the latest local observation, and persist the latest classification and observation fingerprint. Observation fingerprints remain separate from plaintext credentials and must be supplied by the canonical normalization/classification layer.

SQLite timestamps are normalized to UTC and returned as timezone-aware values. Generated database files remain outside source control.

## A8 — Run API + Orchestration

The backend exposes:

```text
POST /api/v1/runs
GET  /api/v1/runs/{run_id}
```

`POST /runs` accepts an optional `Idempotency-Key`. The persisted run is created once and repeated requests resolve to the same `run_id`. The executor runs asynchronously in-process while SQLite remains the authoritative run-state store.

The executor enforces the locked lifecycle:

```text
QUEUED
  -> COLLECTING
  -> NORMALIZING
  -> CLASSIFYING
  -> ASSESSING
  -> GENERATING_REPORT
  -> SUCCEEDED
```

Terminal failure states are `FAILED` or `PARTIAL`. A backend restart does not silently resume an interrupted run; non-terminal runs are reconciled to `FAILED` with `SERVER_RESTARTED` so an incomplete execution can never be mistaken for an authoritative result.

A8 implements real Group-IB collection, bounded network retries, pagination-loop protection, persisted record counts, and explicit provider error mapping.

## A9 — Canonical Normalization

A9 introduces the authoritative internal Group-IB canonical record in `app.domain.normalization`. Provider `account_group` items are normalized without inventing values. Provider record ID is preferred for logical identity; otherwise a deterministic SHA-256 fallback identity is derived from stable account/domain/timeline/source/event fields.

Canonical dates are parsed as UTC-aware values. Invalid optional timestamps, URLs, IPs, and event counts are omitted from canonical values and recorded as data-quality warnings. Missing values remain null/empty rather than being inferred. Record ordering is deterministic by latest seen time, first seen time, then identity.

The observation fingerprint is SHA-256 over stable canonical evidence only. It excludes plaintext passwords, provider credentials, authorization headers, cookies, retrieval timestamps, run IDs, and report IDs. Password presence is represented separately so a password change alone does not turn an otherwise identical observation into a recycled event.

Classification persistence uses the locked seven-day policy: unknown identities with a usable compromise/detection timeline inside the window are `NEW`; older, future-dated, or timeline-missing unknown identities are `OLD_HISTORICAL`; known identities with the same fingerprint are `REPEAT`; changed known observations are `RESEEN_RECYCLED`. History, provider records, observations, and run-level canonical records are persisted through the same database transaction.

A9 completes the collection -> normalization -> classification path. The run intentionally terminates as `PARTIAL` with `ASSESSMENT_PENDING` because deterministic assessment and PDF generation belong to later architecture gates.
