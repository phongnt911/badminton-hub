**Hiện hành (Sửa vòng 1/2):** Đã sửa đủ FH1–FH4 (precondition payment bắt buộc, cleanup receipt validation & hash match, đính chính SHA thực `cd25e1e3557e2013e8991b2031a240818ee84c96`, thu hẹp phạm vi kết luận sentinel V8 và khớp path length 21/20), chờ review độc lập vòng 1/2. Giữ NOT RUN cho các phạm vi chưa đo; người triển khai không tự ghi Đạt toàn V2b/BH-07.

# Bàn giao Mở rộng Độ phủ Bộ nhớ V2b BH-07: Payments & Charges trên Web Profile Local (Sửa Vòng 1/2)

- Ngày: 28/10/2026, Asia/Saigon.
- Nhánh: `feat/bh07-finance-heap-coverage`, base `303a6ccf4374e28188ff0d924fd39d2c8ab674dc`.
- Tested source commit đo heap thực tế: `cd25e1e3557e2013e8991b2031a240818ee84c96` (`git_dirty: false`, đính chính lỗi gõ nhầm chuỗi SHA dài ở bàn giao trước theo FH3).
- Bundle bằng chứng đo heap: [`finance_heap_evidence/`](finance_heap_evidence/).
- Bản đồ độ phủ cập nhật: [`v2b_coverage_map.md`](v2b_coverage_map.md).
- Người nhận bàn giao: Codex điều phối / Reviewer độc lập chốt.

---

## 1. Tóm tắt Kết quả Khắc phục FH1–FH4 (Sửa Vòng 1/2)

1. **FH1 (P1) — Precondition Bắt buộc cho Payment Coverage (Không PASS Dựa Vào Expense IDs):**
   - Trong [`scripts/bh07_appheap/heap_oracle.py`](../../../scripts/bh07_appheap/heap_oracle.py) (`decide()`), bổ sung kiểm tra nghiêm ngặt: khi profile khai báo `payment_id` trong `owner_sentinels`, bắt buộc `payment_id` phải được gate trong `owner_active`. Nếu thiếu precondition (không nạp ở `owner_active` hoặc xuất hiện ở baseline làm mất tính phân biệt), `decide()` trả về `verdict: FAIL` với finding rõ ràng.
   - Trong [`scripts/bh07_appheap/verify_evidence.py`](../../../scripts/bh07_appheap/verify_evidence.py), `_check_cycles` kiểm tra độc lập rằng mọi sentinel tài chính khai báo trong `summary['sentinels']` đều được gate ở `owner_active` của từng chu kỳ; thiếu precondition dẫn đến exit 1.
   - Thêm unit test TDD trong [`tests/test_bh07_finance_heap_coverage.py`](../../../tests/test_bh07_finance_heap_coverage.py) (`test_mutant_2_payment_id_not_loaded_in_owner_active`, `test_mutant_2b_payment_id_seen_at_baseline_fails_precondition`, `test_payment_never_gated_in_cycles_fails_auditor`), kiểm tra cả `decide()` verdict và auditor CLI exit 1.

2. **FH2 (P2) — Xác thực Đầy đủ Cleanup Receipt & Khớp Hash payment_id:**
   - Trong [`scripts/bh07_appheap/verify_evidence.py`](../../../scripts/bh07_appheap/verify_evidence.py) (`_check_cleanup()`), thay thế điều kiện phụ thuộc vào sự tồn tại của cờ bằng ràng buộc theo khai báo sentinel: khi bundle khai báo `payment_id`, bắt buộc phải có `run_only_payment_created: true`, các cờ `extra_payment_removed: true`, `extra_payment_verified_absent: true`, không có `extra_payment_error`, và `run_only_payment_id_sha256_12` bắt buộc phải khớp chính xác với `sha256_12` của `payment_id` trong metadata (`852eec161334`).
   - Giữ nguyên tính tương thích ngược cho các bundle legacy (như `b13e468`, `retained_path`) không khai báo `payment_id`.
   - Bổ sung unit tests cho toàn bộ các trường hợp thiếu cờ, xóa receipt, sai hash, báo lỗi cleanup trong `test_bh07_finance_heap_coverage.py`.

3. **FH3 (P2) — Đính chính Tested Source SHA Theo Git Provenance Thực Tế:**
   - Đính chính SHA runtime đo heap thực tế thành `cd25e1e3557e2013e8991b2031a240818ee84c96` trong toàn bộ tài liệu bàn giao, bản đồ độ phủ và `AGENTS.md`. Khớp chính xác với `tested_source_sha` trong `finance_heap_evidence/summary.json` và `report.md`.

