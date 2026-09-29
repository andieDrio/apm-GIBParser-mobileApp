# Group-IB Mobile Threat Intelligence Reporter

Android-first mobile application with a secure FastAPI backend for Group-IB collection, normalization, durable history, deterministic classification, assessment, and PDF reporting.

## Repository layout

- `backend/` — FastAPI backend and authoritative intelligence pipeline
- `mobile/` — Native Android/Kotlin application
- `docs/` — architecture and API specifications

The backend owns Group-IB credentials and intelligence processing. The Android app never calls Group-IB directly.

## Development status

Architecture gates A1-A8 are locked. A9 establishes canonical Group-IB normalization and durable classification input.

## Security

Real `.env`, Group-IB credentials, Android signing keys, generated databases, and build artifacts are ignored by Git.

## Current Architecture Gate

**A9 — Canonical Normalization — IMPLEMENTED / VALIDATED**

The backend exposes `POST /api/v1/runs` and `GET /api/v1/runs/{run_id}` with durable SQLite run state, idempotency handling, bounded Group-IB collection retries, pagination-loop protection, canonical normalization, deterministic seven-day classification input, and explicit terminal failure/partial semantics. Assessment and PDF generation remain later gates.

## Validation

```text
python -m compileall -q app tests
python -m pytest -q
```
