# Group-IB Mobile Threat Intelligence Reporter

Android-first mobile application with a secure FastAPI backend for Group-IB collection, normalization, durable history, deterministic classification, assessment, and PDF reporting.

## Repository layout

- `backend/` — FastAPI backend and authoritative intelligence pipeline
- `mobile/` — Native Android/Kotlin application
- `docs/` — architecture and API specifications

The backend owns Group-IB credentials and intelligence processing. The Android app never calls Group-IB directly.

## Development status

Architecture gates A1-A5 are locked. A6 establishes the backend implementation foundation.

## Security

Real `.env`, Group-IB credentials, Android signing keys, generated databases, and build artifacts are ignored by Git.


## Current Architecture Gate

**A7 — SQLite Persistence & Durable History — IMPLEMENTED / VALIDATED**

The backend now defines durable SQLite persistence for runs, reports, compromise history, provider records, observations, report records, assessments, and data quality. Database uniqueness protects provider/identity history and run-level report-record associations, while idempotency keys resolve repeated run requests to the same persisted run. UTC timestamps are normalized through a SQLite-safe SQLAlchemy type.

Validation:

```text
python -m compileall -q app tests
python -m pytest -q
10 passed
```

