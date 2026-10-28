# Bàn giao Mở rộng Độ phủ Bộ nhớ V2b BH-07: Payments & Charges trên Web Profile Local

- Ngày: 28/10/2026, Asia/Saigon.
- Nhánh: `feat/bh07-finance-heap-coverage`, base `56ffbf9a4f1b524cd8fbc7f1e9118a94b06b9cbc`.
- Tested source commit đo heap thực tế: `cd25e1ea1f93e9a7eecdb8da951a37c56bf0a624` (`git_dirty: false`).
- Bundle bằng chứng đo heap mới: [`finance_heap_evidence/`](finance_heap_evidence/).
- Bản đồ độ phủ cập nhật: [`v2b_coverage_map.md`](v2b_coverage_map.md).
- Người nhận bàn giao: Codex điều phối / Reviewer độc lập chốt.

---

## 1. Tóm tắt Kết quả Thực hiện

1. **Đo thực tế trên Chromium Web profile cho `FinancePayment`:**
   - Đã tích hợp fixture `EXTRA_PAYMENT` có UUID độc nhất và mã tham chiếu `PAYREF-BH07-...` vào `scripts/bh07_appheap/run_app_profile_heap.js`.
   - Kết quả đo heap thật cùng một tài liệu SPA qua 2 chu kỳ (`Owner -> logout -> Cohost`, `Owner -> logout -> Member`):
     - `payment_id` (`distinctive: true`, `rendered: false`): có mặt tại `owner_active` (path length 20 từ GC roots), biến mất 100% (`occurrences: 0`, `reachable: false`) ở cả `post_logout` và `post_actor` trong cả 2 chu kỳ. Model `FinancePayment` được giải phóng sạch sẽ khỏi bộ nhớ Dart khi logout.
     - `payment_ref` (`distinctive: true`, `rendered: true`): xuất hiện trên UI [`SessionFinanceScreen._paymentsSection`](../../../lib/screens/session_finance_screen.dart#L696), tồn lưu trong `segmentationCache` của Flutter Web Engine (`text_fragmenter.dart`, path length 12). Được ghi nhận và phân loại trung thực là **`unattributed residual risk`** tương tự tiêu đề chi phí (`expense`).
   - Cả 2 fixture dùng một lần (`EXTRA_EXPENSE` và `EXTRA_PAYMENT`) được tạo có guard, xóa sạch sau đo và xác minh vắng mặt 100% bằng read-back request.

2. **Phân định ranh giới DTO và Chống nhập nhằng Roster Identity cho `FinanceCharge`:**
   - Đối chiếu trực tiếp mã nguồn [`lib/models/finance.dart`](../../../lib/models/finance.dart#L258): `FinanceCharge` chỉ có 3 trường `playerId`, `displayName`, `amountDueVnd`. Hoàn toàn **KHÔNG có `chargeId`** và **KHÔNG có `notes`**.
   - Trường định danh duy nhất là `playerId`, trùng khớp với danh tính thành viên phiên (`SessionPlayer.id`).
   - Tại `owner_active`: `playerId` được giữ bởi cả `FinanceProvider._finance.charges` và `SessionProvider._session.players`.
   - Tại `post_logout`: toàn bộ provider được reset qua `clearAll()`, `playerId` biến mất hoàn toàn (`occurrences: 0`).
   - Tại `post_cohost`: `playerId` xuất hiện lại qua `SessionProvider` (path length 18) vì Cohost tải lại danh sách thành viên phiên hợp lệ. Đây là retainer danh tính (`scope: identity`), **KHÔNG PHẢI** rò rỉ của `FinanceCharge`.
   - Khẳng định nguyên tắc: Không suy từ việc xuất hiện lại của `playerId` thành rò rỉ khoản thu, cũng không suy việc thiếu trường độc quyền thành model đã sạch toàn app.

3. **Bộ kiểm thử TDD & Fixture Controls:**
   - Tạo mới [`tests/test_bh07_finance_heap_coverage.py`](../../../tests/test_bh07_finance_heap_coverage.py):
     - `test_finance_charge_fields_exact`: chặn các giả định sai về `chargeId`/`notes`/`dueVnd`/`referenceCode`.
     - `test_finance_payment_fields_exact`: xác thực cấu trúc `FinancePayment`.
     - `test_positive_control_with_payment_and_charge_sentinels`: kiểm tra positive control với sentinels payment và expense.
     - `test_mutant_1_payment_id_retained_fails_oracle`: fail-closed khi `payment_id` rò rỉ sau logout.
     - `test_mutant_2_payment_id_not_loaded_in_owner_active`: fail-closed khi precondition không nạp payment.
     - `test_mutant_3_roster_conflation_prevention`: chứng minh ranh giới giữa roster identity và model tài chính.
   - Cập nhật [`scripts/bh07_appheap/fixture_controls.js`](../../../scripts/bh07_appheap/fixture_controls.js): 8/8 controls PASS.
   - Cập nhật [`scripts/bh07_appheap/verify_evidence.py`](../../../scripts/bh07_appheap/verify_evidence.py): xác thực trường cleanup của payment fixture.

---

## 2. Lệnh Tự Kiểm tra & Tái lập (Replay Commands)

```powershell
# 1. Kiểm tra tính toàn vẹn bundle bằng chứng đo heap mới (PASS)
python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir docs/reviews/bh07/finance_heap_evidence

# 2. Chạy test suite hồi quy Python (325/325 OK)
python -X utf8 -m unittest discover -s tests

# 3. Chạy fixture controls độc lập (8/8 OK)
node scripts/bh07_appheap/fixture_controls.js

# 4. Phân tích tĩnh Flutter (0 issues) & test suite Dart (247 passed + 1 skipped)
flutter analyze
flutter test

# 5. Đối chiếu bundle QA lịch sử (PASS, không đổi byte)
python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir docs/reviews/bh07/review_runtime_b13e468_evidence
```

---

## 3. Bảng Trạng thái Phủ & NOT RUN V2b §4.4

| Thực thể / Hạng mục | Trạng thái Hiện tại | Bằng chứng / Ranh giới |
| :--- | :--- | :--- |
| **Mã chi phí (`expense_id`, `expense_id_2`)** | **ĐÃ ĐO & ĐẠT LOCAL** | Web profile (`review_runtime_b13e468_evidence`, `finance_heap_evidence`). |
| **Tiêu đề chi phí (`expense`, `expense2`)** | **RESIDUAL RISK UNATTRIBUTED** | Web engine `segmentationCache` (path len 12). |
| **Mã thanh toán (`payment_id`)** | **ĐÃ ĐO & ĐẠT LOCAL** | Web profile (`finance_heap_evidence`). Vắng mặt 100% sau logout. |
| **Mã tham chiếu thanh toán (`payment_ref`)** | **RESIDUAL RISK UNATTRIBUTED** | Web engine `segmentationCache` (path len 12). |
| **Khoản thu (`charges`)** | **PHÂN ĐỊNH RANH GIỚI DTO** | Không có `chargeId`/`notes`; `playerId` chia sẻ với roster identity; Provider unit test đạt. |
| **Ngân hàng CLB (`bank`, `receiver`)** | **NOT RUN** | Chưa duyệt màn hình cấu hình ngân hàng CLB trong runner. |
| **Chỉ dẫn thanh toán QR (`payment_instructions`)** | **NOT RUN** | Chưa duyệt màn hình xem QR của người chơi trong runner. |
| **Sổ quỹ CLB (`club_ledger`)** | **NOT RUN** | Chưa duyệt màn hình Quỹ CLB trong runner. |
| **Tổng kết số tiền (`session_summary`)** | **CHƯA CÓ SENTINEL CHUỖI** | Chỉ chứa số nguyên tiền tệ, chia sẻ vòng đời Provider đã reset. |
| **Listener object graph trên Web heap** | **NOT RUN** | Chưa probe đồ thị đối tượng bộ nhớ runtime cho listener closure. |
| **Đo heap trên Dart VM (desktop/mobile)** | **NOT RUN** | Chưa chạy trên Dart VM service. |
| **Nghiệm thu toàn V2b và toàn BH-07** | **CHƯA NGHIỆM THU** | Không merge `main`/`staging`/`production`, không deploy/pilot/BH-08. Người triển khai không tự ghi Đạt. |
