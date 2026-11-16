# Hosted staging hardening — 2026-11-12

Owner confirmed running `lean-ctx allow npx.cmd`. Supabase CLI3.1.0 was fetched into npm cache, help inspected, and `migration new bh07_role_helper_hardening` generated [the canonical migration](../../../supabase/migrations/20261112151424_bh07_role_helper_hardening.sql). Its22executable statements match the reviewed candidate; only the first comment differs. LF SHA256 `bcc8ef85cccc9dbd480cb9ee8c1fd831eef7d6e042b187e074fe93887a133819`. [Independent packaging review](staging_hardening_canonical_review_20261112.md).

Applied successfully using the hosted migration tool only to approved test project `mxqpukhfiugdwsjsbihj`; source checkpoint57a2308 plus this canonical-file delta. Hosted history now19entries; new tool-generated version `20261112151606`, name `20261112151424_bh07_role_helper_hardening`. Original source versions remain in names. This does not reconcile historical CLI migration versions; do not blindly use CLI db push.

[Receipts](staging_hardening_hosted_receipts_20261112.json) contain before/after metadata and results. Codex verified:

- All10helpers: anon EXECUTE false, authenticated EXECUTE true.
- Both legacy trigger functions: search_path fixed to public,pg_temp.
- All12function-body hashes and3view-definition hashes unchanged.
- Still21public tables/21RLS; zero Auth users/sessions/payments. No fixtures provisioned.
- Actual [HTTP probe](staging_hardening_hosted_probe_20261112.js):15/15controls PASS. All10helpers return401/42501 anonymously; public summary,venues and public-list RPC return200/empty arrays; outstanding view and bank getter deny401/42501. This is empty-project access verification, not populated-row isolation or authenticated GoTrue/JWT testing. The probe reads a publishable key from ignored `.build/bh07-staging-public-key.local.json`; no key or response data is retained in evidence.

Security advisor no longer reports mutable search paths; anon-callable definer count falls19→9. Remaining notices require their own assessment: [two definer views](https://supabase.com/docs/guides/database/database-linter?lint=0010_security_definer_view), [nine anon-callable functions](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable), [62authenticated-callable functions](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable). Intentional public RPCs, trigger-only functions and actor guards must be distinguished from access defects; no blanket security clearance is claimed. Health advisor has no notices.

The [independent post-apply review](staging_hardening_hosted_review_20261112.md) confirms this target's anonymous-helper denials and pinned paths: reviewer separately ran15HTTP controls and catalog SQL, with no new scoped P1/P2. Reviewer did not independently remeasure every body/view hash, count or advisor result. Authenticated arbitrary-UUID helper probing, remaining advisor triage, actual test-user provisioning/Auth, managed backup/PITR/retention, staging release/restore, workload/SLO/load and native/whole-model gaps remain open. No paid add-on, old-project mutation, application deploy, restore, load, pilot, risk acceptance or BH-08 performed. Full BH-07/V8 remains unaccepted.
