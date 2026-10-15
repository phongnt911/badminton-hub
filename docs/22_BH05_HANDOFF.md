# BH-05 — Đăng ký / duyệt / huỷ / danh sách chờ (bàn giao, nhánh tích hợp)

Ngày: 16/10/2026 (Việt Nam). Trạng thái: **CHỜ REVIEW** — A, B, C đã được gộp trên nhánh
`feat/bh05-integration` theo thứ tự A→B→C, đã giải xung đột và chạy lại toàn bộ regression.
Phần A và B đã được reviewer độc lập kết luận **Đạt**; phần C đang **chờ review** ở vòng sửa 2.
**Chưa** apply staging/production, **chưa** kiểm PostgREST HTTP/JWT thật.

Baseline: `d8dfe74` (đã đạt 104 Flutter + 161 DB). Hợp đồng RPC:
[08_DOMAIN_CONTRACTS.md](08_DOMAIN_CONTRACTS.md) §12. Người triển khai **không** tự ghi "Done";
trạng thái cao nhất trong lượt này là "Chờ review".

## 1. Phạm vi đã làm

- Người chơi tự đăng ký buổi đã công bố: `host_approval` → `pending`; `auto_confirm` → `confirmed` nếu còn chỗ, hết chỗ → `waitlisted`. Một đăng ký mỗi người/buổi.
- Host/cohost thêm thành viên CLB theo **ID** (không tự khớp tên/SĐT) hoặc khách chưa có tài khoản (`host_recorded`, `user_id NULL`).
- Host/cohost duyệt (`confirmed`), đưa vào danh sách chờ (`waitlisted`), từ chối (`rejected`) theo quyền.
- Người chơi tự huỷ theo `cancellation_deadline`; host/quản lý huỷ theo quyền; huỷ buổi thu hồi luôn lời mời `pending` trong cùng transaction.
- Điểm danh (`present`/`no_show`) chỉ khi `lifecycle='in_progress'` và chỉ với `confirmed`.
- Lời mời nhận chỗ: phát hành/thu hồi/chấp nhận, **không** giữ slot, đơn dùng một lần, kiểm lại người nhận/state/hết hạn/deadline/slot ở DB.
- UI màn chi tiết buổi: thẻ trạng thái đăng ký của người chơi, danh sách host có hành động theo trạng thái, hộp thoại thêm người (khách/thành viên CLB), loading/empty/error + retry, chống lỗi tải danh sách hiển thị thành "chưa có người đăng ký".

Nguyên tắc xuyên suốt: chỉ `confirmed` giữ chỗ và được xem thông tin thanh toán/QR; `pending`/`waitlisted` không giữ slot. Client **không** ghi bộ đếm/role/số dư/tác nhân audit; mọi mutation qua RPC bắt buộc `p_request_id`.

## 2. Nhánh, commit và quy trình hai AI

Theo quy trình hai AI trong `AGENTS.md`, BH-05 được tách phần A/B/C, mỗi phần một nhánh và **chờ review**; người triển khai không tự ghi "Done".

| Phần | Nhánh | Commit code | Kết luận review gần nhất | Bằng chứng |
|---|---|---|---|---|
| A — DB/RPC/RLS | `feat/bh05a-db` | `dae8763` | **Đạt** tại `9f2d455` | [review_9f2d455.md](reviews/bh05/review_9f2d455.md) |
| B — model/repository/provider | `feat/bh05b-data` | `33277ea` | **Đạt** tại `cf65199` | [review_cf65199.md](reviews/bh05/review_cf65199.md) |
| C — UI màn chi tiết buổi | `feat/bh05c-ui` | `7707a76` | **Chưa đạt** tại `48b4ad2`; đã sửa C1-R ở vòng 2, **chờ review** | [review_48b4ad2.md](reviews/bh05/review_48b4ad2.md) |

Nhánh tích hợp `feat/bh05-integration` (tách từ `main` = `da1285d`):

| Commit | Nội dung |
|---|---|
| `eecf24a` | Merge `feat/bh05a-db` (A). Xung đột: `docs/09`, `run_bh05_tests.py`. |
| `a0f5d35` | Merge `feat/bh05b-data` (B). Xung đột: `session_provider.dart`, `session_provider_test.dart`. |
| `b126f17` | Merge `feat/bh05c-ui` (C). Xung đột: `session_detail_screen.dart`, `session_detail_screen_test.dart`. |
| `3867c99`…`bae8bcd` | 6 commit bằng chứng (chỉ thêm JSON kết quả runner), giữ `worktree_dirty=false`. |

