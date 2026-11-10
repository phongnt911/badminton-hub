# BH-07 V4 — kiểm bản sửa vòng 2/3, 09/11/2026

**Chưa đạt.** Candidate working tree, base `b72c563d9e519986dbd88ec98bcc3f015a41a442`; Anti triển khai, Codex chạy các kiểm chứng dưới đây. Source runner vẫn bị gateway giữ với `secret.redacted/redaction.incomplete` khi đọc fresh; không có full source review hoặc Docker/DB V4 runtime. Không kết luận có secret thật từ thông báo này.

## Kiểm chứng

- `python tests/test_bh07_v4_backup_concurrency.py -v`: **49/49 PASS**, exit0.
- `python scripts/bh07_backup/v4_concurrent_probe.py`: **44 controls PASS**, exit0.
- [post_r2_controls.py](v4_review_r1_evidence/post_r2_controls.py): exit1, [capture](v4_review_r1_evidence/post_r2_capture_20261109.json). Positive PASS; serial writers, unrelated cleanup, ledger amount sai và audit request sai đều bị chặn; request payment ID sai vẫn PASS.
- [post_r2_request_controls.py](v4_review_r1_evidence/post_r2_request_controls.py): exit1, [capture](v4_review_r1_evidence/post_r2_request_capture_20261109.json). Positive PASS; request ID sai/thiếu request bị chặn; request receipt status 500 và cặp replay fingerprint bằng nhau nhưng không phải digest vẫn PASS.
- Hai bộ control mới hash source **trước cả import/fixture load**, kiểm lại sau, lưu input/output và source/input hashes, từ chối ghi đè. Các mutant quan hệ tính lại SHA256 canonical độc lập, đồng thời cập nhật restored row evidence theo row sai; không dùng lỗi checksum cũ hoặc source/restore không khớp để giả chứng minh kiểm invariant.

## R1 còn mở — P1, bằng chứng operation request/replay còn fail-open

`scripts/bh07_backup/run_v4_concurrent_rehearsal.py`, `validate_v4_rehearsal` (số dòng source chưa đọc được):

1. `request_payment_wrong_valid_digest`: đổi `row_evidence.request.payment_id` của P0 sang UUID khác, tính lại relational digest và đặt restored row evidence giống row sai ⇒ **PASS, findings=[]**. Trong receipt synthetic, phần request không còn trỏ đúng payment của operation nhưng gate không phát hiện. Đây là trường normalized row evidence, chưa phải quan sát raw `operation_requests.result` trên DB hoặc bằng chứng dữ liệu DB thật bị hỏng.
2. `invalid_equal_replay_fingerprints`: cả before/after là `not-a-digest`, cờ unchanged true ⇒ **PASS, findings=[]**. Equality của hai chuỗi bất kỳ không chứng minh fingerprint dữ liệu không đổi.
3. `wrong_stored_request_status`: receipt `request.status=500`, operation transport status vẫn 200, digest mới khớp ⇒ PASS. Đây là trường receipt hiện hành, không khẳng định DB có cột HTTP status. [Schema thật](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql), dòng 501–508: `operation_requests` có actor/operation/request_id/payload_hash/**result**, không có cột status HTTP. Bản sửa phải truy vấn/đối chiếu **stored result** thật (payment_id, amount, trạng thái nghiệp vụ), không tạo status=200 rồi gọi là dữ liệu DB. Có thể bỏ trường HTTP tự tạo khỏi row evidence nếu nó không phải dữ liệu lưu trữ; transport receipt vẫn phải kiểm riêng.

Yêu cầu sửa: request evidence phải ràng buộc đúng actor/operation/request_id, stored result payment/amount/status với workload và RPC response; replay phải trả đúng kết quả, hash là digest hợp lệ gắn với scoped dữ liệu thật trước/sau, không chỉ so hai string/cờ. Giữ các control sai FK/amount với digest đã tính lại, bổ sung RED cho request result sai và replay evidence thiếu/sai kiểu/sai hash.

## Trạng thái các phần khác

Triệu chứng V4-R4/R5 cũ đã bị chặn ở control hiện hành; chưa đóng đầy đủ phần DB observation/created resource identity thực tế vì source/runtime chưa kiểm. Manifest canonical hiện là danh sách tên, chưa là bằng chứng resource ID/ownership ngoài đời. V4-R2/R3 tiếp tục GREEN trong unit/probe đã chạy. Không diễn giải unit/canonical synthetic thành runtime đạt hoặc gate V4 hoàn tất.

Full Python 477 PASS và Flutter analyze0/247+1skip trước đó giữ đúng phạm vi bản vòng 1/ứng dụng không đổi; chưa có full suite vòng 2 mới. Chỉ chạy full suite bản cuối sau khi xử lý lỗi còn tái hiện. Không có DB schema/app thay đổi được giao.

Giao Anti **sửa vòng 3/3 cuối cùng** trên bốn file đã giao; giữ mọi probe/capture reviewer. [AGENTS.md](../../../AGENTS.md), dòng 148: “Còn lỗi sau 3 vòng thì dừng và báo chủ dự án.” Không tự mở vòng 4 hoặc tự thay vai trò implementer; toàn BH-07/V8 chưa nghiệm thu, không merge/push/deploy/pilot/BH-08.
