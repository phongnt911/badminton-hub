**Hiện hành (Sửa vòng 1/2):** Đã sửa đủ FH1–FH4, đính chính source SHA thực `cd25e1e3557e2013e8991b2031a240818ee84c96`, thu hẹp phạm vi kết luận sentinel V8 và khớp path length 21/20, chờ review độc lập vòng 1/2. Không tự ghi Đạt toàn V2b/BH-07.

# Bản đồ Độ phủ Bộ nhớ Riêng tư V2b BH-07 (Private Memory & In-Memory Cache Coverage Map)

- Tài liệu tham chiếu: [AGENTS.md](../../../AGENTS.md), [bh07_readiness.md §4.4](bh07_readiness.md), [retention_attribution_report.md](retention_attribution_report.md).
- Trạng thái hiện hành: **Đã mở rộng đo thực thêm payments (`payment_id` clean, `payment_ref` residual risk unattributed) cùng 2 expense ID trên Web profile local; phân định rõ ranh giới DTO charges và chống nhập nhằng roster identity; các thực thể ngân hàng/sổ quỹ còn lại và listener/object graph Web heap GIỮ NOT RUN.**

---

## 1. Mục đích Bản đồ

Bản đồ này vạch rõ từng thực thể dữ liệu riêng tư nhạy cảm của Owner trong ứng dụng `badminton-hub`, đối chiếu từ tầng Model -> Provider/Cache -> UI Surface -> Hiện trạng kiểm chứng thực tế, và xác định chính xác những gì còn thiếu để có thể nghiệm thu đầy đủ cổng V2b §4.4.

---

## 2. Ma trận Độ phủ Chi tiết (11 Thực thể)

### 2.1. Nhóm Dữ liệu Chi phí Buổi (`session_expenses`)