Mã nguồn tích hợp (lib/test/supabase) **trùng khít** cây C đã review: `git diff feat/bh05c-ui -- lib test supabase` rỗng.

## 3. Thay đổi DB

Forward migration (không sửa lịch sử), đo trên cây tích hợp:

- `supabase/migrations/20261015170500_bh05_registrations.sql` — SHA256 `2c63e2cb5cf98d7b7c1474ec09e7ada61bc0a6b67130b5776a8ca8f95aaade51`.
- `supabase/migrations/20261016090000_bh05_review_fixes.sql` (sửa A1/A2) — SHA256 `629a0cad48587fe7516f48962d4a5c44fac69c493fb1b1b0f1e42a535ef369a7`.
- `supabase/migrations/20261016091000_bh05_a3_cancel_revokes_invitations.sql` (sửa A3) — SHA256 `5981843750597ec54864bdf99e26a75d920dfb8c889bda0f6a748b60a09a0442`.

Nội dung:

- 9 RPC: `request_join_session`, `add_session_player`, `decide_registration`, `cancel_registration`, `record_attendance`, `invite_waitlisted_player`, `revoke_waitlist_invitation`, `accept_waitlist_invitation`, `get_my_waitlist_invitation`.
- `list_session_players` `CREATE OR REPLACE` bổ sung `pending_invitation_id`, `pending_invitation_expires_at` (giữ nguyên grant cũ: chỉ management).
- Helper nội bộ `registration_result(...)`, `bump_billing_input_version(...)` bị `REVOKE` khỏi mọi role client.
- Mọi mutation: `SECURITY DEFINER`, `search_path = public, pg_temp`, `REVOKE PUBLIC/anon` + `GRANT authenticated`, idempotency theo actor/operation/request + hash canonical ổn định, audit, `FOR UPDATE` khoá và kiểm lại lifecycle/deadline/quyền/state trong cùng transaction.

Chi tiết hợp đồng từng RPC: [08_DOMAIN_CONTRACTS.md §12](08_DOMAIN_CONTRACTS.md).

Ghi chú hash: bản handoff ngày 15/10 ghi `356f5831…` cho migration gốc; đó là hash của bản chuẩn hoá LF. Tệp trong repo dùng CRLF nên hash byte thực là `2c63e2cb…` (cùng nội dung).

## 4. Thay đổi Flutter

- `lib/models/session.dart`: `SessionPlayer` thêm `pendingInvitationId`/`pendingInvitationExpiresAt`; model `WaitlistInvitation`, `RegistrationResult`.
- `lib/data/session_repository.dart`: 9 phương thức gọi RPC typed.
- `lib/providers/session_provider.dart`: `myInvitation` + `fetchMyInvitation` với trạng thái riêng `isLoadingInvitation`/`invitationErrorMessage` + serial chống phản hồi trễ; `_runPlayerMutation` (chống nhấn lặp, **giữ** request key khi lỗi/timeout, **xoá key ngay khi server xác nhận rồi mới refresh**, chặn double-submit), 8 action public.
- `lib/providers/club_provider.dart`: API roster có scope cho dialog thêm người (`fetchClubRoster`/`rosterMembers`/`isLoadingRoster`/`rosterErrorMessage`/`clearClubRoster`, có serial) — không dùng `currentMembers` của CLB khác.
- `lib/screens/session_detail_screen.dart`: thay stub "BH-05" bằng thẻ trạng thái đăng ký của người chơi, danh sách host có hành động theo trạng thái, hộp thoại thêm người (khách/thành viên CLB, cờ danh sách chờ và miễn phí cần quyền tài chính); loading/empty/error+retry/submitting; tôn trọng loading/error lời mời của provider B.

Không thêm dependency (giữ Flutter + Provider + Supabase).

## 5. Giải quyết xung đột khi tích hợp

