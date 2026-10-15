# Bàn giao BH-05 — Đăng ký / duyệt / huỷ / danh sách chờ

Ngày: 15/10/2026 · trạng thái: **ĐÃ TRIỂN KHAI (local/staging)**.
Baseline: `d8dfe74` (đã đạt 104 Flutter + 161 DB). Commit code BH-05: `814d85b`
(`feat(bh05): dieu hanh dang ky, duyet, diem danh va loi moi cho doi`).

## 1. Phạm vi đã làm

- Người chơi tự đăng ký buổi đã công bố: `host_approval` → `pending`; `auto_confirm` → `confirmed` nếu còn chỗ, hết chỗ → `waitlisted`. Một đăng ký mỗi người/buổi.
- Host/cohost thêm thành viên CLB theo **ID** (không tự khớp tên/SĐT) hoặc khách chưa có tài khoản (`host_recorded`, `user_id NULL`).
- Host/cohost duyệt (`confirmed`), đưa vào danh sách chờ (`waitlisted`), từ chối (`rejected`) theo quyền.
- Người chơi tự huỷ theo `cancellation_deadline`; host/quản lý huỷ theo quyền; huỷ thu hồi luôn lời mời `pending` trong cùng transaction.
- Điểm danh (`present`/`no_show`) chỉ khi `lifecycle='in_progress'` và chỉ với `confirmed`.
- Lời mời nhận chỗ: phát hành/thu hồi/chấp nhận, **không** giữ slot, đơn dùng một lần, kiểm lại người nhận/state/hết hạn/deadline/slot ở DB.

Nguyên tắc xuyên suốt: chỉ `confirmed` giữ chỗ và được xem thông tin thanh toán/QR; `pending`/`waitlisted` không giữ slot. Client **không** ghi bộ đếm/role/số dư/tác nhân audit; mọi mutation qua RPC bắt buộc `p_request_id`.

## 2. Thay đổi DB

Forward migration (không sửa lịch sử):
`supabase/migrations/20261015170500_bh05_registrations.sql`
SHA256 `356f5831649eb4d09efa624402679cce67211056ce44e09cf6088715970ac588`.

- 9 RPC: `request_join_session`, `add_session_player`, `decide_registration`, `cancel_registration`, `record_attendance`, `invite_waitlisted_player`, `revoke_waitlist_invitation`, `accept_waitlist_invitation`, `get_my_waitlist_invitation`.
- `list_session_players` `CREATE OR REPLACE` bổ sung `pending_invitation_id`, `pending_invitation_expires_at` (giữ nguyên grant cũ: chỉ management).
- Helper nội bộ `registration_result(...)`, `bump_billing_input_version(...)` bị `REVOKE` khỏi mọi role client.
- Mọi mutation: `SECURITY DEFINER`, `search_path = public, pg_temp`, `REVOKE PUBLIC/anon` + `GRANT authenticated`, idempotency theo actor/operation/request + hash canonical từ input ổn định, audit, `FOR UPDATE` khoá và kiểm lại lifecycle/deadline/quyền/state trong cùng transaction.

Chi tiết hợp đồng từng RPC: [08_DOMAIN_CONTRACTS.md §12](08_DOMAIN_CONTRACTS.md).

## 3. Thay đổi Flutter

- `lib/models/session.dart`: `SessionPlayer` thêm `pendingInvitationId`/`pendingInvitationExpiresAt`; model `WaitlistInvitation`, `RegistrationResult`.
- `lib/data/session_repository.dart`: 9 phương thức gọi RPC typed.
- `lib/providers/session_provider.dart`: `myInvitation` + `fetchMyInvitation`, `_runPlayerMutation` (chống nhấn lặp, **giữ** request key khi lỗi/timeout, **xoá key ngay khi server xác nhận rồi mới refresh** danh sách, chặn double-submit), 8 action public.
- `lib/screens/session_detail_screen.dart`: thay stub "BH-05" bằng thẻ trạng thái đăng ký của người chơi, danh sách host có hành động theo trạng thái, hộp thoại thêm người (khách/thành viên CLB, cờ danh sách chờ và miễn phí cần quyền tài chính). Loading/empty/error+retry/submitting; lỗi tải danh sách **không** bị hiển thị thành "chưa có người đăng ký".

Không thêm dependency (giữ Flutter + Provider + Supabase).

## 4. Kiểm thử

Môi trường: Windows, PostgreSQL trong Docker (`bh02-test-postgres`), Auth stub (đặt JWT claims mô phỏng). Không apply production.

