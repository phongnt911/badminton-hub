**Hiện hành:** Codex đã sửa trực tiếp AT1 vòng3 theo ủy quyền chủ dự án; **Chờ reviewer độc lập**, không tự ghi Đạt. Xem [bàn giao mới](codex_retention_attribution_r3_handoff.md),source f11d20f6. Phần dưới là lịch sử bàn giao vòng2/2.

# Bàn giao Điều tra Phân định Giữ Dữ liệu (Retention Attribution) & Bản đồ Phủ (Coverage Map) V2b BH-07

- Ngày: 28/10/2026, Asia/Saigon.
- Nhánh: `feat/bh07-retention-attribution`, base `dcdb7ce51095d03afbbb7f28e4bbb5117f8a3e48`.
- Tested source runtime QA đối chiếu: `b13e468d33e0d96437b58bb2da6088bff689b9eb` (`git_dirty: false`).
- Báo cáo phân định chi tiết: [`retention_attribution_report.md`](retention_attribution_report.md).
- Bản đồ độ phủ V2b: [`v2b_coverage_map.md`](v2b_coverage_map.md).
- Bộ bằng chứng điều tra: [`retention_attribution_evidence/`](retention_attribution_evidence/).
- Người nhận bàn giao: Codex điều phối / Reviewer độc lập chốt.

---

## 1. Kết quả Hoàn thành (Sửa Vòng 2/2: AT1 & AT2)

1. **AT1 (P1) — Kiểm tra Đầy đủ 8 Tổ hợp & Toàn bộ Rendered Paths & Strict Counts:**
   - Trong [`scripts/bh07_appheap/audit_retention_attribution.py`](../../../scripts/bh07_appheap/audit_retention_attribution.py), thêm cơ chế xác thực toàn bộ 8 tổ hợp `(cycle, epoch, sentinel)` (2 chu kỳ × 2 mốc `post_logout`/`post_actor` × 2 sentinel `expense`/`expense2`), chặn đứng các trường hợp trùng lặp hoặc thiếu tổ hợp.
   - Kiểm tra độc lập toàn bộ 8 đường dẫn giữ tiêu đề: cả `expense` và `expense2` ở cả `post_logout` và `post_actor` của cả 2 chu kỳ đều bắt buộc phải tồn tại, `reachable: true`, `path_len: 12`, đi qua closure `segmentationCache`, và đối chiếu khớp với bản ghi trong `residual_risks`.
   - Loại bỏ hoàn toàn việc gán mặc định 0 cho `occurrences` bị thiếu: trường `occurrences` bắt buộc phải có mặt và có kiểu số nguyên thực sự (`type is int`).
   - Đã phát lại nguyên bản bộ test probe reviewer cũ (`review_37b4954_evidence/probes.py`) và bộ extra controls mới (`review_eda1ead_evidence/extra_controls.py`):
     - Positive control: **exit 0**, `valid=True`, `status='SUPPORTED_HYPOTHESIS_WITH_LIMITS'`
     - 3 mutant cũ (`peer_retained`, `wrong_environment`, `missing_rendered_paths`): đều **exit 1**, `valid=False`, `primary_retainer_component='UNATTRIBUTED'`
     - 4 mutant mới (`expense2_path_missing`, `post_actor_paths_missing`, `duplicate_risk_record`, `missing_post_logout_occurrences`): đều **exit 1**, `valid=False`, `primary_retainer_component='UNATTRIBUTED'`
2. **AT2 (P2) — Tách bạch Ranh giới Hai ID Chi phí và Không Khẳng định App Sạch Toàn diện:**
   - Đính chính dứt khoát các trường dữ liệu máy (machine fields):
     - `app_model_retention`: chuyển thành `'SCOPED_TWO_IDS_CLEAN_APP_WIDE_UNKNOWN'`.
     - Thêm tường minh: `observed_peer_ids_absent: True` (ghi nhận đúng phạm vi thực nghiệm hai ID) và `app_wide_retention_proven: False`.
     - `app_criteria.app_wide_model_retention`: `'UNKNOWN'`.
     - `summary.json`: loại bỏ `"models_released": true`, thay bằng `"observed_peer_ids_absent": true` và `"app_wide_models_released": "UNKNOWN"`.
   - Đồng bộ văn phong báo cáo: loại bỏ mọi câu khẳng định dứt khoát "tầng ứng dụng đã giải phóng hoàn toàn" hay "không cần sửa app". Nhấn mạnh: việc 2 expense ID biến mất không loại trừ việc app giữ tiêu đề ở nơi khác hoặc đường dẫn phụ; 8 rủi ro tồn lưu tiếp tục giữ phân loại chính thức là **`unattributed residual risk`**.
3. **Các Gate AT3–AT6 Đã Đóng:**
   - Giữ nguyên 100% các sửa đổi đã được xác nhận Đóng tại vòng 1: DTO fields thực tế trong Dart, listener Web object graph giữ `NOT RUN`, `run.log` được track thật qua Git, link Markdown tương đối portable, và không chứa sentinel thô.

---

## 2. Lệnh Tự Kiểm tra & Tái lập (Replay Commands)

```powershell
# 1. Chạy công cụ điều tra phân định & lập bản đồ phủ
python -X utf8 scripts/bh07_appheap/audit_retention_attribution.py

# 2. Phát lại reviewer probe suite cũ (positive: 0, 3 mutants: exit 1 UNATTRIBUTED)
python docs/reviews/bh07/review_37b4954_evidence/probes.py

# 3. Phát lại reviewer extra controls suite mới (positive: 0, 4 mutants: exit 1 UNATTRIBUTED)
python docs/reviews/bh07/review_eda1ead_evidence/extra_controls.py

# 4. Chạy test suite hồi quy Python (317/317 OK)
python -X utf8 -m unittest discover -s tests

# 5. Kiểm tra tính toàn vẹn bundle bằng chứng điều tra (5/5 files PASS, 0 secret)
python -X utf8 scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir "$PWD\docs\reviews\bh07\retention_attribution_evidence"

# 6. Kiểm tra đối chiếu bundle QA lịch sử (PASS, không đổi byte)
python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir "$PWD\docs\reviews\bh07\review_runtime_b13e468_evidence"

# 7. Phân tích tĩnh Flutter & test suite Dart (0 issue, 247 passed + 1 skipped)
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
