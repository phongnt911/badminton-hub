# Backlog triển khai và nghiệm thu

Trạng thái khởi đầu: mọi ticket dưới đây **chưa triển khai theo đặc tả v1.1**. Code demo có sẵn được tận dụng sau khi đối chiếu. Mỗi ticket cần commit riêng hoặc nhóm thay đổi có liên quan; không triển khai toàn bộ app trong một prompt.

## Thứ tự và phụ thuộc

BH-01 → BH-02 → BH-03 → BH-04 → BH-05 → BH-06 → BH-07. BH-08/BH-09 sau pilot. BH-02 dựng nền schema/RLS và các kiểm tra quyền; RPC chi tiết hoàn thiện theo từng ticket, không gọi function chưa tồn tại từ UI.

| Ticket | Phạm vi | Đầu ra / nghiệm thu |
|---|---|---|
| BH-01 | Auth và cấu hình | Email login/signup/reset/logout, callback đúng môi trường; auth provider/repository, route return; analyze + test auth state/guard; public read vẫn mở được; không nối test production |
| BH-02 | Schema nền, migrations và quyền | Từ điển 03_DATABASE được ánh xạ thành migration versioned, RLS/projection/helpers/idempotency/audit; dựng DB local/staging từ đầu; A không đọc/sửa B; anonymous không ghi; không chạy legacy SQL |
| BH-03 | CLB/thành viên/ngân hàng | Tạo club+owner atomic, member không account, role/contact private, config receiver; owner cấp quyền nhưng member không tự nâng quyền; dữ liệu cũ cần ownership reconciliation |
| BH-04 | Buổi/lịch/chia sẻ | Create/edit/duplicate/publish; ngày tương lai, qua nửa đêm, version conflict; link mở đúng ID trước/sau login; duplicate không sao chép người/tiền; phân trang/empty/error |
| BH-05 | Đăng ký/duyệt/hủy/điểm danh | DB RPC và UI; slot cuối 2 người tối đa 1 confirmed; retry không trùng; member cố định vẫn đăng ký từng buổi; guest host-added; contact không lộ; cancel deadline và capacity bảo vệ |
| BH-06 | Phí/thu tiền/quỹ | Expenses/revision/charges/payment/ledger atomic; QR thật, cash/transfer manual confirmation; phân dư chính xác, n=0 lỗi đúng; thu nhiều lần không dư; refinalize/đảo không trùng; quyền finance |
| BH-07 | Buổi hoàn chỉnh và pilot | start/complete/lịch sử, công nợ còn sau complete; sao chép tổng kết; test end-to-end trên mobile/web, mất mạng, mở lại app; tài liệu vận hành/migration/backup có kết quả rehearsal |
| BH-08 | Xoay tua và trận | Từ present, gợi ý → bắt đầu → kết thúc; nhiều sân không trùng người; số trận tăng sau finish; lưu server, override host; test thuật toán thực |
| BH-09 | Kèo giao lưu | Gắn match và participant IDs, vật phẩm/số lượng tự nguyện, kết quả versioned/hoàn tác; không trộn quỹ; tách bảng điểm phong trào và quy tắc giải chính thức |

## Checklist mỗi ticket

1. Đọc yêu cầu/contract, xem code và schema có thật, nêu phạm vi/file cần sửa.
2. Viết code/migration hoàn chỉnh và tests kiểm chứng hành vi có rủi ro.
3. Chạy flutter analyze/tests liên quan; nếu đổi DB, DB quyền/RPC/transaction tests tại local/staging.
4. Thử các trạng thái loading/error/empty/submitting và dữ liệu của user khác.
5. Ghi kết quả/lệnh/giới hạn, cập nhật trạng thái trong phần nhật ký dưới đây.
6. Commit/push khi được yêu cầu; tách deploy production khỏi việc có migration trong repo.

## Ca nghiệm thu xuyên suốt

- Host A tạo CLB, thêm 5 thành viên từ Zalo và tạo buổi tuần sau, 2 sân/12 người. Host chỉ chiếm slot khi tự đăng ký.
- Người chơi B mở link không login, thấy thông tin đúng; login rồi gửi yêu cầu; host duyệt. B không thấy phone của C và không sửa buổi/quỹ.
- Host thêm khách từ Zalo; một người hủy trước hạn; hai người tranh slot cuối; DB vẫn đúng capacity, không phantom slot.
- Host start, điểm danh present/no_show, ghi sân 300.000đ + cầu 150.000đ. Chia cho 7 người chịu phí ra tổng đúng 450.000đ; người miễn phí được ghi 0.
- Người chơi gửi chuyển khoản chưa thành confirmed; finance xác nhận, thu phần còn lại bằng cash; outstanding về 0; không tạo income kép khi retry.
- Host kết thúc dù còn một người nợ; lịch sử vẫn hiển thị outstanding. Đổi tab/khởi động lại không mất dữ liệu.
- Chủ CLB đọc quỹ: expenses/payments xuất hiện đúng một lần. Cohost thiếu finance không chỉnh tiền. Người ngoài không đọc ledger qua API.

## Cổng trước pilot

Không còn policy public write trên bảng nghiệp vụ; các ca đồng thời/permission/tiền đạt; callback/link đúng; account receiver được host kiểm tra; backup/restore staging đã thử; dữ liệu legacy chưa xác minh được cách ly; không có secret trong repo; các lỗi đọc/ghi có retry rõ.

## Nhật ký

| Ngày | Ticket | Trạng thái | Bằng chứng |
|---|---|---|---|
| 14/10/2026 | Bộ đặc tả v1.1 | Đã soạn tài liệu | 00/01/02/03/04/08/09/10; chưa triển khai app/DB |
| 14/10/2026 | BH-01 | Đã hoàn thành (Done) | AuthRepository, AuthProvider, AuthScreen, AccountScreen, AuthGuard, AppConfig; 28 tests passed (unit + widget); flutter analyze clean 0 issues; scripts/supabase_client.dart kết nối trực tiếp thành công. Giới hạn: Deep link scheme trên thiết bị di động thật và migration DB mới (thuộc BH-02) chưa kiểm chứng trên production. |
| 15/10/2026 | BH-02 | Hoàn thành file migration & schema unit test (Live DB tests: NOT RUN) | File migration `20261015051808_init_schema_v1_1.sql` (21 bảng, RLS, projections, idempotency, audit trail, compatibility cho 3 bảng legacy). 9/9 schema unit tests passed trong `test/schema/schema_v1_1_migration_test.dart`; toàn bộ 37 flutter tests passed; analyze 0 issues. Kiểm thử RLS trực tiếp trên DB live/staging: NOT RUN (Nguyên nhân: Môi trường Windows chưa có Docker để chạy `supabase start`, không có Postgres local, và không được phép tự ý apply migration lên production). |

AI chỉ ghi ticket done sau khi đạt nghiệm thu hoặc ghi rõ ngoại lệ đã được chủ dự án chấp nhận. Không xóa nhật ký để giả tiến độ.

