# Bàn giao Điều tra Phân định Giữ Dữ liệu (Retention Attribution) & Bản đồ Phủ (Coverage Map) V2b BH-07

- Ngày: 28/10/2026, Asia/Saigon.
- Nhánh: `feat/bh07-retention-attribution`, base `272bb29d2960959cb856771e8b95c16f140645f4`.
- Tested source runtime QA đối chiếu: `b13e468d33e0d96437b58bb2da6088bff689b9eb` (`git_dirty: false`).
- Báo cáo phân định chi tiết: [`retention_attribution_report.md`](retention_attribution_report.md).
- Bản đồ độ phủ V2b: [`v2b_coverage_map.md`](v2b_coverage_map.md).
- Bộ bằng chứng điều tra: [`retention_attribution_evidence/`](retention_attribution_evidence/).
- Người nhận bàn giao: Codex điều phối / Reviewer độc lập chốt.

---

## 1. Kết quả Hoàn thành (Sửa triệt để AT1–AT6)

1. **AT1 (P1) — Fail-closed CLI & Derivation từ Validated Evidence:**
   - Trong [`scripts/bh07_appheap/audit_retention_attribution.py`](../../../scripts/bh07_appheap/audit_retention_attribution.py), mọi kết luận phân định đều được suy luận từ điều kiện tiên đề (`environment_consistent`, `peer_sentinels_clean`, `path_leads_to_segmentationCache`, `residual_risks_count == 8`).
   - Nếu bất kỳ điều kiện nào thất bại (như peer sentinel còn rò rỉ, môi trường SDK/build sai, hoặc thiếu chuỗi giữ rendered path), CLI trả về mã lỗi `exit 1`, gán nhãn `primary_retainer_component = 'UNATTRIBUTED'` và `app_model_retention = 'UNKNOWN_OR_UNCLEAN'`, chặn hoàn toàn việc kết luận engine cache khi chứng cứ chưa đầy đủ.
   - Đã phát lại nguyên bản bộ test probe reviewer (`docs/reviews/bh07/review_37b4954_evidence/probes.py`): Cả 3 ca mutant đều fail-closed (exit 1, `UNATTRIBUTED`), ca positive control giữ nguyên exit 0.
2. **AT2 (P2) — Tách bạch Observed, Supported Hypothesis và Limits:**
   - Đính chính attribution trong báo cáo và JSON artifact:
     - **Observed:** Chuỗi giữ ngắn nhất BFS có 12 frame dẫn tới `dart._engine.segmentationCache._itemMap._strings` trên Web profile (Chrome 155, dart2js); 2 sentinel không render `expense_id` và `expense_id_2` biến mất hoàn toàn (`occurrences: 0`, `reachable: false`) sau khi logout ở cả 2 chu kỳ.
     - **Supported Hypothesis:** Cơ chế cache văn bản 10.000 entry LRU của engine Flutter Web (`text_fragmenter.dart:43`) giải thích cho frame `segmentationCache`.
     - **Limits & Unknown:** Một đường dẫn ngắn nhất BFS không loại trừ các đường dẫn phụ khác từ phía app; 2 expense ID không chứng minh toàn bộ app hay native engine sạch; Dart VM desktop/mobile là `NOT RUN`; 8 bản ghi rủi ro tồn lưu tiếp tục giữ phân loại chính thức là **`unattributed residual risk`**.
3. **AT3 (P2) — Map đúng DTO Fields hiện hành & Đánh dấu Listener Web Heap là NOT RUN:**
   - Bản đồ độ phủ [`v2b_coverage_map.md`](v2b_coverage_map.md) và danh mục `ENTITIES_INVENTORY` được đối chiếu chính xác với mã nguồn Dart:
     - `FinanceCharge`: chỉ có `playerId`, `displayName`, `amountDueVnd` (không có `chargeId`, `status`, `notes`, `chargeVnd`).
     - `FinancePayment`: `paymentId`, `playerId`, `amountVnd`, `method`, `status`, `reference`, `confirmedAt`, `createdAt` (không có `displayName`, `referenceCode`).
     - `PaymentInstructions`: `sessionId`, `playerId`, `displayName`, `billingState`, `activeRevisionId`, `sourceVersion`, `amountDueVnd`, `totalPaidVnd`, `outstandingVnd`, `reference`, `receiverSnapshot`, `hasReceiver`, `canPay`.
     - `SessionSummary`: `expensesTotalVnd`, `amountDueTotalVnd`, `totalPaidVnd`, `outstandingTotalVnd`.
   - `auth_listeners`: Chuyển trạng thái sang **`NOT_RUN_WEB_HEAP_OBJECT_GRAPH`**. Không chấp nhận AST zero-static hay Provider unit test làm bằng chứng object graph trên Web heap đã sạch.
