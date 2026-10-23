# Lệnh và provenance — R1 vòng 2/2 cleanup backup/restore local

- Nhánh: `feat/bh07-backup-rehearsal`.
- Base review R1 vòng 2: `f216ae1fb220f140b091abd5acd2969333ec7f53`.
- Tested source: `282f978ba2afaa58e3f5810f282bdfd0febf334d`, worktree sạch trước lượt rehearsal cuối.
- Script vẫn giữ `base_sha` nội bộ `ec0784f359ed877177330c59dbf40e0ce384ecbf` trong `summary.json`; đây là baseline fixture ban đầu của script, không phải base review `f216ae1`.
- Chỉ đổi `scripts/bh07_backup/run_local_rehearsal.py` và `scripts/bh07_backup/cleanup_probe.py`; không đổi `lib`, `test`, `supabase`, migration/RPC, contract hay backend.
- Nền tảng thực chạy: Windows 11, Python 3.12.7, Docker server 29.8.2, Flutter 3.47.6/Dart 3.13.5. Đây là môi trường local khác evidence Linux cũ.

## Tái hiện trước khi sửa

Chạy probe mới trên source cũ `f216ae1` (probe đã bổ sung control, source chưa sửa):

```powershell
python scripts\bh07_backup\cleanup_probe.py
```

Kết quả: exit `1`; 3 control sai vì lỗi context vẫn bị coi là resource vắng mặt:
`inspect_error_before_remove_context`, `inspect_error_after_remove`,
`network_inspect_error_after_remove`. Log: `cleanup_probe_before.log`; exit ghi ở `exits.json`.

## Sau khi sửa

```powershell
python scripts\bh07_backup\cleanup_probe.py
```

Kết quả: exit `0`, 14/14 control `ok=true`. Năm control cũ vẫn giữ nguyên; thêm control inspect lỗi trước remove (context/daemon/permission/transport), inspect lỗi sau remove của container/network, network remove failure, container remove trả0 nhưng còn resource, network remove trả0 nhưng còn resource. Log: `cleanup_probe_after.log`.

Probe reviewer được phát lại nguyên file, không sửa:

```powershell
python docs\reviews\bh07\review_6d00e9c_evidence\inspect_probe.py
```

Kết quả thực tế: exit `1` **do assertion cũ của probe yêu cầu false success**. Output mới cho thấy lỗi context thật đã đúng: `actual_exit=1`, `cleanup_failed=true`, `cleanup_errors` có lỗi inspect, `rm_calls=[]`, container/network synthetic còn nguyên. Vì probe cũ kết luận `ok` bằng `(status == 0) == (case == 'positive')` và cuối file assert `not results[2]['ok']`, nó cố ý fail khi lỗi đã được sửa. Không sửa file evidence của reviewer; log: `reviewer_inspect_probe_replay.log`.

## Rehearsal thật

Chạy từ checkout sạch tại `282f978`, output mới ngoài repo:

```powershell
python -u scripts\bh07_backup\run_local_rehearsal.py --out "$env:TEMP\opencode\bh07-r1-r2-rehearsal-20261023-1"
```

Kết quả: exit `0`; 13/13 check PASS; `status=PASS local rehearsal; pending review`; `dirty_before_run=""`; `private_dumps_keys_removed=true`; `cleanup_errors=[]`; `cleanup_failed=false`; source Kong dùng cổng loopback `64444`; backup `0,203giây`; recovery `9,313giây`. Log: `rehearsal.log`; summary/fingerprints: `summary.json`, `source_fingerprints.json`, `restored_fingerprints.json`.

Sau lượt chạy, kiểm tra thực tế không còn container/network tên `bh07-http-review-*` hoặc resource `bh07` khác:

```powershell
docker ps -a --filter name=bh07-http-review
docker network ls --filter name=bh07-http-review
docker ps -a --format '{{.Names}}'   # lọc bh07
docker network ls --format '{{.Name}}' # lọc bh07
```

Log: `post_rehearsal_docker_state.log`; output chỉ có header của lệnh lọc, không có resource khớp.

## Cổng Flutter và DB

```powershell
flutter analyze
flutter test
```

Kết quả: analyze exit `0`, 0 issue; Flutter `240` test pass, `1` skip, exit `0`. Log: `flutter_analyze.log`, `flutter_test.log`.

DB runner được chạy từ worktree sạch (evidence tạm đưa ra ngoài repo), output log ghi ngoài repo rồi mới đưa vào evidence, để `worktree_dirty=false` đúng thực tế:

```powershell
$env:BH02_TEST_CONTAINER='bh02-test-postgres'
python -u docs\reviews\bh07\run_bh07_tests.py
```

Kết quả: exit `0`, `23/23 PASS`, `failed=0`, JSON tự ghi `base_sha=282f978...`, `worktree_dirty=false`, container `bh02-test-postgres`; Auth vẫn là stub riêng, không thay bằng chứng HTTP. Log/result: `bh07_db_runner.log`, `bh07_db_results.json`.

## Manifest

```powershell
python scripts\bh07_browser\clean_and_manifest.py --generate --evidence-dir docs\reviews\bh07\backup_restore_cleanup_r2_evidence
python scripts\bh07_browser\clean_and_manifest.py --verify --evidence-dir docs\reviews\bh07\backup_restore_cleanup_r2_evidence
```

Lần generate đầu tiên exit `1` vì log do PowerShell redirect là UTF-16/CRLF; đã chuẩn hóa text evidence về UTF-8 LF rồi generate lại exit `0`. Lỗi này được ghi ở `exits.json`, không che. Kết quả cuối: `16/16` file, `0 secret/JWT outside allowlist`, verify readonly exit `0`; output ở `manifest_verify.log`. Verify không đổi hash evidence. Không publish dump, roles SQL, password, JWT hay runtime config; fingerprint chỉ chứa count/digest.

## Kiểm tra phụ

```powershell
python -m py_compile scripts\bh07_backup\run_local_rehearsal.py scripts\bh07_backup\cleanup_probe.py
git diff --check
git diff --stat f216ae1..282f978 -- lib test supabase
```

`py_compile` exit `0`; `git diff --check` sạch; diff app/unit/migration/RPC/contract rỗng. Evidence cũ `docs/reviews/bh07/backup_restore_evidence/`, `review_b626a78_evidence/` và `backup_restore_cleanup_evidence/` được giữ nguyên, không ghi đè.

## Ghi chú

- Đây là tự kiểm của người triển khai, chưa phải review độc lập; không tự ghi Đạt, không merge main/deploy/pilot.
- Các giới hạn vẫn NOT RUN: managed Supabase backup/PITR/offsite/encryption/retention; concurrent writers; staging/production/restore thật; browser/device/offline/deep link; banking/webhook; rehearsal tải thật/pilot và nghiệm thu toàn BH-07; fault injection permission thật trên archive/secret.
