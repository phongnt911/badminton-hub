# Lệnh và provenance

Source b626a7852401e91db436ecc70134150f4c87c06f, base74305bb343fbaf548cb5eea38a77475cc3a21b39; checkout sạch khi chạy. Cwd repo badminton-hub Linux. Flutter thực tế `/workspace/toolchains/flutter-review-3.47.7/bin/flutter`.

```bash
python -u scripts/bh07_backup/run_local_rehearsal.py --out /workspace/scratch/bh07-backup-run-01
flutter analyze
flutter test
docker run -d --name bh07-backup-regression -e POSTGRES_HOST_AUTH_METHOD=trust postgres:17
# Lần đầu thiếu roles; giữ log exit1. Bootstrap rồi chạy lại:
docker exec bh07-backup-regression psql -U postgres -v ON_ERROR_STOP=1 -c 'CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN; CREATE ROLE service_role NOLOGIN BYPASSRLS;'
BH02_TEST_CONTAINER=bh07-backup-regression python -u docs/reviews/bh07/run_bh07_tests.py
docker rm -f -v bh07-backup-regression
python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/backup_restore_evidence
```

Không publish private archive/roles SQL/JWT/config runtime. Source và target fingerprints chỉ counts/digests; summary có measurement/13 checks. Manifest được generate ở vai trò tác giả đóng gói, verify sau đó là readonly. Source recipe nguyên bản từ late_response_evidence giữ nguyên trong Git; output setup/bootstrap không cần publish lại vì không bổ sung bằng chứng phục hồi.