## Xử lý phát hiện review P1/P2

Snapshot 14/10/2026, code c8e5428 trước cập nhật tài liệu: public DB có venues/sessions/session_players, không thấy clubs/quỹ; grants anon/authenticated SELECT/INSERT/UPDATE nhưng RLS chỉ có SELECT/INSERT cho sessions/players. Contacts và flags nằm trong bảng player. Chưa có trigger/check/unique registration được liệt kê. Không lấy số rows ước tính để khẳng định DB trống; chưa thử writes hoặc test quyền HTTP bằng dữ liệu thật.

| Review | Ưu tiên | Ticket / cổng nghiệm thu | Trạng thái |
|---|---|---|---|
| R1 public contact/direct inserts | P1 | BH-02: anon không đọc contacts/flags, không insert nghiệp vụ; A không đọc/sửa B; grants+RLS+RPC+projection tests | Migration v1.1 & schema tests hoàn thành; chờ apply staging/live khi có môi trường |
| R2 insert player rồi update count bị policy chặn/không atomic | P1 | BH-05: RPC một transaction, 2 request slot cuối, retry/rollback, count khớp; không mở public UPDATE | Đã đặc tả, chưa sửa code/DB |
| R3 code gọi clubs/quỹ chưa có | P1 | BH-02/03: migration staging tạo đủ nền; schema error khác empty; CRUD club+owner có test | Đã đặc tả, chưa sửa code/DB |
| R4 charges lỗi thời | P1 | BH-06: billing version/source version và gate server QR/thu mới/complete; free cũng revision current; paid/history giữ nguyên | Đã sửa khoảng trống đặc tả, chưa triển khai |
| R5 form bỏ qua giờ nhập/ngày tương lai | P2 | BH-04: ngày mai/giờ thực/qua nửa đêm/validation | Đã đặc tả, chưa sửa code |
| R6 lỗi loading/update/QR mẫu | P2 | BH-04/05/06: lỗi/retry/route mounted, mutation trả ID/state, role đúng, QR thật | Đã đặc tả, chưa sửa code |
| R7 lời mời waitlist thiếu contract | P2 | BH-05: issue/revoke/accept, đúng người/expiry/capacity/consent guest, test retry | Đã bổ sung schema/contract, chưa triển khai |

### Ca mới bắt buộc

- Chốt split 450.000đ, thêm 70.000đ expense: billing stale; không phát QR/thu mới/complete, chốt lại đúng tổng 520.000đ rồi mới tiếp tục. Đổi attendance/roster/exemption có cùng gate.
- Retry cùng request_id của payment đã committed sau khi billing stale: trả kết quả trước đó với quyền hợp lệ, không ghi income lần hai.
- Free session phải có revision current/charges 0; sửa input sau đó không được bỏ qua gate bằng nút miễn phí.
- Waitlisted chưa được mời, lời mời sai người/hết hạn/thu hồi: không accept. Khi đầy, accept không vượt capacity; retry accepted không thêm slot. Guest host_recorded có consent/audit.
- Cấu hình lỗi hoặc tables/functions thiếu: UI error+retry, không fake dữ liệu/success và không mở quyền.

Đầu vào trực tiếp cho Antigravity ở [12_ANTIGRAVITY_PROMPTS.md](12_ANTIGRAVITY_PROMPTS.md). ADR chuẩn ở [11_ARCHITECTURE_DECISIONS.md](11_ARCHITECTURE_DECISIONS.md). Trạng thái review chỉ đóng khi test implementation đạt; sửa tài liệu không đóng lỗi live.

| Ngày | Ticket | Trạng thái | Bằng chứng |
|---|---|---|---|
| 14/10/2026 | Đặc tả v1.1 sau review | Đã cập nhật tài liệu | P1/P2 → contract/tests; ADR-01..09; prompt AG-00..07; chưa thay app/DB |

## Cập nhật review và DB tests 15/10/2026

BH-02 chưa đạt nghiệm thu. Nhật ký tạo migration/9 schema tests phía trên giữ làm lịch sử, không phải xác nhận quyền đúng. Đã chạy 33 ca PostgreSQL cô lập với Auth stub: 18 PASS / 15 FAIL; F1–F6 tái hiện và F7 contact legacy bổ sung. Xem [bàn giao và tiêu chí sửa](13_BH02_REVIEW_HANDOFF.md). Chưa kiểm full Supabase HTTP/JWT và production.

| Ngày | Ticket | Trạng thái | Bằng chứng |
|---|---|---|---|
| 15/10/2026 | BH-02 review/RLS | Chưa đạt, chờ sửa F1–F7 | docs/reviews/bh02/rls_test_results.json; 33 ca: 18 PASS / 15 FAIL, baseline 3fa3cda |
| 15/10/2026 | BH-02 remediation F1–F7 | Đã sửa code migration v1.1 & cập nhật test suite; DB tests runner: NOT RUN (thiếu Docker local) | Đã sửa `20261015051808_init_schema_v1_1.sql` xử lý triệt để F1–F7; `schema_v1_1_migration_test.dart` 10/10 tests passed; toàn bộ 38/38 flutter tests passed, flutter analyze 0 issues. Runner `run_rls_tests.py` chưa chạy trên máy Windows do thiếu Docker (ghi nhận blocker đúng hướng dẫn); không tự ý apply lên production. |
| 15/10/2026 | BH-02 nghiệm thu RLS trên Docker | ĐÃ ĐẠT NGHIỆM THU (Done) | Sau khi dựng Docker container PostgreSQL, đã thực thi runner `run_rls_tests.py`: **33/33 PASS, 0 FAIL** (kết quả lưu tại `docs/reviews/bh02/rls_test_results_20261015115541.json`). 38/38 flutter tests passed; flutter analyze 0 issues. F1–F7 giải quyết triệt để trên cả clean DB và upgrade legacy. Giới hạn: Chưa kiểm PostgREST HTTP/JWT và production. Sẵn sàng chuyển sang BH-03. |

BH-02 đã hoàn thành đạt chuẩn cổng nghiệm thu. Có thể tiếp tục triển khai ticket BH-03 (CLB / Thành viên / Ngân hàng) theo quy trình.

## Đánh giá bổ sung sau remediation 15ef59b

Kết luận hiện hành **BH-02 pending remediation H1–H3**, thay cho kết luận Done ở lịch sử phía trên. Chạy độc lập 33 ca cũ PASS, thêm 6 ca FAIL. Treasury mất công nợ/payment, member/pending còn đọc receiver_snapshot và trigger legacy chưa cập nhật lịch/tên sân đúng. Xem [handoff](13_BH02_REVIEW_HANDOFF.md) và [review 15ef59b](reviews/bh02/review_15ef59b.md).