4. **AT4 (P2) — Khôi phục log thật & Khai báo Manifest nhất quán:**
   - Chạy lại audit thật để ghi nhận toàn bộ log thực thi vào `retention_attribution_evidence/run.log`.
   - Sử dụng `git add -f` đối với `run.log` để bảo đảm file được lưu trữ trong Git (không bị `.gitignore` chặn).
   - Xác minh toàn vẹn manifest 5/5 tệp tin (`clean_and_manifest.py --verify`) đạt kết quả PASS (exit 0).
5. **AT5 (P2) — Liên kết Tương đối Di động (Portable Links):**
   - Loại bỏ toàn bộ liên kết cục bộ `file:///c:/Users/POTA/...` trong toàn bộ tài liệu bàn giao, báo cáo và bản đồ độ phủ; thay bằng liên kết Markdown tương đối trong kho mã nguồn.
6. **AT6 (P2) — Loại bỏ Giá trị Sentinel Thô:**
   - Loại bỏ chuỗi tiếng Việt và tiền tố fixture thô trong `retention_attribution_report.md`; thay bằng định danh, độ dài chuỗi, và mã băm sha256[:12] đã sanitize.

---

## 2. Lệnh Tự Kiểm tra & Tái lập (Replay Commands)

```powershell
# 1. Chạy công cụ điều tra phân định & lập bản đồ phủ
python -X utf8 scripts/bh07_appheap/audit_retention_attribution.py

# 2. Phát lại reviewer probe suite kiểm tra fail-closed (positive: 0, 3 mutants: exit 1 UNATTRIBUTED)
python docs/reviews/bh07/review_37b4954_evidence/probes.py

# 3. Chạy test suite hồi quy Python (317/317 OK)
python -X utf8 -m unittest discover -s tests

# 4. Kiểm tra tính toàn vẹn bundle bằng chứng điều tra (5/5 files PASS, 0 secret)
python -X utf8 scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir "$PWD\docs\reviews\bh07\retention_attribution_evidence"

# 5. Kiểm tra đối chiếu bundle QA lịch sử (PASS, không đổi byte)
python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir "$PWD\docs\reviews\bh07\review_runtime_b13e468_evidence"

# 6. Phân tích tĩnh Flutter & test suite Dart (0 issue, 247 passed + 1 skipped)
flutter analyze
flutter test
```

---

## 3. NOT RUN & Ranh giới Kỹ thuật

| Hạng mục | Trạng thái kỹ thuật | Ranh giới & Ràng buộc |
| :--- | :--- | :--- |
| **Độ phủ V2b §4.4 ngoài 2 expense ID** | **NOT RUN** | 6 thực thể tài chính (`charges`, `payments`, `bank`, `receiver`, `ledger`, `payment instructions`) chưa đo trên app-profile heap. |
| **Listener object graph trên Web profile heap** | **NOT RUN** | Chỉ mới kiểm tra AST và Provider test; chưa đo đồ thị đối tượng heap thực tế. |
| **Đo heap Dart VM trên desktop/mobile** | **NOT RUN** | Chưa chạy trên Dart VM service. |
| **Trình duyệt khác, mobile web, đa tab/actor đồng thời** | **NOT RUN** | Giữ nguyên giới hạn kỹ thuật. |
| **Nghiệm thu toàn V2b và toàn BH-07** | **CHƯA NGHIỆM THU** | Không merge `main`/`staging`/`production`, không deploy/pilot/BH-08. Người triển khai không tự ghi Đạt. |
