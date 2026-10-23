# Reviewer commands / Linux

Checkout detached986baac, source tree same as282f978; clean before execution.
Logs outside repo until tests finished; actual HEAD preserved in runner JSON.

```bash
python scripts/bh07_backup/cleanup_probe.py
python docs/reviews/bh07/review_6d00e9c_evidence/inspect_probe.py
python -u scripts/bh07_backup/run_local_rehearsal.py --out /tmp/bh07-review-r2-20261023-final
/workspace/toolchains/flutter-review-3.47.7/bin/flutter analyze
/workspace/toolchains/flutter-review-3.47.7/bin/flutter test
docker run -d --name bh07-r2-review-regression -e POSTGRES_HOST_AUTH_METHOD=trust postgres:17
docker exec bh07-r2-review-regression psql -U postgres -v ON_ERROR_STOP=1 -c 'CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN; CREATE ROLE service_role NOLOGIN BYPASSRLS;'
BH02_TEST_CONTAINER=bh07-r2-review-regression python -u docs/reviews/bh07/run_bh07_tests.py
docker rm -f -v bh07-r2-review-regression
python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/backup_restore_cleanup_r2_evidence
```

Author evidence is readonly; no generate/normalization. Reviewer bundle manifest built from captured bytes, scan strict UTF8 LF and secret patterns, then verified readonly. post_cleanup.json stores actual empty source/target/network queries and private-runtime path scan. No archive/roles SQL/key/config published.
