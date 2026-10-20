# Rà soát tổng hợp BH-01 → BH-03

> **Hiện hành 20/10/2026:** Nội dung dưới là snapshot lịch sử; không dùng lỗi hoặc prompt cũ để triển khai lại ticket đã nghiệm thu. BH-06 Đạt tích hợp local tại `318bc52` ([review](reviews/bh06/review_318bc52.md)), đã merge vào main tại `e7f7627`; docs/ai đã có trên main (`eaeb209`). Baseline review: analyze sạch, 190 Flutter +335 DB, 7 tích hợp +3 nâng cấp +2 probe PASS. BH-07A **Đạt phần A local tại `4512c3a`** theo [review độc lập](reviews/bh07/review_4512c3a.md); B/C/D và pilot chưa nghiệm thu, không tự chuyển phần tiếp theo. Chưa nghiệm thu HTTP/JWT/Auth thật, thiết bị/ngân hàng thật, staging/production, backup/restore hoặc concurrency HTTP; merge code không phải deploy.

Ngày 15/10/2026. Tài liệu tổng hợp rà soát ba ticket BH-01 (Auth & cấu hình), BH-02 (Schema nền, migration và quyền) và BH-03 (CLB / thành viên / tài khoản nhận tiền) dưới ba góc nhìn: **Code Reviewer**, **Backend Architect** và **Software Architect**.

Đây là tài liệu rà soát, **không phải** tài liệu nghiệm thu. Kết luận "Done" trong `09_IMPLEMENTATION_PLAN.md` giữ nguyên làm lịch sử; tài liệu này bổ sung phát hiện mới và chỉ rõ phần chưa kiểm chứng.

- **Baseline rà soát (BH-03)**: `88dd247` — trạng thái trước khi khắc phục; xem thêm [review_88dd247](reviews/bh03/review_88dd247.md).
- **HEAD khi tổng hợp**: `a433349` (feat/fix: harden BH-03 consent, retries and auth-scoped state) — đã khắc phục một phần BH-03 theo [17_BH03_REMEDIATION.md](17_BH03_REMEDIATION.md). BH-01/BH-02 **không** thay đổi trong commit này.
- **Bằng chứng tôi tự chạy tại HEAD `a433349`** (ghi file timestamp mới, giữ baseline cũ):
  - `flutter analyze` → **No issues found**; `flutter test` → **61/61 passed**.
  - `docs/reviews/bh02/rls_test_results_20261015145918.json` — **33/33 PASS**.
  - `docs/reviews/bh02/extended_results_20261015145918.json` — **14/14 PASS**.
  - `docs/reviews/bh03/bh03_test_results_20261015145923.json` — **48/48 PASS** (24 ca × 2 DB clean/legacy).
  - `docs/reviews/bh03/bh03_retry_results_20261015145923.json` — **14/14 PASS**.
  - Tổng DB: **109/109 PASS**.
- **Chưa kiểm chứng**: PostgREST HTTP/JWT thật, Supabase local/staging, concurrency qua HTTP/PostgREST, apply production, thiết bị thật (deep link).

---

## 1. Tóm tắt điều hành

Ba ticket đã dựng được nền vững: auth email đầy đủ vòng lặp (login/signup/reset/logout/guard), schema v1.1 có RLS + projection + idempotency/audit, và lớp CLB dùng RPC nguyên tử có phân quyền chặt. Bộ kiểm thử DB hành vi (33 + 14 + 48 + 14 = **109 ca**) đều PASS khi tôi chạy lại độc lập tại HEAD, và Flutter sạch (analyze 0, 61/61).

Commit `a433349` đã đóng các lỗi nặng nhất của BH-03 (consent, race idempotency, vòng đời private state, request key, hash payload). **Điều còn lại không kém phần quan trọng**: rủi ro lớn nhất hiện **không** nằm ở các RPC đã sửa, mà ở **hai vùng giáp ranh chưa chạm tới**:

1. **Tồn tại hai mô hình dữ liệu song song.** Lớp demo cũ (`SupabaseService` + `SessionProvider` + màn Kèo/Sân) vẫn ghi trực tiếp bộ đếm/số dư client và dùng cột demo (`joined_count`, `estimated_cost`, `contact_phone`, `owner_phone`, `balance`, `type`). Trên DB sạch v1.1 các cột này không tồn tại và mọi direct write đã bị REVOKE ⇒ các màn này sẽ lỗi runtime, đồng thời vi phạm ADR cấm client ghi bộ đếm/số dư.
2. **Cấu hình mặc định trỏ production + script ghi production.** `AppConfig` hardcode URL/anon key production làm mặc định và `AppConfig.environment` không được dùng để chọn giá trị; `scripts/update_db.dart` POST thẳng lên project thật.

Bên cạnh đó, một số lỗi hợp đồng vẫn còn ở HEAD: phân trang `list_club_members` hỏng hoàn toàn (đã tái hiện), lỗi tải Thành viên/Tài khoản quỹ bị hiển thị thành empty state, và `list_my_clubs` thiếu field mà UI render.

### 1.1 Bảng phát hiện (trạng thái tại HEAD `a433349`)