| Ngày | Ticket | Trạng thái | Bằng chứng |
|---|---|---|---|
| 15/10/2026 | BH-02 re-review 15ef59b | Chưa đạt đầy đủ; sửa H1–H3 trước BH-03 | verification_15ef59b_baseline.json: 33 PASS; verification_15ef59b_extended.json: 6 FAIL; chưa full Supabase tests |
| 15/10/2026 | BH-02 remediation H1–H3 & kiểm thử mở rộng | ĐÃ ĐẠT NGHIỆM THU (Done) | Đã khắc phục triệt để H1–H3 trong migration `20261015051808_init_schema_v1_1.sql` (SHA256: `91680c9b32fc438057293db0e4df29f4b979f50ee6e00a5ea08c6603e3967e50`). Thực thi trên Docker PostgreSQL đạt: 33/33 baseline PASS (`rls_test_results_20261015122655.json`) + 14/14 extended/regression PASS (`extended_results_20261015122655.json`), tổng 47/47 DB tests PASS (100%). Flutter: 39/39 tests PASS, analyze 0 issues. Giới hạn: Chưa test PostgREST HTTP/JWT và production. Sẵn sàng chuyển sang BH-03. |

BH-02 đã hoàn thành toàn diện các yêu cầu phân quyền và tương thích schema nền. Có thể chuyển sang ticket tiếp theo BH-03 (CLB / Thành viên / Ngân hàng).

## Bổ sung nghiên cứu Vmito/Vụt (15/10/2026)

Nguồn/giới hạn và acceptance tại [14_PRODUCT_LEARNINGS_VMITO_VUT.md](14_PRODUCT_LEARNINGS_VMITO_VUT.md). Không đánh dấu feature đã làm hoặc H1–H3 đã đóng từ lượt tài liệu. Commit 11aaec7 mới báo sửa H1–H3 cần review/test riêng.

| Ticket | Bổ sung có phạm vi | Điều kiện |
|---|---|---|
| BH-03 | Receiver của own CLB/host, private member contacts | Không lấy keys/account từ report đối thủ |
| BH-04 | PD-01/02: resource link, return URL validation, manual area/date/availability/fee filter và card | Projection quyền đúng, không yêu cầu GPS, chưa thêm SDK map/router tự động |
| BH-05 | PD-03: status join request và consent waitlist, role/ID tests | Chỉ confirmed giữ chỗ, pending không đọc bank |
| BH-06 | PD-04: VietQR fallback/identity/reference và manual confirmation | Current charge revision và finance/player quyền đúng |
| BH-07 | PD-05/06: state refresh/lịch sử, permission/deep link/backup/provider/version release checklist | Thiết bị thật/web và PASS/FAIL/NOT RUN; không suy pass từ thư viện |
| BH-10 (đề xuất) | Push opt-in, preferences/device ownership, payload riêng tư | Sau pilot, chưa được giao triển khai/schema; không chặn hoàn thành MVP |

Không mở lại BH-01 hoặc làm BH-10 trước BH-02/03 chỉ vì có nghiên cứu mới. Các tính năng runtime suy ra từ strings phải được xác minh độc lập hoặc coi là giả thuyết sản phẩm của mình.

## Bàn giao BH-03 (15/10/2026)

Chủ dự án yêu cầu IDE tiếp tục BH-03 từ code hiện có sau remediation 11aaec7; xem [15_BH03_IMPLEMENTATION_HANDOFF.md](15_BH03_IMPLEMENTATION_HANDOFF.md). Chia BH-03A DB/RPC → BH-03B model/repository/state → BH-03C UI → BH-03D regression/evidence.

**Kết quả triển khai thực tế (15/10/2026):**
- **BH-03A (DB & RPC)**: Tạo migration `supabase/migrations/20261015133247_bh03_clubs_and_members.sql` triển khai 12 RPC nguyên tử, kiểm soát chặt chẽ actor/role, idempotency, audit trail. Viết bộ kiểm thử PostgreSQL `docs/reviews/bh03/run_bh03_tests.py` chạy trên Docker: **24/24 PASS** (bao gồm atomic create_club, offline members, chặn self-escalation, bảo vệ owner, giữ leading zero STK ngân hàng, privacy quỹ và SĐT).
- **BH-03B (Data & State)**: Xây dựng typed models (`Club`, `ClubMember`, `BankAccount`), `ClubRepository` và `ClubProvider` với quản lý state loading/error/submitting, chống bấm trùng và dọn dẹp state private khi switch CLB / logout. Viết unit tests model và provider: **13/13 PASS**.
- **BH-03C (UI Layer)**: Nâng cấp `ClubsScreen` & `ClubDetailScreen` 3 tabs (Tổng quan, Thành viên, Tài khoản quỹ). Form tạo CLB chỉ yêu cầu Tên, Mô tả, Quyền riêng tư; chuyển nút demo ghi quỹ sang trạng thái thông báo thuộc BH-06. Viết widget tests: **4/4 PASS**.
- **BH-03D (Kiểm thử tích hợp & Regression)**: Chạy lại chuỗi 47 ca kiểm thử BH-02 (`run_rls_tests.py` 33 ca + `extended_tests_15ef59b.py` 14 ca): **47/47 PASS**. Toàn bộ Flutter test suite: **56/56 PASS**. `flutter analyze`: **0 issues**. Không apply production.

## BH-03 khắc phục sau review 88dd247

| Ngày | Phạm vi | Bằng chứng | Giới hạn |
|---|---|---|---|
| 15/10/2026 | C1–C5 code + forward SQL + tests | Flutter 61/61; analyze 0 issues; DB clean/legacy BH-03 48+14, BH-02 47, tổng 109 PASS; docs/17_BH03_REMEDIATION.md | PostgreSQL Auth stub; chưa full Supabase HTTP/JWT/thiết bị thật, chưa apply production |

Giữ request_id bắt buộc và guest user_id NULL tới khi có acceptance thật. Kiểm chuỗi migration mới và client cùng rollout; không đánh dấu production đã chạy từ kết quả DB cô lập.

## Rà soát tổng hợp BH-01 → BH-03 (15/10/2026)

Rà soát độc lập ba ticket dưới ba góc nhìn (code reviewer, backend architect, software architect), kết luận tại [18_REVIEW_CONSOLIDATED_BH01_BH03.md](18_REVIEW_CONSOLIDATED_BH01_BH03.md). Baseline BH-03 là `88dd247`; HEAD khi tổng hợp `a433349`.

- Chạy lại độc lập tại HEAD: `flutter analyze` 0 issues; `flutter test` 61/61; DB tests 33/33 (`rls_test_results_20261015145918.json`) + 14/14 (`extended_results_20261015145918.json`) + 48/48 (`bh03_test_results_20261015145923.json`) + 14/14 retry (`bh03_retry_results_20261015145923.json`) = 109/109.
- Đã đóng bởi `a433349` (C1–C5): consent `user_id`, race idempotency, vòng đời private state sau logout, request key, hash payload.
- **Chặn tiếp tục (P0)**, còn mở: (X1) lớp demo `SupabaseService`/`SessionProvider` còn ghi bộ đếm/số dư trực tiếp và dùng cột demo không có trong schema v1.1 — app "nửa migration"; (X2) cấu hình mặc định trỏ production, `AppConfig.environment` không có tác dụng, `scripts/update_db.dart` ghi thẳng project thật.
- **Còn mở tại HEAD**: phân trang `list_club_members` (đã tái hiện: bỏ qua `limit`, `offset>0` trả NULL); lỗi tải Thành viên/Tài khoản quỹ hiển thị thành empty; `list_my_clubs` thiếu `balance_vnd`; RPC đọc chưa REVOKE PUBLIC/anon; invariant clean/legacy lệch; test cấu trúc thay test hành vi. Ghi chú trung thực: mục "số dư quỹ" ở danh sách CLB (BH-03C) không đúng thực tế.
- Giới hạn: chưa kiểm PostgREST HTTP/JWT thật, concurrency đa kết nối, thiết bị thật, production.