| Tệp | Cách giải | Lý do |
|---|---|---|
| `docs/09_IMPLEMENTATION_PLAN.md` | Giữ **cả** snapshot 15/10 của `main` và tường thuật A/B/C, theo thứ tự thời gian | Không xoá nội dung đã publish trên `main`; bổ sung phần hai-AI |
| `docs/reviews/bh05/run_bh05_tests.py` | Lấy bản nhánh A | Bản đầy đủ (42 kịch bản, gồm test tái hiện A1/A2/A3); B/C không đổi runner |
| `lib/providers/session_provider.dart`, `test/providers/session_provider_test.dart` | Lấy bản nhánh B | Bản đã sửa B1/B2; `git diff main -- <2 tệp>` chỉ còn đúng hunk sửa B |
| `lib/screens/session_detail_screen.dart`, `test/screens/session_detail_screen_test.dart` | Lấy bản nhánh C | Bản đã sửa C1/C2/C3/C1-R |
| `lib/providers/club_provider.dart`, `test/providers/club_provider_test.dart` | Auto-merge | C thuần bổ sung API roster có scope, không xung đột `main` |
| `supabase/migrations/*`, `docs/08`, `docs/22` | Auto-merge / giữ `main` | A chỉ thêm migration; `docs/08` §12 và `docs/22` chỉ có trên `main` |

Không có xung đột mã nguồn nào còn sót (không còn dấu `<<<<<<<`/`=======`/`>>>>>>>`). `git diff feat/bh05c-ui -- lib test supabase` rỗng ⇒ cây tích hợp = cây C đã review.

## 6. Acceptance — PASS/FAIL/NOT RUN

| Hạng mục BH-05 | Kết quả | Bằng chứng |
| --- | --- | --- |
| Tự đăng ký `host_approval`→`pending`, `auto_confirm`→`confirmed`/`waitlisted`, một đăng ký/người/buổi | PASS | `bh05_test_results_20261015185157.json` (nhóm đăng ký) |
| Thêm người theo ID (không khớp tên/SĐT) + khách `host_recorded` (`user_id NULL`) | PASS | nhóm `add_session_player` |
| Duyệt/từ chối/đưa vào danh sách chờ theo quyền; `waitlisted→confirmed` trực tiếp bị chặn | PASS | nhóm `decide_registration` |
| Huỷ theo `cancellation_deadline`; host huỷ theo quyền; huỷ buổi thu hồi lời mời `pending` | PASS | nhóm `cancel_registration`, A3 |
| Điểm danh chỉ khi `in_progress` + chỉ `confirmed`, replay cùng kết quả | PASS | nhóm `record_attendance` |
| Lời mời: phát hành/thu hồi/chấp nhận, không giữ slot, một lần, kiểm người nhận/state/hết hạn/deadline/slot | PASS | nhóm invitation |
| Chỉ `confirmed` xem được thông tin thanh toán/QR | PASS | ca `confirmed player gets payment instructions via RPC` / `pending player blocked` |
| Gate quyền tài chính sau khi chốt phí (A1) | PASS | test tái hiện A1 trong runner |
| `update_session` không hạ `capacity` dưới số `confirmed` (A2) | PASS | test tái hiện A2 trong runner |
| Không direct write `session_players`/`waitlist_invitations`; `anon` bị chặn; thiếu `request_id` bị chặn | PASS | nhóm ACL/idempotency |
| UI: trạng thái đăng ký/host action/điểm danh/dialog thêm người, loading/error+retry | PASS | `test/screens/session_detail_screen_test.dart` |
| UI: đang tải lại lời mời không cho chấp nhận bằng cache cũ (C1-R) | PASS | test widget "C1-R …" |
| PostgREST HTTP/JWT thật; thiết bị/browser e2e; apply staging/production | NOT RUN | chỉ PostgreSQL + Auth stub |

## 7. Kiểm thử và môi trường

- Flutter 3.47.6 (stable), `flutter analyze`: **No issues found**.
- `flutter test`: **132/132 PASS** (104 nền BH-04 + 28 mới của BH-05 A/B/C).
- PostgreSQL 17 trong container Docker cô lập `bh02-test-postgres`, Auth stub, dựng lại toàn chuỗi 9 migration trên cả DB clean và legacy:

| Bộ | Kết quả | Bằng chứng | `tested_commit` | `worktree_dirty` |
|---|---|---|---|---|
| BH-02 RLS | 33/33 PASS | `docs/reviews/bh02/rls_test_results_20261015185106.json` | `b126f17` | n/a (không ghi) |
| BH-02 extended | 14/14 PASS | `docs/reviews/bh02/extended_results_20261015185106.json` | `b126f17` | n/a (không ghi) |
| BH-03 | 48/48 PASS | `docs/reviews/bh03/bh03_test_results_20261015185119.json` | `153f72a` | false |
| BH-03 retry | 22/22 PASS | `docs/reviews/bh03/bh03_retry_results_20261015185119.json` | `153f72a` | false |
| BH-04 | 44/44 PASS | `docs/reviews/bh04/bh04_test_results_20261015185143.json` | `830dfbf` | false |
| BH-05 | 84/84 PASS (42 kịch bản × CLEAN + LEGACY) | `docs/reviews/bh05/bh05_test_results_20261015185157.json` | `0979bbe` | false |