| ID | Ticket | Mức | Tóm tắt | Tại HEAD `a433349` |
|---|---|---|---|---|
| **X1** | BH-02/03 | 🔴 P1 | Lớp demo (`SupabaseService`/`SessionProvider`) xung đột schema và ghi bộ đếm/số dư trực tiếp | **Còn mở tại baseline a433349** |
| **X2** | BH-01 | 🔴 P1 | Cấu hình mặc định = production; `environment` chết; script ghi production | **Còn mở tại baseline a433349** |
| **B3-A** | BH-03 | 🔴 P1 | `add_club_member` nhận `user_id` không consent (vi phạm hợp đồng) | ✅ Đã sửa (C1) |
| **B3-B** | BH-03 | 🔴 P1 | Logout không xóa state CLB ⇒ rò rỉ giữa các phiên | ✅ Đã sửa (C3) |
| **B3-C** | BH-03 | 🟡 P1 | Phân trang `list_club_members` hỏng: `limit` bị bỏ qua, `offset>0` trả NULL | **Còn mở tại baseline a433349** |
| **B3-D** | BH-03 | 🟡 P2 | Hash idempotency thiếu field ⇒ "khác payload" không bị chặn | ✅ Đã sửa (C5) |
| **B3-E** | BH-03 | 🟡 P2 | UI không truyền `request_id` ⇒ retry có thể tạo bản ghi kép | ✅ Đã sửa (C4) |
| **B3-F** | BH-03 | 🟡 P2 | Lỗi tải Thành viên/Tài khoản quỹ hiển thị thành empty state | **Còn mở tại baseline a433349** |
| **B3-G** | BH-03 | 🟡 P2 | `list_my_clubs` không trả `balance_vnd` nhưng UI render ⇒ nhánh chết + báo cáo sai | **Còn mở tại baseline a433349** |
| **B3-H** | BH-03 | 🟡 P2 | RPC `SECURITY DEFINER` giữ `EXECUTE` cho PUBLIC/anon | ✅ Một phần (mutation đã REVOKE; read RPC còn mặc định) |
| **B3-I** | BH-03 | 🟡 P2 | Dialog đổi vai trò âm thầm thất bại; `create_club` chưa chống race | ✅ Một phần (race đã sửa — C2; nửa UI còn mở) |
| **B1-A** | BH-01 | 🟡 P2 | `signUp` coi là đã đăng nhập dù chưa có session (email chưa confirm) | **Còn mở tại baseline a433349** |
| **B1-B** | BH-01 | 🟡 P2 | `AuthScreen._handleSuccess` không pop khi có `onSuccess` | **Còn mở tại baseline a433349** |
| **B1-C** | BH-01 | 🟡 P2 | `throw String` thay vì Exception; lộ chi tiết lỗi nội bộ | **Còn mở tại baseline a433349** |
| **B1-D** | BH-01 | 💭 P3 | Khớp lỗi bằng chuỗi message GoTrue; fallback tiếng Anh | **Còn mở tại baseline a433349** |
| **B2-A** | BH-02 | 🟡 P2 | Invariant clean vs legacy lệch (cột mới chỉ nullable trên nhánh upgrade) | **Còn mở tại baseline a433349** |
| **B2-B** | BH-02 | 🟡 P2 | Test cấu trúc `sqlContent.contains` thay thế test hành vi; có tên test sai mô tả | **Còn mở tại baseline a433349** |
| **B2-C** | BH-02 | 🟡 P2 | `get_session_public_detail` không kiểm `lifecycle` (draft vẫn đọc được theo ID) | **Còn mở tại baseline a433349** |
| **B2-D** | BH-02 | 💭 P3 | Chưa xác định migration đã apply ở môi trường nào; chưa có forward migration | **Còn mở tại baseline a433349** |

Mức: 🔴 chặn nghiệm thu/không nên phát hành · 🟡 nên sửa · 💭 tùy chọn. X1/X2 được điều chỉnh thành P1 chặn phát hành; không chặn triển khai BH-04. C1–C5 là mã lỗi trong [review_88dd247](reviews/bh03/review_88dd247.md), đã khắc phục theo [17_BH03_REMEDIATION.md](17_BH03_REMEDIATION.md).

---

## 2. BH-01 — Auth & cấu hình

### 2.1 Điểm tốt

- Repository tách bạch, inject `SupabaseClient` ⇒ test độc lập được, đúng hướng kiến trúc.
- Provider quản lý `isSubmitting` chống bấm trùng, lắng nghe `authStateChanges`, `dispose()` huỷ subscription — vòng đời đúng.
- `AuthGuard` + `requireAuth` cho phép cả hai kiểu bảo vệ (chặn cứng bằng widget, và mở màn hình login rồi quay lại) — phù hợp luồng "mở link trước/sau login" của BH-04.
- Dịch lỗi GoTrue sang tiếng Việt, có test cho các nhánh chính.
- Public read vẫn mở: AccountScreen hiển thị view khách + nút đăng nhập, có widget test xác nhận.

### 2.2 Phát hiện

**🔴 X2 — Cấu hình mặc định trỏ production, `environment` không có tác dụng** *(còn mở)*
`lib/core/app_config.dart:11-17`, `scripts/update_db.dart:5-6`, `scripts/supabase_client.dart:11-13`

**Why:** `_defaultSupabaseUrl`/`_defaultAnonKey` là project **production** (`vqelcjxljddxoyplgcvm`), và `environment` bị ghim `const AppEnvironment.dev` nhưng **không** được dùng để chọn URL/key. Nghĩa là mọi lần `flutter run`, mọi build dev/test và cả `main()` đều trỏ vào production trừ khi người dùng nhớ truyền `--dart-define`. `AGENTS.md` yêu cầu "không tự thay đổi Supabase production khi nhiệm vụ chỉ là viết code/tài liệu", và định nghĩa BH-01 nói rõ "không nối test production". `AppConfig.isTest` không được dùng ở đâu (dead code gây cảm giác an toàn giả). Anon key bản chất là khoá công khai nên không phải secret rò rỉ, nhưng `scripts/update_db.dart` **POST thẳng lên project thật** bằng anon key ⇒ đây là công cụ có thể ghi production ngoài kế hoạch release.

