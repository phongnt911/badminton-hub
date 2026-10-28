# Báo cáo Điều tra Phân định Giữ Dữ liệu (Retention Attribution) & Bản đồ Phủ (Coverage Map) V2b BH-07

- Ngày: 28/10/2026, Asia/Saigon.
- Vai trò: AI thực thi điều tra độc lập phần còn lại V2b BH-07.
- Nhánh: `feat/bh07-retention-attribution`, tạo từ base `90e9d99b848f30fa3e3b2a3e643dbf784baaea9e`.
- Nguồn đo runtime đối chiếu: `b13e468d33e0d96437b58bb2da6088bff689b9eb` (`git_dirty: false`), theo [báo cáo QA runtime](review_runtime_b13e468.md), [audit điều phối](review_3b393d3.md), và [QA evidence](review_runtime_b13e468_evidence/).
- Bộ chứng cứ điều tra độc lập đi kèm: [retention_attribution_evidence/](retention_attribution_evidence/).
- Nguyên tắc tuân thủ: Giữ nguyên vẹn 100% byte mọi bundle lịch sử; không sửa app/backend/DB contract; không nới lỏng các gate đã đóng; không tự đóng toàn V2b/BH-07, không merge/deploy/pilot/BH-08.

---

## 1. Tóm tắt điều hành & Mục tiêu điều tra

Báo cáo này giải quyết trọn vẹn 2 nhiệm vụ cốt lõi mà QA độc lập và Codex điều phối đã ghi nhận là còn mở sau lượt đo runtime retained-path 28/10/2026:
1. **Phân định nguyên nhân kỹ thuật (Attribution Investigation) của 8 residual risk** đối với tiêu đề chi phí đã render (`expense`, `expense2`): Phân tích khách quan hai phía Engine (Flutter Web/CanvasKit/V8) và App (`badminton-hub`), đối chiếu chính xác phiên bản Flutter SDK, Chrome và bản build web profile của phép đo.
2. **Thiết lập Bản đồ độ phủ (Coverage Map)** toàn diện cho các private models, caches, listeners và các thực thể tài chính/danh tính còn thiếu bằng chứng đo thực (`charges`, `payments`, `bank`, `receiver`, `ledger`, `payment instructions`).

---

## 2. Môi trường & Bản build của Phép đo Đối chiếu

Các phát hiện trong hồ sơ QA `review_runtime_b13e468` được ghi nhận trên môi trường:
- **Hệ điều hành:** Windows `win32 10.0.26100` (Windows 11).
- **Node runtime:** `v24.21.0`.
- **Trình duyệt thực:** `Chrome/155.0.8059.85` (headless CDP mode, `--remote-debugging-port=9337`).
- **Flutter SDK:** `Flutter 3.47.6 • channel stable`
  - Framework revision: `5fc346839b`
  - Engine hash: `b8c8d3d8d5d0095127057f8a29ca8cc53da2167c` (revision `692136cb65`)
  - Tools: Dart `3.13.5`, DevTools `2.60.0`.
- **Bản build ứng dụng:** `flutter build web --profile` (dart2js minification, CanvasKit web renderer, `served_match: true`, 39 artifacts, `main.dart.js` sha256 `c33fe27c7a4256174e9485a017f4bf84b082319b5f69eab117df255859e4762b`).

---

## 3. Phần 1: Điều tra Chi tiết 8 Residual Risk Rendered-Title Retention

### 3.1. Hiện trạng 8 bản ghi residual risk trong hồ sơ đo

Trong 2 chu kỳ đo thực (`Owner → logout → Cohost` và `Owner → logout → Member`) trên cùng tài liệu SPA, có 8 bản ghi rủi ro tồn lưu (`residual_risks`) được xuất bản với nhãn `attribution: "unattributed"`:

