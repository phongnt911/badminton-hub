# Bàn giao backup/restore rehearsal BH-07 local — sửa R1 cleanup vòng2/2

**Trạng thái hiện hành: Đạt local vòng2/2, đóng R1 và công việc backup/restore local tại source282f978 theo [review chốt](review_282f978.md). Không nghiệm thu toàn BH-07/production/pilot; giữ NOT RUN. Nội dung chờ review dưới đây là lịch sử bàn giao trước kết luận.**

**Điểm tiếp tục (23/10/2026):** Hồ sơ readiness BH-07 docs-only đang **Chờ review độc lập** tại [bh07_readiness.md](bh07_readiness.md), base `b91a350e619529d389af3edf6d4a06408af8d200`. Hồ sơ map cổng/SHA/evidence, tách Đạt local với NOT RUN và lập kế hoạch kiểm chứng; không chạy môi trường thật. Không merge main/deploy/pilot hoặc tự chuyển BH-08.

**Lịch sử bàn giao trước chốt: R1 cleanup vòng2/2 từng Chờ review độc lập.** Người triển khai tự kiểm, **không phải review độc lập; không tự ghi Đạt**. Base review `f216ae1fb220f140b091abd5acd2969333ec7f53`, tested source `282f978ba2afaa58e3f5810f282bdfd0febf334d`, nhánh `feat/bh07-backup-rehearsal`. Evidence mới ở `backup_restore_cleanup_r2_evidence/`. Đã được review chốt local vòng2/2; browser giữ Đạt local. Không merge main/deploy/pilot.

## Phạm vi bàn giao trước review (lịch sử)

- Chỉ sửa `scripts/bh07_backup/run_local_rehearsal.py` và `scripts/bh07_backup/cleanup_probe.py`; không đổi `lib`, `test`, `supabase`, migration/RPC, contract hay backend.
- R1 vòng1/2 bị review Chưa đạt tại [review_6d00e9c](review_6d00e9c.md): `resource_present` coi mọi stderr có `not found` là resource vắng mặt, nên lỗi Docker context thật vẫn cho PASS/exit0 dù container/network còn nguyên.
- Bản này chỉ chấp nhận absence đúng kind/tên: container `No such object: <name>`/`No such container: <name>`, network `network <name> not found`/`No such network: <name>`, so khớp toàn chuỗi (không dùng substring `not found`). Context/daemon/permission/transport và inspect lỗi đều ghi `cleanup_errors`, `cleanup_failed=true`, status `FAIL`, exit `1`; cleanup vẫn tiếp tục resource khác, private dump/key vẫn được dọn, lỗi chạy chính không bị ghi đè.
- Chỉ dùng tên resource do lượt chạy sở hữu; không xóa resource có sẵn của người khác. Log chỉ có alias/return code, không chứa command/secret.

## Probe và tái hiện

- Probe `scripts/bh07_backup/cleanup_probe.py` trích nguyên `finally` và `return` hiện hành bằng AST, dùng Docker stub stateful; không copy predicate cleanup.
- Trước sửa (source `f216ae1` + probe mới): exit `1`; 3 control sai vì context vẫn bị coi là vắng mặt: `inspect_error_before_remove_context`, `inspect_error_after_remove`, `network_inspect_error_after_remove`. Log `cleanup_probe_before.log`.
- Sau sửa: exit `0`, **14/14 control `ok=true`**. Giữ5 control cũ; thêm:
  - inspect lỗi trước remove: context, daemon, permission, transport;
  - inspect lỗi sau remove: container và network;
  - network remove failure;
  - container remove trả0 nhưng resource vẫn còn;
  - network remove trả0 nhưng resource vẫn còn.
- Probe reviewer `docs/reviews/bh07/review_6d00e9c_evidence/inspect_probe.py` được phát lại **nguyên file, giữ nguyên kỳ vọng**, không sửa evidence của reviewer. Exit `1` là do assertion cũ `not results[2]['ok']` yêu cầu false success; output mới cho thấy lỗi context đã đúng: `actual_exit=1`, `cleanup_failed=true`, `rm_calls=[]`, container/network synthetic còn nguyên. Đây là bằng chứng lỗi đã được chặn, không phải runner PASS. Log `reviewer_inspect_probe_replay.log`.

