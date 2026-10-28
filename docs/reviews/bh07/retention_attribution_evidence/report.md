# Báo cáo Bằng chứng Điều tra Phân định Giữ Dữ liệu (Retention Attribution) & Bản đồ Phủ V2b BH-07

- Gate: V2b — app-profile Dart heap / in-memory retention after actor switch
- Reference: `docs/reviews/bh07/bh07_readiness.md §4.4`
- Trạng thái: **ĐÃ ĐIỀU TRA PHÂN ĐỊNH NGUYÊN NHÂN & LẬP XONG BẢN ĐỒ ĐỘ PHỦ**
- Tested source đối chiếu: `b13e468d33e0d96437b58bb2da6088bff689b9eb`
- Nhánh thực thi: `feat/bh07-retention-attribution` từ base `272bb29d2960959cb856771e8b95c16f140645f4`
- Báo cáo chi tiết: [`docs/reviews/bh07/retention_attribution_report.md`](../retention_attribution_report.md)
- Bản đồ độ phủ: [`docs/reviews/bh07/v2b_coverage_map.md`](../v2b_coverage_map.md)

---

## 1. Kết quả Điều tra Phân định 8 Residual Risk Tiêu đề Chi phí

- **Đối tượng:** 8 bản ghi rủi ro tồn lưu (`residual_risks`) trong hồ sơ QA `review_runtime_b13e468_evidence`.
- **Quan sát thực nghiệm (Observed):**
  - Đường giữ ngắn nhất BFS có độ dài 12 frames, đi thẳng từ GC root tới closure của web engine:
    `root -> element -> internal:closure -> call$0 -> context -> segmentationCache -> _1 -> _itemMap -> _strings -> <redacted> -> hashMapCellKey`.
  - Hai sentinel không render của cùng đối tượng `FinanceExpense` (`expense_id` và `expense_id_2`) xuất hiện ở `owner_active` (đường đi độ dài 20 qua Provider) và **biến mất 100% (`occurrences: 0`, `reachable: false`) ngay sau logout và khi đổi actor ở cả 2 chu kỳ**.
- **Giả thuyết có Bằng chứng Hỗ trợ (Supported Hypothesis):**
  - Vị trí mã nguồn Flutter SDK: `flutter_web_sdk/lib/_engine/engine/text_fragmenter.dart:43`.
  - Biến tĩnh toàn cục `segmentationCache` lưu trữ 10.000 phần tử LRU (`kMediumParagraphCacheSpec`) cho các đoạn văn bản có độ dài 11-100 ký tự để tối ưu hóa việc chia từ/ngắt dòng khi layout CanvasKit.
  - Vòng đời: `segmentationCache.clear()` không bao giờ được framework hay router gọi khi chuyển route hoặc đăng xuất.
  - Việc 2 mã chi phí unrendered biến mất hỗ trợ cho giả thuyết rằng instance model `FinanceExpense` phía ứng dụng đã được thu hồi.
- **Giới hạn Kỹ thuật & Phần Chưa Chứng minh (Unknown & Limits):**
  - Một đường dẫn ngắn nhất BFS trong snapshot V8 không loại trừ sự tồn tại của các đường dẫn giữ khác từ phía ứng dụng.
  - Hai ID chi phí biến mất không chứng minh toàn bộ ứng dụng sạch chuỗi văn bản hoặc các model tài chính khác đã sạch.
  - Dart VM desktop/mobile là **NOT RUN**; không suy diễn heap native không retention.
  - 8 bản ghi tiếp tục giữ phân loại chính thức là **`unattributed residual risk`**.

---

## 2. Kết quả Lập Bản đồ Phủ (Coverage Map)

Kiểm kê toàn bộ 11 thực thể tài chính/danh tính riêng tư trong codebase theo đúng DTO và field hiện hành:
1. `expense_ids`: Đã đo thực & đạt clean trên Web profile (0 occurrences sau logout).
2. `expense_titles`: Residual risk trong engine web cache; giữ `unattributed`.
3. `session_charges`: Mới kiểm ở Provider test; **CHƯA ĐO TRONG APP HEAP (NOT RUN)**.
4. `session_payments`: Mới kiểm ở Provider test; **CHƯA ĐO TRONG APP HEAP (NOT RUN)**.
5. `club_bank_account`: Mới kiểm ở Provider test; **CHƯA ĐO ĐÚNG TRONG APP HEAP (NOT RUN)**.
6. `bank_receiver`: Khai báo nhưng chưa nạp ở `owner_active`; **CHƯA ĐO (NOT RUN)**.
7. `payment_instructions`: Mới kiểm ở Provider test; **CHƯA ĐO TRONG APP HEAP (NOT RUN)**.
8. `club_ledger`: Mới kiểm ở Provider test; **CHƯA ĐO TRONG APP HEAP (NOT RUN)**.
9. `session_summary_totals`: Màn hình đã duyệt nhưng giá trị là số tiền, chưa có sentinel chuỗi.
10. `roster_identities`: Báo cáo dạng note (path 18 ở Cohost); không suy quyền từ heap.
11. `auth_listeners`: **CHƯA ĐO TRÊN WEB HEAP OBJECT GRAPH (NOT RUN)**. AST zero-static không chứng minh đồ thị đối tượng heap sạch.

---

## 3. Ranh giới & Giới hạn Kỹ thuật

- Không sửa bất kỳ file mã nguồn ứng dụng (`lib/`), backend (`supabase/`) hay DB contract nào.
- Toàn bộ 4 bundle lịch sử giữ nguyên 100% byte.
- Cổng V2b §4.4 và toàn bộ BH-07 **TIẾP TỤC GIỮ TRẠNG THÁI CHƯA NGHIỆM THU**.
- Tuyệt đối không merge nhánh, không deploy staging/production, không pilot và không mở BH-08.
- Người triển khai không tự ghi Đạt.