**Suggestion:**
- Bỏ default production; bắt buộc `--dart-define=SUPABASE_URL/...` (fail fast khi thiếu), hoặc dùng giá trị local/staging làm default.
- Đưa URL/key vào `.env`/`--dart-define` cho mọi môi trường; giữ chế độ "blocked" cho test.
- Chuyển `update_db.dart` sang script có xác nhận môi trường tường minh, hoặc chuyển các seed thành migration/SQL có version.

**🟡 B1-A — `signUp` đánh dấu đã đăng nhập khi chưa có session** *(còn mở)*
`lib/providers/auth_provider.dart:88`

**Why:** `_currentUser = res.user` được gán bất kể `res.session`. Với Supabase bật xác nhận email, `signUp` trả `user` nhưng `session == null`; khi đó `isAuthenticated` = true, `AuthGuard`/`requireAuth` cho qua, nhưng mọi RPC sau đó sẽ 401 vì chưa có JWT. Nút "đăng ký thành công" lại pop về màn trước như đã đăng nhập. (Không phải bypass bảo mật vì RLS phía server vẫn chặn — đây là lỗi trạng thái client.)

**Suggestion:** dùng `_currentUser = res.session?.user;` và xác định `isAuthenticated` theo session, không chỉ theo `user`.

**🟡 B1-B — Không pop sau khi đăng nhập khi có `onSuccess`** *(còn mở)*
`lib/screens/auth_screen.dart:59-71`, `lib/screens/account_screen.dart:16-26`

**Why:** `_handleSuccess()` chỉ gọi `widget.onSuccess!()` và **không** `pop`. Từ AccountScreen, `onSuccess` là callback rỗng ⇒ sau khi đăng nhập, AuthScreen vẫn nằm trên stack, người dùng phải tự back. Ba nhánh if/else thực chất chỉ có nhánh đầu khác biệt, gây khó hiểu.

**Suggestion:** sau khi gọi `onSuccess`, chủ động `Navigator.pop(true)` (kiểm tra `mounted`/`canPop`), và rút gọn logic nhánh.

**🟡 B1-C — `throw String` và lộ chi tiết lỗi nội bộ** *(còn mở)*
`lib/data/auth_repository.dart:44,62,76,89,100`

**Why:** Ném `String` phá vỡ type-safety (`catch (e) => e.toString()` vẫn "chạy", nhưng không phân loại được lỗi) và một số nhánh nhét `$e` (raw exception) vào thông điệp hiển thị cho người dùng ⇒ lộ thông tin kỹ thuật và trải nghiệm không đồng nhất. `flutter_lints` không bật `only_throw_errors` nên analyze không bắt.

**Suggestion:** định nghĩa exception riêng (hoặc `AuthFailure`), luôn `throw` object; thông điệp hiển thị tiếng Việt tách khỏi log kỹ thuật.

**💭 B1-D — Khớp lỗi bằng chuỗi GoTrue** (`auth_repository.dart:105-125`): phụ thuộc text message, dễ vỡ khi GoTrue đổi thông điệp/ngôn ngữ; fallback trả `e.message` tiếng Anh. Nên khớp theo `statusCode`/`code` nếu API cung cấp. **💭** `_buildAuthenticatedView(dynamic user)` (`account_screen.dart:197`) nên dùng type `User` để giữ type-safety. **💭** `test/widget_test.dart` tên là "App loads correctly smoke test" nhưng chỉ pump một `Text('Kèo Hôm Nay')` — không tải app thật, dễ gây hiểu nhầm về độ phủ.

### 2.3 Lỗ hổng test

- Không kiểm hành vi pop/`returnRoute` thực tế (chỉ kiểm `onSuccess` được gọi).
- Không kiểm `signUp` khi bắt buộc xác nhận email (session null).
- Không kiểm state sau `logout` ở tầng UI.

---

## 3. BH-02 — Schema nền, migration và quyền

### 3.1 Điểm tốt

- Migration versioned đơn file, 21 bảng, đủ RLS cho toàn bộ bảng nghiệp vụ, `REVOKE ALL ... FROM anon, authenticated` rồi GRANT tối thiểu ⇒ không còn public write.
- Projection tách khỏi bảng gốc: `public_session_summary` (whitelist, `security_barrier`) và RPC `get_session_public_detail`, `get_my_registration`, `get_session_payment_instructions`. Đây là cách sửa đúng cho F2/F3/F7/H1/H2 thay vì mở lại bảng gốc.
- Helper RLS là `SECURITY DEFINER` + `search_path` cố định để tránh đệ quy; helper ghi nội bộ (`check_idempotency`, `record_idempotency`, `log_audit_event`) đã bị REVOKE khỏi `PUBLIC, anon, authenticated`.
- Bất biến quan trọng có partial unique index: một owner active/CLB, một revision active/buổi, một invitation pending/player, một active bank/CLB, một payment gắn nguồn ledger.
- Tương thích legacy có xử lý thật: gỡ NOT NULL cột cũ + trigger đồng bộ + backfill SĐT sang `session_player_contacts`.
- Chuỗi 33 + 14 ca DB được tôi chạy lại **PASS 100%** trên cả DB sạch và DB upgrade.

### 3.2 Phát hiện (đều còn mở tại HEAD)

**🟡 B2-A — Invariant "clean" và "legacy upgrade" lệch nhau**
`supabase/migrations/20261015051808_init_schema_v1_1.sql:199-221` (sessions) và `:313-328` (session_players)

