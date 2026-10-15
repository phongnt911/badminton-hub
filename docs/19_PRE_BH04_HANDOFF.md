# Bàn giao sau đợt sửa trước BH-04

Ngày 15/10/2026. Tiếp nối baseline `004e05f`; không bắt đầu lại BH-01/BH-02.

## Đã sửa

- Cấu hình: không default production; bắt buộc APP_ENV, SUPABASE_URL, SUPABASE_ANON_KEY. APP_ENV=test chỉ nhận host local; project production đã biết chỉ nhận APP_ENV=prod. CLI đọc không có URL/key mặc định, không in key; seed legacy chỉ chạy local.
- Auth: signup trả user nhưng session null vẫn là khách, giữ màn xác nhận email; signup có session được xác thực. Login có callback đóng route auth và trở về màn trước.
- DB: forward migration `20261015151445_pre_bh04_hardening.sql`; list_club_members phân trang trước jsonb_agg, thứ tự role/created_at/id ổn định, page rỗng trả []; giới hạn 1..100, offset không âm. Giữ JSON array, không đổi cursor API.
- UI: member/bank có loading/error/retry; đổi role có submitting, giữ dialog và hiện lỗi nếu thất bại. Số dư chỉ trên chi tiết CLB theo quyền; bỏ nhánh card danh sách thiếu dữ liệu.
- ACL: REVOKE PUBLIC/anon cho list_my_clubs/get_club_detail/list_club_members; GRANT authenticated, giữ kiểm quyền bên trong.
- Báo cáo 18 sửa nhận định concurrency: hai psql là hai kết nối độc lập; HTTP/PostgREST chưa kiểm. X1/X2 là chặn phát hành, không chặn triển khai BH-04. Không ép cursor hoặc tạo thêm ADR chỉ để xử lý bug.

## Kiểm thử

Flutter 3.47.7 / Dart 3.13.5: 66/66 unit/widget PASS, analyze No issues found. Có ca signup session-null/session-present, callback quay lại route trước, lỗi member/bank rồi retry phục hồi, cấu hình thiếu fail-fast, đổi vai trò thất bại giữ dialog và báo lỗi. Ma trận cấu hình chạy bổ sung: test+local hợp lệ, test+remote bị chặn, dev+production bị chặn; không gọi mạng.

PostgreSQL 17.11 cô lập, container bh02-review-postgres, Auth stub; toàn chuỗi migration: BH-02 33+14, BH-03 48+22 = **117/117 PASS**. Tám ca mới kiểm phân trang và ACL ở cả clean/legacy. JSON bằng chứng timestamp 20261015151628 (BH03), 20261015151755 (BH02) trong docs/reviews. Chạy trên worktree có sửa đổi từ baseline 004e05f; metadata/hash migrations trong JSON, không tuyên bố baseline chính là mã đã sửa.

Lệnh tái hiện: đặt BH02_TEST_CONTAINER=bh02-review-postgres; chạy lần lượt run_bh03_tests.py, run_bh03_retry_tests.py trong docs/reviews/bh03; run_rls_tests.py và extended_tests_15ef59b.py trong docs/reviews/bh02. Flutter dùng flutter test --no-pub và flutter analyze --no-pub.

## Còn lại và giới hạn

Chưa apply Supabase production/staging; chưa chạy HTTP/JWT hoặc deep link thiết bị thật. Các kiểm thử local không đóng cổng pilot. B2-A (invariant legacy), B2-C (draft projection), lỗi typed/mapping và các mục ngoài phạm vi trong báo cáo 18 còn cần xử lý theo ticket liên quan; không tự siết NOT NULL bằng dữ liệu suy đoán. Không sửa lịch sử migrations đã chia sẻ.

X1 còn mở: các màn buổi chơi vẫn dùng demo, chưa đủ điều kiện phát hành pilot. Chuyển đổi trong BH-04, không mở direct UPDATE để chữa lỗi. Tài liệu cũ là lịch sử, file này là điểm tiếp tục mới nhất.

## Prompt phiên mới

> Đọc AGENTS.md, docs/00_START_HERE.md và docs/19_PRE_BH04_HANDOFF.md, sau đó các đặc tả 03/08/09/10/11/12 và phần BH-04 trong docs/14. Kiểm tra git status/HEAD và đồng bộ main bằng fast-forward nếu sạch; giữ thay đổi đang có. Triển khai BH-04: thay đường demo SupabaseService/SessionProvider cho buổi chơi bằng model/repository/provider và RPC/projection đúng hợp đồng. Mọi mutation qua RPC có authorization, transaction và request_id/hash/retry; không ghi joined_count/số dư/role từ client. Không thêm thư viện nếu chưa cần. Đảm bảo create/edit/publish, UTC/giờ Việt Nam, link /sessions/:id và return sau login theo spec; chốt quyết định routing dựa trên code hiện có trước triển khai. Public/unlisted chỉ projection whitelist, draft/private cần kiểm quyền. Giữ regression 66 Flutter và 117 DB; bổ sung test hành vi BH-04, báo PASS/FAIL/NOT RUN, tested commit/hash và giới hạn môi trường. Chỉ local/staging, không apply production. Cập nhật tài liệu và push GitHub khi kiểm thử xong.
