# Review BH-04 — dd5c1e6

Áp dụng agency-code-reviewer, so sánh c27865d..dd5c1e6. Đồng bộ fast-forward, không sửa/push code hoặc apply remote DB. Kiểm tra ngày 15/10/2026 (Việt Nam).

Nền typed repository, bỏ direct writes demo và forward migration là cải thiện đúng hướng. Chưa nên đóng nghiệm thu BH-04/chuyển BH-05 với bốn lỗi dưới đây.

## R1 — P1: retry lifecycle thất bại sau khi DB đã commit

supabase/migrations/20261015163000_bh04_sessions.sql:435–437. Hash chứa v_session.version là trạng thái DB và tăng ngay sau publish/cancel. Gọi lại cùng actor/request/action tạo hash khác nên helper báo IDEMPOTENCY_CONFLICT. Tái hiện trên DB clean cô lập: publish đầu returncode 0, cùng câu lệnh lần hai returncode 3; lỗi ghi trong bh04-extra.json. Mất response sau commit khiến client không xác nhận được kết quả bằng retry. Hash chỉ input bất biến; nếu cần optimistic version, nhận expected_version từ request và kiểm replay trước precondition có thể thay đổi. Thêm test replay publish/cancel, bao gồm response lost.

## R2 — P1: link chia sẻ chưa mở được tài nguyên trong app

lib/screens/session_detail_screen.dart:137–141; lib/main.dart:51–59. Clipboard chỉ chứa /sessions/UUID, không có origin để người chơi mở từ Zalo. AppRoutes.parse không có caller ở runtime; MaterialApp chỉ home, không routes/onGenerateRoute/router cho URL này. Đây là khoảng trống web/in-app routing, độc lập với OS-level App Links đã hoãn. Dùng base URL cấu hình và nối route URL vào màn chi tiết; test khởi động app bằng URL thật và quay lại sau login. Test parse và push MaterialPageRoute có sẵn không chứng minh luồng này.

## R3 — P2: key không được giải phóng sau mutation thành công

lib/providers/session_provider.dart:314–318. _pendingRequests chỉ bị xóa khi đổi auth, không xóa operation khi đã có response thành công. Hai ý định create/duplicate cùng payload trong cùng phiên dùng lại UUID, backend trả buổi cũ thay vì tạo mới. Test bổ sung sau timeout→retry thành công→new successful intent cùng payload thất bại: keys[2] == keys[1] (bh04-review-key.log). Xóa key sau response thành công, trước refreshMine; giữ key cho timeout/thất bại chưa rõ commit. Test temp được lưu review_session_retry_test.dart; muốn chạy đặt lại dưới test/providers để Flutter nhận.

## R4 — P2: lỗi danh sách đăng ký bị biến thành danh sách rỗng/cũ

lib/providers/session_provider.dart:288–289; lib/screens/session_detail_screen.dart:414–417. catch bỏ qua lỗi list_session_players. Khi lần tải đầu lỗi, host thấy "Chưa có ai đăng ký"; lần sau lỗi có thể tiếp tục thấy dữ liệu cũ như hiện hành. Thêm players loading/error/retry riêng, giữ chi tiết buổi; test không hiển thị empty state khi RPC lỗi. Phân loại P2 dù chức năng đăng ký mới thuộc BH-05 vì đường đọc roster đã được đưa vào BH-04.

## Kiểm chứng và giới hạn

- Flutter 3.47.7: 101/101 PASS, tự chạy tại dd5c1e6.
- BH-04 runner PostgreSQL17 cô lập: 42/42 PASS (21 clean +21 legacy), toàn chuỗi migration. JSON hash/commit được lưu cùng thư mục.
- Test bổ sung provider 1 FAIL như dự đoán (R3); truy vấn retry lifecycle tái hiện R1.
- Không chạy lại 117 ca BH02/03 trong lượt này; 159/159 trong handoff là báo cáo tác giả, không gọi là kết quả tự kiểm lần này.
- Chưa chạy analyze, HTTP/PostgREST/JWT hoặc thiết bị thật. Không apply production.
- R2 xác nhận bằng truy vết caller và cấu hình app, chưa chạy browser e2e; R4 bằng code path, chưa có runtime regression riêng.
- Tự rà lại: không báo lỗi draft/member vì hợp đồng mới §11 cho phép; không gọi ACL PUBLIC của projection công khai là leak; không xem thiếu OS association là lỗi mới. Bốn finding chỉ nhằm thay đổi BH-04.