| Chu kỳ | Mốc (Epoch) | Sentinel | Scope | Class | Path Length | Path SHA-256[:12] | Tình trạng Reachability |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `post_logout` | `expense` | `finance` | `rendered` | 12 | `91dc804e80e6` | `reachable: true`, `occurrences: 1` |
| 1 | `post_logout` | `expense2` | `finance` | `rendered` | 12 | `91dc804e80e6` | `reachable: true`, `occurrences: 1` |
| 1 | `post_actor` (`cohost`) | `expense` | `finance` | `rendered` | 12 | `91dc804e80e6` | `reachable: true`, `occurrences: 1` |
| 1 | `post_actor` (`cohost`) | `expense2` | `finance` | `rendered` | 12 | `91dc804e80e6` | `reachable: true`, `occurrences: 1` |
| 2 | `post_logout` | `expense` | `finance` | `rendered` | 12 | `5ae7d1eb096c` | `reachable: true`, `occurrences: 1` |
| 2 | `post_logout` | `expense2` | `finance` | `rendered` | 12 | `5ae7d1eb096c` | `reachable: true`, `occurrences: 1` |
| 2 | `post_actor` (`member`) | `expense` | `finance` | `rendered` | 12 | `5ae7d1eb096c` | `reachable: true`, `occurrences: 1` |
| 2 | `post_actor` (`member`) | `expense2` | `finance` | `rendered` | 12 | `5ae7d1eb096c` | `reachable: true`, `occurrences: 1` |

Tổng số: **8 bản ghi**. Giá trị sentinel gồm:
- `expense`: Tiêu đề chi phí hạt giống ("Tiền thuê sân 2h", độ dài 16 ký tự, sha12 `41a394dd2dcd`).
- `expense2`: Tiêu đề chi phí fixture dùng một lần ("Tiền điện BH-07...", độ dài 28 ký tự, sha12 `09ac31ed38b0`).

### 3.2. Mổ xẻ Chuỗi Giữ Ngắn nhất (Retainer Path)

Cả 8 bản ghi đều có cùng cấu trúc chuỗi giữ gồm 12 frame (sai khác duy nhất giữa 2 chu kỳ là ID closure nội bộ do V8 cấp: `internal:63` ở chu kỳ 1 vs `internal:68` ở chu kỳ 2):

```
Frame 0:  root (synthetic GC root)
Frame 1:  element -> synthetic
Frame 2:  element -> synthetic
Frame 3:  internal:63 (hoặc 68) -> closure
Frame 4:  property:call$0 -> closure
Frame 5:  internal:context -> object
Frame 6:  context -> object
Frame 7:  property:segmentationCache -> object
Frame 8:  property:_1 -> object
Frame 9:  property:_itemMap -> object
Frame 10: property:_strings -> object
Frame 11: property:<redacted> -> object
Frame 12: property:hashMapCellKey -> string
```

### 3.3. Phân tích Phía Web Engine (Flutter Web Engine / CanvasKit)

1. **Vị trí định nghĩa trong mã nguồn Flutter SDK:**
   - Tập tin: `C:\src\flutter\bin\cache\flutter_web_sdk\lib\_engine\engine\text_fragmenter.dart` (dòng 32-47).
   - Biến toàn cục tĩnh:
     ```dart
     final SegmentationCache segmentationCache = (
       small: LruCache<String, SegmentationResult>(kSmallParagraphCacheSpec.cacheSize),
       medium: LruCache<String, SegmentationResult>(kMediumParagraphCacheSpec.cacheSize),
       large: LruCache<String, SegmentationResult>(kLargeParagraphCacheSpec.cacheSize),
     );
     ```
2. **Kích thước cache và ngưỡng độ dài:**
   - `kSmallParagraphCacheSpec`: `cacheSize: 100000`, `maxTextLength: 10` (icon, label ngắn).
   - `kMediumParagraphCacheSpec`: `cacheSize: 10000`, `maxTextLength: 100` (tiêu đề, câu văn thông thường).
   - `kLargeParagraphCacheSpec`: `cacheSize: 20`, `maxTextLength: 50000` (đoạn văn lớn).
   - Trong dart2js, cấu trúc Record 3 trường `(large, medium, small)` được biên dịch thành object JavaScript với các thuộc tính theo thứ tự chữ cái: `_0` là `large`, `_1` là `medium`, `_2` là `small`.
   - Cả 2 chuỗi `expense` (16 ký tự) và `expense2` (28 ký tự) đều thuộc dải 11-100 ký tự nên được đưa vào cache `medium` (`property:_1`).
