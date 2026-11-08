# Ledger test design — RED checkpoint, not accepted implementation

2026-11-08. These are Antigravity-authored **draft tests for a new ledger coverage profile**. No ledger helper, profile contract enforcement or ledger runtime has been implemented or accepted. They are stored with review material rather than activated in `tests/` while the required Supabase skill remains inaccessible through lean-ctx. Their expected failures are not part of, or counted as passing in, the accepted 375-test baseline.

Codex moved the files from `tests/` to this directory and adjusted only their project-root lookup from `parents[1]` to `parents[4]`; assertions were preserved. To resume implementation, move them back to `tests/`, restore `parents[1]`, and rerun the RED checkpoint before code changes.

## Last actual result before packaging

`python -m unittest tests.test_bh07_ledger_heap_coverage tests.test_bh07_ledger_fixture -v`: **21 tests, 9 failures, exit 1**, archive `3e5fcc74eadad534`.

- Positive ledger clone and unchanged historical finance clone exit 0 through the real auditor CLI.
- Three required new ledger controls remain RED: missing versioned contract, unverified cleanup, and incorrect receipt hash are not yet rejected. This is missing enforcement for the proposed profile, not evidence that a legacy bank/finance contract regressed.
- Six fixture tests remain RED because `scripts/bh07_appheap/disposable_ledger_fixture.js` does not exist.
- Other tests passed in that run. This is a test-design checkpoint, not a verdict for live ledger retention.

The final narrow Anti correction call timed out (conversation `bf17642e-d46b-41d5-8730-2b86ea1d88c2`, archive `d1bbdd0c1b6b3cbd`). Codex inspected the files actually saved and ran the command above; CLI success was not assumed. Earlier test drafts had invalid assumptions; those failed iterations remain recorded in archives `177eba19a4f3088c` and `36d7ad78f8669240`.

## Resume constraints

- Read the Supabase skill after the owner opens its directory in lean-ctx; do not bypass the path restriction or execute live fixtures before this.
- Reuse the existing bank fixture's owned disposable club; child ledger cleanup must precede parent cleanup. Never adopt/delete a pre-existing row.
- Keep default/generic oracle behavior intact; opt-in ledger metadata must bind owner presence/reachability, baseline absence and post-logout/actor absence to mandatory contract enforcement.
- Test the actual verifier CLI with a valid positive bundle and ledger-specific mutants, preserve historical bundle bytes and strict boolean/hash receipts.
- The 403 fake transport still needs a matching row appearing after rejection to prove no foreign-row adoption; a 403 with no row is insufficient for that claim. Add post-actor retention, invalid class/contract-version, missing/string cleanup and root-reachability controls during implementation review as needed.
- Exercise `THU QUỸ` → `Huỷ` → actual ledger title/list, not merely the overview balance header. UUID use in widget Key/RPC is not rendered text.
- PaymentInstructions has no exclusive ID; do not invent one or use shared revision/roster IDs as proof of whole-object release.
- No app/backend/schema change, merge, push, deployment or pilot is authorized by this checkpoint.

After the root adjustment, the draft files can be inspected or run individually with `python docs/reviews/bh07/ledger_tdd_draft/test_bh07_ledger_heap_coverage.py` and `python docs/reviews/bh07/ledger_tdd_draft/test_bh07_ledger_fixture.py`; the expected RED behavior must remain explicit.

Packaging checks: the two real-CLI positive controls pass from this location (archive `439af6685f19e8f4`); a fresh standard active-suite replay after relocation remains **375 PASS**, exit 0 (archive `514dee4c37f4f232`). Neither result accepts the ledger draft or its nine failures. A separate reviewer checked the root lookup, discovery boundary and scope wording. [Checkpoint metadata](checkpoint.json).
