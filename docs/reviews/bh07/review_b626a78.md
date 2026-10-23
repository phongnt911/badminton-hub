# Review BH-07 — b626a78 backup/restore local

- Vai trò: Codex reviewer/chốt theo yêu cầu chủ dự án. Source do Codex đã viết ở lượt trước; lượt này tự chạy lại và review, **không tuyên bố độc lập với tác giả**. Không sửa source triển khai.
- Base: `74305bb343fbaf548cb5eea38a77475cc3a21b39`.
- Tested source: `b626a7852401e91db436ecc70134150f4c87c06f`.
- Checkout chạy review: `542eb24b3cb5cd1eac526af6d7d496a5d6ed6ad0` (docs/evidence), sạch trước chạy; origin khớp. Diff app/unit/backend từ base rỗng.
- Kết luận: [ ] Đạt [x] **Chưa đạt** trong phạm vi backup/restore local. Không đóng gói; không chuyển bước kế, merge main/deploy/pilot. Browser đã đóng giữ nguyên kết luận.

## Phát hiện

### R1 — P2: Cleanup thất bại vẫn báo PASS và exit0

- File:dòng: `scripts/bh07_backup/run_local_rehearsal.py:244`, `:247`, `:248`, `:252`.
- Tái hiện: chạy `review_b626a78_evidence/cleanup_probe.py`. Probe trích **nguyên AST finalbody và return của main** từ source đang review, không viết lại logic. Dùng thư mục tạm chỉ chứa chuỗi giả, command Docker stub; không tạo secret hay tác động Docker. Positive control cleanup thành công → exit0. Control lỗi private cleanup (rmtree không xóa) → `private_dumps_keys_removed=false` nhưng status PASS/exit0. Control Docker rm/network rm trả1, private cleanup thành công → vẫn status PASS/exit0.
- Kỳ vọng: mọi cleanup tài nguyên do chính runner tạo phải được kiểm kết quả; nếu còn dump/key hoặc không xác nhận tài nguyên đã dọn thì summary FAIL, exit khác0. Vẫn dọn các tài nguyên còn lại, giữ lỗi gốc nếu có, không log credential. Không xóa tài nguyên có sẵn ngoài sở hữu của lần chạy.
- Thực tế: rm/network rm dùng accept_error=True và bỏ returncode; rmtree(ignore_errors=True) chỉ ghi boolean; return chỉ dựa status trước cleanup. Cả hai negative scenario được nhận thành công. Probe exit0 nghĩa là tái hiện đúng lỗi, **không phải gate sản phẩm PASS**.
- Ảnh hưởng: pipeline có thể chốt rehearsal thành công trong khi archive/roles/password/JWT runtime còn trên máy hoặc fixture còn hoạt động; trái cam kết cleanup của runbook. Chưa quan sát rò rỉ thật trong lượt chạy bình thường.
- Cách sửa: thu thập và kiểm kết quả cleanup từng resource + kiểm private path còn tồn tại; đưa cleanup failure vào trạng thái/exit cuối, tiếp tục best-effort cleanup khi lỗi. Kiểm tài nguyên thực đã biến mất khi command báo thành công. Ghi stage/resource alias an toàn, không command/env/SQL chứa password. Thêm test tái hiện trước, positive cleanup, private-delete failure, Docker remove/network failure, cleanup tiếp tục sau lỗi và giữ lỗi chạy chính. Phát lại probe reviewer giữ nguyên kỳ vọng; mở rộng gate để probe đọc đúng logic mới nếu refactor, không bỏ negative case.
- Trạng thái: **FAIL — cần AI triển khai sửa**, reviewer không sửa source.

### P0/P1

Không phát hiện trong phạm vi đã kiểm. Không suy kết luận này sang production hoặc nghiệm thu toàn BH-07.

## Bằng chứng tự chạy

- Restore thật mới:13/13 checks, exit0, source public/Auth/schema/roles/sequences khớp đích; GoTrue/PostgREST HTTP thật, Owner/cohost/outsider/anonymous/sai mật khẩu và payment replay PASS;3 negative controls hiện có PASS. Đây là luồng bình thường, không phủ lỗi cleanup.
- Flutter analyze: exit0,0 issue; toàn bộ Flutter: exit0,240 PASS+1 skip.
- BH-07 DB:23/23 PASS, exit0 trên container fixture riêng với Auth stub; JSON ghi checkout542eb24 và dirty=false. Không coi Auth stub là bằng chứng HTTP.
- Manifest tác giả11/11, UTF8/LF,0 secret theo verifier; so toàn thư mục trước/sau verify readonly không đổi.
- Probe bổ sung:1 positive đúng,2 negative cleanup tái hiện false success; không chỉnh app/runner/unit/backend.
- Linux/Docker PostgreSQL17.11, GoTrue2.197.0, PostgREST16.4, Kong2.8.1, Flutter3.47.7. Log/JSON của lượt review nằm `review_b626a78_evidence/`, không thay evidence tác giả.

## NOT RUN

Review bởi người/AI khác với tác giả; managed Supabase backup toàn project/Storage/Edge/Realtime/external secrets; PITR/offsite/encryption/retention automation; backup với concurrent writer; lỗi cleanup thực do permission/Docker daemon fault (probe dependency-injection, không cố làm kẹt dump thật); browser/device/offline/deep link trong lượt này; banking/webhook; staging/production/restore thật; rehearsal tải thật, pilot và nghiệm thu toàn BH-07. BH-02..06 đầy đủ không chạy lại vì không đổi app/backend/migration.

**Kết luận: Chưa đạt. Giao AI triển khai sửa R1, reviewer kiểm lại trước khi đóng.**
