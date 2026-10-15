# Code review BH-02 và đánh giá bổ sung

Ngày 15/10/2026. Review commit `3fa3cdae72ef08895d3ad62f3a31e95dc5b7fa35` trên GitHub main, so với parent `3e6f9c06f48ac77742a1e81ec6387a46488e1fd9`. Commit có 4 file thay đổi. Có migration nền và test cấu trúc, nhưng còn lỗi quyền đọc/ghi helper và projection; chưa đạt nghiệm thu BH-02 để áp dụng production.

## Phạm vi và bằng chứng

Đã lấy nội dung file theo SHA cố định qua GitHub connector vì git fetch từ shell lỗi proxy. Bản tải review nằm tại `/workspace/scratch/bh02-review`; checkout làm việc `/workspace/badminton-hub` không bị ghi đè. Đã đọc toàn bộ migration/test và đối chiếu đặc tả 03/08/ADR v1.1 cùng các quy tắc repo. Chỉ nêu lỗi trên dòng thay đổi của BH-02, không lặp lại lỗi Dart có trước.

Đã truy vấn chỉ đọc metadata các cột legacy trên Supabase thật: sessions.venue_name/play_date/start_time/end_time và session_players.player_name vẫn NOT NULL. Không đọc dữ liệu người dùng, không chạy migration hoặc SQL ghi. Không dùng quyền postgres để chứng minh quyền ứng dụng.

PostgreSQL/psql local không có trên PATH; `docker version` bị chặn truy cập daemon socket. Vì vậy chưa thực thi migration/RLS trên DB cô lập, chưa chạy Flutter suite của checkout mới. Các lỗi dưới đây được xác định từ SQL và ngữ nghĩa grants/RLS; không khẳng định đã khai thác trên live. Báo cáo 37/37 tests trong README là kết quả do commit ghi nhận, không phải kết quả tôi chạy lại.

Skill áp dụng: code-review đã được người dùng chỉ định; dùng các tiêu chí correctness/security và tự lọc lại nhận xét. Đối chiếu Supabase: https://supabase.com/docs/guides/database/postgres/row-level-security .

## Tóm tắt file

