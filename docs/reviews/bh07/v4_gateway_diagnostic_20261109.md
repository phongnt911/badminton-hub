# Chuẩn đoán cấu hình tiếp nhận Gateway (Gateway Admission Diagnostic) — 09/11/2026

## 1. Mục tiêu & Bối cảnh nhiệm vụ
- **Nhiệm vụ được ủy quyền**: Khảo sát read-only cấu hình gateway admission chính thống theo ủy quyền của chủ dự án; không phải vòng sửa code/test thứ tư.
- **Tài liệu sở hữu**: Duy nhất `docs/reviews/bh07/v4_gateway_diagnostic_20261109.md`. Bảo toàn toàn bộ các chỉnh sửa của người khác.
- **Ranh giới an toàn**: Không chạy bất kỳ lệnh shell nào, không thử lại doctor, không dùng reader thay thế hoặc bản sao, không đổi cấu hình/chính sách/mã nguồn, không cài đặt phần mềm, không thay đổi DB/Docker, không commit, push hay deploy.

## 2. Kết quả kiểm tra công cụ `ctx_read` (Tool Evidence)
Thực hiện đọc read-only qua MCP `ctx_read` đối với hai đường dẫn cấu hình được chỉ định:

1. **Đường dẫn**: `C:/Users/POTA/.codex/LEAN-CTX.md`
   - **Kết quả**: Bị từ chối / giữ lại (**WITHHELD**).
   - **Thông báo lỗi từ công cụ**:
     `path: path escapes project root: C:/Users/POTA/.codex/LEAN-CTX.md (root: C:/Users/POTA/Documents/GitHub/badminton-hub). C:/Users/POTA\.codex is a protected location (credentials and other programs' private data stay jailed). To allow it anyway: lean-ctx allow-path C:/Users/POTA/.codex — the user runs this in their own terminal; it takes effect immediately, no restart.`

2. **Đường dẫn**: `C:/Users/POTA/.config/lean-ctx/config.toml`
   - **Kết quả**: Bị từ chối / giữ lại (**WITHHELD**).
   - **Thông báo lỗi từ công cụ**:
     `path: path escapes project root: C:/Users/POTA/.config/lean-ctx/config.toml (root: C:/Users/POTA/Documents/GitHub/badminton-hub). C:/Users/POTA\.config is a protected location (credentials and other programs' private data stay jailed). To allow it anyway: lean-ctx allow-path C:/Users/POTA/.config/lean-ctx — the user runs this in their own terminal; it takes effect immediately, no restart.`

Theo chỉ thị: Do cấu hình và tài liệu bị giữ lại, nhánh kiểm tra nội dung này **DỪNG LẠI (STOP)**; nội dung cấu hình chi tiết ghi nhận là **UNKNOWN**. Không suy diễn hoặc bịa đặt nguyên nhân gốc rễ hay tên tham số không đọc được.

## 3. Phân định các cơ chế chặn của Gateway (Distinction of Mechanisms)
Cần phân biệt rõ ba cơ chế kiểm soát tách biệt của hệ thống:
1. **Source Authority Withholding / Path Jailing (Bảo vệ đường dẫn ngoài dự án)**:
   - Cơ chế này chặn truy cập vào các đường dẫn nằm ngoài thư mục gốc dự án (`root: C:/Users/POTA/Documents/GitHub/badminton-hub`), đặc biệt là các thư mục bảo vệ chứa dữ liệu riêng tư hoặc thông tin xác thực (`.codex`, `.config`).
   - Đây là cơ chế trực tiếp từ chối đọc hai file cấu hình nêu trên.
2. **Runner Signature Withholding / Secret Redaction Filter (Lọc nội dung mã nguồn)**:
   - Xảy ra ngay bên trong dự án khi đọc `scripts/bh07_backup/run_v4_concurrent_rehearsal.py` qua `ctx_read` với chế độ `signatures` (báo cờ `secret.redacted`, `redaction.incomplete`).
   - Cơ chế này lọc nội dung do khớp với mẫu nhận diện bảo mật, độc lập với cơ chế path jailing.
3. **Shell Allowlist / Doctor Block (Kiểm soát lệnh shell)**:
   - Cơ chế chặn các lệnh CLI không nằm trong allowlist hoặc chứa cờ cấm (ví dụ `-p`), độc lập với việc đọc tệp qua MCP tool.

## 4. Các điểm nghẽn hiện tại (Blockers)
1. **Config Inaccessible**: Agent không thể đọc cấu hình lean-ctx nội bộ do chính sách giam đường dẫn (path jailing) bảo vệ tài nguyên ngoài root.
2. **Runner Source Withheld**: Toàn bộ mã nguồn runner V4 vẫn bị giữ lại bởi bộ lọc redaction; không thể tiến hành rà soát mã nguồn đầy đủ (source full review) theo yêu cầu tiền kiểm.
3. **Working Tree Dirty / Runtime NOT RUN**: Working tree uncommitted; toàn bộ V4 runtime giữ trạng thái NOT RUN; V4/BH-07/V8 chưa nghiệm thu.

## 5. Bước xử lý chính thống tiếp theo (Sanctioned Next Steps)
- Nếu chủ dự án / quản trị viên muốn cho phép kiểm tra cấu hình lean-ctx, quản trị viên có thể chủ động chạy thủ công trong terminal riêng của mình (ngoài phiên agent):
  `lean-ctx allow-path C:/Users/POTA/.config/lean-ctx`
  và/hoặc
  `lean-ctx allow-path C:/Users/POTA/.codex`
- Để giải quyết vấn đề rà soát mã nguồn runner: Cần sự can thiệp từ quản trị viên gateway để làm rõ quy tắc redaction trên `run_v4_concurrent_rehearsal.py` hoặc tổ chức rà soát độc lập trong môi trường được cấp quyền chính thống.
- Anti CLI tiếp tục tuân thủ nghiêm ngặt chế độ read-only / report-only, không bypass, không chạy shell và không can thiệp hệ thống.
