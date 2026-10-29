# BH-07 bank/receiver Web-profile coverage

User delegation: Antigravity implements, Codex independently reviews; ask the user only when the task is ready for integration/merge main. Antigravity must use Gemini 3.8 Flash (High), explicitly selected on every CLI call; never substitute a model.

## Goal and boundaries

Measure bank-account identifiers and rendered account/receiver strings loaded through the real club UI in two same-document Owner→logout→Cohost/Member Web-profile cycles. Reuse the current heap tooling; do not change lib/, test/, Supabase schema/migrations/RPC, permissions or production. Ledger/QR instructions, exhaustive object graphs, native VM and all other NOT RUN gates remain outside this task.

## Approach selected by Codex under the user's delegation

- Extend the existing runner with an opt-in `--bank-coverage` profile and a separate fresh bank evidence directory. Preserve the default runner and all old bundles byte-for-byte.
- Both account number and receiver name are rendered by the bank tab/dialog. Declare them `rendered: true`; post-logout retention is an unattributed residual risk, never evidence that app/model/native memory is clean.
- Add `bank_account_id`: the real BankAccount.id, unrendered/distinctive Owner-private financial data. It must load at Owner, be absent at baseline, and have no reachable occurrences after logout/actor switch. Existing expense/payment gates remain enforced.
- Publish an explicit versioned bank coverage contract. Its required Owner-load group is bank_account_id + bank + receiver. Missing load/baseline discrimination, missing metadata, a forged class, or dropping a required key must fail closed; the auditor must independently enforce it. Rendered values are load controls, not post-logout absence gates.
- Use only a disposable local-only club and its disposable bank account (plus any strictly necessary owned membership), owned by the existing synthetic Owner. There is a unique active bank account per club: never insert a second active account into CLUB_A, archive/update its account, or restore by overwriting it later.
- Preflight collisions on every prospective owned ID; ambiguous POST outcomes must be reconciled without claiming pre-existing rows. Delete only rows this run created, in child-first order; verify absence and publish redacted ownership/cleanup receipts matched to sentinel hashes. Preserve pre-existing fixture rows.
- Account-number fixtures must be valid digit strings, sufficiently long to avoid UUID-substring coincidence. Never use hex account numbers or publish private fixture strings/credentials.

Alternatives rejected: changing existing CLUB_A bank state risks pre-existing fixtures; treating displayed numbers as unrendered creates false leak verdicts; changing app/backend expands scope and invalidates the retained baseline.

## Acceptance

Antigravity code + meaningful positive/adversarial tests; Codex fresh suites, fixture controls, generic/legacy auditors and profile-specific contract/cleanup mutants. If local runtime prerequisites are available, fresh profile build and 8 snapshots with loaded Owner controls and verified fixture cleanup. A runtime leak/missing precondition is FAIL, not a reason to weaken gates or modify app. Runtime unavailable must remain explicitly NOT RUN, never pass the runtime portion.

No self-acceptance by implementer. User exception on 2026-10-29 expands this bank/receiver task to at most three correction rounds in total; currently round 2/3, without resetting the count. Unresolved findings after round 3 then stop and report. This exception does not change the repository-wide two-round default for other tasks. No push, merge/deploy/pilot/BH-08 or next task before user integration approval. Local feature-branch checkpoints may preserve clean source provenance; they do not authorize integration.
