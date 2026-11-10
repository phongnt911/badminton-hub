# Bàn giao sửa phục hồi target Auth SITE_URL — 10/11/2026

**Trạng thái:** Chờ review (vòng 1/3 subtask phục hồi `SITE_URL`).
**Base SHA:** `791bcf7`
**Người thực hiện:** Antigravity (tuân thủ chỉ thị file tools only, không shell, không agent, không runtime, không timeout).

## 1. File thay đổi

- `scripts/bh07_backup/run_v4_concurrent_rehearsal.py` (thêm `GOTRUE_SITE_URL` vào target Auth envfile)
- `tests/test_bh07_v4_runtime_collection.py` (thêm test `test_target_auth_env_includes_valid_loopback_site_url`)
- `docs/reviews/bh07/recovery_site_url_handoff_20261110.md` (tài liệu bàn giao này)

## 2. Nguyên nhân thiếu key (Causality)

- GoTrue v2.197.0 (`ghcr.io/supabase/gotrue:v2.197.0`) yêu cầu bắt buộc `GlobalConfiguration.SiteURL` (`required: true` trong mã nguồn Go chính thức `internal/conf/configuration.go`).
- Khi cấu hình thiếu `GOTRUE_SITE_URL`, GoTrue thoát ngay lập tức với exit code 1 (`configuration_load_failed: true`, `missing_configuration_keys: ['SITE_URL']`), như đã được wrapper chẩn đoán `faf0482c` định vị chính xác.
- Runtime runner thường `0031d57d` ghi nhận exit code 1 tại `port_discovery` / `target_port_discovery`; nó chưa xác lập service cụ thể hoặc trạng thái exit Auth. Direct inspect target_auth exited1/missing SITE_URL thuộc lượt wrapper `faf0482c` với cùng cấu hình. Đây là chẩn đoán lặp có thêm quan sát, không retag metadata wrapper sang lượt runner thường.
- Trong stack nguồn (`run_local_stack.py`), cấu hình đã có sẵn `GOTRUE_SITE_URL=http://127.0.0.1:3000`. Tuy nhiên ở target recovery stack (`t_auth_env` trong `run_v4_concurrent_rehearsal.py`), biến này bị thiếu.

## 3. Bản sửa tối thiểu (Smallest Fix)

- Tại `scripts/bh07_backup/run_v4_concurrent_rehearsal.py` (Boundary 1: `target_auth_start`), thêm đúng 1 dòng:
  ```python
  GOTRUE_SITE_URL=http://127.0.0.1:3000\n
  ```
  vào `t_auth_env.write_text(...)`.
- Giá trị URL loopback hợp lệ, không rỗng, nhất quán với công thức stack local nguồn, không chứa secret/private values.
- Không thay đổi bất kỳ cài đặt không liên quan nào: giữ nguyên `API_EXTERNAL_URL`, image tag (`gotrue:v2.197.0`), port mapping (`127.0.0.1::9999`), cơ chế dynamic port, thời điểm snapshot/padding, validator contract và quy trình cleanup.

## 4. Test điều phối chính (Main Orchestration Test)

- Đã thêm test `test_target_auth_env_includes_valid_loopback_site_url` vào `tests/test_bh07_v4_runtime_collection.py`:
  - Hook qua `command_fn` của `_run_orchestration_scenario` tại ranh giới `OP_TARGET_AUTH_START`.
  - Đọc trực tiếp đường dẫn file `--env-file` khi file đang sống trên đĩa trong quá trình thực thi.
  - Phân tích và chứng minh `GOTRUE_SITE_URL` tồn tại, không rỗng, scheme thuộc `('http', 'https')`, hostname thuộc `('127.0.0.1', 'localhost', '::1')` và bằng `http://127.0.0.1:3000`.
  - Toàn bộ private credentials (mật khẩu database, JWT secret) trong envfile không bị trích xuất hay đưa vào assertion output.
  - Đảm bảo tính fail-closed: nếu chạy test này trên source baseline cũ `791bcf7`, test sẽ FAIL do `GOTRUE_SITE_URL` thiếu (`None`).
  - Toàn bộ các control thành công và failure stage tests hiện có giữ nguyên kết quả mong đợi.

## 5. Lệnh Codex dự kiến để kiểm chứng (Expected Verification Commands)

1. **Phát lại RED trên baseline 791bcf7 bằng helper Codex (không sửa checkout):**
   ```bash
   python .build/replay_site_url_baseline.py
   ```
   Helper đọc Git blob source791bcf7, compile module với đúng ROOT, rồi tạm dùng module đó cho test mới. Codex đã chạy sau bàn giao và thấy1FAIL thiếu SITE_URL; đây là baseline replay hồi cứu, không nhận là Anti đã chạy RED trước edit. Lệnh unittest thông thường chỉ chạy candidate hiện tại, không tự chuyển source về baseline.
2. **Kiểm tra GREEN cho test mới trên candidate:**
   ```bash
   python -m unittest tests.test_bh07_v4_runtime_collection.RuntimeCollectionTests.test_target_auth_env_includes_valid_loopback_site_url
   ```
3. **Chạy toàn bộ suite runtime collection:**
   ```bash
   python -m unittest tests.test_bh07_v4_runtime_collection
   ```
4. **Hồi quy full test suite Python:**
   ```bash
   python -m unittest discover tests
   ```
5. **Kiểm tra tĩnh và test Flutter không đổi:**
   ```bash
   flutter analyze
   flutter test
   ```

## 6. Phạm vi và NOT RUN

- Anti chỉ sử dụng file tools, không chạy shell / subagent / Docker / database runtime trong lượt này.
- Full V4 rehearsal runtime (với Docker stack thực, snapshot held, concurrent writers và restored replay) giữ trạng thái **NOT RUN**.
- Toàn bộ V4 / BH-07 / V8 chưa nghiệm thu; không merge, không deploy, không pilot, không nới gate hay tự chấp nhận rủi ro.