**Why:** Khối `CREATE TABLE` khai báo `host_user_id`, `venue_id`, `title`, `starts_at`, `ends_at`, `capacity`, `court_count` là `NOT NULL`, nhưng nhánh upgrade chỉ `ADD COLUMN IF NOT EXISTS ... DEFAULT/NULL`. Nghĩa là trên DB đã tồn tại, các cột đích này **nullable** ⇒ hai môi trường có bất biến khác nhau; dữ liệu rác có thể lọt ở môi trường production-like mà test "clean" không thấy. `review_15ef59b.md` (F4) đã nêu đúng vấn đề này nhưng remediation mới chỉ gỡ NOT NULL phía legacy, chưa đưa hai nhánh về cùng bất biến.

**Suggestion:** thêm giai đoạn backfill + `SET NOT NULL` có kiểm soát (đếm NULL trước, backfill có mapping, rồi siết ràng buộc), theo pattern expand–contract; ghi rõ trong ADR migration.

**🟡 B2-B — Test cấu trúc thay cho test hành vi, và có test đặt tên sai**
`test/schema/schema_v1_1_migration_test.dart:91-96`, `:153-195`

**Why:** 11 test dùng `sqlContent.contains(...)`; trong đó có check âm `visibility IN ('public', 'unlisted') OR` phải `isFalse` và so khớp SQL **theo đúng khoảng trắng/xuống dòng** (ví dụ khối policy H2). Các test này có thể pass khi quyền thiếu hoặc view trả sai, và dễ vỡ khi chỉ cần format lại SQL — đúng như chính review BH-02 (`code_review.md` mục "Test và tiêu chí hoàn thành") đã cảnh báo. Ngoài ra test mang tên "... Security Views & Projections với security_invoker = true" lại chấp nhận `public_session_summary` dùng `security_barrier` (không phải `security_invoker`) ⇒ mô tả sai. Điểm tích cực: đã có runner DB hành vi thật (`run_rls_tests.py`, `run_bh03_tests.py`) nên không phụ thuộc test cấu trúc.

**Suggestion:** giữ test cấu trúc ở mức "schema guard", đổi tên cho đúng, và chỉ ra rõ trong tài liệu rằng bằng chứng nghiệm thu là runner DB. Hạn chế assert theo whitespace.

**🟡 B2-C — Projection buổi chơi không kiểm `lifecycle`**
`supabase/migrations/20261015051808_init_schema_v1_1.sql:905-918`

**Why:** `get_session_public_detail` chỉ chặn khi `visibility = 'private'`. Buổi `lifecycle = 'draft'` với `visibility` public/unlisted vẫn đọc được đầy đủ theo ID. Trong khi `public_session_summary` lọc `lifecycle IN ('published','in_progress')` ⇒ hai hợp đồng đọc không nhất quán. Contract F2 yêu cầu "draft ... không bị scan"; mở theo ID có thể chấp nhận được cho luồng chia sẻ link, nhưng hiện chưa có quyết định rõ và không được test.

**Suggestion:** chốt contract (buổi draft chỉ host/management đọc được kể cả có ID), thêm điều kiện `lifecycle` tương ứng và test cho `draft`.

**💭 B2-D — Chưa xác định migration đã apply ở môi trường nào.** `docs/13` yêu cầu: nếu migration đã apply/shared thì phải dùng forward migration, không sửa lịch sử. Migration BH-03 remediation đã theo đúng hướng forward (`20261015140216_...`), nhưng `20261015051808_init_schema_v1_1.sql` vẫn chưa có ghi chú đã apply ở đâu. Nên ghi trạng thái apply rõ ràng trước khi sửa tiếp.

---

## 4. BH-03 — CLB, thành viên, tài khoản nhận tiền

### 4.1 Điểm tốt

- `create_club` tạo club + owner membership trong một transaction; partial unique index chốt "một owner".
- `set_club_member_role` chặn hạ quyền owner, chặn self-escalation, chặn cấp quyền quản trị cho member chưa liên kết.
- `set_club_bank_account` khoá `clubs FOR UPDATE` + partial unique index ⇒ serialize cập nhật, giữ lịch sử account cũ, số tài khoản kiểu TEXT giữ zero đầu.
- `get_club_detail` chỉ trả `balance_vnd` cho owner/treasurer; `list_club_members` chỉ lộ contact cho owner/host hoặc chính chủ (treasurer bị chặn) — khớp ma trận quyền.
- `ClubProvider` dọn state + guard `_currentClubId` chống response cũ ghi vào CLB mới; sau `a433349` còn gắn với vòng đời auth (listener + generation).
- 48/48 ca DB (24 × clean/legacy) + 14/14 retry/consent tôi chạy lại đều PASS.

### 4.2 Phát hiện — trạng thái tại HEAD `a433349`

**Các lỗi đã đóng bởi `a433349` (C1–C5):**

- **B3-A (C1) ✅** `add_club_member` giờ từ chối `p_user_id` khác NULL khi chưa có acceptance; guest tạo với `user_id = NULL`. Có 2 ca clean/legacy từ chối liên kết account có sẵn (`bh03_retry_results_20261015145923.json`). *(Trước đây tôi đã tái hiện owner uid(1) gắn được uid(3) — nay bị chặn.)*
- **B3-B (C3) ✅** `ClubProvider` đăng ký listener `AuthProvider` tại root; đổi user/logout clear private state và tăng generation, bỏ response phiên cũ. Có test cached list/pending list/member-bank response trễ/mutation trễ sau logout (`test/providers/club_session_retry_test.dart`).
- **B3-D (C5) ✅** 7 mutation hash JSONB array đầy đủ params (gồm `account_name`, `contact_note`), helper canonical mới.
- **B3-E (C4) ✅** Provider sinh UUID v4 theo ý intent, giữ qua retry; repository/RPC từ chối key thiếu.
- **B3-I (phần race, C2) ✅** `check_idempotency` khoá theo actor+operation+request trước side effect; có ca hai request đồng thời.

