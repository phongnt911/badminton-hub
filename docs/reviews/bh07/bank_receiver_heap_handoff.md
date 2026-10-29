# Bàn giao Kỹ thuật: Bank & Receiver Heap Coverage (Round 3/3)

> **Thông báo quan trọng**: Đây là tài liệu bàn giao từ phía tác giả triển khai (author handoff), **không phải biên bản nghiệm thu độc lập**. Toàn bộ gói công việc BH-07 chưa được nghiệm thu; không merge, deploy, push, pilot hoặc chuyển sang BH-08.

- **Ngày**: 29/10/2026.
- **Nhánh**: `feat/bh07-bank-receiver-heap`.
- **Base commit**: `94fd997674285f4bfe9e56a5ad8e70c06eb8d84b`.
- **Giới hạn số vòng sửa**: Tối đa 3 vòng tổng cộng theo ủy quyền chủ dự án; hiện đang ở vòng **3/3**.
- **Trạng thái source checkpoint**: Pending; runtime heap cho bank profile **NOT RUN** (không dùng SHA tự tạo).

---

## 1. Nội dung Kỹ thuật Triển khai

### 1.1 Cờ kích hoạt có chủ đích (`--bank-coverage`)
- Chế độ đo bank/receiver được kích hoạt riêng qua cờ `--bank-coverage` và khai báo versioned contract `bank_coverage_contract` (phiên bản `1.0`, yêu cầu `required_owner_load: ['bank_account_id', 'bank', 'receiver']`).
- Các lần chạy đo tài chính thông thường (baseline finance runs) không bị ảnh hưởng và giữ nguyên hành vi kiểm tra kế thừa.

### 1.2 Fixture dùng một lần sở hữu độc lập (Club / Member / Bank)
- `DisposableBankFixture` tạo bộ dữ liệu độc lập gồm CLB tạm, thành viên Owner, và bản ghi ngân hàng (`club_bank_accounts`) với UUID riêng biệt cho từng lần chạy.
- Cơ chế dọn dẹp thực hiện nghiêm ngặt theo thứ tự con trước cha sau (`club_bank_accounts` -> `club_members` -> `clubs`), kèm preflight đối chiếu ID tránh va chạm và xác minh vắng mặt sau khi xóa.

### 1.3 Phân định Gating: unrendered `bank_account_id` vs rendered `bank`/`receiver`
- `bank_account_id` (không hiển thị UI, `rendered: false`, `scope: finance`): Là chốt kiểm soát vắng mặt bắt buộc (absence gate). Bắt buộc phải biến mất hoàn toàn (`present: false`, `reachable: false`) sau khi phiên Owner kết thúc (`post_logout`, `post_actor`).
- `bank` và `receiver` (chuỗi hiển thị widget text, `rendered: true`, `scope: bank`): Web engine lưu vết trong bộ nhớ đệm phân mảnh văn bản (`segmentationCache`). Sự tồn lưu sau logout được ghi nhận trung thực là **rủi ro tồn đọng chưa quy kết** (`unattributed residual risk`), tuyệt đối không biến thành absence gate.

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

## 2. Trạng thái Kiểm thử Quan sát bởi Codex

- **Python suite**: 357 tests pass.
- **Bank coverage unit tests**: 22 tests pass.
- **Bank owner graph tests**: 4 tests pass (`tests/test_bh07_bank_owner_graph.py` chạy probe `owner_graph_probe.py` với kết quả positive exit 0/PASS, 2 mutants exit 1/FAIL).
- **Fixture controls**: 8/8 controls pass.
- **Flutter analyze / test**: PENDING.
- **Console regression probe**: PENDING.
*(Không công bố hoặc giả định vượt quá các kết quả quan sát trên).*

---

## 3. Ranh giới & Giới hạn Kỹ thuật

| Phạm vi | Trạng thái | Ghi chú |
| :--- | :--- | :--- |
| **Toàn bộ BH-07** | **CHƯA NGHIỆM THU** | Cần hoàn tất đánh giá độc lập của Codex và chạy runtime đầy đủ. |
| **Runtime bank trên Web profile** | **NOT RUN** | Chưa chạy đo thực tế trên trình duyệt Chromium local cho profile bank. |
| **App-wide memory retention** | **UNKNOWN** | Giới hạn phân tích đồ thị V8 heap theo sentinel; chưa chứng minh toàn bộ app giải phóng. |
| **Listener object graph (Web)** | **NOT RUN** | Chưa probe đồ thị đối tượng closure listener trên Web heap. |
| **Dart VM native (desktop/mobile)**| **NOT RUN** | Phạm vi chỉ bao gồm Web profile V8; chưa đo trên Dart VM runtime. |
