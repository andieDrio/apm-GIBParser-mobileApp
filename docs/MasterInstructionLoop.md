# Master Instruction Loop

## Permanent Development Contract

This document is a mandatory baseline for every development, refactoring, architecture-gate, bug-fix, and validation cycle.

### 1. Source of Truth

GitHub repository:

```text
andieDrio/apm-GIBParser-mobileApp
branch: main
```

`main` is the only implementation source of truth.

The existing `andieDrio/apm-GIBParser` repository is reference-only and must remain untouched unless the user explicitly requests otherwise.

### 2. Mandatory Pre-Execution Reading

Before every execution of project changes, read:

```text
README.md
docs/Architecture.md
docs/MasterInstruction.md
docs/MasterInstructionLoop.md
```

Then inspect the actual current implementation on `main`.

Never rely on:
- stale SHAs;
- previous chat conclusions;
- old screenshots;
- downloaded archives;
- previous generated code;
- assumptions about the current tree.

### 3. Development Loop

Always execute:

```text
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
STATE THE REQUIRED CHANGE INTERNALLY
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

### 4. Change Discipline

- Make the smallest coherent production-grade change.
- Do not rewrite whole files unless required.
- Preserve existing UI/design unless explicitly requested.
- Do not introduce unnecessary dependencies.
- Do not perform unrelated cleanup.
- Do not create mock intelligence or fake telemetry.
- Do not present placeholders as real capabilities.
- Do not fabricate Group-IB fields.
- Prefer null/empty plus data-quality evidence over invented values.
- Preserve backward-compatible contracts unless the architecture gate explicitly changes them.

### 5. Security Requirements

Always enforce:
- backend-only Group-IB credentials;
- no secrets in source control;
- no token/header/cookie leakage;
- strict input validation;
- parameterized database operations;
- safe error messages;
- authorization boundaries where applicable;
- no plaintext secret logging;
- secure Android credential storage;
- safe PDF sharing through content URIs.

### 6. Validation Requirements

Do not claim a gate is validated without executable evidence.

At minimum, when applicable:

```bash
python -m compileall -q app tests
python -m pytest -q
```

For Android gates, also use the appropriate Gradle build/test/device validation available in the repository.

Validation must cover:
- happy path;
- invalid input;
- missing data;
- duplicate/repeat execution;
- error paths;
- security-sensitive paths;
- deterministic output where required.

### 7. GitHub Commit Discipline

Preferred workflow:

```text
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

### 8. Architecture Gate Discipline

Only one highest-priority gate should be advanced at a time unless a dependency requires a coordinated change.

Current gate:

```text
A10 — Deterministic Daily Threat Assessment
```

After A10 is closed, the next gate is A11.

A gate is closed only when:
1. implementation exists on remote `main`;
2. required tests pass;
3. documentation baseline is updated;
4. remote SHA is verified;
5. no known contradiction remains between implementation and architecture documentation.

### 9. Evidence and Reporting

Every development response must state:
- gate addressed;
- actual changes;
- validation performed;
- commit SHA;
- current remote main SHA;
- next highest-priority gate.

Do not claim work was pushed unless remote `main` was actually verified.

### 10. Continuity Rule

If a chat ends or a new chat begins, resume from the verified remote `main` state, then reread all baseline Markdown documents before continuing.

The current repository is always more authoritative than remembered conversation state.