**Các lỗi còn mở tại HEAD:**

**🟡 B3-C — Phân trang `list_club_members` hỏng (đã tái hiện, chưa sửa)**
`supabase/migrations/20261015133247_bh03_clubs_and_members.sql:622-671`

**Why:** `LIMIT p_limit OFFSET p_offset` được áp lên **một dòng aggregate** (`jsonb_agg(...)` không `GROUP BY`), không lên từng member. Tôi đã tái hiện: club có 4 member, `list_club_members(club, 2, 0)` trả **4** phần tử (limit bị bỏ qua), `list_club_members(club, 1)` trả **NULL** (không phải `[]`) vì OFFSET bỏ dòng aggregate duy nhất. Hợp đồng yêu cầu "phân trang ổn định". `a433349` **không** định nghĩa lại hàm này, nên lỗi còn nguyên. Hiện latent vì repository luôn gọi offset 0 và UI không phân trang — nhưng API công khai đã sai.

**Suggestion:** đưa `ORDER BY` + `LIMIT/OFFSET` vào subquery rồi mới `jsonb_agg`, hoặc trả `jsonb_build_object('items', ..., 'next_offset', ...)`; thêm test với `offset > 0`.

**🟡 B3-F — Lỗi bị biến thành empty state (còn mở)**
`lib/screens/clubs_screen.dart` (không có `membersErrorMessage`/`bankErrorMessage` — `a433349` không đụng file này)

**Why:** Handoff §5: "Lỗi network ... hiển thị error+retry tiếng Việt; không biến thành empty." Tab Thành viên chỉ đọc `isLoadingMembers` rồi `members.isEmpty ? 'Chưa có thành viên nào.'`; Tab Tài khoản quỹ không đọc `bankErrorMessage`/`isLoadingBank`, nên khi RPC lỗi, owner/treasurer thấy "Chưa cấu hình tài khoản ngân hàng nhận quỹ" — một kết luận sai.

**Suggestion:** thêm nhánh error+retry và nhánh loading riêng cho cả hai tab.

**🟡 B3-G — `list_my_clubs` không trả `balance_vnd`; UI render nhánh chết; báo cáo sai (còn mở)**
`supabase/migrations/20261015133247_bh03_clubs_and_members.sql:876-887` vs `lib/screens/clubs_screen.dart:320-325`

**Why:** `_buildClubCard` có `if (club.canViewBalance && club.balanceVnd != null)` nhưng `list_my_clubs` không trả `balance_vnd` ⇒ luôn false. `docs/16` lại ghi "danh sách CLB kèm ... số dư quỹ đúng quyền" — không đúng. Cảnh báo kèm: nếu sau này thêm `balance_vnd` vào `list_my_clubs` mà không lọc owner/treasurer thì thành lỗi privacy.

**Suggestion:** bỏ nhánh balance ở card (quỹ chỉ ở màn chi tiết), hoặc thêm `balance_vnd` **có lọc role**; sửa lại mô tả trong `docs/16`.

**🟡 B3-H — `EXECUTE` mặc định cho PUBLIC/anon (đã sửa một phần)**
`supabase/migrations/20261015133247_bh03_clubs_and_members.sql:901-912`, `supabase/migrations/20261015140216_bh03_identity_retry_session_fixes.sql`

**Why/Status:** `a433349` đã `REVOKE EXECUTE ... FROM PUBLIC, anon` cho 8 mutation (`create_club`, `update_club`, `add_club_member`, `set_club_member_role`, `set_club_bank_account`, `set_host_bank_account`, `update_club_member_contact`, `check_idempotency`). Tuy nhiên **các RPC đọc** (`list_my_clubs`, `get_club_detail`, `list_club_members`) chưa thấy REVOKE ⇒ vẫn giữ `EXECUTE` mặc định cho PUBLIC (chúng tự kiểm `auth.uid()` bên trong nên chưa khai thác được, nhưng vẫn lệch least-privilege).

**Suggestion:** REVOKE PUBLIC/anon cho cả RPC đọc; ghi thành quy ước chung (ADR-11) để áp dụng cho mọi `SECURITY DEFINER`.

**🟡 B3-I (phần UI) — Dialog đổi vai trò âm thầm thất bại (còn mở)**
`lib/screens/clubs_screen.dart:878-925`

**Why:** Dialog pop **trước** khi `await setMemberRole` và không hiển thị lỗi ⇒ thất bại im lặng. `a433349` chỉ sửa phần race phía DB, không đụng UI này.

**Suggestion:** await trước, chỉ pop khi thành công, hiện `submitErrorMessage`.

**💭 Ghi chú thêm BH-03:** `set_club_member_role` không kiểm target `status='active'`; `update_club_member_contact` cho host sửa `display_name` của bản ghi owner; `set_host_bank_account` không ghi audit trong khi các mutation khác đều ghi; `Club.fromJson` dùng `?? ''` cho `id`/`name` bắt buộc (che payload hỏng); request key retry giữ trong bộ nhớ provider, không sống qua force-kill (đã ghi nhận trong `17_BH03_REMEDIATION.md`).

---

## 5. Góc nhìn Backend Architect — rủi ro xuyên hệ thống

### 🔴 X1 — Hai mô hình dữ liệu song song đang cùng tồn tại (còn mở)