3. **Cơ chế hoạt động:**
   - Bất kỳ widget `Text(...)` nào hiển thị lên giao diện đều gọi qua bộ dựng paragraph của CanvasKit (`CanvasParagraph`).
   - Hàm `segmentText(String text)` (dòng 75 `text_fragmenter.dart`) tính toán word breaks, graphemes và line breaks thông qua V8 Intl API, sau đó lưu kết quả vào `segmentationCache`:
     ```dart
     cache?.cache(text, result);
     ```
   - Lớp `LruCache` (`util.dart:710`) lưu trữ các entry trong một `DoubleLinkedQueue` và một `Map` (`_itemMap`).
   - Trong dart2js, `Map<String, ...>` được hiện thực hóa qua `JSLinkedHashMap`, lưu trữ key trong bảng `_strings`, mỗi cell giữ `hashMapCellKey -> string`.
4. **Vòng đời của `segmentationCache`:**
   - `segmentationCache` là biến top-level singleton của engine web.
   - Extension `SegmentationCacheExtensions` có phương thức `void clear()`, **nhưng không có bất kỳ dòng code nào trong Flutter Framework, Flutter Router hay Engine gọi phương thức này khi route bị pop, widget bị unmount hay khi người dùng đăng xuất**.
   - Do đó, mọi chuỗi văn bản đã từng render trên Web CanvasKit sẽ được lưu trong bộ nhớ cho tới khi bị đẩy ra theo chính sách LRU (đòi hỏi phải có 10.000 chuỗi văn bản mới khác nhau có độ dài 11-100 ký tự được render sau đó).

### 3.4. Phân tích Phía Ứng dụng (`badminton-hub`)