| Bộ | Kết quả | Bằng chứng |
|---|---|---|
| Flutter analyze | 0 issue | — |
| Flutter test | **116/116 PASS** (104 regression + 12 mới: 7 provider, 5 widget) | `flutter test` |
| BH-02 RLS | 33/33 PASS | `docs/reviews/bh02/rls_test_results_20261015165133.json` |
| BH-02 extended | 14/14 PASS | `docs/reviews/bh02/extended_results_20261015165133.json` |
| BH-03 | 48/48 PASS | `docs/reviews/bh03/bh03_test_results_20261015165137.json` |
| BH-03 retry | 22/22 PASS | `docs/reviews/bh03/bh03_retry_results_20261015165137.json` |
| BH-04 | 44/44 PASS | `docs/reviews/bh04/bh04_test_results_20261015165149.json` |
| BH-05 | **66/66 PASS** (33 kịch bản × CLEAN + LEGACY) | `docs/reviews/bh05/bh05_test_results_20261015165159.json` |

Tổng DB: **227/227 PASS**. Tất cả evidence ghi `tested_commit = 814d85b4`, `worktree_dirty = true` (bản thân tệp JSON kết quả khi đó còn untracked; code đã commit ở `814d85b` trước khi chạy). Runner: `docs/reviews/bh05/run_bh05_tests.py` (dựng lại CLEAN + LEGACY từ chuỗi 7 migration).

### Kịch bản BH-05 đã phủ (33, chạy trên cả CLEAN và LEGACY)

ACL/idempotency (`anon` bị chặn; thiếu `request_id`; replay cùng key; cùng key khác payload → `IDEMPOTENCY_CONFLICT`); đăng ký (`pending` không chiếm slot, `confirmed`+`agreed_fee` fixed, `waitlisted` không vượt sức chứa, chặn trùng, đăng ký lại sau `cancelled` dùng lại `player_id`, chặn `draft`/quá hạn); duyệt (`waitlisted→confirmed` trực tiếp bị chặn, hết chỗ `CAPACITY_FULL`); thêm người (guest `user_id NULL`, giữ contact riêng; member ngoài CLB `INVALID_INPUT`; `fee_exempt` cần quyền tài chính); huỷ (đúng hạn, chặn người khác/quá hạn, người đã `present` cần quyền tài chính, thu hồi lời mời chờ cùng transaction); điểm danh (chỉ `in_progress`/`confirmed`, replay cùng kết quả); lời mời (không giữ slot, replay, chặn non-waitlisted, chặn `expires_at` ngoài biên, hết chỗ khi accept, giải phóng chỗ thì `confirmed`, accept lặp không thêm slot, sai người nhận `FORBIDDEN`, revoked/expired trả đúng mã, chặn revoke lời mời đã accepted); consent khách `host_recorded`; đọc (`get_my_waitlist_invitation` chỉ đúng người, người ngoài không duyệt/không đọc contact); **không** direct write trên `session_players`/`waitlist_invitations`; 2 kịch bản cạnh tranh (2 kết nối tranh slot cuối; 2 người duyệt cạnh tranh không vượt sức chứa).

Widget/provider test Flutter mới: đăng ký thành công, lời mời chờ → "Chấp nhận lời mời", tự huỷ khi `confirmed`, host duyệt `pending`, lỗi mutation → retry phục hồi; provider: gửi `request_id`, giữ key khi lỗi/xoay key sau thành công, chặn double-submit, tải lời mời, phản hồi đến muộn của phiên cũ không lộ state, đăng xuất xoá lời mời.

## 5. Không chạy / chưa kiểm chứng (NOT RUN)

- PostgREST **HTTP/JWT thật** với Supabase Auth: chưa chạy — PostgreSQL + Auth stub **không** chứng minh được xác thực token thật.
- Thiết bị thật / web thật, deep link OS-level: chưa chạy.
- Apply migration lên staging/production, diễn tập backup/restore: chưa chạy (không tự apply production).
- Cạnh tranh chỉ ở mức đa kết nối **trong cùng PostgreSQL** (deterministic bằng lock + `pg_sleep`), chưa qua HTTP đồng thời thực tế.

## 6. Việc còn lại trước pilot

1. Chạy full Supabase HTTP/JWT thật cho các RPC BH-05 (map lỗi PostgREST → thông điệp Việt đã có).
2. Diễn tập apply chuỗi migration + backup/restore trên staging thật.
3. Kiểm thủ công trên thiết bị/web: link chia sẻ `/sessions/:id`, quay lại sau đăng nhập, luồng lời mời qua nhiều người dùng thật.
4. Sau pilot mới xét các mục BH-08/BH-09/BH-10.

## 7. Điểm tiếp tục

Ticket kế tiếp: **BH-06** (chốt phí / VietQR / thu tiền) theo AG-06 trong [12_ANTIGRAVITY_PROMPTS.md](12_ANTIGRAVITY_PROMPTS.md). Giữ regression 116 Flutter + 227 DB. Các mục R2/R6/R7 trong [09_IMPLEMENTATION_PLAN.md](09_IMPLEMENTATION_PLAN.md) đã có bản triển khai local/staging, **chưa** đóng ở mức production.