## Đợt sửa trước BH-04 — 15/10/2026

Đã sửa cấu hình môi trường, auth session, phân trang member, UI error/retry/role và ACL RPC đọc bằng forward migration. Flutter 66/66 PASS; DB 117/117 PASS; analyze sạch. Chi tiết, bằng chứng, giới hạn và prompt phiên mới: [19_PRE_BH04_HANDOFF.md](19_PRE_BH04_HANDOFF.md). Chưa apply production/kiểm HTTP JWT; X1 chuyển đổi buổi chơi demo thuộc BH-04, chặn pilot.

## BH-04 — Buổi chơi/lịch/chia sẻ — 15/10/2026

| 15/10/2026 | BH-04 buổi chơi | ĐÃ TRIỂN KHAI (local/staging) | Thay đường demo `SupabaseService`/`SessionProvider` bằng model + repository + provider typed và migration forward `20261015163000_bh04_sessions.sql` (create/update/duplicate/publish + projection whitelist + `list_my_sessions`/`list_public_sessions`/`list_session_players`, idempotency + audit + REVOKE PUBLIC/anon). Flutter **101/101 PASS** (66 regression + 35 mới), analyze sạch; DB **159/159 PASS** (BH-02 33+14, BH-03 48+22, BH-04 42). Chưa apply production, chưa kiểm PostgREST HTTP/JWT; deep link OS-level NOT RUN. Chi tiết: [20_BH04_HANDOFF.md](20_BH04_HANDOFF.md). |

- Routing chốt theo code hiện có: **không** thêm router/`app_links`; `lib/core/app_routes.dart` kiểm hợp lệ link nội bộ `/sessions/:id` và dùng `AuthScreen.returnRoute` để quay lại đúng buổi sau đăng nhập.
- X1: `lib/data/supabase_service.dart` (và các cột demo) đã bị xoá; sân chuyển sang `VenueRepository` typed.
- Bằng chứng: `docs/reviews/bh04/bh04_test_results_20261015160911.json`; runner `docs/reviews/bh04/run_bh04_tests.py`.
- Ticket tiếp theo: **BH-05** (đăng ký/lời mời), theo AG-05 trong [12_ANTIGRAVITY_PROMPTS.md](12_ANTIGRAVITY_PROMPTS.md).

## Sửa review BH-04 R1–R4 — 15/10/2026

Đã sửa lifecycle replay bằng forward migration, link routing/absolute URL, request key mới sau thành công, roster loading/error/retry. 104/104 Flutter và 161/161 DB PASS; analyze sạch. Chi tiết/giới hạn tại [21_BH04_REMEDIATION.md](21_BH04_REMEDIATION.md); chưa apply remote DB hoặc kiểm HTTP/JWT/OS links.

## BH-05 — Đăng ký / duyệt / huỷ / danh sách chờ — 15/10/2026

| Ngày | Ticket | Trạng thái | Bằng chứng |
|---|---|---|---|
| 15/10/2026 | BH-05 đăng ký/duyệt/huỷ/lời mời | ĐÃ TRIỂN KHAI (local/staging) | Forward migration `supabase/migrations/20261015170500_bh05_registrations.sql` (SHA256 `356f5831649eb4d09efa624402679cce67211056ce44e09cf6088715970ac588`): 9 RPC mutation/đọc + mở rộng `list_session_players`, helper nội bộ bị REVOKE khỏi client. Flutter **116/116 PASS** (104 regression + 12 mới), analyze 0 issue. DB **227/227 PASS** (BH-02 33+14, BH-03 48+22, BH-04 44, BH-05 66). Chi tiết/giới hạn: [22_BH05_HANDOFF.md](22_BH05_HANDOFF.md). |

- Phạm vi đã làm: đăng ký tự phục vụ (`host_approval`→`pending`, `auto_confirm`→`confirmed` nếu còn chỗ, ngược lại `waitlisted`); host/cohost thêm thành viên CLB đúng ID hoặc khách chưa có tài khoản (`host_recorded`, không tự liên kết theo tên/SĐT); duyệt/từ chối/đưa vào danh sách chờ; huỷ theo hạn (người chơi) hoặc theo quyền (host); điểm danh khi `in_progress`; lời mời nhận chỗ (không giữ slot, mặc định `min(now()+30p, deadline, starts_at)`) và accept đơn dùng một lần kiểm lại người nhận/state/hết hạn/deadline/slot.
- Chỉ `confirmed` giữ chỗ và được xem/đọc thông tin thanh toán; `pending`/`waitlisted` không giữ slot. Client không ghi bộ đếm/role/số dư/tác nhân audit.
- Giới hạn: PostgreSQL + Auth stub, **chưa** kiểm PostgREST HTTP/JWT thật, thiết bị thật hay apply production; chưa diễn tập migration/backup trên staging thật.
- Ticket tiếp theo: **BH-06** (chốt phí / QR / thu tiền) theo AG-06 trong [12_ANTIGRAVITY_PROMPTS.md](12_ANTIGRAVITY_PROMPTS.md).
## BH-05 — Đăng ký / duyệt / huỷ / danh sách chờ — 15–16/10/2026

Theo quy trình hai AI trong `AGENTS.md`, BH-05 được tách phần A/B/C, mỗi phần một nhánh và **chờ review** (người triển khai không tự ghi Done).

### BH-05A — DB / RPC / RLS / test DB

| Ngày | Phần | Trạng thái | Bằng chứng |
|---|---|---|---|
| 16/10/2026 | BH-05A DB/RPC | **Chờ review** | Nhánh `feat/bh05a-db` (commit `0d03e0e`). Migration `supabase/migrations/20261015170500_bh05_registrations.sql` SHA256 `2c63e2cb5cf98d7b7c1474ec09e7ada61bc0a6b67130b5776a8ca8f95aaade51`; runner `docs/reviews/bh05/run_bh05_tests.py`; kết quả `docs/reviews/bh05/bh05_test_results_20261015170003.json`. |

