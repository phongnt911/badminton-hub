# Bản đồ Độ phủ Bộ nhớ Riêng tư V2b BH-07 (Private Memory & In-Memory Cache Coverage Map)

- Tài liệu tham chiếu: [AGENTS.md](../../../AGENTS.md), [bh07_readiness.md §4.4](bh07_readiness.md), [retention_attribution_report.md](retention_attribution_report.md).
- Trạng thái hiện hành: **Phạm vi đo thực mới chỉ bao phủ 2 expense ID; 6 thực thể tài chính/ngân hàng còn lại GIỮ NOT RUN.**

---

## 1. Mục đích Bản đồ

Bản đồ này vạch rõ từng thực thể dữ liệu riêng tư nhạy cảm của Owner trong ứng dụng `badminton-hub`, đối chiếu từ tầng Model -> Provider/Cache -> UI Surface -> Hiện trạng kiểm chứng thực tế, và xác định chính xác những gì còn thiếu để có thể nghiệm thu đầy đủ cổng V2b §4.4.

---

## 2. Ma trận Độ phủ Chi tiết (11 Thực thể)

### 2.1. Nhóm Dữ liệu Chi phí Buổi (`session_expenses`)

| Thực thể | Chi tiết Kỹ thuật | Trạng thái Hiện tại | Yêu cầu để Nghiệm thu Đầy đủ |
| :--- | :--- | :--- | :--- |
| **Mã chi phí (`expense_id`, `expense_id_2`)** | - Model: [`FinanceExpense.expenseId`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L222)<br>- Provider: [`FinanceProvider._finance.expenses`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart#L180)<br>- UI: Không render (UUID)<br>- Scope: `finance`, Distinctive: `true`, Rendered: `false` | **ĐÃ ĐO THỰC & ĐẠT LOCAL** trên Web profile (b13e468). Có mặt ở `owner_active` (path len 20), biến mất 100% (`occurrences: 0`) sau logout ở cả 2 chu kỳ. | Dart VM desktop/mobile (iOS/Android/Windows) vẫn `NOT RUN`. |
| **Tiêu đề chi phí (`expense`, `expense2`)** | - Model: [`FinanceExpense.title`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L222)<br>- Provider: [`FinanceProvider._finance.expenses`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart#L180)<br>- UI: [`SessionFinanceScreen._expenseTile`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_finance_screen.dart#L620)<br>- Scope: `finance`, Distinctive: `true`, Rendered: `true` | **RESIDUAL RISK ĐÃ PHÂN ĐỊNH**: Chuỗi còn trong `segmentationCache` của Flutter Web Engine (`text_fragmenter.dart`). Tầng ứng dụng đã giải phóng sạch. | Cần văn bản Residual-Risk Acceptance của chủ dự án đối với text cache của web engine; đo lại trên Dart VM (nơi không có web text cache). |

### 2.2. Nhóm Dữ liệu Thu phí & Thanh toán Buổi (`charges` & `payments`)

| Thực thể | Chi tiết Kỹ thuật | Trạng thái Hiện tại | Yêu cầu để Nghiệm thu Đầy đủ |
| :--- | :--- | :--- | :--- |
| **Khoản thu người chơi (`charges`)** | - Model: [`FinanceCharge`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L258) (`playerId`, `displayName`, `chargeVnd`, `status`, `notes`)<br>- Provider: [`FinanceProvider._finance.charges`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart#L180)<br>- UI: [`SessionFinanceScreen._chargesSection`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_finance_screen.dart#L648)<br>- Scope: `finance` | **CHƯA ĐO TRONG APP HEAP (NOT RUN)**.<br>Mới chỉ có unit test cấp Provider (`bh07_heap_verification_test.dart`). Runner Chrome chưa khai báo sentinel cho charge ID/ghi chú thu. | Cần tạo fixture charge có ghi chú/ID phân biệt, khai báo sentinel trong `run_app_profile_heap.js`, kiểm tra sự có mặt ở `owner_active` và biến mất ở `post_logout`. |
| **Khoản thanh toán của người chơi (`payments`)** | - Model: [`FinancePayment`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L279) (`paymentId`, `playerId`, `displayName`, `amountVnd`, `method`, `referenceCode`, `status`)<br>- Provider: [`FinanceProvider._finance.payments`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart#L180)<br>- UI: [`SessionFinanceScreen._paymentsSection`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_finance_screen.dart#L696)<br>- Scope: `finance` | **CHƯA ĐO TRONG APP HEAP (NOT RUN)**.<br>Mới chỉ có unit test cấp Provider. Chưa có sentinel cho `paymentId` hay mã tham chiếu thanh toán (`referenceCode`). | Cần bổ sung fixture thanh toán đã ghi nhận (`paymentId` UUID độc nhất), đưa vào danh sách sentinel và chạy kiểm chứng heap thực tế. |

### 2.3. Nhóm Dữ liệu Ngân hàng CLB & Chỉ dẫn Thanh toán QR (`bank` & `receiver`)

| Thực thể | Chi tiết Kỹ thuật | Trạng thái Hiện tại | Yêu cầu để Nghiệm thu Đầy đủ |
| :--- | :--- | :--- | :--- |
| **Số tài khoản ngân hàng CLB (`bank`)** | - Model: [`BankAccount.accountNumber`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/club.dart#L127)<br>- Provider: [`ClubProvider._currentBankAccount`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/club_provider.dart#L112)<br>- UI: [`ClubsScreen._showConfigureBankDialog`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/clubs_screen.dart#L472)<br>- Scope: `bank`, Distinctive: `false` (10 chữ số) | **CHƯA ĐO ĐÚNG (NOT RUN)**.<br>Chuỗi 10 số va chạm với phần đuôi của UUID fixture (`...-000000000007`), do đó bị hạ cấp xuống `distinctive: false` và không được gate. Ngoài ra luồng `openOwnerFinance` chưa mở màn hình ngân hàng CLB. | Cần thiết lập fixture STK có độ dài và ký tự đặc thù không trùng khớp ngẫu nhiên với UUID; kịch bản runner phải click mở màn hình Quản lý Ngân hàng của CLB. |
| **Tên chủ tài khoản nhận tiền (`receiver`)** | - Model: [`BankAccount.accountName`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/club.dart#L128)<br>- Provider: [`ClubProvider._currentBankAccount`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/club_provider.dart#L112)<br>- UI: [`ClubsScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/clubs_screen.dart#L913) / Payment QR<br>- Scope: `bank`, Distinctive: `true` | **CHƯA ĐO (NOT RUN)**.<br>Runner có khai báo sentinel nhưng `occurrences: 0` ngay từ `owner_active` vì luồng UI không truy cập màn hình ngân hàng hay mã QR của Owner. | Kịch bản runner cần duyệt qua màn hình ngân hàng để `receiver` thực sự được nạp vào RAM ở `owner_active`. |
| **Chỉ dẫn thanh toán & QR (`payment_instructions`)** | - Model: [`PaymentInstructions`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L34) (`vietqrUrl`, `transferContent`, `bankAccount`, `accountHolder`)<br>- Provider: [`FinanceProvider._instructions`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart#L101)<br>- UI: [`SessionFinanceScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_finance_screen.dart#L458) (chế độ xem Player)<br>- Scope: `finance`, Distinctive: `true` | **CHƯA ĐO TRONG APP HEAP (NOT RUN)**.<br>Chỉ mới xác minh trên mock Provider test. Màn hình quét mã QR của người chơi chưa được chạy trong kịch bản CDP. | Bổ sung kịch bản actor Người chơi bấm xem QR thanh toán, lấy `transferContent` làm sentinel đo heap. |

### 2.4. Nhóm Sổ Quỹ & Tổng kết Tài chính (`ledger` & `summary`)

| Thực thể | Chi tiết Kỹ thuật | Trạng thái Hiện tại | Yêu cầu để Nghiệm thu Đầy đủ |
| :--- | :--- | :--- | :--- |
| **Sổ quỹ CLB (`club_ledger`)** | - Model: [`ClubLedger`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L447), [`ClubLedgerEntry`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L402)<br>- Provider: [`FinanceProvider._ledger`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart)<br>- UI: [`ClubFundScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/club_fund_screen.dart#L179)<br>- Scope: `finance`, Distinctive: `true` | **CHƯA ĐO TRONG APP HEAP (NOT RUN)**.<br>Màn hình Quỹ CLB (`ClubFundScreen`) chưa từng được kích hoạt trong `run_app_profile_heap.js`. | Cần thêm bước Owner vào tab CLB -> Quỹ CLB, nạp `ClubLedger`, chọn `transactionId` làm sentinel để đo retention sau logout. |
| **Tổng kết số tiền buổi (`session_summary`)** | - Model: [`SessionSummary`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L98) (`totalExpensesVnd`, `totalChargesVnd`, `totalCollectedVnd`, `remainingVnd`)<br>- Provider: [`FinanceProvider._summary`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart)<br>- UI: [`SessionSummaryScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_summary_screen.dart#L58)<br>- Scope: `finance` | **MÀN HÌNH ĐÃ DUYỆT NHƯNG CHƯA GATE SENTINEL**.<br>Màn hình đã được mở trong `openOwnerFinance`, nhưng các trường là số tiền (`int`), không thể tìm kiếm theo chuỗi phân biệt trong string table của heap snapshot. | Khối dữ liệu này chia sẻ chung vòng đời với `_finance` và `_summary`. Việc `_summary` reset về `null` đã kiểm chứng ở Provider test, nhưng heap V8 chưa có chuỗi định danh riêng cho summary. |

### 2.5. Nhóm Danh tính & Bộ lắng nghe Sự kiện (`identity` & `listeners`)

| Thực thể | Chi tiết Kỹ thuật | Trạng thái Hiện tại | Yêu cầu để Nghiệm thu Đầy đủ |
| :--- | :--- | :--- | :--- |
| **Danh tính thành viên CLB (`roster_identities`)** | - Model: [`SessionPlayer.id`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/session.dart#L237) (`player_a`, `player_b`)<br>- Provider: [`SessionProvider`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/session_provider.dart)<br>- UI: [`SessionDetailScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_detail_screen.dart)<br>- Scope: `identity`, Distinctive: `true` | **ĐÃ BÁO CÁO DẠNG NOTE**.<br>Biến mất ở `post_logout` và `post_member`; còn reachable ở `post_cohost` (path len 18). Phép đo bộ nhớ không thể khẳng định Cohost có quyền fetch lại hay không. | Cần kiểm tra quyền (Authorization/RLS) độc lập bằng HTTP/API test ở tầng backend (đã đạt ở BH-06), không dùng heap snapshot để kết luận quyền. |
| **Bộ lắng nghe Auth (`auth_listeners`)** | - Lớp: `addListener(_onAuthChanged)` trong `FinanceProvider`, `ClubProvider`, `SessionProvider`<br>- Quản lý generation & serial | **ĐÃ XÁC MINH SẠCH**.<br>AST audit 38 file xác nhận không có static mutable collection; các listener đều gọi `removeListener` khi dispose; bộ tạo số thế hệ (`_generation`) huỷ toàn bộ kết quả đang chờ khi đổi user. | Đã hoàn thành; duy trì hồi quy AST và Provider tests. |

---

## 3. Tổng kết Phân loại Khoảng trống (GAP Summary)

Dựa trên kiểm tra tự động qua [`scripts/bh07_appheap/audit_retention_attribution.py`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/scripts/bh07_appheap/audit_retention_attribution.py):
- **Tổng số thực thể theo dõi:** 11.
- **Đã xác minh sạch trên Web Profile Heap:** 1 (`expense_id`).
- **Xác minh sạch cấp Provider Harness (chưa đo Web Profile Heap thật):** 6 (`charges`, `payments`, `bank`, `receiver`, `payment_instructions`, `ledger`).
- **Residual Risk do Web Engine Text Cache:** 1 (`expense_titles`).
- **Màn hình đã mở nhưng chưa có Sentinel thích hợp:** 1 (`session_summary`).
- **Dữ liệu danh tính báo cáo dạng Note:** 1 (`roster_identities`).
- **Hạ tầng Listener:** 1 (`auth_listeners` - Đạt).

## 4. Lộ trình Kỹ thuật Đề xuất để Đóng Hoàn toàn V2b §4.4

Để chuyển trạng thái V2b §4.4 từ **Đạt phạm vi hẹp** sang **Nghiệm thu toàn diện**, cần thực hiện:
1. **Mở rộng kịch bản `run_app_profile_heap.js`** để duyệt qua:
   - Màn hình Quỹ CLB (`ClubFundScreen` -> nạp `ClubLedger`).
   - Màn hình Cấu hình Ngân hàng CLB (`ClubsScreen` -> nạp `BankAccount`).
   - Màn hình Chỉ dẫn Thanh toán QR (`PaymentInstructions`).
2. **Bổ sung Sentinel độc nhất cho từng thực thể mới**:
   - `charge_id` (UUID).
   - `payment_id` (UUID).
   - `transaction_id` (UUID của sổ quỹ).
   - `bank_account_custom` (chuỗi số kèm tiền tố chữ, ví dụ `STK-9999888877`).
3. **Đo heap trên Dart VM (desktop hoặc mobile)**:
   - Dựng môi trường có Dart VM service kết nối qua DevTools Memory Profiler trên Windows desktop hoặc Android emulator để đối chiếu hành vi retention mà không bị ảnh hưởng bởi `segmentationCache` của web engine.