`lib/data/supabase_service.dart`, `lib/providers/session_provider.dart`, `lib/screens/home_screen.dart`, `session_detail_screen.dart`, `venues_screen.dart`

**Why:** Đây là rủi ro kiến trúc lớn nhất và không thuộc riêng ticket nào:

- `SupabaseService.createSession` / `joinSession` ghi trực tiếp `joined_count`, `status` (**bộ đếm**) và `club_transactions` + `clubs.balance` (**số dư**) từ client. Đây chính là anti-pattern mà `04_LLM_RULES.md` và ADR cấm ("Không chữa bộ đếm bằng public UPDATE policy", "Client không ghi bộ đếm, số dư, role").
- `SupabaseService` dùng cột **demo không tồn tại trong schema v1.1 sạch**: `play_date`, `start_time`, `end_time`, `max_slots`, `joined_count`, `estimated_cost`, `contact_phone`, `status` (sessions) và `owner_phone`, `bank_account`, `balance` (clubs). Trên DB dựng từ migration v1.1, các màn "Kèo Hôm Nay"/"Sân Nha Trang"/chi tiết buổi sẽ lỗi (PostgREST 400 / column does not exist) và mọi write đã bị `REVOKE ALL ... FROM anon, authenticated`.
- `session_players.player_name`/`phone_number` là cột legacy; code mới đã chuyển sang `display_name` + `session_player_contacts`.

**Ảnh hưởng:** app ở trạng thái "nửa migration" — CLB đã đi theo RPC/typed model, buổi chơi vẫn đi theo đường demo. Không thể release pilot với hai nguồn sự thật.

**Suggestion (kiến trúc):**
- Chốt **một** đường ghi duy nhất: mọi mutation qua RPC `SECURITY DEFINER`; cấm client `insert/update` bảng nghiệp vụ.
- Trước khi BH-04 làm, **gỡ hoặc gate** lớp `SupabaseService`/`SessionProvider`: ẩn các màn dùng schema demo cho tới khi được thay bằng RPC mới, hoặc chuyển chúng sang đọc `public_session_summary` + `get_session_public_detail`.
- Ghi ADR (xem §6) để ràng buộc hướng đi và tránh tái phát.

### 🔴 X2 — Cấu hình production mặc định & công cụ ghi production (còn mở)

Trùng X2 tại mục 2.2; nêu ở đây vì đây là rủi ro vận hành chung cho cả ba ticket (dev/test/CI vô tình trỏ production).

### 🟡 X3 — ACL/least-privilege chưa nhất quán

Helper nội bộ và 8 mutation đã REVOKE/PUBLIC đúng, nhưng RPC đọc của BH-03 vẫn để EXECUTE mặc định cho PUBLIC/anon (B3-H). Nguyên tắc đề xuất: mọi `SECURITY DEFINER` phải `REVOKE ... FROM PUBLIC, anon` + `GRANT` tường minh; `search_path` cố định; kiểm quyền bên trong.

### 🟡 X4 — Concurrency & idempotency (đã cải thiện, còn khoảng trống)

- `create_club` TOCTOU đã được sửa (C2) và có ca hai request đồng thời; hash đầy đủ (C5); UI dùng `request_id` (C4).
- Còn lại: các ca "concurrent" dùng trigger test-only trì hoãn tại INSERT — tốt hơn tuần tự, và thực tế chạy hai tiến trình psql, mỗi tiến trình mở một kết nối độc lập; và mutation khác ngoài `create_club` (ví dụ hai `set_club_bank_account` song song) chưa có ca đa kết nối.

**Suggestion:** thêm ca hai `psql`/connection thật cho bank/role; quy chuẩn "mọi mutation có `request_id` + hash toàn bộ payload + khoá chống race".

### 🟡 X5 — An toàn migration & tiến hoá dữ liệu

- Invariant clean/legacy lệch (B2-A); `20261015051808` chưa ghi trạng thái apply (B2-D).
- Điểm tích cực: BH-03 remediation đã dùng **forward migration** (`20261015140216_...`) thay vì sửa file đã chia sẻ — đúng quy trình.
- BH-03 yêu cầu "dữ liệu cũ cần ownership reconciliation" cho clubs; chưa thấy cơ chế/đối chiếu nào cho dữ liệu club legacy.

**Suggestion:** theo expand–contract: (1) thêm cột/backfill có đối chiếu, (2) dual-read nếu cần, (3) siết ràng buộc, (4) mới gỡ cột cũ. Ghi rõ migration nào đã apply ở đâu.

### 🟡 X6 — Hợp đồng lỗi & khả năng quan sát

- Client hiển thị `$e` thô (`club_provider.dart`, `auth_provider.dart`) ⇒ vừa lộ chi tiết Postgres vừa trải nghiệm không đồng nhất.
- Không có mã lỗi ổn định (đang trả chuỗi `FORBIDDEN:`, `UNAUTHENTICATED:`... tốt cho người đọc nhưng chưa chuẩn hoá cho client/analytics).
- Toàn bộ "observability" là `debugPrint` trong `SessionProvider`; không có request id tương quan, không có SLO/metric.

**Suggestion:** chuẩn hoá `{code, message_vi}`; log có `request_id`/`actor`; map lỗi ở biên UI.

### 🟡 X7 — Hợp đồng đọc & phân trang

`list_club_members` hỏng phân trang (B3-C); `list_my_clubs` thiếu field mà UI trông đợi (B3-G). Giữ hợp đồng JSON array hiện có, sửa LIMIT/OFFSET và thứ tự ổn định; chưa cần chuyển sang cursor cho pilot.

