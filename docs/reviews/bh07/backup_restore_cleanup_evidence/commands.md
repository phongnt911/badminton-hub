# Lệnh và provenance — R1 cleanup fix backup/restore local

- Nhánh: `feat/bh07-backup-rehearsal`.
- Base review: `ec0784f359ed877177330c59dbf40e0ce384ecbf`.
- Tested source cuối: `6d00e9cea29c29a2b57d3291fb92be7600110f98`, worktree sạch trước lượt rehearsal cuối.
- Nguồn thay đổi: `scripts/bh07_backup/run_local_rehearsal.py` và probe mới `scripts/bh07_backup/cleanup_probe.py`; không đổi app, unit test, migration/RPC, contract hay backend.
- Nền tảng thực chạy: Windows 11, Python 3.12.7, Docker server 29.8.2, Flutter 3.47.6. Đây là môi trường khác với evidence Linux cũ; số liệu dưới đây là lần chạy thật trên máy hiện tại.

## Tái hiện trước khi sửa

```powershell
python scripts\bh07_backup\cleanup_probe.py
```

Kết quả: exit `1`; positive control đúng, nhưng private-cleanup và Docker-cleanup vẫn trả exit `0` nên probe báo `ok=false`. Log: `cleanup_probe_before.log`. Probe reviewer cũ (`review_b626a78_evidence/cleanup_probe.py`) cũng được phát lại; nó chỉ in hiện tượng và exit `0`, log: `reviewer_cleanup_probe_before_fix.log`. Không sửa file evidence của reviewer.

## Sau khi sửa

```powershell
python scripts\bh07_backup\cleanup_probe.py
```

Kết quả: exit `0`, cả 5 control `ok=true`: positive, private cleanup failure, Docker cleanup failure, cleanup tiếp tục sau lỗi, và giữ lỗi chạy chính. Log: `cleanup_probe_after.log`.

## Rehearsal thật

Một lượt sạch tại source `2c6225f3c1383d89d8d6c5101ddc1320b99313f8` exit `1` vì target PostgreSQL chưa sẵn sàng trước khi restore; log và summary thất bại được giữ ở `rehearsal_attempt_2c6225f_failed.log` và `summary_attempt_2c6225f_failed.json`. Đã bổ sung chờ tối đa 60 giây và nhãn stage an toàn tại `6d00e9c`; không che lỗi và không đổi kỳ vọng kiểm thử.

```powershell
python -u scripts\bh07_backup\run_local_rehearsal.py --out "$env:TEMP\bh07-backup-r1-final2-20261023173601"
```

Kết quả cuối: exit `0`, `status=PASS local rehearsal; pending review`, 13/13 check PASS, `dirty_before_run=""`, `private_dumps_keys_removed=true`, `cleanup_errors=[]`, `cleanup_failed=false`; source Kong dùng cổng loopback tự do `55874` để không đụng Supabase local đang giữ `54321`. Log: `rehearsal.log`; summary/fingerprints: `summary.json`, `source_fingerprints.json`, `restored_fingerprints.json`.

Sau lượt chạy, kiểm tra thực tế không còn container/network tên `bh07-http-review-*`:

```powershell
docker ps -a --filter name=bh07-http-review
docker network ls --filter name=bh07-http-review
```

Log: `post_rehearsal_docker_state.log` (hai lệnh, không có resource trả về).

## Cổng Flutter và DB

```powershell
flutter analyze
flutter test
$env:BH02_TEST_CONTAINER='bh02-test-postgres'
python -u docs\reviews\bh07\run_bh07_tests.py
```

Kết quả: analyze exit `0`; Flutter `240` test pass, `1` skip, exit `0`; DB runner `23/23 PASS`, exit `0`. Log: `flutter_analyze.log`, `flutter_test.log`, `bh07_db_runner.log`, `bh07_db_results.json`.

## Manifest

```powershell
python scripts\bh07_browser\clean_and_manifest.py --generate --evidence-dir docs\reviews\bh07\backup_restore_cleanup_evidence
python scripts\bh07_browser\clean_and_manifest.py --verify --evidence-dir docs\reviews\bh07\backup_restore_cleanup_evidence
```

Generator chuẩn hóa text evidence về UTF-8 không BOM, LF; verify chỉ đọc, kiểm hash/extra/missing/encoding và secret/JWT ngoài allowlist. Exit thực tế ghi ở `exits.json`; output verify ở `manifest_verify.log` trong thư mục evidence. Không publish dump, roles SQL, password, JWT hay runtime config; fingerprint chỉ chứa count/digest.

## Ghi chú

- Evidence cũ `docs/reviews/bh07/backup_restore_evidence/` và `review_b626a78_evidence/` được giữ nguyên, không ghi đè.
- Đây là tự kiểm của người triển khai, chưa phải review độc lập; không tự ghi Đạt, không merge main/deploy/pilot.
- Các giới hạn vẫn NOT RUN: managed Supabase backup/PITR/offsite, writer đồng thời, staging/production, mobile/browser khác, banking/webhook, rehearsal/pilot.
