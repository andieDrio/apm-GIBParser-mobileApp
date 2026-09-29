# Master Instruction

GitHub `main` is the only implementation source of truth.

For every development cycle, the mandatory loop is:

1. Read `README.md`.
2. Read `docs/Architecture.md`.
3. Read `docs/MasterInstruction.md`.
4. Read `docs/MasterInstructionLoop.md`.
5. Fetch the current remote `main`.
6. Deep-inspect the actual implementation.
7. Identify the highest-priority unfinished architecture gate.
8. Make the smallest production-grade surgical change.
9. Validate with executable tests.
10. Re-inspect the resulting implementation.
11. Commit directly to `main`.
12. Verify the remote `main` SHA before reporting completion.

Never rely on stale SHAs, screenshots, previous diagnoses, generated archives, or remembered implementation state.

Do not modify `andieDrio/apm-GIBParser`; it is reference-only unless explicitly requested.

Security is mandatory: Group-IB credentials remain backend-only; never commit or log secrets; validate inputs; use safe database operations; avoid secret leakage; and preserve secure mobile credential handling.

Do not fabricate intelligence, telemetry, provider fields, assessment evidence, or successful states. Missing data must remain explicit.

Preserve existing UI/design unless a UI change is explicitly requested. Avoid unrelated cleanup and unnecessary dependencies.
