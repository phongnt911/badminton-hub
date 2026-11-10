**Cập nhật sau ủy quyền “codex tự sửa” 09/11/2026:** bản sửa guard/probe đã [Đạt review độc lập có giới hạn](codex_v4_supplemental_review.md); Codex và reviewer chạy riêng 499 Python PASS, probe 49 controls PASS. Full source/runtime V4 chưa kiểm đủ, toàn BH-07/V8 chưa nghiệm thu. [Handoff bổ sung](codex_v4_supplemental_handoff.md). Điểm dừng Anti bên dưới là lịch sử trước bản sửa này.

**Kết luận reviewer 09/11/2026: CHƯA ĐẠT, dừng sau sửa vòng 3/3.** 56 targeted tests PASS; standalone probe FAIL và 3 semantic mutant còn PASS sai. Source/runtime V4 chưa kiểm đủ. Xem [review chốt](review_v4_concurrent_backup_final_20261109.md). Bàn giao implementer dưới đây giữ lịch sử trước kết luận.

# BH-07 V4: Bàn giao diễn tập Backup/Restore dưới tải ghi đồng thời (Concurrent HTTP Writers)

> **Trạng thái: Ứng viên sửa đổi vòng 3/3 cuối cùng chờ Codex review độc lập (09/11/2026).** Người triển khai **KHÔNG tự ghi Đạt, KHÔNG tuyên bố PASS**. Toàn bộ số lượng unit test, probe, và runtime thực tế ở lượt này là **NOT RUN bởi implementer** (Codex trực tiếp chạy kiểm chứng và runtime). Base thực tế: `b72c563d9e519986dbd88ec98bcc3f015a41a442`; Nhánh: `feat/bh07-completion-local`. Kết quả này thuộc phạm vi diễn tập local cô lập; không tự suy thành nghiệm thu toàn BH-07, không tự merge main, deploy, production, hay pilot.

---

## 1. Nội dung sửa chữa Vòng 3/3 (Giải quyết triệt để V4-R1 Request/Replay Evidence)

Theo kết quả rà soát từ [`review_v4_concurrent_backup_after_r2.md`](review_v4_concurrent_backup_after_r2.md):

1. **Ràng buộc Stored Result & Payment ID của Operation Request (`request_payment_wrong_valid_digest`):**
   - Validator bắt buộc đối chiếu `payment_id` trong bản ghi `request` và trong `result` JSON của `operation_requests` phải khớp chính xác với `payment_id` của thao tác (`pid`), từ chối mọi trường hợp thay thế UUID (`relational_evidence_mismatch`).
   - Kiểm tra ràng buộc cả trong `source_operations` lẫn `restored_row_evidence`.

2. **Ràng buộc Digest và Nguồn gốc Replay Fingerprints (`invalid_equal_replay_fingerprints`):**
   - Replay fingerprints (`before_replay_fingerprint`, `after_replay_fingerprint`) bắt buộc phải là chuỗi băm hex SHA-256 64 ký tự hợp lệ (`^[0-9a-f]{64}$`).
   - Từ chối các chuỗi không phải digest (`not-a-digest`) dù chúng bằng nhau (`invalid_replay_fingerprint`).
   - Bắt buộc `before_replay_fingerprint` phải khớp với băm SHA-256 của bảng `public.payments` trong DB đã khôi phục (`replay_fingerprint_mismatch`).

3. **Loại bỏ cột HTTP Status giả trong DB & Kiểm tra Stored Business Status (`wrong_stored_request_status`):**
   - Schema thật (`20261015051808_init_schema_v1_1.sql` dòng 501–508) của `operation_requests` gồm `actor_user_id`, `operation`, `request_id`, `payload_hash`, `result` JSONB; **không** có cột `status` HTTP.
   - Truy vấn `query_row_evidence` đọc trực tiếp `result` JSONB và trích xuất `result->>'payment_id'`, trạng thái nghiệp vụ `confirmed`.
   - Validator từ chối trạng thái thất bại (500, fail, error) trong stored request (`relational_evidence_mismatch`), giữ mã phản hồi transport HTTP (200) ở trường riêng biệt của operation.

4. **Trạng thái Gateway Admission & Literal Credentials:**
   - Mã nguồn không chứa bất kỳ secret literal nào; toàn bộ credential được sinh ngẫu nhiên tại runtime. Báo cáo trung thực thông báo `secret.redacted/redaction.incomplete` từ gateway freshread như một rào cản xét duyệt bên ngoài (external admission blocker), không can thiệp né tránh hay làm mờ mã nguồn.

---

## 2. Bốn file sở hữu của lượt triển khai

- [`../../../tests/test_bh07_v4_backup_concurrency.py`](../../../tests/test_bh07_v4_backup_concurrency.py):
  - Cập nhật fixture `setUp` theo cấu trúc `operation_requests.result` thật.
  - Bổ sung 7 unit tests mới cho V4-R1: `request_payment_wrong_valid_digest`, `invalid_equal_replay_fingerprints`, `wrong_stored_request_status`, `missing_stored_request`, `replay_fingerprint_mismatch_with_restored_db`, `stored_result_payment_id_mismatch`, và `stored_result_amount_mismatch`.
- [`../../../scripts/bh07_backup/run_v4_concurrent_rehearsal.py`](../../../scripts/bh07_backup/run_v4_concurrent_rehearsal.py):
  - Nâng cấp `validate_v4_rehearsal` với kiểm tra chặt chẽ stored `result` JSON, `payment_id`, trạng thái nghiệp vụ, digest replay hợp lệ và khớp với DB restored.
  - Cập nhật `query_row_evidence` truy vấn đúng schema `operation_requests` mà không bịa đặt cột HTTP status.