## Kết quả tự chạy

| Lệnh | Exit | Kết quả |
|---|---|---|
| `python scripts\bh07_backup\cleanup_probe.py` trước sửa |1|3 control context/inspect-after sai, tái hiện false success|
| `python scripts\bh07_backup\cleanup_probe.py` sau sửa |0|14/14 control `ok=true`|
| `python docs\reviews\bh07\review_6d00e9c_evidence\inspect_probe.py` (nguyên file) |1|Assertion cũ yêu cầu false success; output thực tế context exit1, cleanup failed, resources còn, không rm|
| `python -u scripts\bh07_backup\run_local_rehearsal.py --out <temp>` tại `282f978` |0|13/13 check PASS; dirty rỗng; private dump/key đã xóa; cleanup lỗi rỗng; source_port `64444`|
| `flutter analyze` |0|0 issue|
| `flutter test` |0|240 PASS,1 skip|
| `BH02_TEST_CONTAINER=bh02-test-postgres python -u docs/reviews/bh07/run_bh07_tests.py` |0|23/23 DB PASS; JSON `worktree_dirty=false`, Auth stub riêng|
| `clean_and_manifest.py --generate/--verify` |0/0|16/16 file, UTF-8 LF,0 secret/JWT ngoài allowlist, verify readonly không đổi hash|

Rehearsal cuối: `status=PASS local rehearsal; pending review`, `private_dumps_keys_removed=true`, `cleanup_errors=[]`, `cleanup_failed=false`; sau chạy không còn container/network `bh07-http-review-*` hoặc resource `bh07` khác (log `post_rehearsal_docker_state.log`). Đây là môi trường Windows/Docker local, không phải Linux cũ.

Một lần generate manifest đầu tiên exit1 vì log PowerShell là UTF-16/CRLF; đã chuẩn hóa text evidence về UTF-8 LF rồi generate/verify lại exit0. Lỗi này được ghi trong `exits.json`/`commands.md`, không che.

## Cần review

Tập trung `scripts/bh07_backup/run_local_rehearsal.py` phần `resource_present`/`finally`/`return` và `scripts/bh07_backup/cleanup_probe.py`. Reviewer tự chạy lại probe, rehearsal thật từ checkout sạch với output mới, `flutter analyze`, `flutter test`, DB runner và manifest readonly. Kiểm:
- lỗi context/daemon/permission/transport hoặc inspect sau remove không thể cho exit0/PASS;
- absence chỉ được xác nhận đúng kind/tên, không dùng substring `not found`;
- cleanup vẫn tiếp tục resource khác sau lỗi; private dump/key còn lại phải FAIL;
- lỗi chạy chính không bị cleanup ghi đè;
- chỉ resource của lượt chạy bị xóa; không log secret;
- probe không copy logic cleanup và không nới kỳ vọng; 14 control thực sự chạy;
- manifest không đổi sau verify readonly.

Không chấp nhận kết luận chỉ dựa vào log của người triển khai; phải tự chạy. Không merge main/deploy/pilot.

## NOT RUN

Managed Supabase backup/PITR/offsite/encryption/retention; backup cùng concurrent writer; staging/production/restore thật; browser/device/offline/deep link ở gói này; ngân hàng/webhook; rehearsal tải thật/pilot và nghiệm thu toàn BH-07; fault injection permission thật trên archive/secret. Local PostgreSQL/Auth không đại diện cho các cổng này. Không merge/apply DB thật/deploy/chuyển pilot.

## Lịch sử

Bàn giao ban đầu source `b626a7852401e91db436ecc70134150f4c87c06f` (base `74305bb`) bị review [Chưa đạt R1 P2](review_b626a78.md); bản sửa vòng1/2 tại `6d00e9c` bị review [Chưa đạt R1 P2](review_6d00e9c.md) vì lỗi context false absence. Evidence cũ `backup_restore_evidence/`, `review_b626a78_evidence/` và `backup_restore_cleanup_evidence/` được giữ nguyên, không ghi đè. Runbook: [26](../../26_BH07_OPERATIONS_REHEARSAL.md).
