# Bàn giao Điều tra Phân định Giữ Dữ liệu (Retention Attribution) & Bản đồ Phủ (Coverage Map) V2b BH-07

- Ngày: 28/10/2026, Asia/Saigon.
- Nhánh: `feat/bh07-retention-attribution`, tạo từ base `90e9d99b848f30fa3e3b2a3e643dbf784baaea9e`.
- Tested source runtime QA đối chiếu: `b13e468d33e0d96437b58bb2da6088bff689b9eb` (`git_dirty: false`).
- Báo cáo phân định chi tiết: [`retention_attribution_report.md`](retention_attribution_report.md).
- Bản đồ độ phủ V2b: [`v2b_coverage_map.md`](v2b_coverage_map.md).
- Bộ bằng chứng điều tra: [`retention_attribution_evidence/`](retention_attribution_evidence/).
- Người nhận bàn giao: Codex điều phối / Reviewer độc lập chốt.

---

## 1. Kết quả Hoàn thành

1. **Điều tra Phân định Nguyên nhân 8 Residual Risk (Rendered-Title Retention):**
   - Đã mổ xẻ chi tiết 8 bản ghi residual risk trong hồ sơ đo V8 heap snapshot của QA (`review_runtime_b13e468_evidence/summary.json`).
   - Cả 8 bản ghi đều có đường giữ ngắn nhất dài 12 frame, kết thúc tại closure của biến tĩnh toàn cục `segmentationCache` trong Flutter Web Engine (`C:\src\flutter\bin\cache\flutter_web_sdk\lib\_engine\engine\text_fragmenter.dart:43`).
   - Engine giữ 10.000 entry LRU cho văn bản medium (11-100 ký tự) và không bao giờ gọi `.clear()` khi route pop hay logout.
   - Tầng ứng dụng đã giải phóng sạch các model tài chính (`FinanceProvider.clearAll()` -> `_resetFinance()`); bằng chứng thực nghiệm đối chứng là hai sentinel không render của cùng model `FinanceExpense` (`expense_id`, `expense_id_2`) biến mất 100% (`occurrences: 0`, `reachable: false`) ở cả `post_logout` và `post_actor` trong cả 2 chu kỳ.
   - Phân định rõ ràng: Tiêu đề chi phí lưu trong heap là đặc tính kỹ thuật của bộ segmenter văn bản trong Flutter Web SDK (CanvasKit/dart2js); ứng dụng không rò rỉ model hay controller. Hiện tượng này không tồn tại trên Dart VM desktop/mobile do Dart VM dùng native C++ Skia/Impeller.
2. **Thiết lập Bản đồ Độ phủ Toàn diện (V2b Coverage Map):**
   - Đã lập danh mục chi tiết 11 thực thể tài chính/danh tính riêng tư tại [`v2b_coverage_map.md`](v2b_coverage_map.md).
   - Chỉ rõ hiện trạng: Mới chỉ có **2 mã chi phí** (`expense_id`, `expense_id_2`) được đo sạch trên Web profile heap snapshot; còn **ít nhất 6 thực thể** (`charges`, `payments`, `bank`, `receiver`, `ledger`, `payment instructions`) chưa từng được đo thực tế trong heap của app thật khi chạy trình duyệt (`NOT RUN`).
3. **Bổ sung Công cụ Kiểm soát Tự động & Unit Tests:**
   - Script audit: [`scripts/bh07_appheap/audit_retention_attribution.py`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/scripts/bh07_appheap/audit_retention_attribution.py).
   - Test suite: [`tests/test_bh07_retention_attribution.py`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/tests/test_bh07_retention_attribution.py) (4/4 tests PASS, gồm mutant peer leak và count mismatch).
   - Hồi quy 316/316 tests Python OK, `flutter analyze` 0 issue, `flutter test` 247 pass + 1 skip.
4. **Bảo toàn Dữ liệu:**
   - Toàn bộ 4 bundle lịch sử giữ nguyên 100% byte.
   - Bundle mới [`retention_attribution_evidence/`](retention_attribution_evidence/) đạt chuẩn strict UTF-8 LF, 0 secret, manifest 5/5 verified.

---

## 2. Lệnh Tự Kiểm tra & Tái lập (Replay Commands)

```powershell
# 1. Chạy công cụ điều tra phân định & lập bản đồ phủ
python -X utf8 scripts/bh07_appheap/audit_retention_attribution.py

# 2. Chạy test suite hồi quy Python (316/316 OK)
python -X utf8 -m unittest discover -s tests

# 3. Kiểm tra tính toàn vẹn bundle bằng chứng điều tra (5/5 files PASS, 0 secret)
python -X utf8 scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir "$PWD\docs\reviews\bh07\retention_attribution_evidence"

# 4. Kiểm tra đối chiếu bundle QA lịch sử (PASS, không đổi byte)
python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir "$PWD\docs\reviews\bh07\review_runtime_b13e468_evidence"

# 5. Phân tích tĩnh Flutter & test suite Dart (0 issue, 247 passed + 1 skipped)
flutter analyze
flutter test
```

---

## 3. NOT RUN & Ranh giới Kỹ thuật

| Hạng mục | Trạng thái kỹ thuật | Ranh giới & Ràng buộc |
| :--- | :--- | :--- |
| **Độ phủ V2b §4.4 ngoài 2 expense ID** | **NOT RUN** | 6 thực thể tài chính (`charges`, `payments`, `bank`, `receiver`, `ledger`, `payment instructions`) chưa đo trên app-profile heap. |
| **Đo heap Dart VM trên desktop/mobile** | **NOT RUN** | Chưa chạy trên Dart VM service. |
| **Trình duyệt khác, mobile web, đa tab/actor đồng thời** | **NOT RUN** | Giữ nguyên giới hạn kỹ thuật. |
| **Nghiệm thu toàn V2b và toàn BH-07** | **CHƯA NGHIỆM THU** | Không merge `main`/`staging`/`production`, không deploy/pilot/BH-08. |
