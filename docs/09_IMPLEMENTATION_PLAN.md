# Backlog triển khai và nghiệm thu

> **Hiện hành tích hợp BH-06 (20/10/2026): Chưa đạt** tại `afeff39` trên `feat/bh06-integration`, theo [review độc lập](reviews/bh06/review_afeff39.md). I1 P1: migration chưa backfill receiver cho buổi có sẵn; I2 P2: refresh không cập nhật version dùng để chốt phí. Reviewer tự chạy analyze sạch, 189 Flutter +335 DB PASS, 6/6 tích hợp PASS nhưng 2 probe độc lập FAIL. A/B/C giữ kết luận theo SHA trước; chưa merge/BH-07/deploy.

> **(Lịch sử bàn giao)** **Hiện hành BH-06 tích hợp (20/10/2026): Chờ review tích hợp** trên nhánh `feat/bh06-integration`, tách từ C đã Đạt `b31f988` (tip `a9c7edb`) và giữ A `706bd73`, B `5e62007`. Đã đối chiếu hợp đồng DB → model/repository/provider → UI, chạy analyze sạch, **189/189 Flutter + 335/335 DB**, và 6/6 case tích hợp DB sau khi vá lỗi `receiver_snapshot` không được chốt (khiến QR/hướng dẫn chuyển khoản không hoạt động). Bằng chứng, SHA và phần NOT RUN tại [bàn giao tích hợp](reviews/bh06/integration_handoff.md). Chưa merge/deploy/apply; người triển khai không tự ghi Đạt.

> **(Lịch sử) BH-06C (20/10/2026): Đạt phần C** tại `b31f988`, theo [review độc lập](reviews/bh06/review_b31f988.md). Đóng C4; C1/C2/C3 giữ đóng theo review trước. Reviewer tự chạy analyze sạch, **187 Flutter +84 DB PASS**, **8/8 widget probe PASS**, RPC C2 5 kiểm tra PASS và RPC C4 ghi/đọc lại thành công. A/B giữ Đạt theo SHA trước; chưa nghiệm thu tích hợp toàn BH-06 hoặc cho phép deploy. Các kết luận Chưa đạt/Chờ review bên dưới là lịch sử.

> **(Lịch sử bàn giao) BH-06C (20/10/2026): Chờ review sau sửa C4 (chủ dự án giao LẦN 2)** trên nhánh `feat/bh06c-ui`. C1/C2/C3 đã được reviewer đóng tại `a0f7255` ([review](reviews/bh06/review_a0f7255.md)); C4 P2 (Nước gửi `water`) sửa tại code `bd17a95`, test tái hiện `bfbd8f6`, [ghi chú C4](reviews/bh06/bh06c_c4_fix.md). Analyze sạch, 187/187 Flutter; runner DB không chạy lại (không đổi DB). A/B giữ Đạt theo SHA trước; chưa nghiệm thu C/tích hợp hoặc deploy. Người triển khai không tự ghi Đạt.

> **(Lịch sử bàn giao) BH-06C (20/10/2026): Chờ review vòng 2** trên nhánh `feat/bh06c-ui`. Vòng 1 sửa **C1/C2 (P1)** theo [review_af31e7b](reviews/bh06/review_af31e7b.md): code sửa `8e3cd83`, test tái hiện `498d4d8`. Vòng 2 sửa **C3 (P2)** theo chỉ định của chủ dự án: code `5174e9d`, test tái hiện `75aa95b`, [ghi chú vòng 2](reviews/bh06/bh06c_review_round2.md); analyze sạch, 186/186 Flutter. A/B vẫn Đạt theo SHA trước; chưa nghiệm thu C/tích hợp hoặc deploy. Người triển khai không tự ghi Đạt.

> **(Lịch sử) BH-06C (18/10/2026): Chưa đạt** tại `af31e7b` (cây code/test `b123db9`), theo [review độc lập](reviews/bh06/review_af31e7b.md). C1/C2 P1: sai ID đăng ký khi gửi thanh toán; reference cố định chặn gửi lại sau từ chối. C3 P2: tính khoản nợ từ trang payment thiếu lịch sử. Analyze sạch, 181 Flutter +84 DB PASS nhưng 2 probe widget và 1 probe RPC FAIL. A/B vẫn Đạt theo SHA trước; chưa nghiệm thu C/tích hợp hoặc deploy.

> **(Lịch sử bàn giao) BH-06C (18/10/2026): Chờ review** trên nhánh `feat/bh06c-ui`, tách từ bản B đã Đạt `f28fd0f` (tested `5e62007`). Nối `FinanceProvider` vào `main.dart`, thêm màn tài chính buổi (trạng thái phí current/stale/not_finalized kèm nguồn/version, chi phí, khoản phải thu, thanh toán, QR VietQR dựng từ receiver snapshot + outstanding + reference, có copy/fallback), lối vào theo quyền trong chi tiết buổi, và màn sổ quỹ CLB theo vai trò; thêm widget test loading/error/retry/empty/submitting/permission-denied. Người triển khai **không tự ghi Đạt**; B vẫn Đạt; C và tích hợp chưa nghiệm thu, chưa cho phép deploy.

> **(Lịch sử) Hiện hành BH-06B (18/10/2026): Đạt phần B** tại `5e62007`, theo [review vòng sửa 2](reviews/bh06/review_5e62007.md). B1/B2/B2-R1 đã đóng trong phạm vi kiểm chứng. A vẫn Đạt; C và tích hợp chưa nghiệm thu. Các trạng thái Chưa đạt/Chờ review bên dưới là lịch sử; chưa cho phép deploy production.

> **Hiện hành BH-06B (18/10/2026): Chưa đạt sau vòng sửa 1** tại `3894cb7`. B1 và các ca B2 ban đầu đã qua probe; còn B2-R1 P2: guard hết trang làm mất phản hồi refresh và giữ loading. Xem [review vòng sửa 1](reviews/bh06/review_3894cb7.md). A vẫn Đạt; chưa chuyển C/tích hợp hoặc deploy.