- Lệnh đã chạy trên nhánh `feat/bh05a-db`: `flutter analyze` (0 issue); `flutter test` (**104/104 PASS** — chưa gồm test B/C); `python docs/reviews/bh05/run_bh05_tests.py` (**66/66 PASS**, `tested_commit=0d03e0e8`, worktree sạch).
- 4 invariant trọng yếu PASS trên cả CLEAN và LEGACY: hai kết nối tranh slot cuối chỉ một `confirmed`; retry cùng `request_id` không ghi trùng (replay cùng key; accept lặp không thêm slot); người ngoài/không quyền không duyệt được và không đọc contact; không có direct write cho `authenticated` trên `session_players`/`waitlist_invitations`.
- Phần B (model/repository/provider) và C (UI) đã có bản tham chiếu nhưng **chưa tách nhánh/gửi review**; sẽ làm sau khi A đạt.
- NOT RUN: PostgREST HTTP/JWT thật (chỉ PostgreSQL + Auth stub), apply staging/production, thiết bị thật.

### BH-05A — Vòng sửa review 1 (16/10/2026), nhánh `feat/bh05a-db`

Review độc lập tại [docs/reviews/bh05/review_7fcbdee.md](reviews/bh05/review_7fcbdee.md) kết luận **Chưa đạt** với A1 (P1), A2 (P1) và A3 (P2). Đã sửa cả **A1 + A2 + A3** (chủ dự án chốt: mặc định sửa hết lỗi trong nhánh A, không chỉ P0/P1).

| Phát hiện | Mức | Trạng thái | Bằng chứng |
|---|---|---|---|
| A1 — thiếu gate quyền tài chính khi đổi tập `confirmed` sau khi chốt phí | P1 | **Đã sửa (chờ review)** | Test tái hiện FAIL trước sửa (`bh05_test_results_20261015172330.json`, 12 FAIL), PASS sau sửa; migration mới `supabase/migrations/20261016090000_bh05_review_fixes.sql` |
| A2 — `update_session` cho hạ `capacity` dưới số `confirmed` | P1 | **Đã sửa (chờ review)** | Cùng file migration (forward, không sửa migration đã chia sẻ) |
| A3 — huỷ buổi không thu hồi lời mời `pending` | P2 | **Đã sửa (chờ review)** | Test tái hiện FAIL trước sửa (`bh05_test_results_20261015173045.json`, 6 FAIL); migration mới `supabase/migrations/20261016091000_bh05_a3_cancel_revokes_invitations.sql` |

- Cách sửa: forward migration `20261016090000_bh05_review_fixes.sql` `CREATE OR REPLACE` 5 hàm (không sửa file migration đã chia sẻ). A1 chặn khi có `charge_revisions.status='active'` mà actor thiếu `has_session_finance_access` ở `add_session_player`, `decide_registration` (nhánh `confirmed`), `cancel_registration` (người đang `confirmed`), `accept_waitlist_invitation`. A2 chặn trong `update_session` khi `p_capacity < count(confirmed)` (dưới cùng khoá `FOR UPDATE`). A3 `CREATE OR REPLACE` `set_session_lifecycle`: khi `cancel`, thu hồi toàn bộ `waitlist_invitations` đang `pending` của người thuộc buổi (đặt `revoked_by`/`revoked_at`, ghi số lượng vào audit) trong cùng transaction, giữ thứ tự khoá session → invitation như `accept`.
- Test tái hiện (thêm vào runner, FAIL trước sửa và PASS sau sửa): `A1 add/decide/cancel/accept`, `A2 update_session`, `A2 race hạ capacity đấu với join`, `A3 huỷ buổi thu hồi lời mời + get_my_waitlist_invitation trả NULL`, `A3 race huỷ buổi đấu với accept`, `A3 replay huỷ buổi không tác dụng phụ`.
- Lệnh đã chạy trên nhánh `feat/bh05a-db`: `flutter analyze` (**0 issue**); `flutter test` (**104/104 PASS**); `python docs/reviews/bh05/run_bh05_tests.py` (**84/84 PASS**, `tested_commit=dae8763`, worktree sạch — `docs/reviews/bh05/bh05_test_results_20261015173326.json`).
- NOT RUN: PostgREST HTTP/JWT thật, apply staging/production, thiết bị thật (như trên).

### BH-05A — Xác nhận Đạt sau review độc lập (16/10/2026)

- **Trạng thái hiện tại: Đạt phần A** tại tested commit `9f2d455`, theo [review_9f2d455.md](reviews/bh05/review_9f2d455.md); chủ dự án đã xác nhận yêu cầu cập nhật trạng thái.
- Bằng chứng độc lập: analyze sạch; 104/104 Flutter, 84/84 DB và 6/6 probe hồi quy đúng kỳ vọng. Báo cáo và bằng chứng đã push tại `b55a793`.
- Các dòng Chờ review/Chưa đạt phía trên là lịch sử trước remediation, không phải trạng thái hiện tại. Phần B/C chưa được nghiệm thu trong kết luận này.
- NOT RUN: HTTP/PostgREST/JWT thật, thiết bị/browser e2e, staging/production apply và các lịch cạnh tranh bổ sung được liệt kê trong báo cáo. Không tự merge main hoặc deploy; bước tiếp theo chờ chủ dự án giao.

### BH-05B — Model / Repository / Provider + test đơn vị — 16/10/2026

| Ngày | Phần | Trạng thái | Bằng chứng |
|---|---|---|---|
| 16/10/2026 | BH-05B Dart (model/repository/provider) | **Chờ review** | Nhánh `feat/bh05b-data`, tách từ `feat/bh05a-db` (`7bc4423`). File: `lib/models/session.dart`, `lib/data/session_repository.dart`, `lib/providers/session_provider.dart`, `test/providers/session_provider_test.dart` (nguyên bản đã viết sẵn ở `814d85b` trên `main`, không viết lại). |

- Phạm vi: chỉ lớp Dart phía client (model `SessionPlayer` invitation fields/`WaitlistInvitation`/`RegistrationResult`; repository gọi RPC BH-05; provider `myInvitation`/`fetchMyInvitation`/`_runPlayerMutation`; 7 test provider). Không bao gồm UI phần C.
- Lệnh đã chạy trên nhánh `feat/bh05b-data`: `flutter analyze` (**0 issue**); `flutter test` (**111/111 PASS** — 104 nền của A + 7 test B).
- Không chạy runner DB: phần B không đổi DB/migration (theo IMPLEMENTER.md, runner DB chỉ bắt buộc khi đổi DB).
- NOT RUN: kiểm thử thiết bị thật/browser e2e; PostgREST HTTP/JWT thật (phần B chỉ được test bằng unit test với provider giả, chưa gọi RPC qua mạng); apply staging/production. UI phần C chưa tách nhánh/nghiệm thu.
- Ghi chú phạm vi tài liệu: `docs/08_DOMAIN_CONTRACTS.md` §12 và `docs/22_BH05_HANDOFF.md` hiện chỉ có trên `main` (từ `814d85b`/`aa90066`), chưa đưa vào nhánh A/B; cần chủ dự án quyết nơi đặt.

### BH-05B — Kết luận cuối cùng của reviewer (16/10/2026)

