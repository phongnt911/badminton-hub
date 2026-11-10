# Bàn giao V4 Tooling: Bounded COPY Observation Window (Sửa Cuối Vòng 3/3 — Persistent Observer) — 10/11/2026

**Trạng thái: Chờ review (NOT Done, NOT runtime PASS). Toàn V4/BH-07/V8 chưa nghiệm thu.**
Base HEAD `4093608` (sau khi commit sạch candidate R2) trên nhánh `feat/bh07-completion-local`. Implementer: Anti CLI (Gemini 3.8 Flash High); Reviewer: Codex.

---

## 1. Bối cảnh và Nguyên nhân Gốc từ Runtime `4093608`

Theo báo cáo kiểm chứng runtime Docker thực tế tại [`docs/reviews/bh07/v4_copy_window_runtime_4093608_20261110.md`](docs/reviews/bh07/v4_copy_window_runtime_4093608_20261110.md):
- Fixture padding 40.000 dòng / 39.680.000 byte với digest `ba818c38a576623314f70b7db59e4d9c` đã thiết lập thành công.
- Thời gian sống của `pg_dump` kéo dài đạt 1.160s (start `1794292028.5122879`, end `1794292029.6722262`).
- Mẫu ban đầu `initial_observation` đã bắt được `COPY` thành công (backend 409, `1794292028.6372006` – `1794292028.8271687`).
- Hai HTTP writer đã được kích hoạt đồng thời và đều trả về HTTP 200:
  - Writer A: `1794292028.827756` – `1794292028.9075356` (~79.8ms).
  - Writer B: `1794292028.828551` – `1794292028.8653798` (~36.8ms).
  - Khoảng giao thoa thực tế giữa hai HTTP calls: `1794292028.828551` – `1794292028.8653798` (~36.8ms).
- **Nguyên nhân FAIL:** Mỗi lần gọi `observe_dump` trước đây là một lệnh `docker exec psql` subprocess mới, tốn ~190ms cho một chu kỳ spawn/auth/query. Vì thời gian một chu kỳ quan sát (~190ms) lớn hơn khoảng giao thoa (~36.8ms), không có mẫu nào thỏa mãn điều kiện `overlap_start <= observed_start <= observed_end <= overlap_end`, dẫn đến `observation: None` và gate fail-closed.

---

## 2. Kiến trúc và Triển khai Sửa đổi Vòng 3/3 (Persistent Observer)

Để khắc phục độ trễ spawn mà không làm suy yếu bất kỳ cổng kiểm tra nào:
1. **Persistent Warmed-up Connection (`PersistentDumpObserver`):**
   - Khởi tạo một tiến trình `psql` duy nhất qua `docker exec -i` với các cờ `-X -qAt -U postgres -d postgres -v ON_ERROR_STOP=1` **trước khi** `pg_dump` bắt đầu.
   - Gửi truy vấn làm nóng `SELECT 'WARMED_UP:0:READY';` và kiểm tra phản hồi để xác nhận kết nối đã sẵn sàng.
   - Các truy vấn quan sát tiếp theo được gửi trực tiếp qua pipe `stdin/stdout` đã kết nối, giảm thời gian roundtrip từ ~190ms xuống chỉ còn ~1–2ms.
2. **Giao thức Phân định Rõ ràng với Sequence Marker:**
   - Mỗi truy vấn mang marker tuần tự duy nhất: `SELECT 'OBSERVATION:' || {seq} || ':' || COALESCE(json_agg(...), '[]'::json) ...`.
   - Phản hồi từ pipe bắt buộc phải có tiền tố `OBSERVATION:{seq}:[...]`. Mọi trường hợp lệch sequence, phản hồi rỗng, EOF bất ngờ, hoặc JSON sai định dạng đều kích hoạt lỗi fail-closed ngay lập tức.
3. **Đọc Có Giới hạn Thời gian (Bounded Pipe Read) Tái sử dụng Queue/Thread Idiom:**
   - Luồng nền đọc stdout đưa từng dòng vào `queue.Queue`.
   - Hàm `observe()` đọc từ queue với timeout giới hạn (mặc định 5.0s, có thể chỉ định ngắn hơn).
   - `observed_start` và `observed_end` ghi nhận chính xác mốc thời gian host thực tế ngay trước khi ghi `stdin` và ngay sau khi nhận từ queue. Tuyệt đối không thay thế bằng đồng hồ DB hay dữ liệu giả lập.