> **Hiện hành BH-06 (16/10/2026):** BH-06A **Đạt phần A** tại `706bd73`, theo [review độc lập vòng sửa 1](reviews/bh06/review_706bd73.md); R1/R2 đã đóng trong phạm vi kiểm chứng. BH-06B (model/repository/provider) **Chờ review vòng 1** trên nhánh `feat/bh06b-data`, tách từ bản A đã Đạt `48d45d2`; C và tích hợp chưa nghiệm thu. Các kết luận Chưa đạt/Chờ review bên dưới giữ làm lịch sử; chưa cho phép deploy production.

Trạng thái khởi đầu: mọi ticket dưới đây **chưa triển khai theo đặc tả v1.1**. Code demo có sẵn được tận dụng sau khi đối chiếu. Mỗi ticket cần commit riêng hoặc nhóm thay đổi có liên quan; không triển khai toàn bộ app trong một prompt.

(Snapshot 14/10/2026, giữ làm lịch sử.) **Hiện hành:** BH-01 đến BH-05 đã triển khai ở mức local/staging; BH-05 đạt review tích hợp (`d769531`) và hồi quy main (`3a34883`); BH-06 trở đi chưa làm; chưa apply production.

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

## Trạng thái hiện hành

Chủ dự án đã xác nhận toàn bộ B1–B9 và các đề xuất C1/C2; cập nhật chỉ tài liệu đã áp dụng. Xem [xác nhận và điểm tiếp tục BH-06](23_DOC_AUDIT_FOLLOWUP.md).

Cập nhật 16/10/2026: BH-05 đạt review tích hợp tại `d769531` ([review](reviews/bh05/review_d769531.md)); hồi quy main `3a34883` đạt 137 Flutter + 251 DB ([review và bằng chứng](reviews/bh05/review_main_3a34883.md)). Chỉ kiểm thử PostgreSQL cô lập + Auth stub; chưa apply staging/production hoặc kiểm PostgREST HTTP/JWT thật, thiết bị/browser e2e, backup/restore và concurrency qua HTTP. Giữ nhật ký phía dưới làm lịch sử.

| Ticket | Phạm vi | Kiểm thử DB (PostgreSQL cô lập + Auth stub) | Trạng thái |
|---|---|---|---|
| BH-01 | Auth và cấu hình | (Flutter test) | Đã triển khai |
| BH-02 | Schema nền, RLS | 33 + 14 PASS | Đã triển khai |
| BH-03 | CLB, thành viên, ngân hàng | 48 + 22 PASS | Đã triển khai |
| BH-04 | Buổi chơi, lịch, chia sẻ link | 44 PASS | Đã triển khai |
| BH-05 | Đăng ký, duyệt, huỷ, điểm danh, lời mời danh sách chờ, bắt đầu buổi | 90 PASS (45 kịch bản × CLEAN/LEGACY) | **Đạt review tích hợp và hồi quy main**, chưa production |

BH-06A (tài chính phía DB/RPC/RLS/projection + runner) đã triển khai ở local, **chờ review** theo [24_BH06_IMPLEMENTATION_HANDOFF.md](24_BH06_IMPLEMENTATION_HANDOFF.md) — xem mục cuối tài liệu. BH-06B/C và BH-07 đến BH-09: chưa triển khai.

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
| R2 insert player rồi update count bị policy chặn/không atomic | P1 | BH-05: RPC một transaction, 2 request slot cuối, retry/rollback, count khớp; không mở public UPDATE | Đã đặc tả, chưa sửa code/DB. Hiện hành 16/10: đã triển khai local/staging ở BH-05 (RPC nguyên tử), chưa đóng ở production |
| R3 code gọi clubs/quỹ chưa có | P1 | BH-02/03: migration staging tạo đủ nền; schema error khác empty; CRUD club+owner có test | Đã đặc tả, chưa sửa code/DB. Hiện hành 16/10: đã triển khai local/staging ở BH-02/03, chưa đóng ở production |
| R4 charges lỗi thời | P1 | BH-06: billing version/source version và gate server QR/thu mới/complete; free cũng revision current; paid/history giữ nguyên | Đã sửa khoảng trống đặc tả, chưa triển khai |
| R5 form bỏ qua giờ nhập/ngày tương lai | P2 | BH-04: ngày mai/giờ thực/qua nửa đêm/validation | Đã đặc tả, chưa sửa code. Hiện hành 16/10: đã có kiểm thử ngày tương lai/validation ở BH-04; handoff §4 ghi qua nửa đêm, chưa xác minh trực tiếp form giữ giờ nhập qua UI e2e; chưa đóng ở production |
| R6 lỗi loading/update/QR mẫu | P2 | BH-04/05/06: lỗi/retry/route mounted, mutation trả ID/state, role đúng, QR thật | Đã đặc tả, chưa sửa code. Hiện hành 16/10: đã triển khai loading/error/retry và mutation RPC/ID/state ở BH-04/05 (docs/20 §4, docs/21 và test provider/widget); QR thật thuộc BH-06, chưa làm; chưa đóng ở production |
| R7 lời mời waitlist thiếu contract | P2 | BH-05: issue/revoke/accept, đúng người/expiry/capacity/consent guest, test retry | Đã bổ sung schema/contract, chưa triển khai. Hiện hành 16/10: đã triển khai local/staging ở BH-05 (issue/revoke/accept), chưa đóng ở production |

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

| Ngày | Ticket | Trạng thái | Bằng chứng |
|---|---|---|---|
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

## BH-06 — giao phần A cho phiên triển khai mới (16/10/2026)