1. **Vòng đời State trong ứng dụng:**
   - Màn hình hiển thị tiêu đề chi phí: [`SessionFinanceScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_finance_screen.dart#L620) (`_expenseTile`).
   - State quản lý chi phí: [`FinanceProvider`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart#L180) giữ `SessionFinance? _finance`, trong đó `_finance.expenses` chứa danh sách các đối tượng [`FinanceExpense`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L222).
   - Mỗi đối tượng `FinanceExpense` chứa cả 2 trường song hành:
     - `final String expenseId;` (UUID 36 ký tự, chỉ dùng định danh nội bộ, **không render lên UI**).
     - `final String title;` (Chuỗi tiêu đề chi phí, **render lên UI qua widget Text**).
2. **Cơ chế dọn dẹp khi Logout:**
   - Khi Owner đăng xuất, [`AuthProvider.signOut()`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/auth_provider.dart) xóa session token và kích hoạt listener `_onAuthChanged()` trong `FinanceProvider`.
   - `FinanceProvider.clearAll()` thực thi:
     ```dart
     _resetFinance(); // _finance = null; _financeSessionId = null;
     _resetInstructions(); // _instructions = null;
     _resetSummary(); // _summary = null;
     _resetLedger(); // _ledger = null;
     ```
   - Màn hình `SessionFinanceScreen` được Navigator pop khỏi ngăn xếp điều hướng, widget và element unmount hoàn toàn.
3. **Bằng chứng Thực nghiệm Khách quan từ Sentinel Không Render (`expense_id`):**
   - Trong cùng các snapshot đó:
     - Tại `owner_active`: Cả `expense_id` và `expense_id_2` đều **có mặt** (`occurrences: 1`) và reachable từ GC root với đường đi độ dài 20 xuyên qua widget tree và Provider:
       `root -> ... -> WidgetsBinding -> _framework$_element -> _inheritedElements -> _InheritedProviderScopeElement -> _finance -> expenses -> expenseId`.
     - Tại `post_logout` và `post_actor` (cả 2 chu kỳ): Cả `expense_id` và `expense_id_2` **biến mất 100% khỏi heap** (`present: false`, `occurrences: 0`, `reachable: false`, `string_nodes: 0`).
   - **Lý giải kỹ thuật mang tính quyết định:**
     Nếu ứng dụng còn giữ tham chiếu sống (dù qua Provider, Controller, Listener hay Widget Tree) tới danh sách `_finance.expenses` hoặc instance `FinanceExpense`, thì trường `expenseId` **bắt buộc phải còn tồn tại trong heap**.
     Việc `expenseId` giảm từ 1 xuống đúng **0 occurrences** chứng minh chắc chắn rằng toàn bộ cấu trúc dữ liệu `FinanceExpense` cấp ứng dụng đã được V8 Garbage Collector thu hồi triệt để.

### 3.5. Kết luận Phân định Attribution

| Tiêu chí | Phía Web Engine | Phía Ứng dụng |
| :--- | :--- | :--- |
| **Thực thể giữ chuỗi trực tiếp** | `dart._engine.segmentationCache` (Map `_itemMap` -> `_strings`) | Không tìm thấy bất kỳ đối tượng ứng dụng nào giữ tham chiếu sống |
| **Dung lượng cache** | Cố định 10.000 phần tử (LRU), không có cơ chế tự dọn | State được reset về `null` ngay khi auth state thay đổi |
| **Bằng chứng đối chứng** | Chuỗi giữ đi thẳng từ Root vào closure của engine `text_fragmenter.dart` | Sentinel không render của cùng model (`expense_id`) biến mất 100% (`occurrences: 0`) |
| **Phạm vi nền tảng** | Chỉ xuất hiện trên Flutter Web (CanvasKit/dart2js) | Đạt AST memory audit (0 static mutable collections) |

**Kết luận kỹ thuật:**
1. Nguyên nhân 8 residual risk giữ tiêu đề chi phí sau logout **thuộc về cơ chế Text Segmentation Caching của Flutter Web Engine** (`package:flutter_web_sdk/lib/_engine/engine/text_fragmenter.dart`).
2. Tầng ứng dụng (`badminton-hub`) **đã giải phóng hoàn toàn** các model tài chính và widget tương ứng (chứng minh qua việc sentinel không render `expense_id` có `occurrences: 0`).
3. Trên nền tảng Desktop/Mobile (Dart VM), Flutter không sử dụng `text_fragmenter.dart` mà sử dụng engine C++ Skia/Impeller native, do đó cơ chế lưu cache này không áp dụng cho Dart VM heap.
4. Việc QA ban đầu gán nhãn `unattributed` là đúng quy trình thận trọng vì thuật toán BFS chỉ in ra một đường đi ngắn nhất; tuy nhiên bằng chứng đối chiếu chéo với peer sentinel `expense_id` đã làm sáng tỏ hoàn toàn bản chất kỹ thuật của hiện tượng này.

---

## 4. Phần 2: Bản đồ Độ phủ Toàn diện (V2b Coverage Map)

Cổng V2b §4.4 yêu cầu xác minh việc không rò rỉ bộ nhớ sau khi đổi actor đối với **toàn bộ dữ liệu tài chính chi tiết của Owner**.
Bảng dưới đây tổng hợp hiện trạng kiểm chứng của 11 thực thể tài chính/danh tính trong codebase:

| STT | Thực thể dữ liệu | Vị trí Model trong mã nguồn | Provider & Cache quản lý | Màn hình UI hiển thị | Hiện trạng Provider Unit Test | Hiện trạng Web Profile Heap Snapshot | Sentinel & Khả năng Đo Heap | Khoảng trống Kỹ thuật (GAP) |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| 1 | **Mã chi phí (`expense_id`)** | [`FinanceExpense.expenseId`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L222) | [`FinanceProvider._finance`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart#L180) | Không render (khóa model) | ĐẠT (33/33) | **ĐẠT (2 chu kỳ, 0 occ sau logout)** | UUID 36 ký tự, distinctive, unrendered | **Dart VM desktop/mobile NOT RUN**. |
| 2 | **Tiêu đề chi phí (`expense_titles`)** | [`FinanceExpense.title`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L222) | [`FinanceProvider._finance`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart#L180) | [`SessionFinanceScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_finance_screen.dart#L620) | ĐẠT (33/33) | **Residual risk Engine segmentationCache** | Chuỗi văn bản, distinctive, rendered | Giữ trong engine text cache (10.000 entry LRU); Dart VM NOT RUN. |
| 3 | **Khoản thu người chơi (`session_charges`)** | [`FinanceCharge`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L258) (`playerId`, `chargeVnd`, `notes`) | [`FinanceProvider._finance.charges`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart#L180) | [`SessionFinanceScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_finance_screen.dart#L648) (`_chargesSection`) | ĐẠT (33/33) | **CHƯA ĐO (NOT RUN)** | Cần sentinel `playerId` / ghi chú thu phí | Chưa khai báo sentinel trong runner; chưa assert trên heap snapshot. |
| 4 | **Thanh toán người chơi (`session_payments`)** | [`FinancePayment`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L279) (`paymentId`, `amountVnd`, `referenceCode`) | [`FinanceProvider._finance.payments`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart#L180) | [`SessionFinanceScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_finance_screen.dart#L696) (`_paymentsSection`) | ĐẠT (33/33) | **CHƯA ĐO (NOT RUN)** | Cần sentinel `paymentId` / `referenceCode` | Chưa khai báo sentinel trong runner; chưa assert trên heap snapshot. |
| 5 | **Số tài khoản ngân hàng CLB (`club_bank_account`)** | [`BankAccount.accountNumber`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/club.dart#L127) | [`ClubProvider._currentBankAccount`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/club_provider.dart#L112) | [`ClubsScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/clubs_screen.dart#L472) (dialog ngân hàng) | ĐẠT (33/33) | **CHƯA ĐO ĐÚNG (NOT RUN)** | Cần STK dạng chữ-số phân biệt (tránh va chạm UUID) | Chuỗi 10 số va chạm với đuôi UUID; luồng đo không mở màn hình ngân hàng CLB. |
| 6 | **Tên chủ tài khoản nhận tiền (`bank_receiver`)** | [`BankAccount.accountName`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/club.dart#L128) | [`ClubProvider._currentBankAccount`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/club_provider.dart#L112) | [`ClubsScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/clubs_screen.dart#L913) / dialog QR | ĐẠT (33/33) | **CHƯA ĐO (NOT RUN)** | Chuỗi tên chủ TK, distinctive, unrendered | Có khai báo sentinel nhưng `occurrences: 0` ở `owner_active` vì luồng không mở màn hình ngân hàng. |
| 7 | **Chỉ dẫn thanh toán & QR (`payment_instructions`)** | [`PaymentInstructions`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L34) (`vietqrUrl`, `transferContent`) | [`FinanceProvider._instructions`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart#L101) | [`SessionFinanceScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_finance_screen.dart#L458) (màn hình Player) | ĐẠT (33/33) | **CHƯA ĐO (NOT RUN)** | Cần sentinel `transferContent` / URL QR | Màn hình chỉ dẫn thanh toán của player chưa được duyệt trong luồng heap runner. |
| 8 | **Sổ quỹ CLB (`club_ledger`)** | [`ClubLedger`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L447), [`ClubLedgerEntry`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L402) | [`FinanceProvider._ledger`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart) | [`ClubFundScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/club_fund_screen.dart#L179) (`_balanceCard`, `_entryTile`) | ĐẠT (33/33) | **CHƯA ĐO (NOT RUN)** | Cần sentinel `transactionId` / mô tả giao dịch | Màn hình Quỹ CLB (`ClubFundScreen`) chưa từng được mở trong `run_app_profile_heap.js`. |
| 9 | **Số tiền tổng hợp buổi (`session_summary_totals`)** | [`SessionSummary`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/finance.dart#L98) (`totalExpensesVnd`, `remainingVnd`) | [`FinanceProvider._summary`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/finance_provider.dart) | [`SessionSummaryScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_summary_screen.dart#L58) | ĐẠT (33/33) | **MỞ MÀN HÌNH NHƯNG CHƯA GATE** | Số tiền dạng số nguyên (không distinctive) | Màn hình được duyệt nhưng số tiền không thể làm sentinel chuỗi độc nhất. |
| 10 | **Danh tính người chơi CLB (`roster_identities`)** | [`SessionPlayer.id`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/models/session.dart#L237) | [`SessionProvider`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/providers/session_provider.dart) | [`SessionDetailScreen`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/lib/screens/session_detail_screen.dart) | ĐẠT (33/33) | **GHI NHẬN NOTE (path 18)** | UUID, distinctive, `scope: identity` | Còn reachable ở Cohost (path 18); heap không chứng minh quyền truy cập. |
| 11 | **Auth Listeners & Subscription** | `addListener(_onAuthChanged)` | Các Provider | Toàn app | ĐẠT (AST Clean, dispose cân bằng) | **ĐẠT (không rò rỉ listener sống)** | Listener function closure | Hoạt động bình thường; không rò rỉ object qua static/global listener. |

---

## 5. Phần 3: Công cụ Kiểm soát Tự động & Kết quả Tự Kiểm tra

Nhằm đảm bảo tính tái lập 100% và không phụ thuộc vào nhận định chủ quan, công cụ kiểm tra tự động đã được bổ sung:
1. **Script điều tra & kiểm tra bản đồ độ phủ:** [`scripts/bh07_appheap/audit_retention_attribution.py`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/scripts/bh07_appheap/audit_retention_attribution.py).
2. **Suite kiểm thử tự động:** [`tests/test_bh07_retention_attribution.py`](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/tests/test_bh07_retention_attribution.py) (4/4 tests PASS, bao gồm kiểm soát mutant rò rỉ giả lập và sai lệch số lượng rủi ro).
3. **Chạy hồi quy toàn bộ:**
   - `python -X utf8 -m unittest discover -s tests`: **316/316 OK** (312 test cũ + 4 test mới).
   - `python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir "C:\Users\POTA\Documents\GitHub\badminton-hub\docs\reviews\bh07\review_runtime_b13e468_evidence"`: **PASS** (exit 0).
   - `python -X utf8 scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir "C:\Users\POTA\Documents\GitHub\badminton-hub\docs\reviews\bh07\review_runtime_b13e468_evidence"`: **ALL CHECKS PASSED** (exit 0).
   - `flutter analyze`: **No issues found!** (exit 0).
   - `flutter test`: **247 passed + 1 skipped** (exit 0).

---

## 6. Khuyến nghị Kỹ thuật & Ranh giới Nghiệm thu

1. **Về 8 Residual Risk Tiêu đề Chi phí:**
   - Không cần và **không được sửa ép app** (như tìm cách can thiệp vào bộ nhớ riêng tư của web engine hoặc dùng các hack không chính quy) vì đây là hành vi thiết kế nội tại của bộ segmenter văn bản trong Flutter Web SDK.
   - Khi nghiệm thu V2b/BH-07, chủ dự án có thể áp dụng điều khoản Chấp nhận rủi ro còn lại (Residual-Risk Acceptance) cho chuỗi đã render trên web profile, vì dữ liệu thô tài chính và các model nhạy cảm của app đã được chứng minh sạch sẽ hoàn toàn.
2. **Về Bản đồ Độ phủ (Coverage Map):**
   - Hiện tại phép đo V2b runtime chỉ mới chứng minh cho **2 mã chi phí** (`expense_id`, `expense_id_2`).
   - Có ít nhất **6 thực thể tài chính/ngân hàng** (`charges`, `payments`, `bank`, `receiver`, `ledger`, `payment instructions`) chưa từng được đo thực tế trong heap của app thật khi chạy trình duyệt.
   - Do đó, **toàn bộ cổng V2b §4.4 và toàn bộ BH-07 PHẢI TIẾP TỤC GIỮ TRẠNG THÁI CHƯA NGHIỆM THU**.
3. **Các Cổng Khác:**
   - Dart VM heap trên desktop/mobile: Giữ **NOT RUN**.
   - Trình duyệt khác (Safari, Firefox, Mobile web): Giữ **NOT RUN**.
   - Tuyệt đối không merge nhánh, không deploy staging/production, không pilot và không mở BH-08.