- Đã thêm [migration v1.1](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql): tạo bảng, grants/RLS, helper và read projections.
- Đã thêm [schema_v1_1_migration_test.dart](../../../test/schema/schema_v1_1_migration_test.dart): 9 test kiểm tra chuỗi SQL, không thực thi DB.
- Đã cập nhật [README.md](../../../README.md#L64): mô tả migration và tổng tests, hướng dẫn chuyển BH-03.
- Đã cập nhật [backlog](../../09_IMPLEMENTATION_PLAN.md#L50): ghi file/test hoàn thành và DB tests NOT RUN.

## Phát hiện theo ưu tiên

### F1 — P1/high: Không expose helper ghi audit và idempotency cho client

File: [migration](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql#L933). Dòng 933–934.

`record_idempotency` và `log_audit_event` là SECURITY DEFINER, được cấp EXECUTE trực tiếp cho authenticated. Hàm audit không kiểm tra người gọi có quyền với club/session, không bắt buộc actor khác NULL, và nhận action/JSON tùy ý. Một user có thể ghi sự kiện giả vào CLB khác; tùy ACL mặc định, PUBLIC còn có EXECUTE vì migration không REVOKE quyền function từ PUBLIC. REVOKE ALL ON ALL TABLES không thu hồi function privileges. record_idempotency cho phép user tự đặt operation/request/result giả cho chính actor trước khi nghiệp vụ chạy, phá độ tin cậy của replay khi các RPC sau dùng helper này.

Đề xuất: chuyển helper ghi nội bộ sang private schema, REVOKE EXECUTE FROM PUBLIC/anon/authenticated; chỉ RPC nghiệp vụ có kiểm tra actor/quyền được gọi helper bằng quyền phù hợp. Không lọc action/operation ở UI. Với replay, helper phải được gọi trong cùng transaction nghiệp vụ và kiểm tra quyền trước trả kết quả.

Nghiệm thu: anon/user không gọi trực tiếp hai helper được; actor không có quyền không thể tạo audit cho CLB khác; không thể preseed fake replay result bằng API. RPC hợp lệ vẫn tạo đúng một audit/request result.

### F2 — P1/high: Policy sessions lộ cả hàng riêng và cho liệt kê unlisted

File: [migration](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql#L1033). Dòng 1029–1036.

GRANT SELECT toàn bảng sessions cho authenticated, policy cho phép mọi row public/unlisted. Người ngoài có account có thể SELECT receiver_snapshot và các receiver FK, dù không confirmed; trên đường legacy còn có contact_phone. RLS lọc hàng chứ không lọc cột. Người đó cũng có thể liệt kê mọi unlisted session thay vì chỉ mở bằng ID như contract yêu cầu. Điều kiện không kiểm lifecycle nên draft unlisted/public cũng bị đọc.

Đề xuất: giới hạn bảng sessions gốc cho người có quyền đọc dữ liệu riêng; người ngoài/member thông thường dùng projection/RPC whitelist, tách quyền theo trường cần thiết. Public feed chỉ published/in_progress, unlisted chỉ theo ID và không được scan qua bảng gốc. Không khắc phục bằng chỉ ẩn ngân hàng ở widget.

Nghiệm thu: authenticated outsider SELECT receiver_snapshot/contact_phone và list unlisted/draft không được; public/unlisted detail hợp lệ trả đúng whitelist, confirmed player nhận thông tin thanh toán qua API riêng.

### F3 — P1/high: Public summary không dùng được cho anon và đếm sai theo người xem

File: [migration](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql#L620). Dòng 620–626; context security_invoker tại 596 và grants tại 904–917.

View chạy với security_invoker=true nhưng anon chỉ được cấp view/venues, không SELECT sessions/profiles/session_players nguồn; SELECT view sẽ thiếu quyền. Với authenticated outsider/player, RLS session_players chỉ thấy row riêng hoặc buổi được quản lý. COUNT(*) trong view vì thế trả 0/1 thay cho tổng confirmed toàn buổi, hiển thị slot khác nhau theo account.

Đề xuất: dùng read RPC tổng hợp có quyền nội bộ được giới hạn, whitelist trường và điều kiện public/lifecycle; tính tổng confirmed đúng ở DB mà không trả player rows. Không cấp đọc toàn bộ session_players chỉ để COUNT. Nếu giữ view phải thiết kế lại grants/projection của dữ liệu nguồn tương ứng.

Nghiệm thu: anon, player A, outsider B và host cùng thấy một confirmed count đúng, nhưng A/B/anon không đọc danh sách/contact người khác.

### F4 — P1/high: Nhánh nâng cấp legacy chưa tạo schema tương đương DB mới

File: [migration](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql#L199). Dòng 199–205; tương tự session_players tại 262 trở đi.

CREATE TABLE IF NOT EXISTS bỏ qua bảng có sẵn, các ALTER chỉ thêm cột đích. Các trường NOT NULL legacy như venue_name/play_date/start_time/end_time và player_name không được chuyển đổi hoặc bỏ yêu cầu trong giai đoạn tương thích. INSERT theo schema đích chỉ truyền venue_id/title/starts_at/ends_at và display_name sẽ lỗi NOT NULL trên DB nâng cấp, dù chạy được trên DB sạch. Đồng thời nhánh ALTER không bổ sung đầy đủ NOT NULL/cross-column CHECK của CREATE, nên hai môi trường có invariant khác nhau. Metadata live xác nhận các cột legacy trên còn NOT NULL.

Đề xuất: tách rõ baseline sạch và kế hoạch upgrade: backfill/cách ly dữ liệu chưa xác minh, giải quyết cột legacy bắt buộc bằng compatibility mapping hoặc gỡ NOT NULL đúng giai đoạn, thêm/validate constraints sau đối chiếu. Không xóa dữ liệu hoặc tự suy owner từ phone. Có điểm dừng rõ trước client chuyển schema.

Nghiệm thu: chạy migration trên DB sạch và fixture ba bảng legacy có dữ liệu; INSERT theo payload đích thành công cả hai; dữ liệu cũ được giữ/cách ly; constraints cuối phù hợp, không lỗi cột bắt buộc còn sót.

### F5 — P2/medium: Người chơi không thấy công nợ của chính mình

File: [migration](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql#L657). Dòng 656–658; policy charge_revisions tại 1090–1092.

player_outstanding dùng security_invoker và INNER JOIN charge_revisions, nhưng policy revision chỉ cho session finance. Player bình thường thấy session_player và charge riêng nhưng không thấy revision, nên view trả 0 hàng dù đã chốt phí và còn nợ. RPC get_my_registration chỉ trả thông tin đăng ký, không thay thế được phần tài chính bị mất này.

Đề xuất: cung cấp projection khoản riêng qua RPC có kiểm tra đúng player và freshness, hoặc policy revision tối thiểu cho participant cần xem charge của mình. Không mở toàn bộ chi phí/tài chính buổi cho mọi player.

Nghiệm thu: player có charge 70.000, payment confirmed 20.000 thấy due=70.000, paid=20.000, outstanding=50.000 và freshness; player khác không thấy, finance vẫn xem đúng. Không trả phí cũ như số cuối cùng khi source_version stale.

### F6 — P2/medium: Policy ngân hàng có nhưng thiếu quyền SELECT cho chủ tài khoản

File: [migration](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql#L912). Dòng 912–917; policy bank_accounts tại 1014–1026.

Sau REVOKE ALL TABLES, danh sách GRANT không cấp SELECT cho club_bank_accounts hoặc host_bank_accounts. Dù có policy owner/treasurer/self, chính host cũng bị permission denied khi đọc cấu hình ngân hàng của mình. Hiện không có RPC đọc cấu hình thay thế trong migration; đây là khoảng trống của lớp read nền, không phải thiếu mutation BH-03.

Đề xuất: cấp SELECT cho authenticated dưới policy đã giới hạn, hoặc read RPC riêng cho owner/treasurer/self; không cấp anon hoặc public read. Ghi rõ read contract để BH-03 dùng thống nhất.

Nghiệm thu: host đọc account của mình, owner/treasurer đọc account CLB, outsider bị chặn và confirmed player chỉ nhận payment instructions được phép.

## Đánh giá bổ sung so với review trước

BH-02 đã có schema versioned, partial unique indexes, RLS policies, các cột billing_input_version/source_version và bảng waitlist_invitations. Đó là phần nền để triển khai; không đồng nghĩa slot/thu tiền/invitation RPC đã hoàn thành. Không coi các RPC nghiệp vụ BH-05/BH-06 chưa được giao là lỗi riêng của commit này.

Trạng thái cập nhật:

| Hạng mục | Đánh giá sau BH-02 |
|---|---|
| R1 bảo vệ contact/direct writes | Chưa nghiệm thu: raw sessions vẫn lộ dữ liệu, helper writes bypass nguồn tin cậy; legacy player phone vẫn cần kiểm tra theo quyền finance |
| R2 đăng ký atomic | Chưa được sửa bởi commit này; thuộc BH-05, không đóng từ table revoke |
| R3 thiếu schema CLB/quỹ | Đã có định nghĩa trong migration, chưa xác minh triển khai/tương thích DB legacy |
| R4 freshness phí | Đã có cột version, chưa phải gate nghiệp vụ chạy được; thuộc BH-06 |
| R5/R6 UI lịch/error/QR | Commit không đổi Dart; chưa kết luận đã sửa |
| R7 waitlist invitation | Đã có bảng/constraint nền, chưa issue/revoke/accept; thuộc BH-05 |

Chưa có lý do đổi Flutter/Provider/Supabase hoặc thêm backend. Các lỗi trọng tâm là grants + RLS + projection + nâng cấp dữ liệu, sửa trong kiến trúc đã chọn. Không cần refactor toàn app để giải quyết.

## Test và tiêu chí hoàn thành

9 schema tests chỉ kiểm sqlContent.contains(...); chúng có thể pass khi quyền thiếu/ghi helper mở/view trả sai. Đây là kiểm tra cấu trúc, không phải unit test hành vi PostgreSQL hoặc nghiệm thu RLS. Backlog ghi NOT RUN là đúng giới hạn, nhưng README hướng sang BH-03 như BH-02 hoàn tất dễ gây hiểu sai.

Trước đóng BH-02 cần chạy DB tests local/staging với ít nhất: dựng DB sạch; upgrade fixture legacy; anon/authenticated grants; host/player/outsider với claim thật; gọi trực tiếp helper bị từ chối; summary count và player outstanding đúng. Dùng fixtures giả; không chạy bài ghi lên production.

Khuyến nghị xử lý: F1/F2 trước, tiếp F3/F4, rồi F5/F6; thêm ca DB test tương ứng trong cùng thay đổi. Sửa trạng thái BH-02 thành "migration draft, DB acceptance pending" tới khi kiểm thử đạt. Chưa apply migration production trong review này, chưa sửa implementation hoặc push GitHub.


## Kết quả thực thi bổ sung ngày 15/10/2026

[33 ca RLS](rls_test_report.md): 18 PASS / 15 FAIL trên PostgreSQL 17.11 cô lập; F1–F6 đã tái hiện. F7 bổ sung: treasurer đọc được phone_number qua cột legacy dù bảng contacts mới chặn. Xem [expected/actual](rls_test_results.json). Phần phạm vi/chưa chạy phía trên là trạng thái lúc review tĩnh; kết quả thực thi này cập nhật phạm vi đó, không xác nhận Supabase full-stack hoặc production đã được kiểm thử.
