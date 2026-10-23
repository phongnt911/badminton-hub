# Bàn giao backup/restore rehearsal BH-07 local — sửa R1 cleanup

**Trạng thái hiện hành: Chờ review độc lập R1 fix. Người triển khai tự kiểm, không phải review độc lập; không tự ghi Đạt.**

- Nhánh: `feat/bh07-backup-rehearsal`.
- Base review: `ec0784f359ed877177330c59dbf40e0ce384ecbf`.
- Tested source: `6d00e9cea29c29a2b57d3291fb92be7600110f98`, worktree sạch trước lượt rehearsal cuối.
- Docs/evidence: commit chứa file này (reviewer lấy SHA từ prompt); evidence mới ở `backup_restore_cleanup_evidence/`. Evidence cũ `backup_restore_evidence/` và `review_b626a78_evidence/` giữ nguyên.
- Phạm vi sửa: chỉ `scripts/bh07_backup/run_local_rehearsal.py` và probe mới `scripts/bh07_backup/cleanup_probe.py`; không đổi app, unit test, migration/RPC, contract hay backend.

## R1 đã sửa

- Cleanup kiểm tra từng container/network do lượt chạy sở hữu trước khi xóa và `docker inspect` lại sau khi xóa; resource còn tồn tại hoặc lệnh xóa lỗi đều ghi `cleanup_errors`.
- Cleanup tiếp tục các resource còn lại sau một lỗi; private dump/key còn tồn tại thì `private_dumps_keys_removed=false`.
- Nếu cleanup lỗi, summary chuyển `FAIL`, `cleanup_failed=true`, exit `1`; lỗi chạy chính được giữ nguyên (`failure_type` không bị ghi đè).
- Log cleanup chỉ dùng alias/return code, không log command chứa secret.
- Probe `scripts/bh07_backup/cleanup_probe.py` trích nguyên cleanup `finally` và `return` hiện hành bằng AST, không copy logic. 5 control: positive; private cleanup failure; Docker cleanup failure; cleanup tiếp tục sau lỗi; giữ lỗi chạy chính.
- Trước sửa probe exit `1` (positive đúng, hai negative vẫn exit `0`); sau sửa exit `0`, cả 5 control `ok=true`. Probe reviewer cũ được phát lại và giữ nguyên file.

## Kết quả tự chạy

| Lệnh | Exit | Kết quả |
|---|---|---|
| `python scripts\bh07_backup\cleanup_probe.py` trước sửa |1|Tái hiện private/Docker cleanup failure vẫn exit0|
| `python scripts\bh07_backup\cleanup_probe.py` sau sửa |0|5/5 control PASS|
| `python -u scripts\bh07_backup\run_local_rehearsal.py --out <temp>` tại `6d00e9c` |0|13/13 check PASS; dirty rỗng; private dump/key đã xóa; cleanup lỗi rỗng|
| `flutter analyze` |0|0 issue|
| `flutter test` |0|240 PASS,1 skip|
| `BH02_TEST_CONTAINER=bh02-test-postgres python -u docs/reviews/bh07/run_bh07_tests.py` |0|23/23 DB PASS; Auth stub riêng|
| `clean_and_manifest.py --generate/--verify` |0/0|18/18 file, hash read-only, UTF-8 LF, 0 secret/JWT ngoài allowlist|

Rehearsal cuối: `status=PASS local rehearsal; pending review`, `private_dumps_keys_removed=true`, `cleanup_errors=[]`, `cleanup_failed=false`, source_port `55874`; sau chạy không còn container/network `bh07-http-review-*` (log `post_rehearsal_docker_state.log`). Đây là môi trường Windows/Docker local, không phải Linux cũ.

Một lượt sạch tại `2c6225f3c1383d89d8d6c5101ddc1320b99313f8` exit `1` vì target PostgreSQL chưa sẵn sàng trước restore. Log/summary thất bại được giữ trong evidence; đã bổ sung chờ tối đa 60 giây và nhãn stage an toàn tại `6d00e9c`, không che lỗi. Lượt `6d00e9c` mới là evidence cuối.

## Cần review

Tập trung `scripts/bh07_backup/run_local_rehearsal.py` phần `finally`/`return` và `scripts/bh07_backup/cleanup_probe.py`. Reviewer tự chạy lại probe, rehearsal thật từ checkout sạch với output mới, `flutter analyze`, `flutter test`, DB runner và manifest readonly. Kiểm:
- private dump/key còn lại hoặc Docker rm/inspect lỗi không thể cho exit0/PASS;
- cleanup vẫn tiếp tục resource khác sau lỗi;
- lỗi chạy chính không bị cleanup ghi đè;
- chỉ resource của lượt chạy bị xóa; không log secret;
- probe không copy logic cleanup và không nới kỳ vọng;
- manifest không đổi sau verify readonly.

Không chấp nhận kết luận chỉ dựa vào log của người triển khai; phải tự chạy. Không merge main/deploy/pilot.

## NOT RUN

Managed Supabase backup/PITR/offsite/encryption/retention; backup cùng concurrent writer; staging/production/restore thật; browser/device/offline/deep link ở gói này; ngân hàng/webhook; rehearsal tải thật/pilot và nghiệm thu toàn BH-07. Local PostgreSQL/Auth không đại diện cho các cổng này.

## Lịch sử

Bàn giao ban đầu source `b626a7852401e91db436ecc70134150f4c87c06f` (base `74305bb`) bị review [Chưa đạt R1 P2](review_b626a78.md); evidence và probe reviewer cũ vẫn giữ. Runbook: [26](../../26_BH07_OPERATIONS_REHEARSAL.md).