- **Trạng thái hiện tại: Chưa đạt phần B** tại `135d7bd`, theo [review_135d7bd.md](reviews/bh05/review_135d7bd.md). Còn B1/B2 mức P2 về lỗi tải lời mời và state lời mời cũ.
- Analyze sạch, 111/111 Flutter và 84/84 DB PASS; hai probe bổ sung tái hiện lỗi. NOT RUN được liệt kê trong báo cáo.
- Reviewer tự chốt kết luận, không cần chủ dự án xác nhận; trạng thái Chờ review phía trên là lịch sử. Không sửa code, merge main hoặc apply DB remote trong lượt này.

### BH-05B — Vòng sửa review 1 (B1, B2) — 16/10/2026

Review [review_135d7bd.md](reviews/bh05/review_135d7bd.md) kết luận **Chưa đạt** với B1 (P2) và B2 (P2). Đã sửa cả hai.

| Phát hiện | Mức | Trạng thái | Bằng chứng |
|---|---|---|---|
| B1 — lỗi tải lời mời bị nuốt thành "không có lời mời" | P2 | **Đã sửa (chờ review)** | Test mới tái hiện FAIL trước sửa, PASS sau sửa; `flutter test` **118/118** |
| B2 — làm mới chi tiết vẫn giữ lời mời cũ | P2 | **Đã sửa (chờ review)** | Cùng bộ test |

- Cách sửa (chỉ trong `lib/providers/session_provider.dart`; không đổi DB/migration/hợp đồng RPC): thêm state riêng `isLoadingInvitation`/`invitationErrorMessage` và `_invitationSerial`; `fetchMyInvitation` tách loading/error, chỉ coi response thành công `null` là rỗng (không nuốt exception), giữ guard auth/session, chống phản hồi đến trễ bằng serial; `fetchSessionDetail` khi chi tiết mới không còn `waitlisted` thì `_resetInvitation()` (xoá state + vô hiệu hoá phản hồi đang bay).
- Test thêm vào `test/providers/session_provider_test.dart` (FAIL trước sửa, PASS sau sửa): B1 lỗi/loading/null-hợp-lệ/retry; B2 waitlisted→confirmed, waitlisted→không còn đăng ký, phản hồi lời mời đến trễ.
- Lệnh đã chạy trên nhánh `feat/bh05b-data`: `flutter analyze` (**0 issue**); `flutter test` (**118/118 PASS**); `python docs/reviews/bh05/run_bh05_tests.py` (**84/84 PASS** — không đổi vì B không chạm DB).
- NOT RUN: thiết bị thật/browser e2e; PostgREST HTTP/JWT thật (unit test vẫn dùng repository giả, chưa gọi RPC qua mạng); apply staging/production.

### BH-05B — Kết luận cuối cùng sau review cf65199 (16/10/2026)

- **Trạng thái hiện tại: Đạt phần B** tại `cf65199`, theo [review_cf65199.md](reviews/bh05/review_cf65199.md). Reviewer tự chốt theo quy tắc hiện hành, không cần chủ dự án xác nhận.
- Kiểm chứng độc lập: analyze sạch; 118/118 Flutter, 84/84 DB, 2/2 probe hồi quy PASS. Các trạng thái Chờ review/Chưa đạt trước đây là lịch sử.
- NOT RUN và giới hạn nằm trong báo cáo; chưa nghiệm thu UI phần C, HTTP/JWT/thiết bị thật hoặc deploy production. Không tự merge main hay chuyển sang triển khai C.

### BH-05C — UI màn chi tiết buổi (đăng ký/duyệt/điểm danh/lời mời chờ) — 16/10/2026

| Ngày | Phần | Trạng thái | Bằng chứng |
|---|---|---|---|
| 16/10/2026 | BH-05C UI | **Chờ review** | Nhánh `feat/bh05c-ui`, tách từ `feat/bh05b-data` (`3bb07ca`). File: `lib/screens/session_detail_screen.dart`, `test/screens/session_detail_screen_test.dart` — nguyên bản viết sẵn ở `814d85b` trên `main`, lấy nguyên trạng không viết lại (`git diff main -- <2 file>` rỗng). |

- Phạm vi: chỉ UI màn chi tiết buổi phía client (nút đăng ký/hủy, trạng thái pending/waitlisted/confirmed, host duyệt/từ chối pending, điểm danh, mời/thu hồi lời mời chờ, banner lời mời của tôi) và test widget tương ứng. Không đổi model/repository/provider/migration.
- Lệnh đã chạy trên nhánh `feat/bh05c-ui`: `flutter analyze` (**0 issue**); `flutter test` (**123/123 PASS**).
- Không chạy runner DB: phần C không đổi DB/migration (theo IMPLEMENTER.md, runner DB chỉ bắt buộc khi đổi DB).
- NOT RUN: thiết bị thật/browser e2e (test widget dùng provider/repository giả, chưa chạm Supabase thật); PostgREST HTTP/JWT thật; apply staging/production; chưa nghiệm thu đồng thời A/B/C trên `main`.

### BH-05C — Kết luận cuối cùng reviewer 8974d3c (16/10/2026)

- **Trạng thái hiện tại: Chưa đạt phần C**, theo [review_8974d3c.md](reviews/bh05/review_8974d3c.md). Còn C1/C2/C3 mức P2: UI lỗi/tải lời mời, đăng ký waitlist khi đầy và roster trong dialog thành viên CLB.
- Kiểm thử độc lập: analyze sạch, 123/123 Flutter và 84/84 DB PASS; 3 probe UI bổ sung FAIL tái hiện lỗi. NOT RUN và cách sửa trong báo cáo.
- Trạng thái Chờ review phía trên là lịch sử. Reviewer tự chốt, không cần xác nhận; không sửa code, merge main hoặc apply DB remote.

### BH-05C — Vòng sửa review 1 (C1, C2, C3) — 16/10/2026

Review [review_8974d3c.md](reviews/bh05/review_8974d3c.md) kết luận **Chưa đạt** với C1/C2/C3 (đều P2). Đã sửa cả ba.

| Phát hiện | Mức | Trạng thái | Bằng chứng |
|---|---|---|---|
| C1 — UI bỏ qua loading/error lời mời của provider B | P2 | **Đã sửa (chờ review)** | 2 test widget tái hiện FAIL trước sửa, PASS sau |
| C2 — buổi đầy chặn luôn đăng ký vào danh sách chờ | P2 | **Đã sửa (chờ review)** | 1 test widget tái hiện FAIL trước sửa, PASS sau |
| C3 — dialog thành viên dùng roster sai scope, không theo dõi tải | P2 | **Đã sửa (chờ review)** | 2 test widget + 3 test provider roster |

