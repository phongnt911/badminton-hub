# Báo cáo Điều tra Phân định Giữ Dữ liệu (Retention Attribution) & Bản đồ Phủ (Coverage Map) V2b BH-07

- Ngày: 28/10/2026, Asia/Saigon.
- Vai trò: AI thực thi điều tra độc lập phần còn lại V2b BH-07.
- Nhánh: `feat/bh07-retention-attribution`, base `dcdb7ce51095d03afbbb7f28e4bbb5117f8a3e48`.
- Nguồn đo runtime đối chiếu: `b13e468d33e0d96437b58bb2da6088bff689b9eb` (`git_dirty: false`), theo [báo cáo QA runtime](review_runtime_b13e468.md), [audit điều phối](review_3b393d3.md), và [QA evidence](review_runtime_b13e468_evidence/).
- Bộ chứng cứ điều tra độc lập đi kèm: [retention_attribution_evidence/](retention_attribution_evidence/).
- Nguyên tắc tuân thủ: Giữ nguyên vẹn 100% byte mọi bundle lịch sử; không sửa app/backend/DB contract; không nới lỏng các gate đã đóng; không tự đóng toàn V2b/BH-07, không merge/deploy/pilot/BH-08.

---

## 1. Tóm tắt điều hành & Mục tiêu điều tra

Báo cáo này giải quyết trọn vẹn 2 nhiệm vụ cốt lõi mà QA độc lập và Codex điều phối đã ghi nhận là còn mở sau lượt đo runtime retained-path 28/10/2026:
1. **Phân định nguyên nhân kỹ thuật (Attribution Investigation) của 8 residual risk** đối với tiêu đề chi phí đã render (`expense`, `expense2`): Phân tích khách quan hai phía Engine (Flutter Web/CanvasKit/V8) và App (`badminton-hub`), đối chiếu chính xác phiên bản Flutter SDK, Chrome và bản build web profile của phép đo. Phân tách rõ ràng giữa quan sát thực nghiệm (observed), giả thuyết có bằng chứng hỗ trợ (supported hypothesis) và các giới hạn kỹ thuật chưa được chứng minh (unknown/limits).
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

