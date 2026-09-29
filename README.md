# Group-IB Mobile Threat Intelligence Reporter

Android-first mobile application with a secure FastAPI backend for Group-IB collection, normalization, durable history, deterministic classification, deterministic assessment, and PDF reporting.

## Repository layout

- `backend/` — FastAPI backend and authoritative intelligence pipeline
- `mobile/` — Native Android/Kotlin application
- `docs/` — architecture and permanent development baselines

The backend owns Group-IB credentials and intelligence processing. The Android app never calls Group-IB directly.

## Permanent development baselines

Every implementation cycle must read:

```text
README.md
docs/Architecture.md
docs/MasterInstruction.md
docs/MasterInstructionLoop.md
```

GitHub `main` is the only implementation source of truth.

## Development status

Architecture gates A1-A9 are locked. A10 establishes deterministic Daily Threat Assessment.

## Security

Real `.env`, Group-IB credentials, Android signing keys, generated databases, and build artifacts are ignored by Git.

## Current Architecture Gate

**A10 — Deterministic Daily Threat Assessment — IMPLEMENTED / VALIDATED**

The backend now evaluates classified canonical records using fixed, auditable rules. Assessment output includes Activity Level, Assessment Confidence, Facts, Key Observations, Assessment, Recommended Analyst Attention, and Assessment Basis. No LLM is used for the assessment.

A run intentionally remains `PARTIAL / REPORT_GENERATION_PENDING` until the later PDF/report gate is implemented.

## Validation

```bash
python -m compileall -q app tests
python -m pytest -q
```
