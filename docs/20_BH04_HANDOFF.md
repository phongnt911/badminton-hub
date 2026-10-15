# BH-04 — Buổi chơi, lịch và chia sẻ link (bàn giao)

Trạng thái: **ĐÃ TRIỂN KHAI LOCAL/STAGING** (chưa apply production, chưa kiểm PostgREST HTTP/JWT thật).
Tiếp theo: BH-05 (đăng ký và lời mời). Chi tiết hợp đồng RPC: [08_DOMAIN_CONTRACTS.md](08_DOMAIN_CONTRACTS.md) §11.

## 1. Phạm vi đã làm

- Thay đường demo buổi chơi (`SupabaseService`/`SessionProvider` cũ) bằng lớp typed: model/repository/provider + RPC.
- X1 (chặn pilot) được đóng một phần: xoá `lib/data/supabase_service.dart` (ghi `joined_count`/`balance` trực tiếp) và các cột demo; thêm `VenueRepository` typed cho sân.
- Migration forward-only mới, không sửa migration đã chia sẻ, không tự đổi DB production.

## 2. Quyết định routing (dựa trên code hiện có)

- Code hiện tại dùng `Navigator`/`MaterialPageRoute`, bottom-bar trong `lib/main.dart`; **không** có router package và `AuthScreen.returnRoute` đã khai báo nhưng chưa dùng.
- Theo docs/09/PD-01 ("chưa thêm SDK map/router tự động"), **không** thêm `go_router`/`app_links`. Thay vào đó:
  - `lib/core/app_routes.dart`: parse/kiểm hợp lệ link tài nguyên `/sessions/:id` (và `/clubs/:id`): allowlist scheme (`https`/`http`) + host (`badminton-hub.app`, `app.badminton-hub.vn`) + path, UUID bắt buộc, query chỉ nhận `src`/`invite` (từ chối `token`/`access_token`).
  - `sessionPath(id)` sinh link nội bộ; `AuthScreen.returnRoute` nhận `/sessions/<id>` để sau đăng nhập quay lại đúng buổi.
- **NOT RUN**: deep link cấp hệ điều hành (App Links/Universal Links) cần tên miền sở hữu + cấu hình platform association + SDK riêng — chưa bật trong lượt này (đúng giới hạn docs/09 PD-01).

## 3. File đã sửa/thêm

DB:
- `supabase/migrations/20261015163000_bh04_sessions.sql` (mới; SHA256 `489f13e230949ac398cf0ffb32c91c4b3bdd91303f3a7b957d228920094479b2`).

Flutter (mới):
- `lib/core/time_utils.dart` (UTC ↔ Asia/Ho_Chi_Minh +07), `lib/core/domain_error.dart` (ánh xạ mã lỗi → tiếng Việt, không lộ chi tiết DB), `lib/core/app_routes.dart`.
- `lib/models/session.dart` (Session, SessionRegistration, SessionPlayer, SessionFilter), `lib/models/venue.dart`.
- `lib/data/session_repository.dart`, `lib/data/venue_repository.dart`.
- `lib/screens/public_sessions_screen.dart`, `lib/screens/session_form_screen.dart`.

Flutter (viết lại):
- `lib/providers/session_provider.dart` (typed, auth-scoped, generation guard, request key qua retry).
- `lib/screens/home_screen.dart` (tab "Buổi chơi": buổi tôi quản lý + lối vào khám phá), `lib/screens/session_detail_screen.dart` (projection + quản lý + return-after-login), `lib/screens/venues_screen.dart` (dùng `VenueRepository`), `lib/main.dart` (SessionProvider gắn auth, đổi nhãn tab).
- Xoá: `lib/data/supabase_service.dart`.

Test:
- `test/core/app_routes_test.dart`, `test/models/session_test.dart`, `test/providers/session_provider_test.dart`, `test/screens/session_detail_screen_test.dart`, `test/screens/sessions_screen_test.dart`.
- `docs/reviews/bh04/run_bh04_tests.py` + `docs/reviews/bh04/bh04_test_results_20261015160911.json`.

