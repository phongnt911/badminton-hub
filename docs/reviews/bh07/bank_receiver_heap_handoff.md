**2026-11-02 — Đóng gói hồ sơ Bank & Receiver Heap Coverage sau runtime Codex độc lập (RUN/PASS, auditor 0):** Tested source `a095a457f2f12e8d65fe69ba5a3ca3ddb79ea110` (`git_dirty: false`), bundle `bank_receiver_heap_r4_runtime_evidence`, độc lập `bank_receiver_heap_r4_runtime_review_evidence/results.json`. 2 chu kỳ cùng document Owner → logout → Cohost/Member (8 epochs): toàn bộ nhóm baseline absent/unreachable, Owner present/reachable; `bank_account_id` (unrendered finance ID) absent/unreachable sau logout/actor; `bank`/`receiver` (rendered UI text) retained sau logout/actor là rủi ro tồn đọng chưa quy kết (unattributed residual risks), KHÔNG PHẢI absence gate sạch và KHÔNG PHẢI chứng minh toàn bộ object đã giải phóng. DB before/after row fingerprints trùng khớp, fixture dọn sạch và xác minh vắng mặt, Chrome/dumps đã dọn sạch; 1.606 tệp bằng chứng lịch sử (historical files) readonly nguyên vẹn, cùng 1.719 đường dẫn evidence/app được bảo vệ và 16 payload vòng 4 trước đó đã xác minh. Code checks: 375 Python pass, fixture 8/8 controls pass, legacy/finance audit exit 0; Flutter fresh checks đã đạt: analyze 0 issues (archive `acc950d1867dbe8f`), test 247 pass + 1 skip (archive `7b13b952014a42cb`). Đóng gói tài liệu bàn giao, KHÔNG mở vòng triển khai mới. Toàn bộ V2b/BH-07 CHƯA NGHIỆM THU; instructions/ledger/listener graph/native Dart VM/whole-model giữ NOT RUN/UNKNOWN; không merge/push/deploy/pilot/BH-08, cần chủ dự án phê duyệt tích hợp. Lịch sử trạng thái bên dưới giữ nguyên để truy vết.

**2026-11-02 — Exceptional bank/receiver correction round 4:** Antigravity (Gemini 3.8 Flash High) fixes pass 375 Python tests, fixture8/8, legacy/finance audit and focused real-Chrome shutdown/profile-removal probe. BKR8 navigation label corrected; BKR9 root CDP sessionId and exited-launcher handling corrected. Full bank heap runtime for this revision NOT RUN; old Chrome/profile cleanup remains blocked by lean-ctx Stop-Process/Remove-Item rules. Full task/BH-07 NOT ACCEPTED; no merge/push/deploy/pilot/BH-08. See [round 4 review](bank_receiver_heap_round4_review.md). Earlier status below is historical.

**2026-10-29 — Bank/receiver heap: NOT ACCEPTED; STOP after correction round 3/3.** Fresh reviewer runtime at `c73bc4404cb6992141797ace13e1009db83342b0` (`git_dirty: false`) aborted at `Clubs tab`: runner expects `Câu Lạc Bộ`, actual destination `CLB & Quỹ`. No completed cycle/verdict; bank coverage NOT RUN. DB fixtures removed and independent before/after row fingerprints match. Chrome profile cleanup remains incomplete; Stop-Process is blocked by lean-ctx. 358 Python, analyze0,247Flutter+1skip do not override runtime failure. BKR8/BKR9 open; no fourth round, merge/push/deploy/pilot/BH-08. See [runtime review](bank_receiver_heap_runtime_review.md). Earlier status below is historical.

# Bàn giao Kỹ thuật: Bank & Receiver Heap Coverage (Closure sau Runtime Round 4)

> **Thông báo quan trọng**: Đây là tài liệu bàn giao kỹ thuật ghi nhận kết quả sau runtime Codex độc lập (closure handoff), **không phải biên bản nghiệm thu toàn bộ BH-07**. Toàn bộ gói công việc BH-07 chưa được nghiệm thu; không merge, push, deploy, pilot hoặc chuyển sang BH-08 khi chưa có sự phê duyệt tích hợp của chủ dự án.

- **Ngày**: 02/11/2026.
- **Nhánh**: `feat/bh07-bank-receiver-heap`.
- **Base commit**: `94fd997674285f4bfe9e56a5ad8e70c06eb8d84b`.
- **Tested source SHA**: `a095a457f2f12e8d65fe69ba5a3ca3ddb79ea110` (`git_dirty: false`).
- **Bằng chứng runtime**: Bundle `bank_receiver_heap_r4_runtime_evidence`, kết quả kiểm tra độc lập `bank_receiver_heap_r4_runtime_review_evidence/results.json`.
- **Trạng thái kiểm chứng**: **RUN / PASS, auditor exit 0**.
- **Phạm vi**: Đóng gói hồ sơ tài liệu (Documentation-only closure); **không mở vòng triển khai mới**.
- **Ranh giới nghiệm thu**: Toàn bộ BH-07 và cổng V2b **CHƯA ĐƯỢC NGHIỆM THU**.

