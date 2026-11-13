# BH-07 PaymentInstructions synthetic heap implementation

> Execute using standing AGENTS Anti implementation / Codex review and runtime workflow. Owner approved continuation after feasibility checkpoint159d896; no new approval needed for scoped local work.

**Goal:** Measure two synthetic non-rendered receiverSnapshot values in a local Web profile heap, with real UI load/cancel and logout/actor transitions.

**Architecture:** New companion tooling preserves old runner/oracles/evidence. UUID-owned private fixture, local-only configuration, bounded streamed CDP dumps outside repository, existing reachability oracle and a new narrow verifier. Presence/path attribution must be established before any cleanup claim.

**Spec:** `docs/reviews/bh07/payment_instructions_heap_feasibility_20261113.md` (including reviewer corrections).

**Global constraints:** No app/schema/remote changes. No payment mutations. No whole-model/listener/native claim, risk acceptance, merge/deploy/pilot/BH-08. Preserve existing artifacts. Anti model gemini-4-hydrogen-high with --print-timeout0. At most3 correction rounds then Codex fixes residuals.

**Ownership:** Anti owns five new tooling/test files and handoff only; Codex owns runtime configuration, evidence/report/status and review. Existing feature branch already isolates work from main.

## Task1: bounded companion tooling

- [ ] Write failing controls for missing/unreachable canary, actor epochs, cleanup/baseline mismatch, raw output leakage, snapshot cap/write error, fixture ownership/collision. Observe RED.
- [ ] Implement new fixture helper with collision preflight, exact ownership readback and cleanup finally; actual charge_revisions/payments/club_transactions schema, current billing source_version.
- [ ] Implement same-document real UI runner, baseline → Owner instructions load/cancel → logout → Cohost → logout → Owner again → logout → Member; snapshot each relevant epoch, enforce stable document identity. Stream outside repo, remove private dumps/profiles on success/failure. Never inject canary into page evaluate or JS globals; only app RPC may load it.
- [ ] Implement verifier requiring both canaries loaded/reachable in each Owner epoch, baseline absent and no strong-root reachability after logout/actor change; unknown/error fails. Require real app retaining-path attribution before a PaymentInstructions-specific conclusion; otherwise report narrow RPC-payload retention only.
- [x] Run controls GREEN and hand off source/interfaces/commands without claiming runtime PASS. Source/control reviewed after2 correction rounds; Codex+reviewer separately19Python/8Node PASS.

## Task2: review and runtime

- [x] Codex/reviewer review source/control failures and corrections, max3 Anti correction rounds. IH1–IH6 closed in reviewed source/control delta afterround2; live runtime pending.
- [ ] Commit reviewed source for clean provenance; verify build/served all artifacts from unchanged app source/config. Smoke first; if measurement invalid, preserve FAIL/UNKNOWN and diagnose without widening claim.
- [ ] Run full two-cycle measurement if smoke establishes preconditions. Capture exact scope, path/baseline evidence, no-payment DB gate, cleanup receipt and fingerprint equality; Auth changes separate.
- [ ] Independent source/artifact review, preserve failed attempts, redact bundle, verify hashes and local links; commit progress/status without full BH-07 acceptance.

## Review focus

Canaries must never be loaded through runner injection/console; full-snapshot serialized response matches are not proof of DTO attribution. Background RPC must not legitimately reload them for alternate actors. Dump stream failures and cap overflow must fail with cleanup. Fixture deletion must never adopt pre-existing rows. Reused served build needs exact artifact provenance and clean source; credentials never in public evidence.

Reviewer plan check: missing app-path attribution cannot become PaymentInstructions coverage PASS; a narrower payload observation leaves that gate UNKNOWN/NOT RUN. Validate unique cycle/actor/document identities and every required epoch; missing/duplicate records fail. Persist attempted fixture IDs/marker before SQL and recover ownership after uncertain create response so finally cleanup still runs.