Tổng DB: **245/245 PASS** (`tested_commit` khác nhau vì mỗi lần chạy commit ngay JSON bằng chứng để giữ cây sạch; các commit này **chỉ thêm** tệp JSON — `git diff b126f17 HEAD` xác nhận không đổi mã nguồn/migration, nên cây nguồn được kiểm thử là `b126f17`). Runner BH-05: `docs/reviews/bh05/run_bh05_tests.py`.

Widget/provider test Flutter mới: đăng ký thành công, lời mời chờ → "Chấp nhận lời mời", tự huỷ khi `confirmed`, host duyệt `pending`, lỗi mutation → retry phục hồi; provider: gửi `request_id`, giữ key khi lỗi/xoay key sau thành công, chặn double-submit, tải lời mời (loading/error/null-hợp-lệ/retry), phản hồi đến muộn của phiên cũ không lộ state, đăng xuất xoá lời mời; roster CLB có scope (tải/lỗi-thử lại/đổi CLB chống rò rỉ + phản hồi trễ); C1/C2/C3/C1-R.

## 8. Không chạy / chưa kiểm chứng (NOT RUN)

- PostgREST **HTTP/JWT thật** với Supabase Auth: chưa chạy — PostgreSQL + Auth stub **không** chứng minh được xác thực token thật.
- Thiết bị thật / web thật, deep link OS-level: chưa chạy.
- Apply migration lên staging/production, diễn tập backup/restore: chưa chạy (không tự apply production).
- Cạnh tranh chỉ ở mức đa kết nối **trong cùng PostgreSQL** (deterministic bằng lock + `pg_sleep`), chưa qua HTTP đồng thời thực tế.
- Chưa nghiệm thu **đồng thời** A/B/C bởi reviewer trên nhánh tích hợp; C còn **chờ review** vòng 2.
- Host thu hồi lời mời qua HTTP trong lúc client đang refresh: chưa kiểm.

## 9. Việc còn lại trước pilot

1. Reviewer độc lập kết luận nhánh `feat/bh05-integration` (và vòng 2 của C).
2. Chạy full Supabase HTTP/JWT thật cho các RPC BH-05 (map lỗi PostgREST → thông điệp Việt đã có).
3. Diễn tập apply chuỗi migration + backup/restore trên staging thật.
4. Kiểm thủ công trên thiết bị/web: link chia sẻ `/sessions/:id`, quay lại sau đăng nhập, luồng lời mời qua nhiều người dùng thật.
5. Sau pilot mới xét các mục BH-08/BH-09/BH-10.

## 10. Điểm tiếp tục

Ticket kế tiếp: **BH-06** (chốt phí / VietQR / thu tiền) theo AG-06 trong [12_ANTIGRAVITY_PROMPTS.md](12_ANTIGRAVITY_PROMPTS.md). Giữ regression 132 Flutter + 245 DB. Các mục R2/R6/R7 trong [09_IMPLEMENTATION_PLAN.md](09_IMPLEMENTATION_PLAN.md) đã có bản triển khai local/staging, **chưa** đóng ở mức production.

## Phụ lục — các vòng sửa review đã gộp

- A: A1 (gate quyền tài chính khi đổi tập `confirmed` sau khi chốt phí), A2 (`update_session` hạ `capacity` dưới số `confirmed`), A3 (huỷ buổi thu hồi lời mời `pending`) — migration `20261016090000`, `20261016091000`.
- B: B1 (lỗi tải lời mời bị nuốt thành "không có lời mời"), B2 (làm mới chi tiết vẫn giữ lời mời cũ) — `lib/providers/session_provider.dart`.
- C: C1 (UI bỏ qua loading/error lời mời), C2 (buổi đầy chặn đăng ký danh sách chờ), C3 (dialog thành viên dùng roster sai scope), C1-R (đang tải lại vẫn cho chấp nhận bằng cache cũ) — `lib/screens/session_detail_screen.dart`, `lib/providers/club_provider.dart`.

Lịch sử đầy đủ theo từng vòng: [docs/09_IMPLEMENTATION_PLAN.md](09_IMPLEMENTATION_PLAN.md) và [docs/reviews/bh05/](reviews/bh05/).
