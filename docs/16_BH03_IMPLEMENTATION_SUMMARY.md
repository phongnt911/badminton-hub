# Báo cáo triển khai & nghiệm thu BH-03: CLB, thành viên và tài khoản nhận tiền

- **Ngày thực hiện**: 15/10/2026
- **Mục tiêu**: Hoàn thiện toàn bộ ticket BH-03 theo [15_BH03_IMPLEMENTATION_HANDOFF.md](15_BH03_IMPLEMENTATION_HANDOFF.md).
- **Môi trường kiểm thử**: 
  - Local Docker PostgreSQL (`postgres:latest` sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24).
  - Không apply Supabase production.

---

## 1. Tóm tắt kết quả theo từng giai đoạn

### BH-03A: Database Migration, RPCs & Quyền
- **File migration**: `supabase/migrations/20261015133247_bh03_clubs_and_members.sql`
- **12 RPC nguyên tử**:
  1. `create_club`: Nguyên tử tạo CLB và gán owner member, idempotency và audit event.
  2. `update_club`: Khóa row, chỉ owner sửa tên/mô tả/visibility.
  3. `add_club_member`: Owner/host thêm thành viên, hỗ trợ thành viên offline (`user_id = NULL`), lưu SĐT vào bảng riêng `member_contacts`.
  4. `update_club_member_contact`: Owner/host cập nhật tên hiển thị và liên hệ riêng tư.
  5. `set_club_member_role`: Owner phân quyền, chặn cấp quyền quản lý cho người chưa có tài khoản (`user_id IS NULL`), chặn sửa hoặc hạ quyền owner, chặn self-escalation.
  6. `set_club_bank_account`: Owner cấu hình ngân hàng CLB, giữ leading zeros (TEXT), vô hiệu hóa tài khoản cũ, chỉ giữ đúng 1 active account.
  7. `set_host_bank_account`: Host tự cấu hình tài khoản cá nhân của chính mình.
  8. `get_club_detail`: Projection phân quyền, chỉ owner và treasurer thấy `balance_vnd`.
  9. `list_club_members`: Owner/host thấy SĐT thành viên; member thường chỉ thấy SĐT của chính mình; treasurer không thấy SĐT người khác.
  10. `get_club_bank_account`: Chỉ owner và treasurer xem được tài khoản nhận tiền CLB.
  11. `get_host_bank_account`: Xem tài khoản cá nhân của host.
  12. `list_my_clubs`: Trả về danh sách CLB mà người dùng đang tham gia hoặc làm chủ kèm vai trò `my_role`.
- **Kiểm thử DB (`docs/reviews/bh03/run_bh03_tests.py`)**: **24/24 PASS** trên cả hai môi trường Clean DB và Legacy DB.

### BH-03B: Data & State Management
- **Models** (`lib/models/club.dart`):
  - `Club`: Typed DTO với các helper getter `isOwner`, `isHost`, `isTreasurer`, `canManageMembers`, `canViewBalance`, `canConfigureBank`.
  - `ClubMember`: Hỗ trợ cờ `isOffline` (`userId == null`).
  - `BankAccount`: Lưu trữ số tài khoản chuẩn chuỗi.
- **Repository** (`lib/data/club_repository.dart`):
  - Giao tiếp với Supabase qua các RPC chuẩn, loại bỏ hoàn toàn các trường legacy (`owner_phone`, direct write vào `clubs.balance`).
- **Provider** (`lib/providers/club_provider.dart`):
  - Tách bạch state danh sách và state chi tiết.
  - Bảo vệ concurrency: `isSubmitting` chặn double tap.
  - Chống rò rỉ dữ liệu: `clearCurrentClub()` dọn dẹp state ngay khi đổi CLB; `clearAll()` khi đăng xuất.
- **Unit tests** (`test/models/club_model_test.dart`, `test/providers/club_provider_test.dart`): **13/13 PASS**.

### BH-03C: UI Layer
- **Màn hình danh sách CLB (`ClubsScreen`)**:
  - Hiển thị danh sách CLB kèm badge vai trò và số dư quỹ đúng quyền.
  - Dialog "Tạo CLB mới" chỉ yêu cầu Tên, Mô tả, Quyền riêng tư (không bắt nhập phone hay bank).
  - Empty state & Error retry đầy đủ.
- **Màn hình chi tiết CLB (`ClubDetailScreen`)**:
  - 3 Tabs: Tổng quan / Thành viên / Tài khoản quỹ.
  - Phần Quỹ: Ẩn với thành viên thường; đối với chủ nhiệm/thủ quỹ, các nút ghi quỹ hiển thị thông báo "Chức năng ghi thu/chi quỹ sẽ khả dụng trong BH-06".
  - Tab Thành viên: Hiển thị nhãn "Chưa liên kết tài khoản" cho thành viên offline; chức năng đổi vai trò từ chối cấp quyền cho người chưa có tài khoản app.
  - Tab Tài khoản quỹ: Giao diện thẻ ngân hàng trực quan, bảo vệ chỉ chủ nhiệm và thủ quỹ xem được.
- **Widget tests** (`test/screens/clubs_screen_test.dart`): **4/4 PASS**.

### BH-03D: Kiểm thử tích hợp & Báo cáo kết quả
- **Kiểm thử hồi quy BH-02**:
  - `run_rls_tests.py`: **33/33 PASS**.
  - `extended_tests_15ef59b.py`: **14/14 PASS**.
  - Tổng cộng: **47/47 PASS** (0 regression).
- **Bộ kiểm thử BH-03 DB**: **24/24 PASS**.
- **Toàn bộ Flutter test suite**: **56/56 PASS**.
- **Phân tích mã nguồn tĩnh (`flutter analyze`)**: **0 issues** (No issues found).

---

## 2. Bảng tổng hợp trạng thái nghiệm thu

| Nhóm nghiệm thu | Trạng thái | Ghi chú |
|---|---|---|
| Atomic & Idempotent create_club | **PASS** | 1 owner duy nhất, rollback khi lỗi, replay cùng payload |
| Role escalation & demotion protection | **PASS** | Chặn self-escalation, không hạ quyền owner qua endpoint role, từ chối cấp quyền quản lý cho offline member |
| Privacy dữ liệu quỹ & danh bạ | **PASS** | Số dư quỹ chỉ owner/treasurer thấy; SĐT chỉ owner/host và chính chủ thấy |
| Offline member identity | **PASS** | `user_id = NULL`, không tài khoản ảo, không gộp số điện thoại |
| Bank account single active & TEXT | **PASS** | Chỉ owner đổi bank CLB, lưu TEXT giữ số 0 ở đầu, 1 active duy nhất |
| UI/UX states & Anti-double tap | **PASS** | Loading, error, empty, submitting guard, reset state khi đổi CLB |
| BH-02 Regression | **PASS** | 47/47 ca kiểm thử BH-02 đều đạt |
| Supabase Production | **NOT RUN** | Tuân thủ quy định không can thiệp production khi chưa có yêu cầu |

---

## 3. Giới hạn & Điểm lưu ý cho các ticket tiếp theo
1. **Self-service Invitation & Account Linking**: Trong phạm vi BH-03, thành viên mới được thêm dưới dạng offline (`user_id = NULL`). Cơ chế tự mời và liên kết tài khoản thông qua OTP/link xác nhận sẽ được tích hợp ở giai đoạn phù hợp.
2. **Ghi thu/chi quỹ (Ledger Mutations)**: Số dư quỹ trong BH-03 chỉ đọc (Read-only view). Các thao tác thu/chi và đối soát tự động thuộc phạm vi ticket **BH-06**.
