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

Architecture gates A1-A5 are locked. A6 establishes the implementation foundation.


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