Tổng số: **8 bản ghi**. Các sentinel đã được sanitize theo đúng chính sách:
- `expense`: Tiêu đề chi phí hạt giống (độ dài 16 ký tự, sha256_12 `41a394dd2dcd`, class `rendered`).
- `expense2`: Tiêu đề chi phí fixture dùng một lần (độ dài 28 ký tự, sha256_12 `09ac31ed38b0`, class `rendered`).

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
   - Tập tin: `flutter_web_sdk/lib/_engine/engine/text_fragmenter.dart` (dòng 32-47).
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
   - Màn hình hiển thị tiêu đề chi phí: [`SessionFinanceScreen`](../../../lib/screens/session_finance_screen.dart#L620) (`_expenseTile`).
   - State quản lý chi phí: [`FinanceProvider`](../../../lib/providers/finance_provider.dart#L180) giữ `SessionFinance? _finance`, trong đó `_finance.expenses` chứa danh sách các đối tượng [`FinanceExpense`](../../../lib/models/finance.dart#L222).
   - Mỗi đối tượng `FinanceExpense` chứa các trường:
     - `final String expenseId;` (UUID 36 ký tự, chỉ dùng định danh nội bộ, **không render lên UI**).
     - `final String title;` (Chuỗi tiêu đề chi phí, **render lên UI qua widget Text**).
2. **Cơ chế dọn dẹp khi Logout:**
   - Khi Owner đăng xuất, [`AuthProvider.signOut()`](../../../lib/providers/auth_provider.dart) xóa session token và kích hoạt listener `_onAuthChanged()` trong `FinanceProvider`.
   - `FinanceProvider.clearAll()` thực thi:
     ```dart
     _resetFinance(); // _finance = null; _financeSessionId = null;
     _resetInstructions(); // _instructions = null;
     _resetSummary(); // _summary = null;
     _resetLedger(); // _ledger = null;
     ```
   - Màn hình `SessionFinanceScreen` được Navigator pop khỏi ngăn xếp điều hướng, widget và element unmount.
3. **Bằng chứng Thực nghiệm Khách quan từ Sentinel Không Render (`expense_id`):**
   - Trong cùng các snapshot đó:
     - Tại `owner_active`: Cả `expense_id` và `expense_id_2` đều **có mặt** (`occurrences: 1`) và reachable từ GC root với đường đi độ dài 20 xuyên qua widget tree và Provider:
       `root -> ... -> WidgetsBinding -> _framework$_element -> _inheritedElements -> _InheritedProviderScopeElement -> _finance -> expenses -> expenseId`.
     - Tại `post_logout` và `post_actor` (cả 2 chu kỳ): Cả `expense_id` và `expense_id_2` **biến mất 100% khỏi heap** (`present: false`, `occurrences: 0`, `reachable: false`, `string_nodes: 0`).

### 3.5. Kết luận Phân định Attribution (Tách bạch Observed, Hypothesis, Limits)

Nhằm bảo đảm tính khách quan và tuân thủ tuyệt đối [review_37b4954](review_37b4954.md) và [review_eda1ead](review_eda1ead.md), kết luận phân định được chia thành 3 bình diện rõ ràng:

#### A. Quan sát Thực nghiệm (Observed)
1. **Retainer path trong V8 heap snapshot:** Đường dẫn giữ ngắn nhất (BFS) dẫn thẳng từ GC root qua closure của engine đến `dart._engine.segmentationCache._itemMap._strings` ở cả 8 bản ghi (2 chu kỳ × 2 mốc × 2 tiêu đề).
2. **Hành vi của sentinel không render:** 2 mã chi phí (`expense_id`, `expense_id_2`) có `occurrences: 1` ở `owner_active` và giảm về `occurrences: 0`, `reachable: false` sau khi logout và sau khi đổi actor ở cả 2 chu kỳ.

#### B. Giả thuyết có Bằng chứng Hỗ trợ (Supported Hypothesis)
1. Cấu trúc frame (`segmentationCache`, `_itemMap`, `_strings`) hoàn toàn khớp với cơ chế LRU cache 10.000 mục được định nghĩa trong mã nguồn `flutter_web_sdk/lib/_engine/engine/text_fragmenter.dart:43`.
2. Việc unrendered model key (`expense_id`) biến mất hỗ trợ cho giả thuyết rằng instance `FinanceExpense` trong Provider đã được GC thu hồi sau khi gọi `clearAll()`.

#### C. Giới hạn Kỹ thuật & Phần Chưa Chứng minh (Unknown & Limits)
1. **Không loại trừ đường dẫn phụ:** Một đường dẫn ngắn nhất BFS trong snapshot V8 không thể chứng minh sự vắng mặt của các đường dẫn giữ khác từ phía ứng dụng (nếu có).
2. **Phạm vi hai expense ID không chứng minh toàn app:** Việc 2 ID chi phí biến mất không chứng minh rằng app không giữ chuỗi ở nơi khác, cũng không chứng minh cho các model tài chính khác (`charges`, `payments`, `bank`, `ledger`); trạng thái giữ bộ nhớ toàn ứng dụng (app-wide retention) vẫn là **UNKNOWN**.
3. **Dart VM desktop/mobile là NOT RUN:** Chưa có phép đo đối chứng trên native Dart VM; không suy diễn rằng heap native không có hiện tượng retention.
4. **Phân loại chính thức:** Theo readiness §4.4 và AGENTS.md, 8 bản ghi này **tiếp tục giữ phân loại chính thức là `unattributed residual risk`**. Toàn bộ V2b/BH-07 **CHƯA NGHIỆM THU**.

---

## 4. Phần 2: Bản đồ Độ phủ Toàn diện (V2b Coverage Map)

Cổng V2b §4.4 yêu cầu xác minh việc không rò rỉ bộ nhớ sau khi đổi actor đối với **toàn bộ dữ liệu tài chính chi tiết của Owner**.
Bảng dưới đây đối chiếu đúng 100% các model, DTO, field hiện hành trong codebase:

| STT | Thực thể dữ liệu | Vị trí Model trong mã nguồn | Provider & Cache quản lý | Màn hình UI hiển thị | Hiện trạng Provider Unit Test | Hiện trạng Web Profile Heap Snapshot | Sentinel & Khả năng Đo Heap | Khoảng trống Kỹ thuật (GAP) |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| 1 | **Mã chi phí (`expense_id`)** | [`FinanceExpense.expenseId`](../../../lib/models/finance.dart#L222) | [`FinanceProvider._finance`](../../../lib/providers/finance_provider.dart#L180) | Không render (khóa model) | ĐẠT (33/33) | **ĐẠT (2 chu kỳ, 0 occ sau logout)** | UUID 36 ký tự, distinctive, unrendered | **Dart VM desktop/mobile NOT RUN**. |
| 2 | **Tiêu đề chi phí (`expense_titles`)** | [`FinanceExpense.title`](../../../lib/models/finance.dart#L222) | [`FinanceProvider._finance`](../../../lib/providers/finance_provider.dart#L180) | [`SessionFinanceScreen`](../../../lib/screens/session_finance_screen.dart#L620) | ĐẠT (33/33) | **Residual risk Engine segmentationCache** | Chuỗi văn bản, distinctive, rendered | Giữ trong engine text cache (10.000 entry LRU); Dart VM NOT RUN. |
| 3 | **Khoản thu người chơi (`session_charges`)** | [`FinanceCharge`](../../../lib/models/finance.dart#L258) (`playerId`, `displayName`, `amountDueVnd`) | [`FinanceProvider._finance.charges`](../../../lib/providers/finance_provider.dart#L180) | [`SessionFinanceScreen`](../../../lib/screens/session_finance_screen.dart#L648) (`_chargesSection`) | ĐẠT (33/33) | **CHƯA ĐO (NOT RUN)** | Cần sentinel `playerId` / dữ liệu thu phí | Chưa khai báo sentinel trong runner; chưa assert trên heap snapshot. |
| 4 | **Thanh toán người chơi (`session_payments`)** | [`FinancePayment`](../../../lib/models/finance.dart#L279) (`paymentId`, `playerId`, `amountVnd`, `method`, `status`, `reference`, `confirmedAt`, `createdAt`) | [`FinanceProvider._finance.payments`](../../../lib/providers/finance_provider.dart#L180) | [`SessionFinanceScreen`](../../../lib/screens/session_finance_screen.dart#L696) (`_paymentsSection`) | ĐẠT (33/33) | **CHƯA ĐO (NOT RUN)** | Cần sentinel `paymentId` / `reference` | Chưa khai báo sentinel trong runner; chưa assert trên heap snapshot. |
| 5 | **Số tài khoản ngân hàng CLB (`club_bank_account`)** | [`BankAccount`](../../../lib/models/club.dart#L122) (`id`, `clubId`, `userId`, `bankCode`, `accountNumber`, `accountName`, `status`) | [`ClubProvider._currentBankAccount`](../../../lib/providers/club_provider.dart#L112) | [`ClubsScreen`](../../../lib/screens/clubs_screen.dart#L472) (dialog ngân hàng) | ĐẠT (33/33) | **CHƯA ĐO ĐÚNG (NOT RUN)** | Cần STK dạng chữ-số phân biệt (tránh va chạm UUID) | Chuỗi 10 số va chạm với đuôi UUID; luồng đo không mở màn hình ngân hàng CLB. |
| 6 | **Tên chủ tài khoản nhận tiền (`bank_receiver`)** | [`BankAccount.accountName`](../../../lib/models/club.dart#L122) / [`PaymentInstructions.receiverSnapshot`](../../../lib/models/finance.dart#L34) | [`ClubProvider._currentBankAccount`](../../../lib/providers/club_provider.dart#L112) / [`FinanceProvider._instructions`](../../../lib/providers/finance_provider.dart#L101) | [`ClubsScreen`](../../../lib/screens/clubs_screen.dart#L913) / dialog QR | ĐẠT (33/33) | **CHƯA ĐO (NOT RUN)** | Chuỗi tên chủ TK, distinctive, unrendered | Có khai báo sentinel nhưng `occurrences: 0` ở `owner_active` vì luồng không mở màn hình ngân hàng. |
| 7 | **Chỉ dẫn thanh toán & QR (`payment_instructions`)** | [`PaymentInstructions`](../../../lib/models/finance.dart#L34) (`sessionId`, `playerId`, `displayName`, `billingState`, `activeRevisionId`, `sourceVersion`, `amountDueVnd`, `totalPaidVnd`, `outstandingVnd`, `reference`, `receiverSnapshot`, `hasReceiver`, `canPay`) | [`FinanceProvider._instructions`](../../../lib/providers/finance_provider.dart#L101) | [`SessionFinanceScreen`](../../../lib/screens/session_finance_screen.dart#L458) (màn hình Player) | ĐẠT (33/33) | **CHƯA ĐO (NOT RUN)** | Cần sentinel `reference` / `activeRevisionId` | Màn hình chỉ dẫn thanh toán của player chưa được duyệt trong luồng heap runner. |
| 8 | **Sổ quỹ CLB (`club_ledger`)** | [`ClubLedger`](../../../lib/models/finance.dart#L447), [`ClubLedgerEntry`](../../../lib/models/finance.dart#L402) | [`FinanceProvider._ledger`](../../../lib/providers/finance_provider.dart) | [`ClubFundScreen`](../../../lib/screens/club_fund_screen.dart#L179) (`_balanceCard`, `_entryTile`) | ĐẠT (33/33) | **CHƯA ĐO (NOT RUN)** | Cần sentinel `transactionId` / mô tả giao dịch | Màn hình Quỹ CLB (`ClubFundScreen`) chưa từng được mở trong `run_app_profile_heap.js`. |
| 9 | **Số tiền tổng hợp buổi (`session_summary_totals`)** | [`SessionSummary`](../../../lib/models/finance.dart#L98) (`expensesTotalVnd`, `amountDueTotalVnd`, `totalPaidVnd`, `outstandingTotalVnd`) | [`FinanceProvider._summary`](../../../lib/providers/finance_provider.dart) | [`SessionSummaryScreen`](../../../lib/screens/session_summary_screen.dart#L58) | ĐẠT (33/33) | **MỞ MÀN HÌNH NHƯNG CHƯA GATE** | Số tiền dạng số nguyên (không distinctive) | Màn hình được duyệt nhưng số tiền không thể làm sentinel chuỗi độc nhất. |
| 10 | **Danh tính người chơi CLB (`roster_identities`)** | [`SessionPlayer.id`](../../../lib/models/session.dart#L237) | [`SessionProvider`](../../../lib/providers/session_provider.dart) | [`SessionDetailScreen`](../../../lib/screens/session_detail_screen.dart) | ĐẠT (33/33) | **GHI NHẬN NOTE (path 18)** | UUID, distinctive, `scope: identity` | Còn reachable ở Cohost (path 18); heap không chứng minh quyền truy cập. |
| 11 | **Auth Listeners & Subscription** | `addListener(_onAuthChanged)` | Các Provider | Toàn app | ĐẠT (AST Clean, dispose cân bằng) | **CHƯA ĐO TRÊN WEB HEAP OBJECT GRAPH (NOT RUN)** | Object graph listener closure | AST zero-static không chứng minh heap sạch; chưa đo object retention graph trên heap. |

---

## 5. Phần 3: Công cụ Kiểm soát Tự động & Kết quả Tự Kiểm tra

Nhằm đảm bảo tính tái lập 100% và không phụ thuộc vào nhận định chủ quan, công cụ kiểm tra tự động đã được cập nhật và kiểm chứng:
1. **Script điều tra & kiểm tra bản đồ độ phủ:** [`scripts/bh07_appheap/audit_retention_attribution.py`](../../../scripts/bh07_appheap/audit_retention_attribution.py) — logic fail-closed, xác thực toàn bộ 8 tổ hợp cycle×epoch×sentinel không trùng/thiếu, kiểm tra rendered paths cho cả 4 mốc của 2 chu kỳ, không mặc định missing count thành 0, trả exit code 1 và nhãn `UNATTRIBUTED` khi điều kiện tiên đề thất bại.
2. **Suite kiểm thử tự động:** [`tests/test_bh07_retention_attribution.py`](../../../tests/test_bh07_retention_attribution.py) (5/5 tests PASS, phát lại đầy đủ các ca probe reviewer cũ và 4 ca mutant `extra_controls.py`, kiểm tra fail-closed exit khác 0, kiểm tra AT2 machine fields không khẳng định toàn app sạch).
3. **Chạy hồi quy toàn bộ:**
   - `python -X utf8 -m unittest discover -s tests`: **317/317 OK**.
   - `python docs/reviews/bh07/review_37b4954_evidence/probes.py`: Cả 3 mutant (`peer_retained`, `wrong_environment`, `missing_rendered_paths`) đều trả **exit 1** và `primary_retainer_component = 'UNATTRIBUTED'`; positive control trả **exit 0**.
   - `python docs/reviews/bh07/review_eda1ead_evidence/extra_controls.py`: Cả 4 mutant (`expense2_path_missing`, `post_actor_paths_missing`, `duplicate_risk_record`, `missing_post_logout_occurrences`) đều trả **exit 1** và `primary_retainer_component = 'UNATTRIBUTED'`; positive control trả **exit 0**.
   - `python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir docs/reviews/bh07/review_runtime_b13e468_evidence`: **PASS** (exit 0).
   - `python -X utf8 scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/review_runtime_b13e468_evidence`: **ALL CHECKS PASSED** (exit 0).
   - `flutter analyze`: **No issues found!** (exit 0).
   - `flutter test`: **247 passed + 1 skipped** (exit 0).

---

## 6. Khuyến nghị Kỹ thuật & Ranh giới Nghiệm thu

1. **Về 8 Residual Risk Tiêu đề Chi phí:**
   - Hiện tượng chuỗi đã render tồn lưu trong `segmentationCache` của Flutter Web Engine là một giả thuyết kỹ thuật có bằng chứng mạnh hỗ trợ. Tuy nhiên, do một đường dẫn BFS không chứng minh tính vét cạn và chưa có đo đạc đối chứng trên native Dart VM, hiện tượng này tiếp tục được ghi nhận chính thức là **unattributed residual risk**.
   - Người triển khai không kết luận dứt khoát nguyên nhân thuộc về engine hay loại trừ hoàn toàn phía app, và không tự ý sửa đổi ứng dụng/backend khi chưa có chỉ đạo từ chủ dự án. Việc chấp nhận rủi ro còn lại (Residual-Risk Acceptance) hay yêu cầu các biện pháp xử lý khác hoàn toàn thuộc thẩm quyền quyết định của chủ dự án và reviewer độc lập.
2. **Về Bản đồ Độ phủ (Coverage Map):**
   - Hiện tại phép đo V2b runtime chỉ mới chứng minh cho **2 mã chi phí** (`expense_id`, `expense_id_2`).
   - Có ít nhất **6 thực thể tài chính/ngân hàng** (`charges`, `payments`, `bank`, `receiver`, `ledger`, `payment instructions`) và listener object graph chưa từng được đo thực tế trong heap của app thật khi chạy trình duyệt.
   - Do đó, **toàn bộ cổng V2b §4.4 và toàn bộ BH-07 PHẢI TIẾP TỤC GIỮ TRẠNG THÁI CHƯA NGHIỆM THU**.
3. **Các Cổng Khác:**
   - Dart VM heap trên desktop/mobile: Giữ **NOT RUN**.
   - Trình duyệt khác (Safari, Firefox, Mobile web): Giữ **NOT RUN**.
   - Tuyệt đối không merge nhánh, không deploy staging/production, không pilot và không mở BH-08.
   - Người triển khai không tự ghi Đạt.
