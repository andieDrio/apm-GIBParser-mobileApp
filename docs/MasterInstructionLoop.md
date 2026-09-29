# Master Instruction Loop

## Permanent Development Contract

This single document is the governing development instruction for the entire project. It incorporates the former Master Instruction and replaces `docs/MasterInstruction.md`.

### Source of Truth

Repository:

```
andieDrio/apm-GIBParser-mobileApp
branch: main
```

GitHub `main` is the only implementation source of truth. The existing `andieDrio/apm-GIBParser` repository is reference-only and must remain untouched unless explicitly requested.

### Mandatory Pre-Execution Reading

Before every development, refactoring, architecture-gate, bug-fix, or validation cycle, read:

```
README.md
docs/Architecture.md
docs/MasterInstructionLoop.md
```

Then fetch the current remote `main` and inspect the actual implementation.

Never rely on stale SHAs, previous chat conclusions, old screenshots, downloaded archives, previous generated code, or assumptions about the current tree.

### Mandatory Development Loop

Always execute:

```
READ BASELINE .MD FILES
        ↓
FETCH CURRENT main
        ↓
DEEP INSPECT ACTUAL CODE
        ↓
IDENTIFY HIGHEST-PRIORITY UNFINISHED GATE
        ↓
ROOT-CAUSE ANALYSIS
        ↓
STATE REQUIRED CHANGE INTERNALLY
        ↓
SURGICAL PRODUCTION-GRADE PATCH
        ↓
VALIDATE WITH EXECUTABLE TESTS
        ↓
RE-INSPECT RESULT
        ↓
COMMIT DIRECTLY TO main
        ↓
VERIFY REMOTE main SHA
        ↓
REPORT EXACT PULL COMMAND
        ↓
NEXT GATE
```

### Change Discipline

- Make the smallest coherent production-grade change.
- Do not rewrite whole files unless required.
- Preserve existing UI/design unless explicitly requested.
- Do not introduce unnecessary dependencies or unrelated cleanup.
- Do not create mock intelligence, fake telemetry, or fabricated Group-IB fields.
- Do not present placeholders as real capabilities.
- Missing data remains explicit/null/empty with data-quality evidence where applicable.
- Preserve contracts unless the current architecture gate explicitly changes them.
- Only one highest-priority gate is advanced at a time unless a dependency requires a coordinated change.

### Security Requirements

Always enforce:
- Group-IB credentials backend-only;
- no secrets in source control;
- no token/header/cookie leakage in logs, API responses, or reports;
- strict input validation;
- parameterized/safe database operations;
- safe, non-sensitive error messages;
- secure Android credential storage;
- server-controlled PDF paths;
- Android PDF sharing through content URIs.

### Validation Requirements

A gate is not validated without executable evidence.

At minimum, when applicable:

```bash
python -m compileall -q app tests
python -m pytest -q
```

For Android gates, also use the appropriate Gradle build/test/device validation available in the repository.

Validation must cover happy path, invalid input, missing data, duplicate/repeat execution, error paths, security-sensitive paths, and deterministic output where required.

### GitHub Commit Discipline

Preferred direct-to-main workflow:

```
current main
   ↓
create blobs
   ↓
create tree from current tree
   ↓
create commit with current main as parent
   ↓
fast-forward refs/heads/main
   ↓
fetch main again
```

Never force-push or rewrite history unless explicitly authorized.

After a successful commit, verify:
- commit SHA;
- parent SHA;
- remote `main`;
- changed files;
- validation evidence.

### Architecture Gate Discipline

Gate closure requires:
1. implementation exists on remote `main`;
2. required tests pass;
3. documentation baseline is updated;
4. remote SHA is verified;
5. no known contradiction remains between implementation and architecture documentation.

Current status:

```
A1   Security Boundary             LOCKED
A2   Backend API Contract          LOCKED
A3   Domain & Data Model           LOCKED
A4   Group-IB Adapter              LOCKED
A5   Run Orchestration             LOCKED
A6   Implementation Foundation     DONE
A7   SQLite Persistence             DONE
A8   Run API + Orchestration        DONE
A9   Canonical Normalization        DONE
A10  Deterministic Assessment       DONE
A11  Report / PDF Generation        CLOSED
A12  Report History / Sharing       CLOSED
A13  End-to-End Validation           CLOSED
A14  HONOR X9c Device Validation     PENDING
```

### A13 — End-to-End Validation

A13 validates the authoritative backend chain from Group-IB provider acquisition through normalization, classification, assessment, PDF generation, durable report persistence, report retrieval, and PDF download. External Group-IB calls are replaced by deterministic provider-boundary fixtures in automated tests; no live provider credentials or intelligence are required for the end-to-end test suite.

Coverage includes successful authoritative completion, repeat classification, provider authentication failure, and invalid provider response handling.

### A13 Validation Result

A13 executable local validation is complete:

```text
36 passed, 1 warning
```

The warning is the existing Starlette deprecation notice from FastAPI's TestClient dependency path; it did not affect test success. A13 is therefore closed with deterministic provider-boundary end-to-end coverage and no live Group-IB credentials required.

### Evidence and Reporting

Every development response must state:
- gate addressed;
- actual changes;
- executable validation performed;
- commit SHA;
- current remote `main` SHA;
- next highest-priority gate.

Do not claim work was pushed unless remote `main` was actually verified.

### Continuity

If a chat ends or a new chat begins, resume from the verified remote `main` state, then reread this document and `docs/Architecture.md` before continuing.

The current repository is always more authoritative than remembered conversation state.
