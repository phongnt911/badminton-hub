# Review BH-07 — 282f978 cleanup R1 vòng2/2

## Kết luận

**Đạt trong phạm vi BH-07 backup/restore cleanup local. Đóng R1 P2 và đóng công việc backup/restore local trên nhánh `feat/bh07-backup-rehearsal`.** Không có P0/P1/P2 còn mở trong phạm vi bản sửa đã kiểm. Giữ Git ref chưa merge; không nghiệm thu toàn BH-07, không cấp phép staging/production/pilot.

- Review base: `f216ae1fb220f140b091abd5acd2969333ec7f53`.
- Tested source: `282f978ba2afaa58e3f5810f282bdfd0febf334d`.
- Docs/evidence và checkout tự chạy: `986baac29d506282740f477a5fb5ba94e15c496b`, worktree sạch trước chạy.
- Source script tree ở hai commit giống nhau: `baba0aaca005e49e5f7965e630a7f75b2cfff0b1`. JSON reviewer trung thực ghi HEAD docs986baac; không đổi thành source282f978. `base_sha=ec0784f...` là baseline fixture hardcode đã được giải thích; không phải review base vòng này.
- Codex reviewer tự chạy bản sửa của AI triển khai khác, không sửa source. Baseline fixture b626a78 từng do Codex viết; không gọi review này là độc lập với toàn bộ lịch sử tác giả.
- Linux/Docker, Flutter3.47.7, PostgreSQL17.11, GoTrue2.197.0/PostgREST16.4/Kong2.8.1. Khác Windows/Python3.12.7/Flutter3.47.6 của tác giả.

### P0

Không có phát hiện.

### P1

Không có phát hiện.

### P2

Không có phát hiện mới. **Đóng R1** của review_b626a78 và review_6d00e9c: predicate vắng mặt so toàn thông báo đúng kind/tên; context/daemon/permission/transport không bị coi là absence. Inspect lỗi trước/sau remove, remove thất bại/giả thành công và private path còn đều làm FAIL/exit1. Cleanup còn lại tiếp tục; lỗi chạy chính giữ nguyên. Chỉ dùng resource thuộc run, preflight từ chối stack có sẵn. Positive path thực trên Linux xác nhận Docker absence message tương thích; thông báo lạ vẫn fail-closed.

## Bằng chứng reviewer tự chạy

| Kiểm tra | Exit | Kết quả |
|---|---|---|
| `python scripts/bh07_backup/cleanup_probe.py` |0|14/14 `ok=true`, giữ5 control cũ và9 control bổ sung; loader trích finally/return hiện hành bằng AST, không copy predicate|
| `python docs/reviews/bh07/review_6d00e9c_evidence/inspect_probe.py` nguyên file |1 có chủ ý|Positive/daemon/context đều đúng; missing_context_error actual_exit1, cleanup_failed=true, rm_calls=[],1 container synthetic/network còn; assertion lịch sử đòi false success nên exit1. Không sửa file/kỳ vọng để làm xanh|
| `python -u scripts/bh07_backup/run_local_rehearsal.py --out /tmp/bh07-review-r2-20261023-final` |0|13/13 PASS, dirty rỗng, private removed=true, cleanup_errors=[], cleanup_failed=false|
| Docker kiểm source/target/network sau rehearsal |0|Không còn container/network của rehearsal; private dump/key đã xóa|
| `flutter analyze` |0|0 issue|
| `flutter test` |0|240 PASS+1 skip|
| `BH02_TEST_CONTAINER=bh07-r2-review-regression python -u docs/reviews/bh07/run_bh07_tests.py` |0|23/23 PASS; container riêng bootstrap3 roles, Auth stub; không thay bằng chứng HTTP thật|
| Manifest tác giả `--verify` |0|16/16, strict UTF8 không BOM/LF,0 secret/JWT ngoài allowlist; hash toàn evidence trước/sau không đổi|

Lệnh Flutter dùng `/workspace/toolchains/flutter-review-3.47.7/bin/flutter`. Rehearsal restore DB/roles vào cluster mới, so public/Auth rows/schema/roles/sequences, đăng nhập GoTrue và ACL PostgREST thật, payment retry cùng ID/1payment/1ledger/1operation, aggregate server không đổi;3 negative controls dữ liệu/ACL/archive vẫn chạy. Không suy Auth stub DB thành HTTP/JWT.

Source commit chỉ đổi2 script được giao; docs commit chỉ docs/evidence/trạng thái; diff `lib test supabase` rỗng. Bốn thư mục evidence cũ giữ nguyên blob Git. Lỗi generate đầu do UTF16/CRLF được tác giả ghi exit1 trong exits/commands, lần generate/verify cuối0; không có chứng cứ cho rằng lịch sử bị đổi. Reviewer chỉ chạy verify trên evidence tác giả, không generate/normalize/ghi đè. Scan mẫu không thay thế bảo đảm tuyệt đối mọi loại secret; không publish dump/roles SQL/token/config runtime.

Bằng chứng mới tại `review_282f978_evidence/`; report và trạng thái không thay evidence tác giả. Source/app/unit/backend/contract không sửa. Giữ các verdict trước trong lịch sử, trạng thái hiện hành là kết luận này.

### NOT RUN

- Managed Supabase backup/PITR/offsite/encryption/retention; Storage/Edge/Realtime/external secrets ngoài PostgreSQL fixture.
- Concurrent writers; staging/production/restore thật.
- Browser/device/offline/deep link trong lượt này; banking/webhook.
- Rehearsal tải thật/pilot và nghiệm thu toàn BH-07.
- Fault cleanup thật do hỏng Docker context/permission trong một live run: các fault dùng AST hiện tại + stateful stub; riêng stderr context của probe lấy từ Docker thật. Không cố để archive/secret thật kẹt trên máy.
- BH-02..06 đầy đủ không chạy lại vì app/backend/migration không đổi.

**Đạt local vòng2/2 — đóng R1 và gói backup/restore local.** Việc tiếp theo giao AI triển khai là hồ sơ readiness BH-07 dạng docs: map từng cổng sang SHA/bằng chứng/giới hạn và kế hoạch kiểm chứng phần còn thiếu. Không thực thi staging/production/pilot hay tự chuyển BH-08.

Kiểm đóng gói reviewer: manifest15/15, strict UTF8/LF và0 secret theo mẫu scan; không thay manifest/evidence tác giả. `git diff --check` sạch.
