# Architecture Baseline

## Project Identity

**Group-IB Mobile Threat Intelligence Reporter**

Purpose:

```
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

```
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

```
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

```
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

```
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

```
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

If zero NEW records are observed, the assessment must never state or imply that the environment is safe.

## A11 — Report / PDF Generation

A11 makes the PDF artifact part of the authoritative run lifecycle.

### Generation Contract

After assessment:

```
ASSESSING
   ↓
GENERATING_REPORT
   ↓
render ReportLab PDF to temporary file
   ↓
atomically persist final PDF
   ↓
persist ReportModel metadata
   ↓
SUCCEEDED
```

A PDF is never reported as successful before the final artifact exists.

### PDF Contents

Page 1:
- report title and report date
- Quick View
- Activity Level
- Assessment Confidence
- records retrieved
- NEW compromises
- affected domains
- infostealer families
- seven-day NEW compromise trend
- operational note

Page 2+:
- Executive Summary
- Daily Threat Assessment
- Facts
- Key Observations
- Recommended Analyst Attention
- Assessment Basis
- NEW Compromised Accounts
- OLD / HISTORICAL records
- Collection / Data Quality
- Run Metadata

Account table includes:
- Compromised Date
- Date Detected
- First Seen
- Last Seen
- Victim's Domain
- Victim's Login
- Password
- Victim IP
- Source
- Malware
- Threat Actor
- Source Link as the final dedicated column

Operational passwords may be included because this is an explicitly requested reporting field. Provider credentials, authorization headers, session cookies, and application secrets must never be included.

Every page footer:
```
Page X                         Prepared by: APM
```

### PDF Failure Rules

- missing assessment → report generation fails safely;
- ReportLab/rendering error → no successful run;
- temporary artifacts are removed on failure;
- no incomplete PDF is presented as authoritative;
- report path is generated from a server-controlled report UUID, not user input.

### A11 Validation

Required tests cover:
- valid PDF generation;
- PDF artifact persistence;
- operational password presence;
- missing-assessment failure;
- deterministic report sections and data source mapping.

## A12 — Report History / Sharing / Saving

A12 establishes the backend report-history and PDF-delivery contract consumed by the mobile application.

### Report APIs

```text
GET /api/v1/reports/latest
GET /api/v1/reports/history?limit=&offset=
GET /api/v1/reports/{report_id}
GET /api/v1/reports/{report_id}/download
```

Only `SUCCEEDED` reports are exposed as authoritative report history. History is ordered newest-first and returns run/report metadata plus NEW compromise count and PDF availability. PDF download is served only from a server-controlled report root and uses a server-generated report UUID filename; user input is never used as a filesystem path.

Missing reports and missing artifacts return structured errors without exposing internal filesystem details.

## Later Gates

- A13 — End-to-end validation
- A14 — HONOR X9c device validation

## Baseline Rule

This file and `docs/MasterInstructionLoop.md` are permanent project baselines. Every implementation cycle must read them before modifying code. If the current repository contradicts an older assumption, current `main` and these baseline documents are authoritative.