---

## 1. Nội dung Kỹ thuật Triển khai

### 1.1 Cờ kích hoạt có chủ đích (`--bank-coverage`)
- Chế độ đo bank/receiver được kích hoạt riêng qua cờ `--bank-coverage` và khai báo versioned contract `bank_coverage_contract` (phiên bản `1.0`, yêu cầu `required_owner_load: ['bank_account_id', 'bank', 'receiver']`).
- Các lần chạy đo tài chính thông thường (baseline finance runs) không bị ảnh hưởng và giữ nguyên hành vi kiểm tra kế thừa.

### 1.2 Fixture dùng một lần sở hữu độc lập (Club / Member / Bank)
- `DisposableBankFixture` tạo bộ dữ liệu độc lập gồm CLB tạm, thành viên Owner, và bản ghi ngân hàng (`club_bank_accounts`) với UUID riêng biệt cho từng lần chạy.
- Cơ chế dọn dẹp thực hiện nghiêm ngặt theo thứ tự con trước cha sau (`club_bank_accounts` -> `club_members` -> `clubs`), kèm preflight đối chiếu ID tránh va chạm và xác minh vắng mặt sau khi xóa.

### 1.3 Phân định Gating: unrendered `bank_account_id` vs rendered `bank`/`receiver`
- `bank_account_id` (không hiển thị UI, `rendered: false`, `scope: finance`): Là chốt kiểm soát vắng mặt bắt buộc (absence gate). Đã kiểm chứng biến mất hoàn toàn và không khả đạt (`present: false`, `reachable: false`) sau khi phiên Owner kết thúc (`post_logout`, `post_actor`) ở cả 2 chu kỳ.
- `bank` và `receiver` (chuỗi hiển thị widget text, `rendered: true`, `scope: bank`): Chuỗi rendered quan sát được vẫn còn khả đạt (`reachable: true`) sau khi đăng xuất hoặc đổi actor, được phân loại trung thực là **rủi ro tồn đọng chưa quy kết** (`attribution: UNATTRIBUTED`). Một đường dẫn ghi nhận được không thể loại trừ các đường dẫn app hay đường dẫn khác; tuyệt đối **KHÔNG PHẢI clean absence gate và KHÔNG PHẢI chứng minh toàn bộ object đã được giải phóng**.

### 1.4 Kiểm soát Đồ thị Owner Reachable & Baseline Discrimination
- Toàn bộ nhóm 3 sentinel (`bank_account_id`, `bank`, `receiver`) bắt buộc phải có đường dẫn khả đạt (`reachable: true`) từ GC root trong snapshot `owner_active`.
- Ở snapshot `baseline`, toàn bộ nhóm bắt buộc **không được khả đạt** (`reachable: false`), ngay cả khi bảng đếm chuỗi ghi nhận `occurrences: 0`. Cả `heap_oracle.py` và `verify_evidence.py` đều từ chối (fail-closed) nếu phát hiện đường dẫn còn sống tại baseline.

### 1.5 Xử lý từ chối chính xác HTTP 403
- HTTP adapter truyền nguyên vẹn mã trạng thái HTTP số (`res.status`) vào đối tượng lỗi.
- Helper fixture nhận diện từ chối dứt khoát (như HTTP 403 Forbidden) trong pha preflight và POST, không nhận quyền sở hữu dữ liệu ngoại lai và không kích hoạt lệnh DELETE sai mục tiêu.

### 1.6 Output Guard kiểm soát thư mục kết quả mới
- Cơ chế kiểm soát ghi nhận thư mục xuất kết quả từ chối các đường dẫn đã tồn tại hoặc nằm lồng dưới các bundle bằng chứng lịch sử nhằm bảo toàn tính bất biến của dữ liệu.

### 1.7 Console Sanitizer bảo vệ dữ liệu nhạy cảm
- Cơ chế làm sạch thông tin trước khi ghi log console, ngăn chặn việc in trực tiếp số tài khoản hoặc tên chủ tài khoản thật ra terminal/console trong quá trình đo lường.

---

## 2. Trạng thái Kiểm thử & Runtime Quan sát bởi Codex

