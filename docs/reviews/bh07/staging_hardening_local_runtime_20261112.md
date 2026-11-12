# Local PostgreSQL verification of staging candidate — 2026-11-12

**Codex execution: PASS within local SQL scope**, not independent runtime QA, hosted migration, or BH-07 acceptance. Candidate remains outside canonical migrations pending the blocked CLI migration-new step. Source baseline d1361d8 plus uncommitted Anti candidate and verification artifacts.

[Executable probe](staging_hardening_local_probe_20261112.py) imports the existing BH-07 DB suite and creates a UUID-named PostgreSQL17 container with `--network none`, no published ports and `--pull=never`. It applies all18canonical migrations and the candidate, uses the existing auth.uid stub, and removes only its exact container ID after checking its unique ownership label. This does not test GoTrue/JWT/session validation or managed Supabase services.

Final [receipt](staging_hardening_local_pass_20261112.json):42/42 focused checks and21/21 existing clean DB-suite cases PASS. Cleanup verified by successful exact-ID removal and successful empty Docker inventory. Checked all10helper anon denials and authenticated execution grants; actual public/unlisted Guest detail, private/draft denial, public-only listing/summary, venue access; outstanding-row identity for two players, owner/treasurer access and unrelated-user denial; both trigger configs and insert/update behavior on temporary legacy-shaped tables. Function bodies and view-definition hashes unchanged.

Two earlier verification attempts are preserved:

- [Attempt1](staging_hardening_local_attempt1_20261112.json):40focused checks and21DB cases passed, but verifier queried legacy play_date on a clean modern sessions table where that column does not exist. Overall FAIL; cleanup verified. This is a verifier assumption failure, not evidence that the candidate changed schema or broke a trigger. Final probe tests the legacy function against explicit temporary legacy-shaped tables.
- [Attempt2](staging_hardening_local_attempt2_20261112.json):FAIL before migration setup because Unix-socket pg_isready observed the image's temporary initialization server before its restart. Cleanup verified. Final probe uses container-local TCP readiness, which excludes that temporary server.

Run the published probe from the repository with Python and an existing Docker postgres:17 image. It writes a fresh temporary receipt under .build; it never contacts hosted Supabase. Test fixtures persist only inside the owned container; cleanup destroys the entire isolated database. This is not a claim that every fixture operation used SQL ROLLBACK.

No staging data/users created. Anonymous helper exposure on hosted staging remains until the reviewed candidate is made canonical, applied to that exact target and independently checked through hosted grants/HTTP/advisor. Authenticated arbitrary-UUID helper probing remains outside this body-preserving repair. Other security-advisor notices and full V3/V5/V7/BH-07/V8 remain open.