## 4. Acceptance — PASS/FAIL/NOT RUN

| Hạng mục BH-04 | Kết quả | Bằng chứng |
| --- | --- | --- |
| create/edit/duplicate/publish qua RPC, có quyền + transaction | PASS | `bh04_test_results_20261015160911.json`: tạo draft, update version, publish, duplicate |
| Ngày tương lai + validate | PASS | ca `create_session từ chối thời gian bắt đầu trong quá khứ`, `ends_at <= starts_at`, `fee_mode=fixed thiếu phí` |
| Qua nửa đêm | PASS | `time_utils` xử lý `ends_at` ngày kế tiếp; schema chỉ ràng buộc `ends_at > starts_at` |
| Version conflict | PASS | ca `update_session ... VERSION_CONFLICT` |
| Duplicate không sao chép người/tiền | PASS | ca `duplicate_session ... không sao chép người/tiền` (0 player, 0 charge) |
| Link mở đúng ID trước/sau login | PASS (nội bộ) | `app_routes_test.dart` + `session_detail_screen_test.dart` (returnRoute `/sessions/s1`) |
| Public/unlisted chỉ qua projection whitelist | PASS | ca `get_session_public_detail: host đọc được draft, whitelist sạch` (không có `receiver_snapshot`/`host_user_id`) |
| draft/private cần quyền | PASS | ca `draft ẩn với anon`, `private chỉ thành viên/host` |
| Phân trang/empty/error | PASS | `list_my_sessions` offset>0 trả phần còn lại; provider error → retry phục hồi |
| Không ghi bộ đếm/số dư/role từ client | PASS | REVOKE ghi trực tiếp + RPC; DB clean không còn cột `joined_count` |
| Deep link OS-level (App Links) | NOT RUN | cần tên miền + cấu hình platform (ngoài phạm vi) |

## 5. Kiểm thử và môi trường

- Flutter 3.47.6 (stable), `flutter analyze`: **No issues found**.
- `flutter test`: **101/101 PASS** = 66 regression (giữ nguyên) + 35 mới BH-04.
- PostgreSQL 17 trong container Docker cô lập `bh02-test-postgres`, auth stub, chạy toàn chuỗi migration trên cả DB clean và legacy:
  - BH-02 baseline 33/33 (`rls_test_results_20261015160855.json`).
  - BH-02 extended 14/14 (`extended_tests_15ef59b.py`).
  - BH-03 48/48 (`bh03_test_results_20261015160859.json`).
  - BH-03 retry 22/22 (`bh03_retry_results_20261015160859.json`).
  - BH-04 42/42 (`bh04_test_results_20261015160911.json`) = 21 ca × 2 DB.
  - **Tổng 159/159 PASS**; regression trước BH-04 117/117 được giữ nguyên.
- Commit nền khi kiểm thử: `c27865d` (working tree có thay đổi BH-04 chưa commit → `worktree_dirty=true` trong JSON).

## 6. Giới hạn (chưa kiểm chứng)

- Chưa kiểm PostgREST HTTP/JWT thật; chỉ psql + `auth.uid()` stub.
- Chưa kiểm concurrency đa kết nối qua HTTP; `check_idempotency` dùng `pg_advisory_xact_lock` như BH-03.
- QR thanh toán thật, phí/ledger, đăng ký/điểm danh thuộc BH-05/06 (màn hình hiện chỉ ghi chú "sẽ có ở BH-05").
- **Chưa apply migration lên production.**

## 7. Prompt phiên tiếp theo (BH-05)

Đọc `docs/12_ANTIGRAVITY_PROMPTS.md` AG-05 và `docs/08_DOMAIN_CONTRACTS.md` §3/§7. Triển khai `request_join_session`/`add_session_player`/`decide_registration`/`cancel_registration`/invitation (issue/accept có expiry, đúng player, guest host_recorded consent) bằng RPC transaction + UI, không dùng `currentJoined` từ client, không coi UPDATE 0 hàng là thành công, RPC trả ID/state/version. Giữ regression 101 Flutter + 159 DB; thêm ca BH-05. Không đổi routing đã chốt ở BH-04.