- **Python suite**: 375 tests pass.
- **Fixture controls**: 8/8 controls pass.
- **Legacy & Finance auditors**: b13e468 legacy auditor và finance auditor đều exit 0.
- **Flutter analyze / test**: ĐÃ ĐẠT — `flutter analyze` 0 issues (archive `acc950d1867dbe8f`), `flutter test` 247 pass + 1 skip (archive `7b13b952014a42cb`).
- **Runtime heap thực tế (Codex runtime độc lập)**:
  - Source commit: `a095a457f2f12e8d65fe69ba5a3ca3ddb79ea110` (`git_dirty: false`).
  - Bundle: `bank_receiver_heap_r4_runtime_evidence`.
  - Kết quả độc lập: `bank_receiver_heap_r4_runtime_review_evidence/results.json`.
  - Kết quả: `status: "RUN"`, `verdict: "PASS"`, `auditor_exit: 0`.
  - Chu kỳ: 2 chu kỳ cùng document Owner → logout → Cohost/Member (8 epochs):
    - **Baseline (cả 2 chu kỳ)**: Cả 3 sentinel (`bank_account_id`, `bank`, `receiver`) đều `present: false`, `reachable: false`. Toàn bộ nhóm yêu cầu sạch ở baseline.
    - **Owner active (cả 2 chu kỳ)**: Cả 3 sentinel đều `present: true`, `reachable: true`. Nạp thành công vào heap khi xem màn hình.
    - **Post logout & post actor (cả 2 chu kỳ)**:
      - `bank_account_id`: `present: false`, `reachable: false` (absence gate ĐẠT sạch 100%).
      - `bank` & `receiver`: `present: true`, `reachable: true` (chuỗi rendered quan sát được vẫn khả đạt sau logout/actor, ghi nhận dạng rủi ro tồn đọng chưa quy kết `attribution: UNATTRIBUTED`; một đường dẫn BFS không loại trừ các đường dẫn app hay đường dẫn khác, KHÔNG PHẢI absence gate sạch và KHÔNG PHẢI chứng minh toàn bộ object đã giải phóng).
  - **Toàn vẹn cơ sở dữ liệu (DB Integrity)**: Full-row fingerprints trước và sau khi chạy hoàn toàn trùng khớp; các fixture tạo riêng cho lần chạy (`disposable_club`, `disposable_bank`) đã được xóa và xác minh vắng mặt (`disposable_club_verified_absent: true`, `disposable_bank_verified_absent: true`).
  - **Dọn dẹp môi trường**: Thư mục dump ngoài repo và Chrome profile đã được dọn sạch hoàn toàn (`dumps_dir_removed: true`, `chrome_profile_dir_removed: true`, `raw_snapshots_remaining: 0`).
  - **Tính bất biến của bằng chứng**: 1.606 tệp evidence lịch sử giữ nguyên byte (0 mismatch), cùng 1.719 đường dẫn evidence/app được bảo vệ và 16 payload vòng 4 trước đó đã xác minh; 87 tệp app/backend nguyên vẹn (0 mismatch).
*(Không công bố hoặc giả định vượt quá các kết quả quan sát trên).*

---

## 3. Ranh giới & Giới hạn Kỹ thuật

| Phạm vi | Trạng thái | Ghi chú |
| :--- | :--- | :--- |
| **Toàn bộ BH-07** | **CHƯA NGHIỆM THU** | Toàn bộ V2b và BH-07 chưa nghiệm thu; cần chủ dự án phê duyệt tích hợp. |
| **Runtime bank/receiver trên Web profile** | **ĐÃ ĐO V8 RUNTIME (PASS)** | Chạy thực tế thành công trên Chromium local (a095a45, RUN/PASS); `bank_account_id` sạch, `bank`/`receiver` là rủi ro tồn đọng chưa quy kết (`attribution: UNATTRIBUTED`, chuỗi rendered còn khả đạt, chưa loại trừ các đường dẫn khác). |
| **App-wide memory retention / Whole-model** | **UNKNOWN** | Giới hạn phân tích đồ thị V8 heap theo sentinel; không chứng minh toàn bộ object graph hay model app được giải phóng. |
| **Chỉ dẫn thanh toán & QR (`payment_instructions`)** | **NOT RUN** | Chưa probe heap cho màn hình QR thanh toán của player. |
| **Sổ quỹ CLB (`club_ledger`)** | **NOT RUN** | Chưa probe heap cho màn hình Quỹ CLB. |
| **Listener object graph (Web)** | **NOT RUN** | Chưa probe đồ thị đối tượng closure listener trên Web heap. |
| **Dart VM native (desktop/mobile)**| **NOT RUN** | Phạm vi chỉ bao gồm Web profile V8; chưa đo trên Dart VM runtime. |