- [`../../../scripts/bh07_backup/v4_concurrent_probe.py`](../../../scripts/bh07_backup/v4_concurrent_probe.py):
  - Cập nhật `build_canonical_summary` và bổ sung 5 mutants kiểm chứng: `request_payment_wrong_valid_digest`, `invalid_equal_replay_fingerprints`, `wrong_stored_request_status`, `missing_stored_request`, và `replay_fingerprint_mismatch_with_restored_db`.
- [`v4_concurrent_backup_handoff.md`](v4_concurrent_backup_handoff.md):
  - Hồ sơ bàn giao này.

---

## 3. Lệnh thực thi dành cho Codex (Implementer KHÔNG tự chạy ở lượt này)

> Toàn bộ các lệnh dưới đây là **NOT RUN bởi implementer**. Codex sẽ độc lập kiểm tra mã nguồn, chạy kiểm thử và thực thi runtime.

```powershell
# 1. Chạy suite unit test V4 (Codex chạy kiểm chứng)
python -m unittest tests.test_bh07_v4_backup_concurrency -v

# 2. Chạy probe độc lập kiểm tra fail-closed validator và semantic mutants (Codex chạy)
python scripts/bh07_backup/v4_concurrent_probe.py

# 3. Chạy diễn tập V4 thực tế trên cụm Docker cô lập (Codex chạy trên máy có Docker)
python -u scripts/bh07_backup/run_v4_concurrent_rehearsal.py --out scratch/bh07-v4-rehearsal

# 4. Hồi quy toàn bộ test Python trong repository (Codex chạy)
python -m unittest discover -s tests
```

---

## 4. Hợp đồng CLI & Cấu trúc kết quả (Exact CLI Contract)

Lệnh `run_v4_concurrent_rehearsal.py` nhận tham số:
- `--out <path>`: Thư mục xuất bằng chứng (bắt buộc chưa tồn tại trước khi chạy).

Cấu trúc thư mục đầu ra `--out`:
- `summary.json`: Báo cáo có cấu trúc JSON chứa đầy đủ mốc snapshot, bằng chứng quan sát `pg_stat_activity`, thời gian thực thi của từng writer, kết quả kiểm tra invariants, và trạng thái dọn dẹp.
- `source_fingerprints.json`: Bảng băm SHA-256 và số dòng của DB nguồn.
- `restored_fingerprints.json`: Bảng băm SHA-256 và số dòng của DB khôi phục.

Mã thoát (Exit Code):
- `0`: Khi toàn bộ luồng diễn tập thành công, validator xác nhận `verdict == 'PASS'`, và dọn dẹp sạch 100% tài nguyên (`cleanup.ok == True`).
- `1`: Bất kỳ lỗi khởi tạo, snapshot mismatch, vi phạm ranh giới commit, sai lệch invariants, hoặc còn sót tài nguyên Docker.

---

## 5. Rủi ro còn lại, Ranh giới V2b & Điều kiện nghiệm thu V8

1. **Ranh giới Diễn tập vs Dịch vụ quản lý Supabase Cloud (Cổng V3):** Rehearsal này chứng minh khả năng phục hồi của PostgreSQL 17 và PostgREST trong môi trường Docker local; **không** thay thế cho việc cấu hình sao lưu tự động của Supabase Cloud, PITR, lưu trữ offsite hoặc mã hóa khối tại tầng hạ tầng đám mây.
2. **Điều phối nhân tạo (Artificial Coordination):** Rào chắn `V4CoordinationBarrier` và cơ chế quan sát `pg_stat_activity` là công cụ điều phối có kiểm soát nhằm chứng minh độ đúng đắn ACID của PostgreSQL dưới ghi đồng thời, **không phải là bài kiểm tra tải cao (load benchmark)**. Kiểm thử tải thực tế thuộc về cổng **V7**.
3. **Các rủi ro tồn đọng của Cổng V2b:**
   - Dữ liệu `payment_ref` còn tồn tại dạng unattributed residual risk trong engine `segmentationCache` (ranh giới giữa Dart/Flutter engine và app memory chưa thể xác lập).
   - Rendered text đối với bank receiver và expense titles vẫn là **unattributed residual risks**.
   - Phép đo heap toàn bộ model (`whole-model`), cây listener (`listener graph`) và môi trường native (Dart VM desktop/mobile) vẫn ở trạng thái **UNKNOWN / NOT RUN** do thiếu Android SDK và Visual Studio C++ toolchain.
4. **Thẩm quyền nghiệm thu V8:** Việc hoàn thành cổng kỹ thuật V4 (nếu Codex nghiệm thu Đạt) chỉ đóng cổng kỹ thuật V4 trên ma trận. Toàn bộ BH-07 và cổng V8 vẫn chưa đủ điều kiện nghiệm thu. Các cổng vận hành chưa chạy (V2 mobile, V3 managed, V5 staging/prod, V7 pilot) bắt buộc phải có văn bản Chấp nhận rủi ro còn lại (Residual-Risk Acceptance) chính thức từ Chủ dự án theo quy tắc [BH-07 readiness §4.11](bh07_readiness.md#411-v8--nghiệm-thu-toàn-bh-07). Người triển khai và Reviewer không ký thay hay bịa đặt nghiệm thu.
