# BH-07 trên Edge và Firefox cục bộ — 11/11/2026

## Sửa tải tổng kết bị treo

Trong lượt Firefox headless trước bản sửa, một POST đọc tổng kết vẫn chờ sau khi trình duyệt đã về online. Nút tải lại tiếp tục bị khóa. Một yêu cầu đọc riêng tới backend cục bộ nhận HTTP 200, với quyền Cohost và số lượt 2/0/2. Quan sát này xác nhận ứng dụng cần xử lý yêu cầu chờ quá lâu. Nguyên nhân khiến yêu cầu Firefox chờ vẫn chưa được xác định.

`FinanceProvider.fetchSessionSummary` áp dụng thời hạn 15 giây cho lượt đọc. Khi hết thời hạn, màn hình giữ dữ liệu lần tải trước, hiển thị lỗi và cho thử lại. Lượt đọc đầu tiên hết thời hạn có thể thử lại từ màn hình lỗi. Phản hồi đến muộn không cập nhật state. `Future.timeout` vẫn để yêu cầu HTTP gốc chạy ở tầng mạng.

Ba ca hồi quy tái hiện lỗi trước khi sửa và qua sau khi sửa. Toàn bộ Flutter suite có 250 PASS và 1 SKIP. `flutter analyze` báo 0 lỗi và build web profile thành công. Hash của `main.dart.js` trên máy chủ trùng với hash bản build.

## Phạm vi kịch bản

Kịch bản đi từ khách mở link trực tiếp tới Owner, tải lại trang, rồi chuyển sang Cohost và Member trong cùng tài liệu. Owner thấy tổng phải thu 200.000, đã thu 100.000 và còn 100.000 đồng. Cohost thấy 2 có mặt, 0 vắng và 2 xác nhận, cùng kiểm tra không có số tiền. Member thấy riêng khoản phải thu và đã trả 100.000 đồng, còn 0 đồng. Ca ngoại tuyến kiểm tra cảnh báo dữ liệu cũ, sau đó bấm thử lại và xác nhận một yêu cầu mới cho đúng phiên nhận HTTP 200, nút tải lại hoạt động trở lại, cảnh báo biến mất và số lượt vẫn đúng.

Anti hoàn tất ba vòng sửa kịch bản. Codex xử lý các lỗi còn lại khi chạy trình duyệt. Edge ghi nhận ô email của Member sai ngay trước khi bấm Tab. Codex đổi thao tác sang nhấp ô, chờ focus ổn định, gõ bằng bàn phím và kiểm tra giá trị với tối đa hai lần nhập mỗi ô. Reviewer kiểm tra độc lập mã nguồn, yêu cầu điều kiện nút tải lại hoạt động trở lại để tránh báo đạt khi chỉ mới nhận header HTTP và vẫn đang hiển thị cache. Reviewer xác nhận điều kiện đã được bổ sung. Các lượt trình duyệt do Codex thực hiện.

Đối chứng Edge đặt tổng phải thu kỳ vọng thành 200.001 đồng và dừng đúng tại kiểm tra tổng tiền của Owner. Đối chứng callback từ chối phản hồi cũ, yêu cầu sai phiên, thiếu phiên, JSON lỗi, OPTIONS và sai cổng. Các đối chứng số lượt, khoản phí của Member và khôi phục online cũng từ chối dữ liệu sai.

## Kết quả

Edge và Playwright Firefox headless đều chạy qua các bước bắt buộc trên cùng bản build profile và cùng phiên bản kịch bản. Cả hai ghi nhận lượt thử lại HTTP 200 và không có page error. Clipboard trong hai lượt này giữ NOT RUN. Firefox có cửa sổ vẫn UNKNOWN do chưa xác minh được hình ảnh Flutter ở chế độ đó. Kết quả này áp dụng cho luồng đọc Web cục bộ. Toàn BH-07/V8 vẫn chưa nghiệm thu.

Fingerprint trước và sau trùng cho 21 bảng public với 94 dòng, schema và role. Chỉ giá trị `auth.refresh_tokens_id_seq` tăng từ 8 lên 44 qua các lượt đăng nhập. Trình kiểm tra so sánh toàn bộ ban đầu trả exit 1 vì tính cả sequence này. So sánh lại chỉ loại đúng trường `last_value` của sequence trên và xác nhận các phần còn lại trùng. Các dòng Auth không nằm trong phép đo.

Kết quả theo trình duyệt, hash nguồn và bản phục vụ nằm trong [gói bằng chứng](web_matrix_20261111_evidence/manifest.json). Lượt chạy dùng working tree trên base `1717451` với bản sửa chưa commit, được nhận diện bằng hash trong [provenance](web_matrix_20261111_evidence/provenance.json).

Reviewer đối chiếu độc lập 3/3 hash manifest, kết quả hai trình duyệt sau khi bỏ snapshot thô và đúng một chênh lệch sequence Auth. Review mã và bằng chứng trong phạm vi này không còn P0/P1/P2 mở.