- Cách sửa:
  - C1: `_PlayerRegistrationCard` nhận `isLoadingInvitation`/`invitationErrorMessage` + callback thử lại; hiển thị "Đang tải lời mời…", lỗi kèm "Thử lại lời mời" gọi `fetchMyInvitation`, và chỉ cho "Chấp nhận lời mời" khi tải thành công (không trình bày dữ liệu cũ khi lỗi).
  - C2: bỏ chặn theo `session.isFull` khi buổi còn mở đăng ký; vẫn hiện "Đăng ký tham gia" (kèm ghi chú vào danh sách chờ khi đầy) để RPC quyết định chỗ/pending, không dùng count phía client thay quy tắc server.
  - C3: thêm API roster có scope trên `ClubProvider` (`fetchClubRoster`/`rosterMembers`/`isLoadingRoster`/`rosterErrorMessage`/`clearClubRoster`, có serial chống phản hồi trễ), dialog "Thêm người" tự tải roster theo `clubId` của buổi và `watch` provider (hiện loading/error/empty/thử lại, không dùng `currentMembers` của CLB khác). Không đổi migration/quyền DB.
- Test thêm: `test/screens/session_detail_screen_test.dart` C1×2, C2×1, C3×2; `test/providers/club_provider_test.dart` roster scope ×3 (tải/lỗi-thử lại/đổi CLB chống rò rỉ + phản hồi trễ). 5 test widget FAIL trước sửa (11 pass/5 fail), sau sửa PASS.
- Lệnh đã chạy trên nhánh `feat/bh05c-ui`: `flutter analyze` (**0 issue**); `flutter test` (**131/131 PASS**); `python docs/reviews/bh05/run_bh05_tests.py` (**84/84 PASS** — phần C không chạm DB, chạy lại theo IMPLEMENTER.md mục "Sửa theo review").
- NOT RUN: thiết bị thật/browser e2e; PostgREST HTTP/JWT thật (widget test dùng provider/repository giả); apply staging/production; chưa nghiệm thu đồng thời A/B/C trên `main`.

### BH-05C — Kết luận cuối cùng review 48b4ad2 (16/10/2026)

- **Trạng thái hiện tại: Chưa đạt phần C** tại `48b4ad2` (code `ef88f05`), theo [review_48b4ad2.md](reviews/bh05/review_48b4ad2.md). Còn C1-R mức P2: nút accept vẫn enabled khi đang refresh lời mời có cache.
- Kiểm chứng độc lập: analyze sạch, 131/131 Flutter, 84/84 DB; 4 probe UI gồm 3 PASS/1 FAIL tái hiện phần còn lại. NOT RUN trong báo cáo.
- Đây là kết luận sau vòng sửa 1, thay trạng thái Chờ review của bản sửa; không tự sửa code, merge main hoặc apply remote DB. Reviewer tự chốt, không cần xác nhận.

### BH-05C — Vòng sửa review 2 (C1-R) — 16/10/2026

Review [review_48b4ad2.md](reviews/bh05/review_48b4ad2.md) kết luận **Chưa đạt** với C1-R (P2). Đây là vòng sửa thứ 2 (giới hạn tối đa 2 vòng theo IMPLEMENTER.md).

| Phát hiện | Mức | Trạng thái | Bằng chứng |
|---|---|---|---|
| C1-R — đang tải lại lời mời vẫn cho chấp nhận bằng cache cũ | P2 | **Đã sửa (chờ review)** | 1 test widget tái hiện FAIL trước sửa, PASS sau |

- Cách sửa (chỉ trong `lib/screens/session_detail_screen.dart`, không đổi RPC/quyền/DB): `hasInvitation`/`canAccept` loại trạng thái đang tải — điều kiện `isWaitlisted && !isLoadingInvitation && invitationErrorMessage == null && invitation != null`, nên nút "Chấp nhận lời mời" chỉ bật sau khi response thành công hợp lệ; nhánh lỗi+thử lại giữ nguyên.
- Test thêm: `test/screens/session_detail_screen_test.dart` "C1-R đang tải lại lời mời thì không cho chấp nhận bằng cache cũ" (cache cũ + refresh đang chờ → ẩn nút; response hợp lệ → bật lại; null hợp lệ → không nút, không lỗi; lỗi → hiện lỗi + thử lại). FAIL trước sửa (`Found 1 widget "Chấp nhận lời mời"`, kỳ vọng none), PASS sau sửa.
- Lệnh đã chạy trên nhánh `feat/bh05c-ui`: `flutter analyze` (**0 issue**); `flutter test` (**132/132 PASS**); `python docs/reviews/bh05/run_bh05_tests.py` (**84/84 PASS** — phần C không chạm DB, chạy lại theo IMPLEMENTER.md).
- NOT RUN: thiết bị thật/browser e2e; PostgREST HTTP/JWT thật; apply staging/production; chưa nghiệm thu đồng thời A/B/C trên `main`; host thu hồi lời mời qua HTTP trong lúc client refresh.

### BH-05C — Kết luận cuối cùng review 1f1f9ce (16/10/2026)

- **Trạng thái hiện tại: Đạt phần C** tại `1f1f9ce` (code `7707a76`), theo [review_1f1f9ce.md](reviews/bh05/review_1f1f9ce.md). Reviewer tự chốt sau vòng sửa 2, không cần xác nhận.
- Kiểm chứng độc lập: analyze sạch, 132/132 Flutter, 84/84 DB và 4/4 probe hồi quy PASS. Các trạng thái Chưa đạt/Chờ review trước đây là lịch sử.
- NOT RUN và giới hạn trong báo cáo; chưa nghiệm thu toàn A/B/C trên main hoặc triển khai production. Không sửa code, merge main hoặc apply DB remote.

### BH-05 — Tích hợp A+B+C trên nhánh `feat/bh05-integration` (16/10/2026)

| Ngày | Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|---|
| 16/10/2026 | Tích hợp A→B→C | **Chờ review** | Nhánh `feat/bh05-integration` (tách từ `main` = `da1285d`): merge A `eecf24a`, B `a0f5d35`, C `b126f17`, kết luận Đạt C `678ee95`; commit bằng chứng `3867c99`, `153f72a`, `6742e69`, `830dfbf`, `0979bbe`, `bae8bcd`. |

- Lệnh đã chạy trên cây tích hợp `b126f17`: `flutter analyze` (**0 issue**); `flutter test` (**132/132 PASS**); `python docs/reviews/bh02/run_rls_tests.py` (**33/33**), `python docs/reviews/bh02/extended_tests_15ef59b.py` (**14/14**), `python docs/reviews/bh03/run_bh03_tests.py` (**48/48**), `python docs/reviews/bh03/run_bh03_retry_tests.py` (**22/22**), `python docs/reviews/bh04/run_bh04_tests.py` (**44/44**), `python docs/reviews/bh05/run_bh05_tests.py` (**84/84**) — tổng DB **245/245 PASS**. Mỗi runner commit ngay JSON để `worktree_dirty=false`; các commit này chỉ thêm tệp JSON (`git diff b126f17 HEAD` không đổi mã nguồn/migration).
- Giải xung đột: `docs/09` (giữ cả snapshot 15/10 trên `main` và tường thuật A/B/C); `run_bh05_tests.py` (lấy bản A, 42 kịch bản); `session_provider.dart` + test (lấy bản B — diff so với `main` chỉ còn hunk B1/B2); `session_detail_screen.dart` + test (lấy bản C — C1/C2/C3/C1-R); `club_provider.dart` + test auto-merge. Kết quả: `git diff feat/bh05c-ui -- lib test supabase` rỗng ⇒ mã tích hợp = cây C đã review.
- Bàn giao/điểm tiếp tục: [22_BH05_HANDOFF.md](22_BH05_HANDOFF.md).
- NOT RUN: HTTP/PostgREST/JWT thật, thiết bị/browser e2e, apply staging/production, cạnh tranh qua HTTP, và **nghiệm thu độc lập chính bản tích hợp**. A, B, C đều đã Đạt độc lập (A `9f2d455`, B `cf65199`, C `1f1f9ce`); bản tích hợp hợp nhất các bản đã Đạt, **chờ review tổng**. Không tự merge `main` hay deploy.

