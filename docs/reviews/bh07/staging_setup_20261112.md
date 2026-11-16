# Free staging setup — 2026-11-12

Owner explicitly selected `phongnt911's Org` and approved creation at **0 USD/month**, test data only, without paid PITR/add-ons.

**Current after hardening:**19hosted migrations. [Canonical hardening and hosted checks](staging_hardening_hosted_runtime_20261112.md):10helpers now deny anon, both legacy paths pinned,15anonymous HTTP controls PASS. Remaining advisor/Auth/operational gates are not closed. Initial18-migration setup and the former CLI blocker below are historical.

[Sanitized setup receipts and migration mapping](staging_setup_receipts_20261112.json), [security triage and anonymous HTTP baseline](staging_security_triage_20261112.md), [independent documentation review](staging_setup_review_20261112.md). Documentation review does not close security findings.

- Organization: `ddttmuoowqhiuayjlfnw`.
- Project: `badminton-hub-staging`, ref `mxqpukhfiugdwsjsbihj`.
- Region: Singapore (`ap-southeast-1`); observed status ACTIVE_HEALTHY.
- API: https://mxqpukhfiugdwsjsbihj.supabase.co
- Existing inactive project `vqelcjxljddxoyplgcvm` untouched.
- Canonical source: feature branch at `c960c2d968f913a9075f65852ba7e0c36ed49180`.

Applied all 18 repository migrations, from `20261015051808_init_schema_v1_1` through `20261020180000_bh07_reads`, using the hosted migration tool. The tool generates execution-time migration versions; original source versions remain in migration names. Do not blindly run CLI db push against this history without reconciling the version mapping.

One third-migration attempt failed on an execution-time version collision with the second migration. History and function-definition inspection confirmed it had not applied; retry and subsequent spaced calls succeeded. Final history contains 18 entries.

Postmigration SQL: 21 public tables, all RLS enabled, all empty; zero Auth users. `confirm_payment`, `get_session_summary`, and `record_cash_payment` deny anon EXECUTE and permit authenticated EXECUTE. This checks grants, not complete authorization semantics.

Health advisor: no notices. Security advisor requires triage before fixture provisioning:

Direct grant inspection: both views have `security_barrier=true`, without `security_invoker=true`. `public_session_summary` permits anon/authenticated SELECT; `player_outstanding` denies anon SELECT but permits authenticated SELECT. A security barrier alone does not establish caller-based RLS. Predicate/column semantics remain under review.

- Two SECURITY DEFINER views: `public_session_summary`, `player_outstanding`. [Remediation](https://supabase.com/docs/guides/database/database-linter?lint=0010_security_definer_view).
- Two mutable function search paths: legacy session/session-player column sync triggers. [Remediation](https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable).
- 19 anon-callable and 62 authenticated-callable SECURITY DEFINER functions. These are advisor findings, not proof of exploitable access; public RPCs, authorization helpers, and trigger functions require individual review. [Anon remediation](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable), [authenticated remediation](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable).

No real users/data, paid features, application deployment, restore, load, or pilot performed. Project creation and schema setup do **not** close V3/V5/V7 or BH-07/V8. Managed PITR is not enabled; bank sandbox remains outside the existing manual-payment scope.

## Reviewed local candidate; hosted application pending (historical)

Anti CLI completed the helper-grant/search-path candidate after two correction rounds. [Independent delta review](staging_hardening_review_final_20261112.md) closes candidate P2 findings;6static tests PASS. [Codex local SQL runtime](staging_hardening_local_runtime_20261112.md):42focused checks +21existing DB cases PASS, owned-container cleanup verified. This is PostgreSQL/auth.uid-stub verification, not hosted Auth or independent runtime QA.

Hosted schema remains at18migrations with the original grants. The canonical migration-new step is blocked by the environment's permanent `npx.cmd` shell allowlist denial. Owner was asked to run `lean-ctx allow npx.cmd`; no retry through another launcher or policy bypass was used. Until that command is permitted and a canonical migration is created/reviewed/applied, anonymous-helper exposure remains open on staging. No fixture provisioning yet.

Owner subsequently confirmed the allowlist command was run. CLI3.1.0 generated the canonical migration, independent packaging review passed, and the migration was applied/verified on the same approved staging. See the current hosted report above; no paid features or real data were introduced.
