# Bàn giao sang máy khác — 10/11/2026

Chủ dự án yêu cầu cập nhật tiến độ lên Git để tiếp tục trên máy khác. Cho phép commit/push nhánh `feat/bh07-completion-local` nhằm đồng bộ công việc; không phải phê duyệt merge, deploy, pilot hoặc BH-08. Các dòng cấm push trước đây là trạng thái lịch sử trước ủy quyền này.

## Trạng thái mang theo

- Ledger sentinel Web local giữ kết luận tại `b25aaef`/`b72c563`.
- Guard/probe V4 sửa bổ sung đã Đạt trong phạm vi delta: [review](codex_v4_supplemental_review.md), [handoff](codex_v4_supplemental_handoff.md). Kết quả lịch sử 499 Python, analyze 0, Flutter 247 PASS +1 SKIP giữ nguyên attribution.
- Lượt đồng bộ này chạy lại hai file test V4: 6 +56 = **62 PASS**. `git diff --check` sạch trước cập nhật bàn giao. Không chạy lại full suite, Flutter hoặc runtime.
- Tiền kiểm V4 đã Đạt phần báo cáo: [review](v4_runtime_preflight_review_20261109.md). Full source review/runtime V4 **NOT RUN**, toàn BH-07/V8 **chưa nghiệm thu**, risk acceptance chưa ký.
- [Chẩn đoán gateway](v4_gateway_diagnostic_20261109.md) đã có báo cáo Anti; chưa có review chốt riêng. Không coi báo cáo này là xác nhận nguyên nhân gốc hoặc admission đã được khôi phục. Không tiếp tục process/job ID của máy cũ.

## Tiếp tục trên máy mới

```powershell
git fetch origin
git switch feat/bh07-completion-local
git pull --ff-only origin feat/bh07-completion-local
```

Đọc [nhật ký tiếp tục](bh07_completion_continuation_20261109.md), review bổ sung và tiền kiểm nêu trên. Kiểm tra công cụ/dependency và môi trường máy mới; Docker containers, cấu hình local, credentials, heap/dump/profile và process đang chạy không được Git chuyển sang máy khác.

Bước tiếp là review báo cáo chẩn đoán và giải quyết source admission qua cơ chế chính thống của môi trường mới. Chỉ sau khi đọc/review được full runner, chốt candidate/provenance và tiền kiểm tài nguyên cô lập mới chạy rehearsal V4. Không bypass gateway, không nâng kết quả synthetic thành runtime PASS. Giữ các evidence lịch sử nguyên byte và không tự mở lại vòng sửa Anti thứ tư.