4. **Quản lý Vòng đời An toàn (Context Manager — No Leaked Processes):**
   - Context manager quản lý chặt chẽ tiến trình: gửi `\q` thoát êm, fallback `kill()` nếu quá hạn, đóng toàn bộ streams (`stdin`, `stdout`, `stderr`) và `join()` luồng đọc.
   - Đảm bảo dọn dẹp sạch sẽ trong mọi kịch bản thành công, exception, hoặc timeout.
5. **Giữ Nguyên Workload & Cổng Kiểm tra Nghiêm ngặt:**
   - Không chèn thêm `sleep` hay độ trễ giả tạo vào HTTP writers; giữ nguyên tải công việc và padding.
   - Giữ nguyên điều kiện kiểm tra giao thoa: mẫu quan sát bắt buộc phải nằm trọn vẹn bên trong cả hai khoảng HTTP writer thành công và thời gian dump thực tế.
   - Nếu không bắt được mẫu `COPY` trước khi dump thoát, writers tuyệt đối không được gửi.

---

## 3. Danh mục Tệp Sở hữu và Thay đổi

1. **`scripts/bh07_backup/run_v4_concurrent_rehearsal.py`**:
   - Thêm lớp `PersistentDumpObserver` và hàm factory `open_dump_observer`.
   - Cập nhật `dump_with_writers` sử dụng `factory(container)` để mở và warm-up observer trước khi submit dump.
   - Giữ nguyên hàm `observe_dump` cho khả năng tương thích ngược.

2. **`tests/test_bh07_v4_runtime_collection.py`**:
   - Cập nhật `test_dump_completion_is_not_delayed_until_writer_join` mock đúng ranh giới observer (`open_dump_observer`).
   - Thêm bộ test `PersistentDumpObserverTests` (9 test cases) kiểm tra toàn diện qua real subprocess pipes không cần Docker:
     - `test_observer_protocol_happy_path_and_timing`
     - `test_observer_protocol_eof_detected_fail_closed`
     - `test_observer_protocol_malformed_marker_rejected`
     - `test_observer_protocol_malformed_json_rejected`
     - `test_observer_protocol_ambiguous_rows_rejected`
     - `test_observer_protocol_warmup_timeout_and_no_child_leak`
     - `test_observer_protocol_query_timeout_and_no_child_leak`
     - `test_dump_with_writers_wiring_with_mock_observer`
     - `test_dump_with_writers_no_initial_observation_aborts_without_writers`

3. **`docs/reviews/bh07/v4_copy_window_handoff_20261110.md`**:
   - Cập nhật tài liệu bàn giao vòng 3/3.

---

## 4. Trạng thái Kiểm chứng & Giới hạn Hiện tại

- **Môi trường Implementer:** Thực hiện hoàn toàn bằng công cụ đọc/sửa file cục bộ; không gọi lệnh shell/powershell, không chạy runtime Docker hay DB thật trong phiên này theo chỉ đạo.
- **Trạng thái Test trong phiên này:** RED / GREEN **NOT RUN** (do không dùng công cụ shell).
- **Runtime Docker / DB / Auth / Dump / Restore:** **NOT RUN**.
- **Chưa nghiệm thu:** Toàn bộ V4 / BH-07 / V8 chưa nghiệm thu. Đây là vòng sửa chữa cuối cùng (3/3) được phép. Không commit, không push, không merge, không deploy, không pilot, không BH-08.

---

## 5. Hướng dẫn Lệnh cho Codex Reviewer

Codex reviewer có thể kiểm chứng độc lập trên môi trường có Python bundled và Docker:

1. **Kiểm tra Unit Test V4 (bao gồm các test mới về Persistent Observer):**
   ```powershell
   python -m unittest tests.test_bh07_v4_runtime_collection -v
   python -m unittest tests.test_bh07_v4_backup_concurrency -v
   python -m unittest tests.test_bh07_v4_codex_supplemental -v
   ```

2. **Kiểm tra Standalone Probe (49 controls):**
   ```powershell
   python scripts/bh07_backup/v4_concurrent_probe.py
   ```

3. **Chạy Full Python Test Suite:**
   ```powershell
   python -m unittest discover -s tests
   ```

4. **Chạy Rehearsal Docker Runtime sạch (khi môi trường sẵn sàng):**
   ```powershell
   python scripts/bh07_backup/run_v4_concurrent_rehearsal.py --out tmp/v4-runtime-test
   ```
