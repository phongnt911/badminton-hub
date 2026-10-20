# BH-06A — sửa theo review vòng 1

Ngày 16/10/2026 (Việt Nam). Vai trò: người triển khai (DeepSeek), theo `docs/ai/IMPLEMENTER.md` mục "Sửa theo review" trên `chore/ai-roles` (`163bc45`). Xử lý [review `e3c73c1`](review_e3c73c1.md) (Chưa đạt, 2 phát hiện P1). Không sửa ngoài phạm vi review, không merge `main`, không deploy. Trạng thái: **Chờ review vòng 1**.

- Nhánh `feat/bh06a-db`, base `main` = `c35dd27`.
- Commit sửa: `59baa25` (test tái hiện, phải FAIL trước khi sửa), `83586ed` (migration forward sửa R1/R2).

## R1 — quyền null-safe cho khách offline `user_id = NULL`

- Vị trí: `supabase/migrations/20261016130000_bh06_reads.sql:51–54`, sửa bằng migration forward rồi `CREATE OR REPLACE` trong `20261016140000_bh06a_review_round1.sql`.
- Trước: `v_authorized := has_session_finance_access(...) OR (v_player.user_id = v_actor AND ...)`; với khách `user_id=NULL` và actor không finance cho `false OR NULL = NULL`, `IF NOT v_authorized` không chặn ⇒ outsider biết UUID đọc được công nợ/ngân hàng.
- Sau: `v_player.user_id IS NOT DISTINCT FROM v_actor` (actor đã non-NULL) và `IF v_authorized IS NOT TRUE`. Finance đọc khách đúng scope vẫn giữ; không sửa client để che lỗi server.
- Test tái hiện: `Quyền: outsider/cohost không đọc công nợ khách offline user_id NULL (R1)` — FAIL trước sửa (outsider nhận JSON công nợ), PASS sau sửa; kèm negative control outsider đọc khách đã liên kết user và finance đọc khách offline.

## R2 — RPC bank cũ (BH-02) chưa gate `current`

- Vị trí quyết định: `supabase/migrations/20261016130000_bh06_reads.sql:2–5` + tuyên bố ở `docs/08_DOMAIN_CONTRACTS.md` (mục §13 "Đường đọc/QR"); endpoint `get_session_payment_instructions(UUID)` từ nền BH-02.
- Trước: RPC cũ trả `receiver_snapshot` mà không kiểm revision ⇒ caller lấy bank khi chưa chốt/stale rồi ghép số tiền đã cache, lọt gate §7.
- Sau: `20261016140000_bh06a_review_round1.sql` `CREATE OR REPLACE` RPC cũ với `PERFORM public.assert_billing_current(p_session_id)` — chưa chốt ⇒ `BILLING_NOT_FINALIZED`, stale ⇒ `BILLING_STALE`; giữ quyền tương thích (host/management/finance/confirmed player) và chỉ trả `session_id` + `receiver_snapshot`. Không dùng endpoint hướng dẫn thanh toán làm API history.
- Đồng bộ contract (docs/08 §13) và handoff; không sửa ba migration BH-06A đã chia sẻ.
- Test tái hiện: `Gate: RPC bank cũ và mới đều chặn not_finalized/stale (R2)` — FAIL trước sửa (RPC cũ trả snapshot khi chưa chốt), PASS sau sửa; kiểm cả đường cũ và mới.

## Bằng chứng (cây `83586ed` sạch)

- `flutter analyze --no-pub`: **0 issue**, exit 0.
- `flutter test --no-pub`: **137/137 PASS**, exit 0 (A không chạm Dart).
- `python docs/reviews/bh06/run_bh06_tests.py`: **84/84 PASS** (42 ca × CLEAN/LEGACY), exit 0, `tested_commit=83586edc829e75194e48fadcce4488750ee4f371`, `worktree_dirty=false` → [`bh06_test_results_20261016151610.json`](bh06_test_results_20261016151610.json). SHA256 migration mới `20261016140000_bh06a_review_round1.sql` = `22baea9065a7fbe4213685a2d2dae692fcf4d4334073edf2ec68297216187fae`.
- Hồi quy trên cùng cây (đều exit 0): BH-02 baseline **33/33** + extended **14/14**; BH-03 **48/48** + retry **22/22**; BH-04 **44/44**; BH-05 **90/90** — log lưu ở scratch, không thêm JSON vào repo để giữ cây sạch cho bằng chứng.

## NOT RUN / giới hạn

- PostgREST HTTP/JWT/Supabase Auth thật (chỉ PostgreSQL cô lập + Auth stub), apply staging/production, backup/restore, thiết bị/browser e2e, concurrency qua HTTP.
- UI/provider/repository BH-06B/C và phần lịch sử/công nợ sau complete (BH-07).
- Mọi repro dùng dữ liệu giả ở PostgreSQL local; tối đa 2 vòng sửa theo quy trình, đây là vòng 1.
