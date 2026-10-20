# Review BH-06C — af31e7b

Ngày 18/10/2026 (Việt Nam). Tested HEAD `af31e7bb5134dadab401e78c4233411e5404b526`, nhánh `feat/bh06c-ui`, dependency B `f28fd0f` (Đạt tại `5e62007`), main `c35dd27`. Source/test/migration của HEAD trùng cây `b123db9`; phần sau chỉ đổi docs. Theo `docs/ai/REVIEWER.md` tại `origin/chore/ai-roles` = `163bc45`. Đọc diff main...HEAD và tách phần C so với dependency B. Không sửa code triển khai, migration hoặc test tác giả.

## Phát hiện

### C1 — P1: gửi auth user ID thay vì ID đăng ký

`lib/screens/session_finance_screen.dart:755` (nguồn ID tại dòng 404, caller dòng 323). Nút gửi thanh toán dùng `AuthProvider.currentUser.id` làm `playerId`, trong khi RPC `submit_payment` tra `session_players.id`, rồi mới so `user_id` với actor (`20261016120000_bh06_payments_ledger.sql:44–52`). Hai ID độc lập; người chơi thực tế bấm “Đã chuyển khoản” nhận NOT_FOUND, không tạo được yêu cầu chờ xác nhận. Fixture tác giả dùng cùng `u1` cho hai ID nên bỏ sót.

Sửa: dùng `instructions.playerId` của bản hướng dẫn đúng người/buổi hiện hành, kiểm tra dữ liệu cần thiết trước khi bật nút. Test hồi quy với auth ID và registration ID khác nhau. Probe reviewer giữ auth `u1`, đổi registration thành `registration-p1`: verify thất bại; log ghi caller vẫn gửi `playerId: u1`.

### C2 — P1: mã QR cố định chặn gửi thanh toán mới sau từ chối

`lib/screens/session_finance_screen.dart:326`. UI truyền `instructions.reference` làm reference của mọi payment mới. `get_payment_instructions` trả mã cố định theo registration (`20261016140000_bh06a_review_round1.sql:88`), còn `payments.reference` là UNIQUE và RPC không tái sử dụng reference của bản bị rejected. Sau lần gửi bị từ chối, outstanding vẫn dương nhưng lần gửi tiếp với request ID mới luôn lỗi `INVALID_INPUT: Mã tham chiếu đã tồn tại`. Đây là intent mới sau từ chối, không phải retry cùng request ID; cũng có thể gặp khi chốt thêm phí sau lần đã trả.

Sửa: tách mã nội dung chuyển khoản cố định khỏi định danh duy nhất của từng payment; dùng cơ chế reference mới do RPC hỗ trợ khi tạo intent mới, đồng thời giữ request ID ổn định cho retry của cùng intent. Không bỏ ràng buộc UNIQUE hoặc đổi key mỗi retry để né lỗi. Bổ sung ca gửi → từ chối → gửi lại và trả thêm sau refinalize. Probe RPC app role trên DB cô lập tái hiện: mã trước/sau giống nhau, outstanding 100.000, lần gửi mới exit 3 do trùng reference. Probe này dùng đúng registration ID để kiểm chứng C2 độc lập với C1.

### C3 — P2: khoản còn phải thu tính từ một trang payment

`lib/screens/session_finance_screen.dart:773` (hiển thị/prefill tại 563–573). `_outstandingFor` trừ tiền confirmed chỉ trong `finance.payments`, trong khi `get_session_finance` phân trang payment mặc định 50 bản mới nhất (`20261016130000_bh06_reads.sql:175–178`). Khoản confirmed cũ nằm ngoài trang bị bỏ qua: người đã trả đủ vẫn hiện còn nợ và ô thu tiền mặt được điền dư. Tổng outstanding của RPC có thể bằng 0 nhưng dòng người chơi vẫn hiện 100.000. Server chặn thu dư không sửa được thông tin sai trên UI.

Sửa: lấy outstanding mỗi người từ nguồn tổng hợp đầy đủ phía server, hoặc chỉ cho hiển thị/prefill khi đã có dữ liệu đầy đủ được xác nhận; không suy khoản nợ từ một trang lịch sử. Probe fixture có 50 payment mới của người khác, charge 100.000 của người đã trả ở trang cũ và tổng outstanding RPC bằng 0: UI thực tế hiện “Còn phải thu: 100,000 VNĐ”, kỳ vọng 0 thất bại. Handoff gọi phép tính này “chỉ prefill” chưa khớp phần hiển thị.

## Kiểm chứng độc lập

[Summary/hash](review_af31e7b_evidence/summary.json), [analyze](review_af31e7b_evidence/analyze.log), [Flutter](review_af31e7b_evidence/flutter.log), [DB JSON](review_af31e7b_evidence/db-results.json), [DB log](review_af31e7b_evidence/bh06.log), [widget probe/log](review_af31e7b_evidence/widget_probe.dart.txt), [log widget](review_af31e7b_evidence/probes.log), [RPC probe](review_af31e7b_evidence/reference_probe.py), [log RPC](review_af31e7b_evidence/reference-probe.log).

| Nhóm | Kết quả |
|---|---|
| Flutter 3.47.7 / Dart 3.13.5 analyze --no-pub | 0 issue, exit 0 |
| flutter test --no-pub, trước khi thêm probe | 181/181 PASS, exit 0 |
| Runner DB BH-06, PostgreSQL17 cô lập | 84/84 PASS, exit 0 |
| Hai widget probe reviewer, chạy với --plain-name 'review ' | 2 FAIL, exit 1, tái hiện C1/C3 |
| RPC probe gửi lại sau từ chối | 1 FAIL, exit 1, tái hiện C2 |

Widget probe dùng widget/provider thật với repository fixture; nguồn là bản sao test tác giả với ID tách biệt và thêm ca phân trang, chỉ chọn hai test có tên bắt đầu `review `. Chạy tạm trong test/screens rồi chuyển sang .dart.txt; không để lại test/code sửa trong cây triển khai. RPC probe tái sử dụng helper runner, dùng dữ liệu giả, SET ROLE authenticated và Auth stub trong DB local `--network none`; không apply DB thật. Các FAIL là kỳ vọng hồi quy độc lập, không gộp vào số 181 PASS của suite hiện có. Không chạy lại riêng BH-02..05; 335 DB của review A là bằng chứng lịch sử, không phải số tự chạy lượt này.

## Kết luận

**Chưa đạt phần C BH-06 tại `af31e7b`**: C1/C2 P1 và C3 P2 còn mở. A/B giữ kết luận theo tested SHA trước; chưa nghiệm thu tích hợp BH-06. Chỉ publish báo cáo/bằng chứng/trạng thái, không sửa triển khai, merge main hoặc deploy. Theo AGENTS, người triển khai viết test tái hiện trước, xử lý P1 được nêu, tối đa hai vòng; C3 giữ mở, không tự coi được phép sửa P2 hoặc đóng vì đã có tài liệu.

**NOT RUN:** HTTP/PostgREST/JWT/Supabase Auth thật; thiết bị/browser e2e; tải ảnh VietQR và chuyển khoản/ngân hàng thật; apply staging/production, backup/restore, concurrency qua HTTP và pilot/tích hợp A+B+C. Ca C3 dùng fixture phản ánh contract phân trang, chưa tái tạo 51 payment qua HTTP. Ca trả thêm sau refinalize của C2 chưa chạy riêng; ca sau reject đã tái hiện bằng RPC local.
