# Giao Anti CLI chẩn đoán runtime V4 — 10/11/2026

Owner yêu cầu sau runtime FAIL: “tiếp tục, cần giao việc code thì giao cho anti cli làm”. Đây là ủy quyền mới cho phần tooling/test của phát hiện runtime; không dùng để mở lại các phát hiện cũ hoặc bỏ giới hạn vòng sửa chung. Codex review/chạy kiểm chứng, Anti CLI triển khai. Không đổi app/schema, merge/deploy/pilot/BH-08.

## Phạm vi đầu tiên

Base `08c2069aaa111b7805c785bdf0af205a6b374ae8`. Theo [runtime review](v4_runtime_review_20261110.md), lỗi hiện có là main raise trước khi lưu `measured`, khiến không phân biệt được nhánh thất bại. Nguyên nhân overlap runtime vẫn UNKNOWN.

Anti chỉ sở hữu runner V4, `tests/test_bh07_v4_runtime_collection.py` và handoff mới `v4_failure_diagnostics_handoff_20261110.md`. Giữ receipt an toàn trên nhánh FAIL: dump exit/timing, writer timing/status hoặc chưa gửi, observation identity/timing, overlap verdict và exporter returncode. Không lưu dump bytes, stderr chưa lọc, SQL thô, credential/JWT hoặc body HTTP vào diagnostics. Không nới gate hoặc thay workload trong pha này.

Viết test trước và bàn giao cho Codex chạy RED trước khi sửa runner. Test đi qua main thật với external boundary mock cho missing observation/writers chưa gửi, insufficient overlap, dump nonzero, exporter exit và success control; kiểm marker nhạy cảm không lọt diagnostics. Cleanup/FAIL phải được giữ nguyên. Synthetic PASS không thay runtime.

## Giao CLI

Đã kiểm `agy models` bằng phiên ngoài sandbox: đăng nhập hoạt động, có `gemini-3.8-flash-high`. Lần kiểm trong sandbox báo chưa đăng nhập do không truy cập được local state; không coi là tài khoản thực bị logout.

Giao Gemini 3.8 Flash High, effort high, `accept-edits`, thời hạn 6 phút. Chỉ đọc/sửa file trong phạm vi; không shell, Docker/SQL, agent con, commit/push hoặc thay policy/global settings. Task cục bộ được giữ dưới `.build/` bị ignore; đây không phải reviewer prompt thay cho bàn giao trực tiếp.

Conversation `1525e391-4d7c-42f7-a58e-662ee36e5b55`: lượt đầu kết thúc exit 1, `DEADLINE_EXCEEDED/print_timeout` sau 6 phút (duration 357.332s), response rỗng. Không có thay đổi test/runner. CLI báo 131.843 input tokens và 39.815 output tokens dù không có bàn giao; đây là metadata CLI, không phải bằng chứng code hoặc test.

Đã tiếp tục cùng conversation với timeout 3 phút, yêu cầu không đọc lại docs/AGENTS, viết test ngay từ phân tích đã có hoặc báo chính xác tool bị từ chối. Không tăng quyền tool hoặc bypass gateway. Chưa có kết quả RED/GREEN mới. Không tính timeout hoặc lỗi kết nối thành một vòng sửa/review.

Lượt tiếp tục bàn giao 5 test và helper main mock, chưa sửa runner. Codex chạy `python tests/test_bh07_v4_runtime_collection.py -v`: **19 test, 5 FAIL mới, 14 PASS cũ**, exit 1, 0.458s; cả 5 lỗi do thiếu diagnostics. Log local `.build/v4-diagnostics-red.log`; đây là synthetic main test, không phải runtime Docker. Đã giao Anti triển khai receipt whitelist trước raise, ghi exporter poll vô điều kiện một lần, giảm duplication harness và siết marker writer chưa gửi. Không đổi scheduling/workload/gates. Chờ bàn giao implementation cùng conversation.
