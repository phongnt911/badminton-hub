# Bàn giao chẩn đoán lỗi V4 Docker runtime — Phase B (Triển khai runner)

- **Thời điểm**: 10/11/2026
- **Trạng thái nguyên nhân gốc**: **UNKNOWN** (vẫn chưa kết luận nguyên nhân gốc của runtime overlap; cần lượt chạy runtime thực tế với diagnostics receipt được lưu lại để phân biệt).
- **Base HEAD**: `08c2069aaa111b7805c785bdf0af205a6b374ae8`
- **Xác nhận RED từ Codex**: Codex đã chạy `python tests/test_bh07_v4_runtime_collection.py -v`: 19 tests, 5 failures do thiếu `diagnostics`, 14 existing pass, exit 1.
- **Tự nhận định kết quả**: Anti CLI **KHÔNG** tự nhận GREEN và không tự chạy lệnh/runtime. Toàn bộ kiểm chứng giao lại cho Codex chạy.

## 1. Các file đã chỉnh sửa

1. `scripts/bh07_backup/run_v4_concurrent_rehearsal.py`:
   - Bổ sung hàm `_safe_diagnostics(measured, exporter_rc)` với whitelist nhỏ nhất:
     - `dump_exit_code`: mã thoát thực tế của dump subprocess.
     - `dump_start`, `dump_end`: mốc thời gian dump.
     - `observation`: dict an toàn gồm `dump_pid`, `dump_application_name`, `observed_start`, `observed_end`, `observed_during_active_dump`, hoặc `None` (không chứa `dump_query` hoặc SQL thô).
     - `writer_a`, `writer_b`: dict an toàn `status`, `start`, `end`, hoặc `None` khi chưa gửi (không chứa payload, response body, payment reference, token).
     - `overlap_verified`: boolean.
     - `exporter_returncode`: mã thoát thực tế của snapshot exporter process.
   - Gọi `exporter_rc = exporter.poll()` một lần vô điều kiện và lưu vào `summary['diagnostics']` **TRƯỚC KHI** kiểm tra overlap/exporter và raise `ValueError`.
   - Không thay đổi bất kỳ scheduling, workload, gate, validator hay cấu hình nào khác.

2. `tests/test_bh07_v4_runtime_collection.py`:
   - Tái sử dụng `_run_orchestration_scenario` cho test thành công hiện có (`test_main_wires_scoped_collection_replay_and_success_audit`), loại bỏ khoảng 70 dòng mock trùng lặp mà vẫn bảo toàn 100% các assertion ban đầu.
   - Loại bỏ các tham số ghi đè không sử dụng trong `_run_orchestration_scenario`.
   - Siết chặt assertion writer-not-sent: bắt buộc `None` hoặc `{'sent': False}`, không chấp nhận dict rỗng thiếu status.

## 2. Reviewer prompt (giao Codex chạy kiểm chứng)

Codex chạy suite kiểm thử đơn vị để xác nhận 19/19 tests chuyển sang GREEN:
```text
python tests/test_bh07_v4_runtime_collection.py -v
```