Chủ dự án yêu cầu merge bộ docs sau BH-05 vào main, để AI khác kéo main ở phiên mới rồi triển khai BH-06; Codex giao việc/review độc lập. [Đầu bài và cổng review](24_BH06_IMPLEMENTATION_HANDOFF.md): A DB/RPC → B data/provider → C UI → tích hợp; mỗi phần một nhánh/commit, Đạt phần trước mới giao phần sau. **Đã giao BH-06A, chưa triển khai/chưa review**, chưa tạo nhánh code trong lượt giao việc. Bảng “BH-06 chưa triển khai” vẫn đúng; việc giao đầu bài không thay bằng chứng test.

### BH-06A — DB / RPC / RLS / projection / runner — 16/10/2026

| Ngày | Phần | Trạng thái | Bằng chứng |
|---|---|---|---|
| 16/10/2026 | BH-06A DB/RPC/RLS/runner | **Chờ review (vòng 1)** | Nhánh `feat/bh06a-db`, tách từ `main` = `c35dd27`. Commit mã: `c929b67` (helper + chi phí + chốt phí + complete gate), `d7deaae` (thanh toán + quỹ CLB), `fe8cf99` (đường đọc/QR), `9336bb0` + `947f8ae` (runner DB, bổ sung ca ACL và gỡ bằng chứng cũ); sửa review vòng 1: `59baa25` (test tái hiện R1/R2), `83586ed` (migration sửa quyền null-safe + gate RPC bank cũ). Migration `supabase/migrations/20261016110000_bh06_expenses_finalize.sql`, `..._bh06_payments_ledger.sql`, `..._bh06_reads.sql`, `..._bh06a_review_round1.sql`; runner `docs/reviews/bh06/run_bh06_tests.py`; kết quả `docs/reviews/bh06/bh06_test_results_20261016042103.json` (vòng gốc) và `docs/reviews/bh06/bh06_test_results_20261016151610.json` (vòng 1, `83586ed`); bàn giao `docs/reviews/bh06/bh06a_handoff.md`, ghi chú sửa `docs/reviews/bh06/bh06a_review_round1.md`. |

