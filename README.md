# Group-IB Mobile Threat Intelligence Reporter

Android-first mobile application with a secure FastAPI backend for Group-IB collection, normalization, durable history, deterministic classification, assessment, and PDF reporting.

## Repository layout

- `backend/` — FastAPI backend and authoritative intelligence pipeline
- `mobile/` — Native Android/Kotlin application
- `docs/` — architecture and API specifications

The backend owns Group-IB credentials and intelligence processing. The Android app never calls Group-IB directly.

## Development status

Architecture gates A1-A7 are locked. A8 establishes the executable run API and orchestration control plane.

## Security

Real `.env`, Group-IB credentials, Android signing keys, generated databases, and build artifacts are ignored by Git.

## Current Architecture Gate

**A8 — Run API + Orchestration — IMPLEMENTED / VALIDATED**

The backend exposes `POST /api/v1/runs` and `GET /api/v1/runs/{run_id}` with durable SQLite run state, idempotency handling, bounded Group-IB collection retries, pagination-loop protection, and explicit terminal failure/partial semantics. Canonical normalization remains a separate gate and is never fabricated as a successful stage.

## Validation

```text
python -m compileall -q app tests
python -m pytest -q
```
