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
docs/MasterInstructionLoop.md
```

GitHub `main` is the only implementation source of truth.

## Development status

Architecture gates A1-A13 are closed. A14 is the HONOR X9c device validation gate.

## Security

Real `.env`, Group-IB credentials, Android signing keys, generated databases, and build artifacts are ignored by Git.

## Current Architecture Gate

**A11 — Report / PDF Generation — CLOSED**

**A12 — Report History / Sharing / Saving — CLOSED**

**A13 — End-to-End Validation — CLOSED**

**A14 — HONOR X9c Device Validation — IMPLEMENTED / VALIDATION PENDING DEVICE**

The backend now evaluates classified canonical records using fixed, auditable rules. Assessment output includes Activity Level, Assessment Confidence, Facts, Key Observations, Assessment, Recommended Analyst Attention, and Assessment Basis. No LLM is used for the assessment.

A run now transitions through `GENERATING_REPORT` and reaches `SUCCEEDED` only after the PDF artifact and report metadata are persisted successfully.

## Validation

```bash
python -m compileall -q app tests
python -m pytest -q
```