| Thực thể | Chi tiết Kỹ thuật | Trạng thái Hiện tại | Yêu cầu để Nghiệm thu Đầy đủ |
| :--- | :--- | :--- | :--- |
| **Mã chi phí (`expense_id`, `expense_id_2`)** | - Model: [`FinanceExpense.expenseId`](../../../lib/models/finance.dart#L222)<br>- Provider: [`FinanceProvider._finance.expenses`](../../../lib/providers/finance_provider.dart#L180)<br>- UI: Không render (UUID)<br>- Scope: `finance`, Distinctive: `true`, Rendered: `false` | **ĐÃ ĐO THỰC & ĐẠT LOCAL** trên Web profile (b13e468). Có mặt ở `owner_active` (path len 20), biến mất 100% (`occurrences: 0`) sau logout ở cả 2 chu kỳ. | Dart VM desktop/mobile (iOS/Android/Windows) vẫn `NOT RUN`. |
| **Tiêu đề chi phí (`expense`, `expense2`)** | - Model: [`FinanceExpense.title`](../../../lib/models/finance.dart#L222)<br>- Provider: [`FinanceProvider._finance.expenses`](../../../lib/providers/finance_provider.dart#L180)<br>- UI: [`SessionFinanceScreen._expenseTile`](../../../lib/screens/session_finance_screen.dart#L620)<br>- Scope: `finance`, Distinctive: `true`, Rendered: `true` | **RESIDUAL RISK UNATTRIBUTED**: Chuỗi còn trong `segmentationCache` của Flutter Web Engine (`text_fragmenter.dart`). 2 peer expense ID biến mất hỗ trợ giả thuyết model app được giải phóng, nhưng 1 đường dẫn BFS chưa loại trừ các đường dẫn khác. | Cần văn bản Residual-Risk Acceptance của chủ dự án; đo đối chiếu trên Dart VM (nơi không dùng engine web text segmentation). |

### 2.2. Nhóm Dữ liệu Thu phí & Thanh toán Buổi (`charges` & `payments`)

| Thực thể | Chi tiết Kỹ thuật | Trạng thái Hiện tại | Yêu cầu để Nghiệm thu Đầy đủ |
| :--- | :--- | :--- | :--- |
| **Khoản thu người chơi (`charges`)** | - Model: [`FinanceCharge`](../../../lib/models/finance.dart#L258) (`playerId`, `displayName`, `amountDueVnd`) — *Lưu ý kỹ thuật: DTO KHÔNG có `chargeId`, KHÔNG có `notes`*.<br>- Provider: [`FinanceProvider._finance.charges`](../../../lib/providers/finance_provider.dart#L180)<br>- UI: [`SessionFinanceScreen._chargesSection`](../../../lib/screens/session_finance_screen.dart#L648)<br>- Scope: `finance` | **PHÂN ĐỊNH RANH GIỚI DTO & CHỐNG NHẬP NHẰNG ROSTER IDENTITY (CHƯA CÓ RETAINER TÀI CHÍNH ĐỘC QUYỀN)**.<br>Do `FinanceCharge` chỉ lưu `playerId` (trùng mã thành viên phiên `SessionPlayer.id`), tại `post_logout` toàn bộ provider reset (`occurrences: 0`). Tại `post_cohost`, `playerId` xuất hiện lại qua `SessionProvider._session.players` (path len 18) do Cohost tải lại danh sách thành viên phiên. Đây là retainer danh tính (`scope: identity`), **KHÔNG PHẢI** retain của `FinanceCharge`. Không thể dùng `playerId` làm bằng chứng độc lập cho `FinanceCharge` mà không phân tích retain graph; Provider unit test đã kiểm chứng `_finance.charges` được giải phóng. | Cần thiết lập trường dữ liệu phân biệt độc quyền nếu DTO/schema tương lai bổ sung trường tài chính riêng; kiểm chứng trên Dart VM desktop/mobile. |
| **Khoản thanh toán của người chơi (`payments`)** | - Model: [`FinancePayment`](../../../lib/models/finance.dart#L279) (`paymentId`, `playerId`, `amountVnd`, `method`, `status`, `reference`, `confirmedAt`, `createdAt`)<br>- Provider: [`FinanceProvider._finance.payments`](../../../lib/providers/finance_provider.dart#L180)<br>- UI: [`SessionFinanceScreen._paymentsSection`](../../../lib/screens/session_finance_screen.dart#L696)<br>- Scope: `finance` | **1. `payment_id` (UUID không render): ĐÃ ĐO TRÊN V8 HEAP SNAPSHOT** trên Web profile local (`cd25e1e3557e2013e8991b2031a240818ee84c96`, bundle `finance_heap_evidence`). Có mặt tại `owner_active` (path len 21 ở chu kỳ 1, 20 ở chu kỳ 2), biến mất 100% (`occurrences: 0`, `reachable: false`) sau logout ở cả 2 chu kỳ Owner -> logout -> Cohost/Member. Lưu ý kỹ thuật theo FH4: phép đo xác nhận chuỗi `payment_id` không còn reachable trong snapshot V8; không suy từ một chuỗi sentinel sang việc toàn bộ object graph Dart, native Dart VM hay app-wide retention đã sạch (các phạm vi này giữ UNKNOWN/NOT RUN).<br>**2. `payment_ref` (Mã tham chiếu thanh toán rendered): RESIDUAL RISK UNATTRIBUTED**. Chuỗi còn trong `segmentationCache` của Flutter Web Engine (`text_fragmenter.dart`, path len 12), tương tự `expense` title. Việc chuỗi `payment_id` biến mất 100% trong V8 hỗ trợ phân định rủi ro tồn lưu UI text, nhưng không thay thế cho kiểm chứng native. | Dart VM desktop/mobile (iOS/Android/Windows) vẫn `NOT RUN`. Cần văn bản chấp thuận rủi ro tồn lưu (Residual-Risk Acceptance) cho chuỗi render trong web engine cache. |

### 2.3. Nhóm Dữ liệu Ngân hàng CLB & Chỉ dẫn Thanh toán QR (`bank` & `receiver`)

| Thực thể | Chi tiết Kỹ thuật | Trạng thái Hiện tại | Yêu cầu để Nghiệm thu Đầy đủ |
| :--- | :--- | :--- | :--- |
| **Số tài khoản ngân hàng CLB (`bank`)** | - Model: [`BankAccount`](../../../lib/models/club.dart#L122) (`id`, `clubId`, `userId`, `bankCode`, `accountNumber`, `accountName`, `status`)<br>- Provider: [`ClubProvider._currentBankAccount`](../../../lib/providers/club_provider.dart#L112)<br>- UI: [`ClubsScreen._showConfigureBankDialog`](../../../lib/screens/clubs_screen.dart#L472)<br>- Scope: `bank`, Distinctive: `false` (10 chữ số) | **CHƯA ĐO ĐÚNG (NOT RUN)**.<br>Chuỗi 10 số va chạm với phần đuôi của UUID fixture (`...-000000000007`), do đó bị hạ cấp xuống `distinctive: false` và không được gate. Ngoài ra luồng `openOwnerFinance` chưa mở màn hình ngân hàng CLB. | Cần thiết lập fixture STK có độ dài và ký tự đặc thù không trùng khớp ngẫu nhiên với UUID; kịch bản runner phải click mở màn hình Quản lý Ngân hàng của CLB. |
| **Tên chủ tài khoản nhận tiền (`receiver`)** | - Model: [`BankAccount.accountName`](../../../lib/models/club.dart#L122) / [`PaymentInstructions.receiverSnapshot`](../../../lib/models/finance.dart#L34)<br>- Provider: [`ClubProvider._currentBankAccount`](../../../lib/providers/club_provider.dart#L112) / [`FinanceProvider._instructions`](../../../lib/providers/finance_provider.dart#L101)<br>- UI: [`ClubsScreen`](../../../lib/screens/clubs_screen.dart#L913) / Payment QR<br>- Scope: `bank`, Distinctive: `true` | **CHƯA ĐO (NOT RUN)**.<br>Runner có khai báo sentinel nhưng `occurrences: 0` ngay từ `owner_active` vì luồng UI không truy cập màn hình ngân hàng hay mã QR của Owner. | Kịch bản runner cần duyệt qua màn hình ngân hàng để `receiver` thực sự được nạp vào RAM ở `owner_active`. |
| **Chỉ dẫn thanh toán & QR (`payment_instructions`)** | - Model: [`PaymentInstructions`](../../../lib/models/finance.dart#L34) (`sessionId`, `playerId`, `displayName`, `billingState`, `activeRevisionId`, `sourceVersion`, `amountDueVnd`, `totalPaidVnd`, `outstandingVnd`, `reference`, `receiverSnapshot`, `hasReceiver`, `canPay`)<br>- Provider: [`FinanceProvider._instructions`](../../../lib/providers/finance_provider.dart#L101)<br>- UI: [`SessionFinanceScreen`](../../../lib/screens/session_finance_screen.dart#L458) (chế độ xem Player)<br>- Scope: `finance`, Distinctive: `true` | **CHƯA ĐO TRONG APP HEAP (NOT RUN)**.<br>Chỉ mới xác minh trên mock Provider test. Màn hình quét mã QR của người chơi chưa được chạy trong kịch bản CDP. | Bổ sung kịch bản actor Người chơi bấm xem QR thanh toán, lấy `reference` hoặc `activeRevisionId` làm sentinel đo heap. |

### 2.4. Nhóm Sổ Quỹ & Tổng kết Tài chính (`ledger` & `summary`)

| Thực thể | Chi tiết Kỹ thuật | Trạng thái Hiện tại | Yêu cầu để Nghiệm thu Đầy đủ |
| :--- | :--- | :--- | :--- |
| **Sổ quỹ CLB (`club_ledger`)** | - Model: [`ClubLedger`](../../../lib/models/finance.dart#L447), [`ClubLedgerEntry`](../../../lib/models/finance.dart#L402)<br>- Provider: [`FinanceProvider._ledger`](../../../lib/providers/finance_provider.dart)<br>- UI: [`ClubFundScreen`](../../../lib/screens/club_fund_screen.dart#L179)<br>- Scope: `finance`, Distinctive: `true` | **CHƯA ĐO TRONG APP HEAP (NOT RUN)**.<br>Màn hình Quỹ CLB (`ClubFundScreen`) chưa từng được kích hoạt trong `run_app_profile_heap.js`. | Cần thêm bước Owner vào tab CLB -> Quỹ CLB, nạp `ClubLedger`, chọn `transactionId` làm sentinel để đo retention sau logout. |
| **Tổng kết số tiền buổi (`session_summary`)** | - Model: [`SessionSummary`](../../../lib/models/finance.dart#L98) (`expensesTotalVnd`, `amountDueTotalVnd`, `totalPaidVnd`, `outstandingTotalVnd`)<br>- Provider: [`FinanceProvider._summary`](../../../lib/providers/finance_provider.dart)<br>- UI: [`SessionSummaryScreen`](../../../lib/screens/session_summary_screen.dart#L58)<br>- Scope: `finance` | **MÀN HÌNH ĐÃ DUYỆT NHƯNG CHƯA GATE SENTINEL**.<br>Màn hình đã được mở trong `openOwnerFinance`, nhưng các trường là số tiền (`int`), không thể tìm kiếm theo chuỗi phân biệt trong string table của heap snapshot. | Khối dữ liệu này chia sẻ chung vòng đời với `_finance` và `_summary`. Việc `_summary` reset về `null` đã kiểm chứng ở Provider test, nhưng heap V8 chưa có chuỗi định danh riêng cho summary. |

### 2.5. Nhóm Danh tính & Bộ lắng nghe Sự kiện (`identity` & `listeners`)

| Thực thể | Chi tiết Kỹ thuật | Trạng thái Hiện tại | Yêu cầu để Nghiệm thu Đầy đủ |
| :--- | :--- | :--- | :--- |
| **Danh tính thành viên CLB (`roster_identities`)** | - Model: [`SessionPlayer.id`](../../../lib/models/session.dart#L237) (`player_a`, `player_b`)<br>- Provider: [`SessionProvider`](../../../lib/providers/session_provider.dart)<br>- UI: [`SessionDetailScreen`](../../../lib/screens/session_detail_screen.dart)<br>- Scope: `identity`, Distinctive: `true` | **ĐÃ BÁO CÁO DẠNG NOTE**.<br>Biến mất ở `post_logout` và `post_member`; còn reachable ở `post_cohost` (path len 18). Phép đo bộ nhớ không thể khẳng định Cohost có quyền fetch lại hay không. | Cần kiểm tra quyền (Authorization/RLS) độc lập bằng HTTP/API test ở tầng backend (đã đạt ở BH-06), không dùng heap snapshot để kết luận quyền. |
| **Bộ lắng nghe Auth (`auth_listeners`)** | - Lớp: `addListener(_onAuthChanged)` trong `FinanceProvider`, `ClubProvider`, `SessionProvider`<br>- Quản lý generation & serial | **CHƯA ĐO TRÊN WEB HEAP OBJECT GRAPH (NOT RUN)**.<br>AST audit xác nhận 0 static mutable collection và Provider unit test kiểm tra `removeListener`, nhưng **Web profile heap object graph của active listener nodes CHƯA ĐƯỢC ĐO**. Không nhận AST zero-static là bằng chứng heap sạch. | Cần probe bộ nhớ đối tượng (object retention graph) trên heap runtime để xác minh không còn listener closure trỏ giữ model sau sign-out. |

---

## 3. Tổng kết Phân loại Khoảng trống (GAP Summary)

Dựa trên mở rộng đo thực tế và phân tích DTO:
- **Tổng số thực thể theo dõi:** 11.
- **Đã xác minh sạch trên Web Profile Heap:** 2 (`expense_id`, `payment_id`).
- **Residual Risk giữ unattributed (Web engine `segmentationCache`):** 2 (`expense_titles`, `payment_ref`).
- **Phân định ranh giới DTO / Roster (chưa có trường tài chính riêng biệt):** 1 (`charges`).
- **Chưa đo trong App Heap (NOT RUN):** 4 (`bank`, `receiver`, `payment_instructions`, `ledger`).
- **Màn hình đã mở nhưng chưa có Sentinel thích hợp:** 1 (`session_summary`).
- **Dữ liệu danh tính báo cáo dạng Note:** 1 (`roster_identities`).
- **Bộ lắng nghe Auth trên Web heap object graph:** 1 (`auth_listeners` - NOT RUN).
- **Đánh giá chung:** Toàn bộ V2b §4.4 **CHƯA ĐỦ ĐIỀU KIỆN NGHIỆM THU**. Giữ nguyên NOT RUN cho các thực thể còn lại và Dart VM desktop/mobile.

## 4. Lộ trình Kỹ thuật Đề xuất để Đóng Hoàn toàn V2b §4.4

Để tiếp tục thu hẹp khoảng cách và tiến tới nghiệm thu toàn diện V2b §4.4:
1. **Mở rộng kịch bản `run_app_profile_heap.js`** để duyệt qua:
   - Màn hình Quỹ CLB (`ClubFundScreen` -> nạp `ClubLedger`).
   - Màn hình Cấu hình Ngân hàng CLB (`ClubsScreen` -> nạp `BankAccount`).
   - Màn hình Chỉ dẫn Thanh toán QR (`PaymentInstructions`).
2. **Bổ sung Sentinel độc nhất cho từng thực thể mới**:
   - `transaction_id` (UUID của sổ quỹ).
   - `bank_account_custom` (chuỗi số kèm tiền tố chữ, ví dụ `STK-9999888877`).
   - `payment_instructions_ref` (mã tham chiếu hướng dẫn thanh toán).
3. **Đo heap trên Dart VM (desktop hoặc mobile)**:
   - Dựng môi trường có Dart VM service kết nối qua DevTools Memory Profiler trên Windows desktop hoặc Android emulator để đối chiếu hành vi retention mà không bị ảnh hưởng bởi `segmentationCache` của web engine.
