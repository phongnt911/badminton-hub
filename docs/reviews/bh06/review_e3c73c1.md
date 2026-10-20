# Review BH-06A — e3c73c1

Ngày 16/10/2026 (Việt Nam). Tested HEAD `e3c73c168def0a15ee5a71cb8eb263a7f2b5eaee`, base main `c35dd27`; diff `git diff origin/main...HEAD`. Vai trò reviewer theo `docs/ai/REVIEWER.md` trên `chore/ai-roles` (`163bc45`), file chưa có trên nhánh A. Không sửa code triển khai, không apply DB remote.

## Phát hiện

### R1 — P1: kiểm quyền NULL cho phép outsider đọc bank/công nợ của khách offline

**Vị trí:** `supabase/migrations/20261016130000_bh06_reads.sql:51–54`.

Khi `p_player_id` là khách `user_id=NULL`, `registration_status='confirmed'` và actor không có finance, biểu thức `false OR (NULL AND true)` cho `v_authorized=NULL`; `IF NOT v_authorized` không vào nhánh từ chối. Authenticated outsider biết session/player ID gọi RPC thành công, nhận tên khách, receiver_snapshot, amount_due/outstanding, reference và version. Không cần có vai trò trong buổi/CLB. Đây là lộ dữ liệu qua SECURITY DEFINER, không được coi biết UUID là có quyền.

**Tái hiện:** fixture giả có khách offline confirmed/present, revision current với due 100.000; actor 10 không có quyền gọi `get_payment_instructions(session, guest_id)`. Trên CLEAN và LEGACY đều exit 0 trả bank `TEST_ONLY`, account `00001234`, outstanding 100000; kỳ vọng FORBIDDEN. Negative control khi cùng player liên kết actor 5 thì outsider bị FORBIDDEN. [JSON probe](review_e3c73c1_evidence/probes.json), [log](review_e3c73c1_evidence/probes.log).

**Cách sửa:** migration forward dùng điều kiện null-safe, ví dụ `(v_player.user_id IS NOT DISTINCT FROM v_actor)` kết hợp actor đã non-NULL, hoặc kiểm `v_authorized IS NOT TRUE`. Giữ quyền finance đọc khách đúng scope. Trước sửa thêm test outsider và cohost không finance với khách offline confirmed; kiểm cả CLEAN/LEGACY và finance hợp lệ. Không sửa client để che lỗi quyền server.

### R2 — P1: giữ RPC bank cũ làm đường bỏ qua gate chưa chốt/stale

**Vị trí quyết định trong diff:** `supabase/migrations/20261016130000_bh06_reads.sql:2–5`; tuyên bố tương ứng ở `docs/08_DOMAIN_CONTRACTS.md:239`. Endpoint còn hiệu lực: `get_session_payment_instructions(UUID)` từ migration nền dòng 995–1042.

Migration mới gate `get_payment_instructions` nhưng chủ động giữ nguyên RPC cũ vẫn callable bởi authenticated/confirmed player và management, trả receiver_snapshot mà không kiểm revision. Đầu bài docs/24 §1, §3.A.5 yêu cầu xử lý mọi đường đọc bank/QR và không để đường cũ lọt gate stale; docs/08 §7 yêu cầu server gate trước phát hướng dẫn thanh toán. Không trả amount/reference không đủ để loại bỏ bypass: caller vẫn lấy bank qua RPC cũ và ghép số tiền đã cache; server không thể bảo đảm hướng dẫn phát ra từ revision current. Reviewer không chấp nhận ngoại lệ số 1 trong handoff theo cách hiện tại.

**Tái hiện:** sau chốt, host gọi `post_session_expense` trong transaction, response xác nhận billing_state=stale; chuyển actor sang confirmed player rồi gọi RPC cũ vẫn exit 0, trả receiver_snapshot trên CLEAN và LEGACY. Cùng fixture, RPC mới trả BILLING_STALE. [Probe/log](review_e3c73c1_evidence/probes.json) có cả kết quả cũ và negative control mới. Probe chứng minh bỏ qua gate; không tuyên bố đã xảy ra chuyển tiền thật.

**Cách sửa:** migration forward gate đường cũ theo current và quyền tương thích, hoặc revoke/deprecate đường cũ sau khi kiểm caller/test, chuyển sang endpoint canonical có version. Đồng bộ contract và handoff; không sửa migration đã chia sẻ. Thêm test trước sửa cho cả not_finalized/stale ở đường cũ và mới, không chỉ kiểm RPC mới. History/reversal phục vụ đối soát phải còn được đọc theo quyền, không dùng endpoint hướng dẫn thanh toán không gate làm API history.

## Kiểm chứng độc lập

[Summary, SHA256 migrations và bằng chứng](review_e3c73c1_evidence/summary.json): Flutter 3.47.7/Dart 3.13.5; PostgreSQL17 cô lập `--network none`, Auth stub, SET ROLE authenticated/anon và fixture giả. Cây sạch trước chạy; JSON runner sinh tạm trong repo, giữ theo cặp để extended/retry đọc rồi chuyển ra scratch, không đổi source/migration. Metadata dirty ở runner phụ có thể phản ánh JSON đang chờ chuyển. Không coi Auth stub là xác thực JWT thật.

| Lệnh/nhóm | Kết quả |
|---|---|
| flutter pub get --enforce-lockfile | exit 0, không đổi lockfile |
| flutter analyze --no-pub | No issues found, exit 0 |
| flutter test --no-pub | 137/137 PASS, exit 0 |
| BH-02 baseline + extended | 33 + 14 PASS, exit 0 |
| BH-03 + retry | 48 + 22 PASS, exit 0 |
| BH-04 | 44/44 PASS, exit 0 |
| BH-05 | 90/90 PASS, exit 0 |
| BH-06 runner tác giả, reviewer tự chạy | 80/80 PASS (40 × CLEAN/LEGACY), exit 0 |
| Probe reviewer | 4 PASS control / **4 FAIL** (R1×2, R2×2), exit 1 |

Tổng runner DB **331/331 PASS** không bao gồm probe lỗi. Lần đầu một số runner cũ từ chối tên container `bh06-...` trước khi chạy test; đổi tên thành `bh02-review-bh06` theo guard rồi chạy lại đúng cặp, không sửa runner/expected. SDK sẵn có 3.47.0/Dart3.13.0 không đủ yêu cầu, nên dùng checkout Flutter3.47.7 riêng. Log và JSON cuối được lưu cùng report. Bộ 80 ca không phủ hai đường quyền/gate nêu trên; kết quả xanh không đủ đóng R1/R2.

## Kết luận

**Chưa đạt phần A** tại `e3c73c1`: cần sửa R1/R2 bằng test tái hiện và migration forward, gửi lại đúng SHA để review vòng 1. Giữ lịch sử Chờ review, chưa chuyển BH-06B/C, chưa nghiệm thu toàn BH-06. Không merge main hoặc deploy.

**NOT RUN:** PostgREST HTTP/JWT/Supabase Auth thật; thiết bị/browser e2e, UI/provider/repository BH-06B/C; apply staging/production, backup/restore; concurrency qua HTTP và bank/VietQR thực tế. Không chứng minh khai thác trên remote; mọi repro dùng dữ liệu giả ở PostgreSQL local. Không nêu Đạt cho các phạm vi chưa kiểm.