---

## 6. Góc nhìn Software Architect — biên giới, phụ thuộc, ADR

### 6.1 Bối cảnh & biên giới hiện tại

Hệ thống hiện có **ba lớp truy cập dữ liệu** chồng lấn:

| Lớp | Ví dụ | Cách vào dữ liệu | Vấn đề |
|---|---|---|---|
| Demo (cũ) | `SupabaseService` | `from(...).insert/update` trực tiếp | Vi phạm schema v1.1, ghi bộ đếm/số dư |
| Demo provider | `SessionProvider` | bọc lớp demo, `Map<String,dynamic>` | Không typed, `debugPrint` nuốt lỗi |
| Mới (đích) | `ClubRepository`/`ClubProvider` | RPC + model typed | Đúng hướng, còn khoảng trống ở mục 4 |

Định hướng phụ thuộc mong muốn: `UI → Provider → Repository → Supabase (RPC)`, **không** cho UI/Provider ghi thẳng bảng. BH-03 đã đúng hướng; lớp demo là nợ kiến trúc cần xoá.

**Bounded context đề xuất** (khớp schema hiện có): Auth/Identity · Club & Membership · Session & Scheduling · Registration & Waitlist · Finance/Ledger · Outreach. BH-02/BH-03 đã đặt nền Club & Membership và một phần Finance (ledger read-only). Không cần microservice/backend mới — modular monolith + Supabase đủ cho MVP này.

### 6.2 ADR đề xuất (chưa chốt)

| ADR | Quyết định | Lý do | Hệ quả |
|---|---|---|---|
| **ADR-10** | Loại bỏ dần `SupabaseService`/`SessionProvider`; mọi mutation qua RPC; cấm client ghi bộ đếm/số dư/role | X1, ADR/rule hiện có | Cần gating màn demo; BH-04 thay thế |
| **ADR-11** | Quy ước ACL cho `SECURITY DEFINER`: REVOKE PUBLIC/anon + GRANT tường minh + `search_path` cố định + kiểm quyền trong hàm | X3, B3-H | Đồng nhất bảo mật, dễ lint/kiểm tự động |
| **ADR-12** | Hợp đồng lỗi thống nhất `{code, message_vi}`; không lộ chi tiết DB | X6, B1-C | Đổi ở tầng repository/provider |
| **ADR-13** | Cấu hình môi trường bắt buộc qua `--dart-define`/`.env`; không default production; test bị cô lập | X2 | CI/dev an toàn hơn |
| **ADR-14** | Idempotency bắt buộc mọi mutation; hash toàn bộ payload; khoá chống race; UI giữ `request_id` khi retry | X4, B3-D/E/I | Đã có mẫu ở `a433349`; chuẩn hoá cho RPC sau |
| **ADR-15** | Read contract chuẩn: Giữ JSON array + LIMIT/OFFSET ổn định cho pilot | X7, B3-C | Sửa `list_club_members`, thống nhất list API |

### 6.3 Đường tiến hoá đề xuất

1. **Trước BH-04**: gate/gỡ lớp demo (X1); chốt ADR-10/13; sửa B3-C/B3-F/B3-G/B3-H và X2.
2. **BH-04**: thay màn buổi chơi demo bằng RPC (create/edit/publish) + projection whitelist — không tái sử dụng `joined_count`.
3. **BH-05**: registration/waitlist RPC nguyên tử (đã có bảng nền), không mở public UPDATE counter.
4. **BH-06**: ledger mutation (thu/chi) qua RPC; `club_balance` chỉ đọc.
5. Trước pilot: kiểm Supabase local/staging thật (PostgREST/JWT) và rehearsal migration/backup (cổng trong `09`).

---

## 7. Kế hoạch hành động

### Đã xong tại `a433349`
- ~~B3-A (C1)~~, ~~B3-B (C3)~~, ~~B3-D (C5)~~, ~~B3-E (C4)~~, ~~B3-I race (C2)~~ — có forward migration + regression tests.

### P1 — chặn phát hành
1. **X1**: gate/gỡ lớp `SupabaseService`/`SessionProvider`; ẩn các màn dùng schema demo tới khi thay bằng RPC. *(bắt buộc nếu không muốn ship app "nửa migration")*
2. **X2**: bỏ default production; bắt buộc cấu hình môi trường; xử lý `scripts/update_db.dart`.

### P1 — sửa hợp đồng còn hở
3. **B3-C**: sửa phân trang `list_club_members` + test `offset>0`. *(đã tái hiện, còn nguyên tại HEAD)*
4. **B3-F**: error+retry cho tab Thành viên/Tài khoản quỹ.
5. **B3-G**: đồng bộ `list_my_clubs` với UI (hoặc bỏ nhánh chết); sửa mô tả `docs/16`.

### P2 — hoàn thiện chất lượng
6. **B3-H**: REVOKE PUBLIC/anon cho RPC đọc; chốt ADR-11.
7. **B3-I (UI)**: dialog đổi vai trò hiển thị lỗi, chỉ pop khi thành công.
8. **B1-A/B/C**: session khi chưa confirm; pop sau login; exception typed.
9. **B2-A/C**: siết invariant nhánh legacy; chốt contract `lifecycle` cho projection buổi.
10. **B2-B**: chỉnh tên/gia cố test schema; nêu rõ bằng chứng nghiệm thu là runner DB.
11. Chốt ADR-12/13/14/15; ghi trạng thái apply migration (B2-D).

---

## 8. Ma trận truy vết nghiệm thu

