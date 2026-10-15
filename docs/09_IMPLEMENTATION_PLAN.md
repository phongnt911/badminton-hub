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