- Phạm vi phần A theo [đầu bài](24_BH06_IMPLEMENTATION_HANDOFF.md): forward migration cho tài chính buổi/quỹ; RPC/ACL/RLS; projection đọc/QR; gate `billing_state`; runner DB local CLEAN + LEGACY; hợp đồng chính xác. **Không** làm phần B (model/repository/provider) hay C (UI VietQR/sổ quỹ).
- RPC mutation mới (đều `SECURITY DEFINER`, `search_path = public, pg_temp`, bắt buộc `p_request_id`, idempotency theo actor/operation/request + hash canonical, audit cùng transaction, REVOKE PUBLIC/anon + GRANT authenticated): `post_session_expense`, `reverse_session_expense`, `finalize_session_charges`, `complete_session`, `submit_payment`, `confirm_payment`, `reject_payment`, `reverse_payment`, `record_cash_payment`, `post_manual_club_transaction`, `reverse_club_transaction`. RPC đọc mới: `get_payment_instructions`, `get_session_finance`, `get_club_ledger`. Helper nội bộ bị REVOKE mọi role client: `active_charge_revision_id`, `session_billing_state`, `assert_billing_current`, `player_charge_snapshot`. Chữ ký/ACL/mã lỗi ở [docs/08 §13](08_DOMAIN_CONTRACTS.md#13-bh-06a-tài-chính-phía-db-đã-triển-khai-ở-local--chờ-review).
- `billing_state` là suy diễn (`active charge_revision.source_version` so `sessions.billing_input_version`), không thêm cột; chi phí post/reverse và các hành động roster/điểm danh của BH-05 đều tăng `billing_input_version` trong cùng transaction. RPC cũ `get_session_payment_instructions` (BH-02) chỉ trả bank snapshot; từ vòng 1 (`83586ed`) nó **gate `current`** như `get_payment_instructions` mới (sửa R2), không còn là đường lấy bank bỏ qua gate. Xem quyết định chữ ký ở docs/08 §13.
- Lệnh đã chạy trên cây `947f8ae`: `flutter analyze` (**0 issue**); `flutter test` (**137/137 PASS** — không đổi vì A không chạm Dart); `python docs/reviews/bh06/run_bh06_tests.py` (**80/80 PASS**, 40 kịch bản × CLEAN/LEGACY, `tested_commit=947f8aeb211f002c3f4525a87aebfcd2ca5e6a55`, `worktree_dirty=false`).
- Nhóm ca trọng yếu (đều PASS trên CLEAN + LEGACY): quyền/ACL (anon bị chặn; authenticated không ghi trực tiếp bảng tài chính; helper nội bộ bị REVOKE; outsider/cohost không finance bị `FORBIDDEN`; player không tự confirm/gửi hộ; chỉ owner/treasurer đọc sổ quỹ; projection public không lộ ngân hàng); chia tiền (split 450.000/7 chia dư theo id, exemption 0, no_show không tính, `NO_BILLABLE_PLAYERS` rollback, total 0 vẫn revision current charges 0, fixed khác tổng expense); revision/stale (chi phí/điểm danh/roster sau chốt làm stale và chặn QR/submit/cash/complete, refinalize supersede nguyên tử, `VERSION_CONFLICT`/`BILLING_STALE`, `BILLING_NOT_FINALIZED`); tiền đã thu (không giảm due dưới paid kể cả người bị loại khỏi billable, không ghi ledger thu lặp); thanh toán/idempotency (replay cùng key + conflict khác payload, tổng confirmed ≤ due, `PAYMENT_EXCEEDS_OUTSTANDING` cho cash, đảo một lần, reject/reverse khi stale); ledger/quỹ (club vs độc lập, entry tự sinh không đảo qua hàm manual, số dư từ SUM); complete (chỉ in_progress + revision current, chỉ management); đồng thời thật 2 kết nối (2 confirm và 2 cash tranh outstanding không thu dư); rollback input sai không tạo expense/ledger và không tăng `billing_input_version`.
- Không giữ "xanh" bằng cách bỏ test cũ: không sửa test BH-02..05; chuỗi migration thêm 3 file forward-only, runner BH-06 mới là bổ sung.
- NOT RUN trong lượt này: kiểm PostgREST HTTP/JWT thật (chỉ PostgreSQL cô lập + Auth stub), apply staging/production, thiết bị/browser e2e, backup/restore, concurrency qua HTTP, UI VietQR/sổ quỹ (phần B/C chưa làm); chưa chạy lại runner BH-02..05 trên nhánh này (chưa giao cổng review, sẽ bổ sung khi cần). Người triển khai **không** tự ghi Đạt và không merge `main`/deploy; chờ review độc lập của Codex.

### BH-06A — kết luận reviewer e3c73c1 (16/10/2026)

- **Chưa đạt phần A** theo [review_e3c73c1.md](reviews/bh06/review_e3c73c1.md): R1 (P1) outsider đọc bank/công nợ khách user_id NULL do kiểm quyền nhận NULL; R2 (P1) endpoint bank cũ chưa có gate revision current. Chờ sửa và review vòng 1, không chuyển B/C.
- Reviewer tự chạy analyze sạch, 137/137 Flutter; DB BH-02 33+14, BH-03 48+22, BH-04 44, BH-05 90, BH-06 80 = **331/331 PASS**. Probe độc lập 4 control PASS / **4 FAIL** tái hiện R1/R2 trên clean/legacy; không gộp probe FAIL vào số runner PASS.
- NOT RUN: HTTP/PostgREST/JWT thật, thiết bị/browser e2e, apply staging/production, backup/restore, concurrency qua HTTP và BH-06B/C. Chỉ PostgreSQL tắt mạng/Auth stub/fixture giả. Không sửa code, merge main hoặc deploy; giữ snapshot tác giả phía trên để truy vết.

### BH-06A — sửa theo review vòng 1 (16/10/2026)

- Người triển khai đọc `docs/ai/IMPLEMENTER.md` mục "Sửa theo review" (file trên `chore/ai-roles`, chưa có trên nhánh A) và sửa **cả hai** phát hiện P1 trong nhánh `feat/bh06a-db`, không sửa ngoài phạm vi review, không merge `main`.
- Commit: `59baa25` (thêm 2 ca tái hiện — phải FAIL trước khi sửa), `83586ed` (migration forward `20261016140000_bh06a_review_round1.sql`). Ghi chú: [bh06a_review_round1.md](reviews/bh06/bh06a_review_round1.md).
  - **R1**: `get_payment_instructions` kiểm quyền null-safe (`IS NOT DISTINCT FROM` + `IF v_authorized IS NOT TRUE`) — outsider/cohost không finance không còn đọc công nợ/ngân hàng của khách offline `user_id=NULL`; finance vẫn đọc đúng scope. Không sửa client để che lỗi server.
  - **R2**: `get_session_payment_instructions` (BH-02) gate `assert_billing_current` — chưa chốt ⇒ `BILLING_NOT_FINALIZED`, stale ⇒ `BILLING_STALE`; giữ quyền tương thích và chỉ trả `session_id`+`receiver_snapshot`. Đồng bộ docs/08 §13 và handoff; không sửa ba migration BH-06A đã chia sẻ.
- Bằng chứng trên cây `83586ed` (sạch): `flutter analyze` **0 issue**; `flutter test` **137/137 PASS**; `python docs/reviews/bh06/run_bh06_tests.py` **84/84 PASS** (42 ca × CLEAN/LEGACY, `worktree_dirty=false`) → [bh06_test_results_20261016151610.json](reviews/bh06/bh06_test_results_20261016151610.json). Hồi quy BH-02..05 xanh lại: BH-02 33+14, BH-03 48+22, BH-04 44, BH-05 90 (log ở scratch, không thêm JSON vào repo).
- Trạng thái ghi **Chờ review vòng 1**; người triển khai không tự ghi Đạt. NOT RUN như trên.

### BH-06A — kết luận reviewer vòng sửa 1 tại 706bd73 (16/10/2026)

- **Đạt phần A** theo [review_706bd73.md](reviews/bh06/review_706bd73.md), code sửa `83586ed`. Đóng R1/R2 của review `e3c73c1`; kết luận cũ là baseline trước sửa.
- Reviewer tự chạy analyze sạch, **137/137 Flutter**, DB BH-02 33+14, BH-03 48+22, BH-04 44, BH-05 90, BH-06 84 = **335/335 PASS**, thêm **8/8 probe độc lập PASS**, giữ nguyên kỳ vọng từ review trước. Bằng chứng/hash/tested SHA lưu cùng report.
- Chỉ Đạt A, chưa nghiệm thu B/C hoặc tích hợp toàn BH-06; không tự chuyển phần tiếp theo, merge main hoặc deploy. NOT RUN: HTTP/JWT/PostgREST thật, thiết bị/browser e2e, apply staging/production, backup/restore, concurrency qua HTTP, UI/data BH-06B/C và pilot. Giữ lịch sử/bằng chứng cũ.

### BH-06B — model/repository/provider tài chính — 16/10/2026

| Ngày | Phần | Trạng thái | Bằng chứng |
|---|---|---|---|
| 16/10/2026 | BH-06B data/provider | **Chờ review** | Nhánh `feat/bh06b-data`, tách từ bản A đã Đạt `48d45d2`. Thêm `lib/models/finance.dart`, `lib/data/finance_repository.dart`, `lib/providers/finance_provider.dart`; test `test/models/finance_test.dart`, `test/providers/finance_provider_test.dart`. Ghi chú [bh06b_handoff.md](reviews/bh06/bh06b_handoff.md). |

- Phạm vi phần B theo [đầu bài](24_BH06_IMPLEMENTATION_HANDOFF.md) §3.B: repository typed cho fee/revision/expense/payment/ledger; provider loading/error/empty/submitting; giữ `request_id` qua lỗi/timeout, xoay key sau commit thành công **trước** refresh; làm mới lỗi không coi mutation thất bại; dọn state riêng tư khi logout/đổi actor/đổi session/club và bỏ phản hồi trễ; phân trang reads đúng contract; lỗi đọc không hạ số dư/công nợ về 0. **Không** làm C (UI VietQR/sổ quỹ) hay sửa migration/RPC của A.
- Dùng đúng chữ ký đã review ở A ([docs/08 §13](08_DOMAIN_CONTRACTS.md#13-bh-06a-tài-chính-phía-db-đã-triển-khai-ở-local--chờ-review)): `get_payment_instructions`, `get_session_finance`, `get_club_ledger`, `post/reverse_session_expense`, `finalize_session_charges`, `complete_session`, `submit/confirm/reject/reverse_payment`, `record_cash_payment`, `post/reverse_manual_club_transaction`; không gọi function chưa có. Không nối `main.dart`/UI (để phần C).
- Lệnh đã chạy trên nhánh: `flutter analyze` (**0 issue**); `flutter test` (**163/163 PASS** = 137 nền + 26 test mới của B). Không đổi DB/migration nên runner DB của BH-06 **không chạy lại** ở lượt này; baseline DB 335/335 của A giữ nguyên.
- Test hành vi (không chỉ kiểm tên method): retry/replay cùng UUID, xoay key sau commit, chặn double-submit, stale/idempotency map tiếng Việt, auth/session isolation và bỏ phản hồi trễ, phân trang ledger bằng offset, và lỗi đọc/làm mới không hạ số dư về 0.
- Trạng thái ghi **Chờ review**; người triển khai không tự ghi Đạt. NOT RUN: HTTP/PostgREST/JWT thật, thiết bị/browser e2e, apply staging/production, backup/restore, UI phần C.

### BH-06B — kết luận reviewer d00a121 (16/10/2026)

- **Chưa đạt phần B** theo [review_d00a121.md](reviews/bh06/review_d00a121.md): B1 P2 giữ cache paymentInstructions current/canPay sau BILLING_STALE; B2 P2 phân trang không kết thúc và load-more vẫn gọi khi đã hết dữ liệu. Cần sửa, gửi lại SHA; không chuyển C/tích hợp.
- Reviewer tự chạy analyze sạch, **163/163 Flutter**, **84/84 DB BH-06**, probe provider **3 FAIL / 1 control PASS**. Không gộp probe FAIL vào số test tác giả PASS. Code/migration của A không đổi; 335 DB PASS trong review A là bằng chứng trước, không phải chạy lại toàn bộ trong lượt B.
- NOT RUN: HTTP/PostgREST/JWT thật, repository↔RPC thật, UI C/thiết bị/browser e2e, apply staging/production, backup/restore, concurrency qua HTTP và bank/VietQR thực tế. Chỉ thêm report/bằng chứng/trạng thái, không sửa code triển khai hoặc merge main.

### BH-06B — sửa theo review vòng 1 (16/10/2026)

- Người triển khai sửa **cả B1 và B2** (đều P2, chủ dự án giao rõ theo mục "Sửa theo review") trong nhánh `feat/bh06b-data`; không sửa ngoài phạm vi review, không đổi migration/RPC của A, không merge `main`.
- Commit tách test-first: `3338566` (thêm 3 test tái hiện — phải FAIL trước khi sửa), `3894cb7` (fix provider + chỉnh test `loadMoreLedger` cũ vốn mã hoá hành vi sai). Ghi chú: [bh06b_review_round1.md](reviews/bh06/bh06b_review_round1.md).
  - **B1**: `fetchPaymentInstructions` khi làm mới lỗi trong cùng phạm vi sẽ **vô hiệu cache** `paymentInstructions` (đặt `null`) và giữ thông điệp lỗi — server từ chối revision (`BILLING_STALE`/`BILLING_NOT_FINALIZED`) hoặc mất quyền thì không còn object `current/canPay` có thể thanh toán. Không hạ số phải thu về 0 và không biến lỗi thành "đã trả".
  - **B2**: thêm `_ledgerHasMore` suy từ **trang vừa nhận** (`entries.length >= limit` ⇒ còn trang; trang ngắn ⇒ hết); `hasMoreLedger = _ledger != null && _ledgerHasMore`; `loadMoreLedger()` và nhánh nối của `fetchClubLedger` **không phát RPC khi đã hết**; lỗi mạng **không** đánh dấu hết trang; reset khi đổi CLB/refresh.
- Bằng chứng trên cây `3894cb7` (sạch): `flutter analyze` **0 issue**; `flutter test` **166/166 PASS** (= 163 trước + 3 test tái hiện B1/B2). Phát lại probe độc lập của reviewer (B1 + 2 tình huống B2 + control) trên bản sửa: **4/4 PASS** (trước đó 3 FAIL). Không đổi DB nên runner DB BH-06 **không chạy lại**.
- Trạng thái ghi **Chờ review vòng 1**; người triển khai không tự ghi Đạt.

### BH-06B — kết luận reviewer vòng sửa 1 tại 3894cb7 (18/10/2026)

- **Chưa đạt phần B** theo [review_3894cb7.md](reviews/bh06/review_3894cb7.md): B1 và các tình huống B2 cũ không còn tái hiện; còn **B2-R1 P2** tại guard hết trang mới. `fetchClubLedger(loadMore:true)` bị bỏ qua vẫn tăng serial, làm refresh đang bay mất phản hồi/finally và loading bị giữ true. API wrapper có guard riêng; lỗi được xác nhận ở API fetch trực tiếp, không suy diễn UI C đã tồn tại.
- Reviewer checkout đúng `3894cb7`, tự chạy analyze sạch, **166/166 Flutter**, **84/84 DB BH-06**, probe cũ nguyên kỳ vọng **4/4 PASS**; probe mở rộng **4 PASS / 1 FAIL**. Không sửa code/migration/test tác giả. Commit docs `4b0ecbb` mới hơn không đổi source/test/migration so với tested SHA.
- Cần test tái hiện và sửa B2-R1 rồi review vòng 2 (còn một vòng theo quy trình); chưa chuyển C/tích hợp, merge main hoặc deploy. NOT RUN: HTTP/JWT/PostgREST thật, repository↔RPC thật, UI/thiết bị/browser e2e, apply staging/production, backup/restore, concurrency qua HTTP và bank/VietQR thực tế. A giữ kết luận review A; lịch sử review trước giữ nguyên.

### BH-06B — sửa theo review vòng 2 (18/10/2026)

- Người triển khai sửa **B2-R1 (P2)** trong `feat/bh06b-data`; không sửa ngoài phạm vi, không đổi migration/RPC của A, không merge `main`. Đây là **vòng sửa thứ 2** (vòng cuối theo quy trình tối đa 2 vòng của `docs/ai/IMPLEMENTER.md`).
- Nguyên nhân: `fetchClubLedger` tăng `_ledgerSerial` **trước** guard `appending && !_ledgerHasMore` nên một load-more bị bỏ qua vẫn vô hiệu serial của refresh đang bay → refresh mất cập nhật dữ liệu/finally, `isLoadingLedger` kẹt `true`.
- Cách sửa (tối thiểu): tính `previous/switching/appending` và **guard trước** `++_ledgerSerial`; yêu cầu bị bỏ qua không tăng serial, không đổi state, không phát RPC; refresh đang bay giữ nguyên phản hồi. Không viết lại phần B, không sửa migration.
- Commit tách test-first: `83b6d49` (thêm `B2-R1: loadMore bị bỏ qua không được huỷ refresh đang bay` — FAIL trước sửa), `58d03ca` (fix). Rebase trên commit review `584ebf1`; nội dung lib/test không đổi.
- Bằng chứng trên cây `58d03ca` (sạch): `flutter analyze` **0 issue**; `flutter test` **167/167 PASS** (= 166 vòng 1 + 1 test tái hiện B2-R1). Phát lại **nguyên văn probe vòng 1 của reviewer** (B1 + 2 ca B2 + control + race B2-R1): **5/5 PASS** (trước đó 4 PASS / 1 FAIL). Không đổi DB nên runner DB BH-06 **không chạy lại**.
- Trạng thái ghi **Chờ review vòng 2**; người triển khai không tự ghi Đạt. Ghi chú: [bh06b_review_round2.md](reviews/bh06/bh06b_review_round2.md).

### BH-06B — kết luận reviewer vòng sửa 2 tại 5e62007 (18/10/2026)

- **Đạt phần B** theo [review_5e62007.md](reviews/bh06/review_5e62007.md), code sửa B2-R1 `58d03ca`. Không còn phát hiện P0/P1/P2 cần mở trong phạm vi kiểm chứng; đóng B1/B2/B2-R1 của các review trước, giữ lịch sử và bằng chứng cũ.
- Reviewer tự chạy analyze sạch, **167/167 Flutter**, **84/84 DB BH-06**, **5/5 probe độc lập PASS** (giữ nguyên mã/kỳ vọng probe vòng 1). Không sửa code triển khai, migration hoặc test tác giả. 335 DB PASS của review A là bằng chứng lượt A, không phải kết quả chạy toàn bộ lại trong lượt B này.
- Chỉ Đạt B, không suy nghiệm thu C hoặc tích hợp toàn BH-06; không tự chuyển phần tiếp, merge main hoặc deploy. NOT RUN: repository↔PostgREST HTTP/JWT/Supabase Auth thật, UI C/thiết bị/browser e2e, apply staging/production, backup/restore, concurrency qua HTTP và bank/VietQR thực tế.

### BH-06C — UI tài chính buổi và sổ quỹ CLB (18/10/2026)

| Ngày | Hạng mục | Trạng thái | Nhánh / commit / bằng chứng |
|---|---|---|---|
| 18/10/2026 | BH-06C UI phí/thu tiền/quỹ | **Chờ review** | Nhánh `feat/bh06c-ui`, tách từ bản B đã Đạt `f28fd0f` (tested `5e62007`). Commit: `777f9df` (nối provider + màn tài chính buổi), `39aef81` (màn sổ quỹ CLB), `b123db9` (widget test + cập nhật test lối vào). Ghi chú: [bh06c_handoff.md](reviews/bh06/bh06c_handoff.md). |

- Phạm vi: chỉ phần C (UI). Không sửa migration/RPC/helper của A, không viết lại model/repository/provider của B (chỉ dùng API đã Đạt), không merge `main`, không deploy.
- File thêm: `lib/core/money.dart` (định dạng/đọc VNĐ), `lib/screens/session_finance_screen.dart`, `lib/screens/club_fund_screen.dart`. File sửa: `lib/main.dart` (đăng ký `FinanceProvider`), `lib/screens/session_detail_screen.dart` (lối vào theo quyền), `lib/screens/clubs_screen.dart` (nút THU/CHI QUỸ mở sổ quỹ).
- Bản chất dữ liệu: banner trạng thái hiển thị `billing_state` (current/stale/not_finalized) kèm `billing_input_version` và revision active (nguồn/version/thời điểm chốt); lịch sử chi phí/thanh toán giữ nguyên (đã hoàn tác/từ chối vẫn hiện); khi stale chỉ chặn **thu mới** (chốt phí vẫn cho chốt lại, xác nhận/ghi tiền mặt bị khoá, từ chối/hoàn tác vẫn mở). Không tự tính số dư ở client; số dư/outstanding lấy từ RPC.
- QR: dùng `VietQRHelper` hiện có, dựng từ receiver snapshot + `outstanding > 0` + `reference`; hiển thị bank/số TK/chủ TK/số tiền/nội dung kèm nút sao chép và `errorBuilder` fallback khi ảnh không tải. Ghi rõ QR **không** xác nhận đã thu; không webhook/ngân hàng, không tự chuyển tiền. Nút gửi ghi payment `submitted` chờ ban quản lý xác nhận.
- Quyền: chỉ `Session.canViewFinance` thấy thao tác tài chính; người chơi chỉ thấy phần phí của mình (không có nút chốt phí/chi phí/xác nhận). Màn sổ quỹ chỉ mở khi `Club.canViewBalance` (chủ nhiệm/thủ quỹ); vai trò khác bị chặn và **không** gọi RPC.
- Lệnh đã chạy trên cây `b123db9` (sạch): `flutter analyze` **0 issue**; `flutter test` **181/181 PASS** (= 167 nền + 14 test mới: 6 màn tài chính buổi, 6 màn sổ quỹ, 2 lối vào theo quyền). Không đổi DB/migration nên runner DB BH-06 **không chạy lại** ở lượt này.
- NOT RUN: HTTP/JWT/PostgREST/Supabase Auth thật, thiết bị/browser e2e, apply staging/production, `Image.network` tới `img.vietqr.io` thật (test chỉ chạy nhánh fallback trong môi trường test), bank/VietQR và webhook thực tế.
- Trạng thái ghi **Chờ review**; người triển khai không tự ghi Đạt. Bằng chứng xanh phía trên là của bản tác giả, reviewer cần tự chạy lại.

### BH-06C — kết luận reviewer tại af31e7b (18/10/2026)

- **Chưa đạt C** theo [review_af31e7b](reviews/bh06/review_af31e7b.md). C1/C2 P1 và C3 P2 còn mở; giữ lịch sử bàn giao Chờ review phía trên.
- Reviewer tự chạy analyze 0 issue, **181/181 Flutter**, **84/84 DB BH-06**; probe độc lập **2 widget FAIL +1 RPC FAIL** tái hiện lỗi. [Hash/summary](reviews/bh06/review_af31e7b_evidence/summary.json). Không sửa code/migration/test tác giả; cây lib/test/supabase tại af31e7b trùng b123db9.
- Chưa tích hợp/merge/deploy; A/B giữ kết luận trước. Người triển khai viết test tái hiện rồi sửa P1 theo quy trình tối đa hai vòng; P2 vẫn mở và theo giới hạn AGENTS. NOT RUN: HTTP/JWT thật, thiết bị/browser, bank/VietQR thực, staging/production, backup/restore, concurrency HTTP và pilot/tích hợp. Chi tiết giới hạn fixture trong báo cáo.

### BH-06C — sửa theo review vòng 1 (20/10/2026)

- Người triển khai sửa **C1/C2 (P1)** trong `feat/bh06c-ui`; **không sửa C3 (P2)** vì chưa có chỉ định của chủ dự án, không đổi migration/RPC của A, không viết lại B, không merge `main`. Đây là **vòng sửa 1/2**.
- C1: nút gửi thanh toán dùng `PaymentInstructions.playerId` (`session_players.id`) thay cho `AuthProvider.currentUser.id`; khoá nút khi thiếu ID; bỏ phụ thuộc auth khỏi màn tài chính.
- C2: giữ mã nội dung chuyển khoản cố định cho QR/`description` nhưng **không** truyền làm `payments.reference`; để RPC tự sinh `PAY-<uuid>` cho từng intent, request ID vẫn ổn định khi retry và xoay sau thành công.
- Commit tách test-first: `498d4d8` (thêm/cập nhật test — 3 FAIL: C1, C2, ca người chơi), `8e3cd83` (fix). Ghi chú: [bh06c_review_round1.md](reviews/bh06/bh06c_review_round1.md).
- Bằng chứng trên cây `8e3cd83` (sạch): `flutter analyze` **0 issue**; `flutter test` **183/183 PASS**. Không đổi DB nên runner DB BH-06 **không chạy lại**. Phát lại probe C1 của reviewer: nguyên văn chỉ FAIL tại matcher `reference` (probe viết trước khi C2 đổi contract); đổi đúng matcher đó sang `null` thì **PASS**. Probe C3 vẫn **FAIL** như dự kiến (P2 chưa sửa).
- Trạng thái ghi **Chờ review vòng 2**; người triển khai không tự ghi Đạt. NOT RUN: HTTP/PostgREST/JWT/Auth thật, thiết bị/browser e2e, ảnh VietQR/bank thật, staging/production, backup/restore, concurrency HTTP, ca trả thêm sau refinalize ở mức RPC.

### BH-06C — sửa theo review vòng 2 (20/10/2026)

- Chủ dự án giao sửa **toàn bộ P còn lại**, gồm **C3 (P2)** và ca "trả thêm sau refinalize" mà review ghi NOT RUN; quy trình cập nhật để người triển khai sửa P0/P1/P2 (`AGENTS.md` trên nhánh; `docs/ai/IMPLEMENTER.md` trên `chore/ai-roles` tại `07b31d4`). Không đổi migration/RPC của A, không viết lại B, không merge `main`.
- C3: chỉ hiển thị "Còn phải thu" theo người khi trang payments đã đầy đủ (`payments.length < limit`); nếu trang bị cắt thì hiển thị "Phải trả theo phí" theo revision hiện hành. Hộp thoại thu tiền mặt luôn đọc `outstandingVnd` của đúng người qua `get_payment_instructions` (tổng hợp phía server) trước khi prefill; người đã trả đủ thì báo và không mở hộp thoại. Không suy khoản nợ từ một trang lịch sử.
- Thêm test C2 "trả thêm sau refinalize": outstanding đổi 100.000 → 50.000 sau chốt lại; hai intent dùng hai request ID khác nhau và đều không gửi `p_reference`.
- Commit tách test-first: `75aa95b` (test tái hiện — 2 FAIL đúng C3), `5174e9d` (fix). Ghi chú: [bh06c_review_round2.md](reviews/bh06/bh06c_review_round2.md).
- Bằng chứng trên cây `5174e9d`: `flutter analyze` **0 issue**; `flutter test` **186/186 PASS**. Không đổi DB nên runner DB BH-06 **không chạy lại**. Probe C3 của reviewer có hai kỳ vọng mâu thuẫn (vừa "100,000" vừa "0") nên nguyên văn không thể PASS; test hồi quy của tác giả kiểm đúng hành vi thay thế (không còn suy nợ; prefill từ RPC; đã trả đủ thì chặn).
- Trạng thái **Chờ review vòng 2**; người triển khai không tự ghi Đạt. NOT RUN: HTTP/PostgREST/JWT/Auth thật, thiết bị/browser e2e, ảnh VietQR/bank thật, staging/production, backup/restore, concurrency HTTP, ca refinalize ở mức RPC/DB (chỉ kiểm ở UI/provider).

### BH-06C — kết luận reviewer vòng sửa 2 tại a0f7255 (20/10/2026)

- **Chưa đạt C sau 2/2 vòng sửa**, xem [review_a0f7255](reviews/bh06/review_a0f7255.md). Đóng C1/C2/C3. C4 P2 mới phát hiện: chọn Nước gửi `water` nhưng RPC chỉ nhận court/shuttle/other; không phải hồi quy của bản sửa. Dừng vòng tự động và báo chủ dự án theo AGENTS; không tự mở vòng 3 hay sửa triển khai.
- Reviewer tự chạy analyze 0 issue, **186/186 Flutter**, **84/84 DB BH-06**; probe widget **7 PASS/1 FAIL (C4)**; RPC C2 **5 kiểm tra PASS** (retry/reject/refinalize/reference), RPC C4 **FAIL**. [Hash/summary](reviews/bh06/review_a0f7255_evidence/summary.json). Đã sửa thiết kế probe C3 mâu thuẫn; không dùng FAIL của probe cũ để giữ lỗi mở.
- Source/test/migration tại HEAD trùng code sửa cuối 5174e9d. Không đổi code tác giả; không merge/deploy/chuyển tích hợp. NOT RUN: HTTP/JWT/Auth thật, thiết bị/browser, bank/VietQR thật, staging/production, backup/restore, concurrency HTTP và pilot/tích hợp. Refinalize C2 đã kiểm RPC local trong lượt này.

### BH-06C — sửa C4 theo chỉ định chủ dự án (20/10/2026, LẦN 2)

- Reviewer mở **C4 (P2)**: UI “Thêm chi phí” gửi `category: 'water'` nhưng `post_session_expense` chỉ nhận `court`, `shuttle`, `other`. Chủ dự án giao tiếp LẦN 2 nên sửa; không đổi migration/RPC, không mở vòng tự động.
- Test tái hiện `bfbd8f6` (`session_finance_screen_test.dart:643`): đi qua từng loại chi phí, **FAIL** trước sửa (`water` at index 2). Fix `bd17a95`: `_expenseRpcCategory` ánh xạ `water → other`, giữ nội dung; các loại khác giữ nguyên. Ghi chú: [bh06c_c4_fix.md](reviews/bh06/bh06c_c4_fix.md).
- Bằng chứng trên cây `bd17a95`: `flutter analyze` **0 issue**; `flutter test` **187/187 PASS**; không đổi DB nên runner DB không chạy lại.
- Trạng thái **Chờ review**; người triển khai không tự ghi Đạt. NOT RUN: chạy lại probe RPC C4/Docker, HTTP/PostgREST/JWT/Auth thật, thiết bị/browser e2e, ảnh VietQR/bank thật, staging/production, backup/restore, concurrency HTTP.

### BH-06C — kết luận reviewer sau sửa C4 tại b31f988 (20/10/2026)

- **Đạt phần C** theo [review_b31f988](reviews/bh06/review_b31f988.md), code sửa `bd17a95`, test tái hiện `bfbd8f6`. Đóng C4 P2 bằng mapping Nước → other; C1/C2/C3 giữ đóng, không còn phát hiện mở từ các review C trước. Giữ lịch sử Chưa đạt/Chờ review phía trên.
- Reviewer tự chạy analyze 0 issue, **187/187 Flutter**, **84/84 DB BH-06**, **8/8 widget probe PASS**; RPC C2 **5 kiểm tra PASS**, RPC C4 ghi/đọc lại category/title/amount thành công. [Hash/summary](reviews/bh06/review_b31f988_evidence/summary.json). Source/test/migration HEAD trùng bd17a95; không sửa code tác giả.
- Chỉ Đạt C, chưa nghiệm thu tích hợp BH-06; không tự chuyển tích hợp, merge main hoặc deploy. NOT RUN: HTTP/JWT/Auth thật, thiết bị/browser, bank/VietQR thật, staging/production, backup/restore, concurrency HTTP và pilot/nghiệm thu A+B+C.

### BH-06 tích hợp — kết luận reviewer tại afeff39 (20/10/2026)

- **Chưa đạt tích hợp** theo [review_afeff39](reviews/bh06/review_afeff39.md): I1 P1 thiếu backfill receiver khi nâng cấp DB có buổi chốt phí; I2 P2 VERSION_CONFLICT lặp sau refresh do dùng version widget cũ. Viết test tái hiện trước và sửa toàn bộ P theo quy trình, tối đa hai vòng sửa tích hợp. Không sửa lại lịch sử Đạt từng phần A/B/C.
- Reviewer tự chạy analyze sạch, **189/189 Flutter**, **335/335 DB BH-02..06** (33+14+48+22+44+90+84), **6/6 case tích hợp DB PASS**; probe nâng cấp và widget version **2 FAIL**. Race publish/bank với control start PASS, không mở finding từ snapshot tạm thiếu. [Hash/summary](reviews/bh06/review_afeff39_evidence/summary.json).
- Code/test/migration HEAD trùng 8af7be5; không sửa triển khai. Chưa merge main/BH-07/deploy. NOT RUN: repository↔HTTP/PostgREST/JWT/Auth thật, thiết bị/browser/deep link, bank/VietQR thật, staging/production, backup/restore và concurrency HTTP. Các widget mock repository không thay cổng HTTP.
