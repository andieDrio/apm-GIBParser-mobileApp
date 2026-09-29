# Architecture Baseline

## Project Identity

**Group-IB Mobile Threat Intelligence Reporter**

Purpose:

```text
OPEN APP
  ↓
RUN GROUP-IB COLLECTION
  ↓
NORMALIZE
  ↓
CLASSIFY
  ↓
GENERATE DETERMINISTIC ASSESSMENT
  ↓
GENERATE REPORT
  ↓
VIEW / SHARE / SAVE PDF
```

The product is a focused Android mobile reporting application. It is not a SIEM, SOAR, ThreatForge, generic CTI platform, or multi-tenant platform.

## Locked Stack

- Mobile: Native Android
- Language: Kotlin
- UI: Jetpack Compose
- Backend: FastAPI/Python
- Initial database: SQLite
- PDF generation: ReportLab backend-side
- Transport: HTTPS/TLS
- Group-IB credentials/API access: backend-only
- Android credential protection: Android Keystore-backed mechanisms
- PDF sharing: Android FileProvider/content URI
- PDF save: Storage Access Framework

The existing `andieDrio/apm-GIBParser` repository is reference-only and must not be modified unless explicitly requested.

## Security Boundary

```text
HONOR X9c
   │ HTTPS/TLS
   ▼
GIB Mobile Backend
   │
   │ Group-IB credentials
   ▼
Group-IB TI&A API
```

The Group-IB token must never be embedded in the APK, returned to the mobile client, logged, or written into reports.

## Authoritative Backend Flow

```text
COLLECTING
  ↓
NORMALIZING
  ↓
CLASSIFYING
  ↓
ASSESSING
  ↓
GENERATING_REPORT
  ↓
SUCCEEDED
```

Terminal incomplete states are `FAILED` and `PARTIAL`. A `SUCCEEDED` run is authoritative only when the required downstream artifact for that gate has been persisted successfully.

## A7 — SQLite Persistence & Durable History

Authoritative tables:

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

Database uniqueness is authoritative for logical history and run/report record association.

## A8 — Run API + Orchestration

Endpoints:

```text
POST /api/v1/runs
GET  /api/v1/runs/{run_id}
GET  /api/v1/status
```

Run creation supports `Idempotency-Key`. Group-IB collection has bounded retry behavior and pagination-loop protection. Backend restart reconciles non-terminal runs to `FAILED / SERVER_RESTARTED`.

## A9 — Canonical Normalization

A9 established the canonical Group-IB record contract.

Rules:
- provider record ID is preferred identity;
- deterministic SHA-256 fallback identity is used when necessary;
- dates are UTC-aware;
- missing data remains null/empty;
- invalid optional values become data-quality warnings;
- ordering is deterministic;
- observation fingerprints exclude plaintext password and all credentials/secrets;
- no intelligence is fabricated.

Classification:

```text
Unknown + usable event <= 7 days   -> NEW
Unknown + older/future/missing      -> OLD_HISTORICAL
Known + same fingerprint            -> REPEAT
Known + changed fingerprint        -> RESEEN_RECYCLED
```

## A10 — Deterministic Daily Threat Assessment

A10 establishes the authoritative assessment engine. It is deterministic, auditable, evidence-based, and contains no LLM-generated conclusions.

### Inputs

- canonical records for the current run
- classification for every canonical record
- normalization warning count
- previous baseline availability
- evaluation timestamp

### Activity Level

Activity level is derived only from NEW records:

| NEW records | Affected domains | Activity Level |
|---:|---:|---|
| 0 | any | NONE_OBSERVED |
| 1–2 | 0–1 | LOW |
| 3–5 | 0–3 | MODERATE |
| 6–10 | 0–5 | HIGH |
| above those thresholds | above those thresholds | CRITICAL |

The rules are fixed and executable; no subjective scoring is introduced.

### Assessment Confidence

- **HIGH**: no normalization warnings and a previous baseline is available.
- **MEDIUM**: assessment is usable but baseline is unavailable or warnings exist.
- **LOW**: no records were evaluated or normalization warnings exceed the evaluated record count.

Confidence describes assessment data quality/coverage, not certainty that an organization is compromised or safe.

### Assessment Content

Every assessment persists:

- Assessment ID
- Run ID
- Activity Level
- Assessment Confidence
- Facts
- Key Observations
- Assessment
- Recommended Analyst Attention
- Assessment Basis

The assessment must explicitly distinguish observed Group-IB intelligence from conclusions that cannot be established from absence of data.

If zero NEW records are observed, the assessment must never state or imply that the environment is safe.

### Deterministic Analyst Attention

When NEW records exist, attention includes:
- review affected compromised accounts;
- follow the affected service's credential-reset/session-invalidation procedure;
- correlate endpoint telemetry for observed infostealer families when present;
- correlate victim IPs with available telemetry when present.

When no NEW records exist:
- continue routine monitoring;
- explicitly avoid treating absence of NEW Group-IB records as proof of no compromise.

### A10 Run Behavior

After classification:

```text
CLASSIFYING
   ↓
ASSESSING
   ↓
persist AssessmentModel
   ↓
PARTIAL / REPORT_GENERATION_PENDING
```

The run remains `PARTIAL` until the later PDF/report gate is implemented. A10 therefore does not falsely claim a successful end-to-end report.

## Later Gates

- A11 — Report/PDF generation
- A12 — Report history and mobile sharing/saving
- A13 — End-to-end validation
- A14 — HONOR X9c device validation

## Baseline Rule

This file and `docs/MasterInstructionLoop.md` are permanent project baselines. Every implementation cycle must read them before modifying code. If the current repository contradicts an older assumption, current `main` and these baseline documents are authoritative.
