# Bàn giao V4 Tooling: Bounded COPY Observation Window & Safe Diagnostics (Sửa CW2 P2 Vòng 2/3) — 10/11/2026

**Trạng thái: Chờ review (NOT Done, NOT runtime PASS). Toàn V4/BH-07/V8 chưa nghiệm thu.**
Base HEAD `5db7e93` trên nhánh `feat/bh07-completion-local`. Implementer: Anti CLI (Gemini 3.8 Flash High); Reviewer: Codex.

---

## 1. Bối cảnh và Tiếp thu Đánh giá Codex sau R1

Theo báo cáo đánh giá độc lập của Codex tại [`docs/reviews/bh07/v4_copy_window_review_after_r1_20261110.md`](docs/reviews/bh07/v4_copy_window_review_after_r1_20261110.md):
- **CW1 ĐÃ ĐÓNG:** Parser đã loại bỏ hoàn toàn fallback stats/expected substitution; mock main được sửa trả đúng JSON.
- **CW3 ĐÃ ĐÓNG:** Padding target receipt đã được đưa vào cấu trúc cuối cùng `summary['restored_verification']`, không còn bị ghi đè.
- **CW4 ĐÃ ĐÓNG:** Khẳng định timing 2–3 giây đã được thay bằng giả thuyết thiết kế chưa đo; native COPY/HTTP overlap vẫn là gate thật.
- **Kết quả kiểm chứng độc lập của Reviewer:** 88 targeted V4 tests PASS (26 runtime-collection + 56 concurrency + 6 supplemental), probe 49/49 PASS, full Python suite kết thúc exit 0.

Vấn đề duy nhất còn lại được giao sửa trong **vòng 2/3**:
- **CW2 P2 — Regex độ dài digest chưa chuẩn xác:**
  - *Vấn đề:* Tại line 93 (`_parse_and_validate_padding_stats`) và line 1062 (`validate_v4_rehearsal`), biểu thức chính quy `[0-9a-f]{32,64}` chấp nhận mọi độ dài nằm giữa 32 và 64 ký tự (ví dụ 33 ký tự được parser và matching validator chấp nhận, `ok=True`, findings rỗng), trong khi đặc tả yêu cầu chính xác 32 HOẶC 64 ký tự hex.
  - *Khắc phục trong vòng 2/3:*
    1. Sửa biểu thức chính quy tại cả hai vị trí thành: `^([0-9a-f]{32}|[0-9a-f]{64})$`.
    2. Thêm negative controls trong unit tests: cả parser và matching source/target receipt validator đều từ chối dứt điểm các chuỗi digest có độ dài 33, 40, 63 ký tự.
    3. Thêm positive controls trong unit tests: chấp nhận chính xác 32 và 64 ký tự hex cho cả parser và matching validator.
    4. Giữ nguyên câu truy vấn SQL native sử dụng `md5` (32 ký tự); không thay đổi workload, schema, hay bất kỳ gate nào khác.

---

## 2. Chi tiết Sửa đổi Phạm vi Hẹp (Round 2/3 Delta)

1. **`scripts/bh07_backup/run_v4_concurrent_rehearsal.py`**:
   - Line 93 trong `_parse_and_validate_padding_stats`:
     Thay `r'^[0-9a-f]{32,64}$'` bằng `r'^([0-9a-f]{32}|[0-9a-f]{64})$'`.
   - Line 1062 trong `validate_v4_rehearsal`:
     Thay `r'^[0-9a-f]{32,64}$'` bằng `r'^([0-9a-f]{32}|[0-9a-f]{64})$'`.

2. **`tests/test_bh07_v4_runtime_collection.py`**:
   - Trong `test_padding_fixture_rejects_malformed_empty_wrong_type_missing_field`: bổ sung các payload có độ dài digest 33, 40 (dạng git sha), 63 ký tự; assert kích hoạt `ValueError` fail-closed cho cả `setup_padding_fixture` và `verify_restored_padding_fixture`.
   - Thêm `test_padding_fixture_accepts_exact_32_and_64_hex_digest`: kiểm tra parser chấp nhận chính xác độ dài 32 và 64 ký tự.
   - Trong `test_validator_rejects_malformed_or_overbudget_padding_fixture`:
     - Positive control: kiểm tra validator chấp nhận matching source/target receipts có digest 64 ký tự hex (`valid_64` với `ok=True`).
     - Negative controls: kiểm tra validator từ chối dứt điểm matching source/target receipts có digest 33, 40, 63 ký tự hex (`ok=False`, `invalid_padding_fixture`).

3. **`docs/reviews/bh07/v4_copy_window_handoff_20261110.md`**:
   - Cập nhật tài liệu bàn giao vòng 2/3.

---

## 3. Trạng thái Kiểm chứng & Giới hạn Hiện tại

- **Môi trường Implementer:** Thực hiện hoàn toàn bằng công cụ đọc/sửa file cục bộ; không gọi lệnh shell/powershell, không chạy runtime Docker hay DB thật trong phiên này theo chỉ đạo.
- **Trạng thái Test trong phiên này:** RED / GREEN **NOT RUN** (do không dùng công cụ shell; kết quả test trước đó thuộc về lượt chạy độc lập của Codex reviewer).
- **Runtime Docker / DB / Auth / Dump / Restore:** **NOT RUN**.
- **Chưa nghiệm thu:** Toàn bộ V4 / BH-07 / V8 chưa nghiệm thu. Không commit, không push, không merge, không deploy, không pilot, không BH-08.

---

## 4. Hướng dẫn Lệnh cho Codex Reviewer

Codex reviewer có thể kiểm chứng độc lập trên môi trường có Python bundled và Docker:

1. **Kiểm tra Unit Test V4 (bao gồm các test mới về CW2 P2 digest lengths):**
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