4. **FH4 (P2) — Thu hẹp Kết luận Đúng Phạm vi Sentinel V8 & Khớp Path Length:**
   - Thu hẹp khẳng định: Kết quả đo xác nhận chuỗi `payment_id` có mặt ở `owner_active` (độ dài đường dẫn 21 ở chu kỳ 1, 20 ở chu kỳ 2 từ GC roots), và biến mất 100% (`occurrences: 0`, `reachable: false`) ở `post_logout` và `post_actor` trong snapshot V8 Web profile đã đo.
   - Không suy từ việc biến mất của chuỗi định danh sang việc toàn bộ object graph Dart, bộ nhớ Dart VM native, hay app-wide retention đã được giải phóng (các phạm vi này giữ `UNKNOWN`/`NOT RUN`).
   - `payment_ref` tiếp tục được phân loại trung thực là `unattributed residual risk` do tồn lưu trong `segmentationCache` (path len 12).
   - Roster identity `playerId` tái xuất hiện ở `post_cohost` là do tải lại danh sách phiên hợp lệ, không suy thành rò rỉ hay bằng chứng sạch cho model `FinanceCharge`.

---

## 2. Lệnh Tự Kiểm tra & Tái lập (Replay Commands)

```powershell
# 1. Phát lại reviewer semantic probes (positive: exit 0; 5 mutants: exit 1)
python -c "import pathlib; pathlib.Path.write_text = lambda self, data, *a, **k: self.write_bytes(data.encode('utf-8') if isinstance(data, str) else data); import runpy; runpy.run_path('docs/reviews/bh07/review_6f59f5e_evidence/probes.py')"

# 2. Kiểm tra tính toàn vẹn bundle bằng chứng đo heap (PASS)
python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir docs/reviews/bh07/finance_heap_evidence

# 3. Chạy test suite hồi quy Python (331/331 OK)
python -X utf8 -m unittest discover -s tests

# 4. Chạy fixture controls độc lập (8/8 OK)
node scripts/bh07_appheap/fixture_controls.js

# 5. Phân tích tĩnh Flutter (0 issues) & test suite Dart (247 passed + 1 skipped)
flutter analyze
flutter test

# 6. Đối chiếu bundle QA lịch sử (PASS, không đổi byte)
python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir docs/reviews/bh07/review_runtime_b13e468_evidence
```

---

## 3. Bảng Trạng thái Phủ & NOT RUN V2b §4.4

| Thực thể / Hạng mục | Trạng thái Hiện tại | Bằng chứng / Ranh giới |
| :--- | :--- | :--- |
| **Mã chi phí (`expense_id`, `expense_id_2`)** | **ĐÃ ĐO & ĐẠT LOCAL** | Web profile (`review_runtime_b13e468_evidence`, `finance_heap_evidence`). |
| **Tiêu đề chi phí (`expense`, `expense2`)** | **RESIDUAL RISK UNATTRIBUTED** | Web engine `segmentationCache` (path len 12). |
| **Mã thanh toán (`payment_id`)** | **ĐÃ ĐO TRÊN V8 HEAP SNAPSHOT** | Web profile (`finance_heap_evidence`). Chuỗi vắng mặt 100% sau logout; object graph/native Dart VM giữ NOT RUN. |
| **Mã tham chiếu thanh toán (`payment_ref`)** | **RESIDUAL RISK UNATTRIBUTED** | Web engine `segmentationCache` (path len 12). |
| **Khoản thu (`charges`)** | **PHÂN ĐỊNH RANH GIỚI DTO** | Không có `chargeId`/`notes`; `playerId` chia sẻ với roster identity; Provider unit test đạt. |
| **Ngân hàng CLB (`bank`, `receiver`)** | **NOT RUN** | Chưa duyệt màn hình cấu hình ngân hàng CLB trong runner. |
| **Chỉ dẫn thanh toán QR (`payment_instructions`)** | **NOT RUN** | Chưa duyệt màn hình xem QR của người chơi trong runner. |
| **Sổ quỹ CLB (`club_ledger`)** | **NOT RUN** | Chưa duyệt màn hình Quỹ CLB trong runner. |
| **Tổng kết số tiền (`session_summary`)** | **CHƯA CÓ SENTINEL CHUỖI** | Chỉ chứa số nguyên tiền tệ, chia sẻ vòng đời Provider đã reset. |
| **Listener object graph trên Web heap** | **NOT RUN** | Chưa probe đồ thị đối tượng bộ nhớ runtime cho listener closure. |
| **Đo heap trên Dart VM (desktop/mobile)** | **NOT RUN** | Chưa chạy trên Dart VM service. |
| **Nghiệm thu toàn V2b và toàn BH-07** | **CHƯA NGHIỆM THU** | Không merge `main`/`staging`/`production`, không deploy/pilot/BH-08. Người triển khai không tự ghi Đạt. |
