# Review độc lập: bản sửa source/test MC1–MC6

Review ngày 10/11/2026 trên candidate `704a32658353a2148b1f94619db1e991b5562713`, base `d2f6b079a7a6f7521d04b88ac6eb780db5718a56`, nhánh `feat/bh07-completion-local`. Agent reviewer riêng không triển khai bản sửa. Ủy quyền cho Codex sửa MC1–MC6 được ghi tại [phương án khắc phục](v4_machine_remediation_plan_20261110.md).

**Kết luận: Đạt trong phạm vi delta source/test MC1–MC6; không phát hiện P0/P1/P2 còn mở trong phạm vi này.** Không nghiệm thu toàn V4/BH-07/V8 và không xác nhận tính đúng đắn của runtime thật.

## Phạm vi và kết quả

Đã đọc runner, probe, test concurrency hiện có và test runtime-collection mới, đối chiếu [sáu phát hiện tiếp tục trên máy mới](review_423f354_machine_continuation.md), schema migration thật và implementation RPC thu tiền mặt.

- **MC1:** Collector dùng cột thật `session_player_id`, `amount_vnd`, liên kết bằng dòng operation-request thực và kiểm kết quả thu tiền mặt đã lưu. Các tên trường tương thích trong receipt lấy giá trị từ dữ liệu đã lưu.
- **MC2:** Exporter dùng psql quiet/tuples-only và marker snapshot tường minh. Luồng đọc cùng queue giới hạn thời gian đọc pipe; output sai, EOF, timeout hoặc exporter thoát đều bị từ chối. Context manager giải phóng hoặc kết thúc exporter khi thoát.
- **MC3:** Observer loại backend của chính nó, yêu cầu backend `pg_dump` đang COPY. Worker dump tự ghi thời điểm hoàn tất. Receipt đòi khoảng quan sát nằm trong giao của hai khoảng HTTP writer và khoảng dump; cả hai HTTP thành công phải nằm trọn trong thời gian dump đo được. Thiếu quan sát không còn được thay bằng PID/query tổng hợp.
- **MC4:** Replay đọc mới fingerprint nội dung bảng public/auth và schema trước/sau RPC. Đổi dữ liệu dù cùng số dòng hoặc đổi schema đều bị chặn; validator yêu cầu receipt trạng thái trước/sau thực tế.
- **MC5:** Main chỉ đánh dấu hoàn tất sau khi collection/replay thành công. Bước chốt đặt trạng thái ứng viên trước auditor, ép FAIL nếu chưa hoàn tất hoặc có loại lỗi. Kiểm checkout sạch trước khi tạo thư mục output; base SHA ghi nhận đúng base review được giao.
- **MC6:** Thiếu hoặc trùng dòng đã lưu khiến collection thất bại. Audit/request được giới hạn theo actor/request, kiểm operation/action thu tiền mặt và liên kết payment/entity. Cardinality workload loại lịch sử tài chính seed không liên quan.

Ranh giới collector rõ hơn và việc bỏ bằng chứng fallback dựng sẵn giúp truy nguyên lỗi về đúng bước thu thập.

## Kiểm chứng độc lập và nguồn gốc

Reviewer tự chạy trên HEAD đã ghim:

`python -m unittest discover -s tests -p test_bh07_v4_runtime_collection.py`

Python bundled trả **14/14 PASS**, exit 0, 0.283 giây. Test dùng DB/HTTP giả, pipe subprocess thật cho giao thức snapshot và điều phối main được mock; không phải rehearsal Docker/PostgreSQL.

Bốn Git blob candidate đều khớp `source_after` trong [summary của implementer](codex_mc_fixes_20261110_evidence/summary.json). Source/test trong working tree không khác candidate.

| File | Git blob candidate |
| --- | --- |
| `scripts/bh07_backup/run_v4_concurrent_rehearsal.py` | `9541600485e5fad3acddd2a9c81126e9174d2579` |
| `scripts/bh07_backup/v4_concurrent_probe.py` | `e91a49b1ff7e4af7b1b5b2b769a5f274bf60fc1b` |
| `tests/test_bh07_v4_backup_concurrency.py` | `c1eb4fa526981afc67aa0313774015a598a061a5` |
| `tests/test_bh07_v4_runtime_collection.py` | `c46a77a5cbc8d10f34e21184c08ccef1889f261d` |

Implementer báo targeted **76/76**, probe **49/49**, full Python **513 test: 509 PASS + 4 SKIP**, exit 0, 131.094 giây. Đây là kết quả tự kiểm của implementer trong evidence liên kết, không phải reviewer chạy độc lập. Implementer báo lần full suite đầu cần khôi phục byte Git chuẩn của evidence lịch sử và chuẩn bị môi trường test local; reviewer không chạy lại độc lập chuỗi sửa môi trường hoặc full suite đó.

## Giới hạn và cổng tiếp theo

Reviewer **NOT RUN** Flutter analyze/test mới, Docker, HTTP/Auth, PostgreSQL, tương thích exported snapshot, overlap dump/writer thật, dump/restore và cleanup runtime. Không thao tác DB/HTTP/Docker thật. Điều phối mock PASS không chứng minh DB seed nhỏ có cửa sổ COPY đủ dài hay cleanup tiến trình theo nền tảng thành công.

Chỉ đóng sáu phát hiện trong delta source/test này. Trước nghiệm thu runtime vẫn cần rehearsal có bằng chứng riêng và tiền kiểm môi trường/tài nguyên/nguồn gốc. Toàn V4/BH-07/V8 chưa nghiệm thu; không suy ra quyền merge/deploy/pilot/BH-08 hoặc chấp nhận rủi ro thay owner. Ủy quyền commit/push tiến độ để bàn giao máy vẫn tách biệt với nghiệm thu.