| Nhóm | Ticket | Kết quả | Ghi chú |
|---|---|---|---|
| Auth login/signup/reset/logout, callback | BH-01 | **PASS (một phần)** | Unit/widget test OK; deep link thiết bị thật + PostgREST/JWT = NOT RUN |
| Auth state/guard | BH-01 | **PASS (một phần)** | Thiếu ca session-null khi cần confirm (B1-A) |
| Public read vẫn mở | BH-01 | **PASS** | Widget test xác nhận |
| Migration dựng DB sạch | BH-02 | **PASS** | 33/33 chạy lại độc lập |
| Upgrade legacy + tương thích | BH-02 | **PASS (một phần)** | 14/14 PASS, nhưng invariant clean/legacy lệch (B2-A) |
| A không đọc/sửa B, anon không ghi | BH-02 | **PASS** | Có ca DB hành vi |
| Contact/receiver private | BH-02 | **PASS** | F7/H2 đã đóng |
| Finance vẫn thấy tiền | BH-02 | **PASS** | H1 đã đóng (14/14) |
| Supabase local/staging thật (HTTP/JWT) | BH-02 | **NOT RUN** | Cổng chưa đóng |
| create_club atomic + concurrent | BH-03 | **PASS** | C2: hai request đồng thời cùng key → một club |
| Owner không bị hạ quyền; self-escalation chặn | BH-03 | **PASS** | |
| Account identity: user_id không consent bị từ chối | BH-03 | **PASS** | C1 đã đóng (2 ca clean/legacy) |
| Bank private/one active/leading zeros | BH-03 | **PASS** | |
| Quỹ read đúng quyền | BH-03 | **PASS** | |
| Retry giữ request key | BH-03 | **PASS** | C4 đã đóng |
| Logout clear | BH-03 | **PASS** | C3 đã đóng |
| UI state: loading/empty/error/submitting | BH-03 | **FAIL (một phần)** | B3-F còn mở |
| Phân trang danh sách (offset>0) | BH-03 | **FAIL** | B3-C còn mở, đã tái hiện |
| Danh sách CLB kèm số dư đúng quyền | BH-03 | **FAIL** | B3-G: field không tồn tại trong payload |
| Regression BH-02 | BH-03 | **PASS** | 47/47 chạy lại độc lập |

---

## 9. Việc chưa kiểm chứng / giới hạn

- Các runner DB dùng **Auth stub tối thiểu** (`auth.uid()` từ GUC), không phải PostgREST/JWT thật; ACL mặc định function trong PostgreSQL local có thể khác Supabase live.
- Ca concurrency của `a433349` dùng hai tiến trình psql/kết nối độc lập; trigger test-only trì hoãn INSERT để tăng thời gian chồng lấn. Chưa kiểm HTTP/PostgREST.
- Không test trên thiết bị di động thật (deep link); chưa apply production; chưa rehearsal migration/backup.
- Tôi **không** sửa code/migration trong lượt này; chỉ đọc, chạy lại test, dọn evidence cũ, và tạo tài liệu này.

## 10. Phụ lục — lệnh đã chạy

```powershell
flutter analyze                 # No issues found
flutter test                    # 61/61 passed
$env:BH02_TEST_CONTAINER='bh02-test-postgres'
python docs/reviews/bh02/run_rls_tests.py          # 33/33 PASS -> rls_test_results_20261015145918.json
python docs/reviews/bh02/extended_tests_15ef59b.py # 14/14 PASS -> extended_results_20261015145918.json
python docs/reviews/bh03/run_bh03_tests.py         # 48/48 PASS -> bh03_test_results_20261015145923.json
python docs/reviews/bh03/run_bh03_retry_tests.py   # 14/14 PASS -> bh03_retry_results_20261015145923.json
```

Tái hiện B3-C (phân trang, còn mở tại HEAD) bằng psql trên container `bh02-test-postgres`, DB `bh03_clean_<ts>`:

```
-- owner tạo club + 4 member:
list_club_members(club, 2, 0) -> 4 phần tử   (đáng lẽ 2)
list_club_members(club, 2, 1) -> NULL        (đáng lẽ 2 phần tử còn lại)
```

Tái hiện B3-A (đã đóng bởi C1 — ghi lại để đối chiếu): trước `a433349`, owner uid(1) gắn được uid(3) không consent và RPC thành công; sau `a433349` cùng thao tác bị từ chối.

## 11. Cập nhật sau đợt sửa trước BH-04

Xem [19_PRE_BH04_HANDOFF.md](19_PRE_BH04_HANDOFF.md) để biết trạng thái mới nhất. Các mục phía trên là snapshot a433349, không phải danh sách lỗi hiện tại.

- X2: bỏ production mặc định, cấu hình APP_ENV/URL/key bắt buộc; seed chỉ local.
- B1-A/B: đăng ký chưa có session không authenticated/không đóng màn; login có callback quay lại route trước.
- B3-C: forward migration phân trang trước aggregate, tie-break bằng ID; không đổi định dạng response.
- B3-F/I UI: loading/error/retry cho member/bank, đổi role chỉ đóng khi thành công và chặn bấm lặp.
- B3-G: bỏ số dư trên card danh sách; giữ số dư đúng quyền tại chi tiết.
- B3-H: thu hồi PUBLIC/anon với ba RPC đọc CLB, authenticated vẫn phải qua kiểm quyền bên trong. Đây là gia cố least-privilege, chưa có bằng chứng rò rỉ từ ACL cũ.
- X1 còn mở, thuộc chuyển đổi màn buổi chơi BH-04; chặn pilot trước khi chuyển đổi xong.
- Không apply production; Supabase HTTP/JWT và thiết bị thật chưa kiểm chứng.