### BH-05 — Vòng sửa review tích hợp 1 (I1, I2) — 16/10/2026

Review [review_c7ed6d5.md](reviews/bh05/review_c7ed6d5.md) kết luận **Chưa đạt tích hợp** với I1 (P1) và I2 (P2). Đã sửa **cả hai** (chủ dự án chốt: mặc định sửa hết lỗi trong nhánh).

| Phát hiện | Mức | Trạng thái | Bằng chứng |
|---|---|---|---|
| I1 — không có đường hợp lệ published→in_progress nên điểm danh không chạy được từ app | P1 | **Đã sửa (chờ review)** | Test widget tái hiện FAIL trước sửa; runner 8 FAIL do thiếu `public.start_session` (`bh05_test_results_20261016000811.json`) |
| I2 — sau huỷ không có đường đăng ký lại dù RPC hỗ trợ | P2 | **Đã sửa (chờ review)** | Test widget tái hiện FAIL trước sửa |

- Cách sửa:
  - I1: migration forward-only mới `supabase/migrations/20261016100000_bh05_start_session.sql` — RPC `start_session(p_session_id, p_request_id)` (SECURITY DEFINER + `search_path`, khoá session `FOR UPDATE`, kiểm `has_session_management_access`, `request_id` bắt buộc, idempotency/hash/replay, audit `START_SESSION`, REVOKE PUBLIC/anon + GRANT authenticated; chỉ cho `published → in_progress`). **Không** mở direct UPDATE trên `sessions` và **không** nới guard `in_progress` của `record_attendance`. Client: `SessionRepository.startSession`, `SessionProvider.startSession` (qua `_runMutation`), nút "Bắt đầu buổi chơi" trong `_ManagementActions` khi `session.isPublished` (chỉ host/cohost thấy vì panel chỉ render khi `canManage`).
  - I2: `_PlayerRegistrationCard` thêm nút "Đăng ký tham gia" khi trạng thái `cancelled`/`rejected` và `session.isShareable`, gửi ý định mới qua `requestJoinSession` để DB giữ `player_id` và tự kiểm slot/hạn (không xoá đăng ký để hiện nút).
- Test thêm: widget I1×2 (host thấy nút + gọi `start_session`; người không quản lý không thấy), I2×3 (huỷ → gọi lại RPC; lỗi → thử lại; buổi đã huỷ không có nút); runner thêm 3 ca (`start_session` ACL/state/replay/điểm danh sau start; tích hợp create→publish→join→approve→start→điểm danh; join→approve→cancel→đăng ký lại giữ `player_id`) và thay fixture `UPDATE sessions SET lifecycle` bằng `start_session` thật ở 2 ca điểm danh.
- Lệnh đã chạy trên nhánh `feat/bh05-integration` (code `a41b48a`): `flutter analyze` (**0 issue**); `flutter test` (**137/137 PASS**); runner BH-05 **90/90 PASS** (`bh05_test_results_20261016001243.json`); chạy lại runner BH-02/03/04 — tổng DB **251/251 PASS**.
- Không có phát hiện nào bị bỏ (I1, I2 đều sửa). Ngoài phạm vi review: không thêm `end_session`/hoàn tất buổi (review không yêu cầu).
- NOT RUN: HTTP/PostgREST/JWT thật, thiết bị/browser e2e, apply staging/production, cạnh tranh qua HTTP. Điều chỉnh phụ do UI đổi: test cũ "host duyệt pending" đổi `scrollUntilVisible` → `ensureVisible` (nút mới làm mục lệch khỏi khung nhìn).

### BH-05 tích hợp — Kết luận cuối cùng reviewer c7ed6d5 (16/10/2026)

- **Trạng thái hiện tại: Chưa đạt tích hợp A+B+C**, theo [review_c7ed6d5.md](reviews/bh05/review_c7ed6d5.md). Còn I1 (P1: thiếu đường start published→in_progress để điểm danh) và I2 (P2: không có hành động đăng ký lại sau hủy).
- Tự chạy: analyze sạch, 132/132 Flutter, 84/84 DB; 2 widget probe FAIL tái hiện lỗi; 1 kiểm tra repository/provider thật qua HTTP bridge local→SQL PASS xác nhận chuỗi đăng ký/duyệt/hủy/rejoin và ranh giới attendance. Không coi bridge là full Supabase JWT/PostgREST.
- Đạt riêng A/B/C không thay nghiệm thu xuyên suốt. NOT RUN/giới hạn trong báo cáo. Không sửa code, merge main hoặc apply remote DB; reviewer tự chốt, không cần xác nhận.

### BH-05 tích hợp — Kết luận cuối cùng reviewer d769531 (16/10/2026)

- **Trạng thái hiện tại: Đạt tích hợp BH-05 A+B+C** tại `d769531` (code sửa I1/I2 `a41b48a`), theo [review_d769531.md](reviews/bh05/review_d769531.md). Reviewer tự chốt, không cần xác nhận.
- Tự chạy: analyze sạch, 137/137 Flutter, 90/90 DB, 2/2 widget probe và 1/1 bridge repository/provider thật→SQL PASS. Chuỗi join/approve/cancel/rejoin/start/attendance không dùng UPDATE lifecycle trực tiếp.
- Các trạng thái Chưa đạt/Chờ review trước đây là lịch sử. NOT RUN/giới hạn trong báo cáo: full Supabase HTTP/JWT, thiết bị/browser e2e, staging/production apply; bridge local không thay các cổng này. Không merge main hoặc tự triển khai ticket tiếp theo.

### BH-05 — Kiểm thử lại main sau merge (16/10/2026)

- Tested HEAD `3a34883`, checkout sạch trước/sau chạy; **Đạt kiểm thử hồi quy**: analyze sạch, 137/137 Flutter, 251/251 DB (BH02 33+14, BH03 48+22, BH04 44, BH05 90), tất cả exit 0.
- [Báo cáo và bằng chứng](reviews/bh05/review_main_3a34883.md). PostgreSQL cô lập/Auth stub; HTTP/JWT thật, thiết bị/browser e2e và staging/production apply vẫn NOT RUN. Không sửa code hoặc apply remote DB.
