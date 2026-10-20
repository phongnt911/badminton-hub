# Bàn giao BH-06C — UI tài chính buổi và sổ quỹ CLB

Ngày 18/10/2026 (Việt Nam). Người triển khai: phiên triển khai (DeepSeek) theo [docs/ai/IMPLEMENTER.md](../ai/IMPLEMENTER.md). Trạng thái bàn giao ban đầu: **Chờ review**. Kết luận reviewer 18/10/2026 tại `af31e7b`: **Chưa đạt C**, C1/C2 P1 và C3 P2 còn mở; xem [review_af31e7b](review_af31e7b.md) và bằng chứng. Giữ mô tả/lệnh tác giả bên dưới làm lịch sử. Người triển khai **không tự ghi Đạt**.

## 1. Nhánh, phụ thuộc, phạm vi

- Nhánh: `feat/bh06c-ui`, tách từ bản B đã Đạt `f28fd0f` (tested `5e62007`, [review_5e62007](review_5e62007.md)). Nền A đã Đạt `48d45d2` (tested `706bd73`); main nền `c35dd27` (không merge).
- Phạm vi: **chỉ phần C (UI)**. Dùng nguyên API đã Đạt ở B; không sửa migration/RPC/RLS/helper của A; không viết lại model/repository/provider của B; không sửa `main.dart` ngoài việc đăng ký `FinanceProvider`; không merge `main`; không deploy; không thêm dependency.
- Commit (theo `docs/24` §3 “mỗi phần commit riêng”, tách nhỏ trong C):
  - `777f9df` — nối `FinanceProvider` + màn tài chính buổi (QR/chốt phí/thu tiền).
  - `39aef81` — màn sổ quỹ CLB theo vai trò.
  - `b123db9` — widget test + cập nhật test lối vào (cây được test).

## 2. File thay đổi (trên cây `b123db9`)

| File | Loại | SHA-256 |
|---|---|---|
| `lib/core/money.dart` | thêm | `e6e571bc38a5f9c4233cc4e064be16724e3270d5603d504879f4c56a19351fde` |
| `lib/screens/session_finance_screen.dart` | thêm | `9a9ccdf930da5625c1db4afe84b946211c5c43e98ae08eb76967059d13b0060e` |
| `lib/screens/club_fund_screen.dart` | thêm | `4f76424f2ba84160e9b7af96fa7bebc43e9f3d0c6d4c71cb14ca020ccc652b86` |
| `lib/main.dart` | sửa | `7a5ac05f2db0f3df508dbeeeb81b76de7d7074a8b09242fbbc1104f1186759bd` |
| `lib/screens/session_detail_screen.dart` | sửa | `a0be60c8432d70db77d303c0dd10754ade070f12e79ade96cbcb292db6392058` |
| `lib/screens/clubs_screen.dart` | sửa | `5120255b70f541c604061218343be056193529191c37ae41e3a8714f897abbf7` |
| `test/screens/session_finance_screen_test.dart` | thêm | `3291cd9788dcab5f01148f7bfe75e8fb379321d93e82401f20f1c203b488a30b` |
| `test/screens/club_fund_screen_test.dart` | thêm | `d2d4d3c8d23ba659ad642c448bd26de905c6a3d77e4c18fa264aa66f56ca803e` |
| `test/screens/clubs_screen_test.dart` | sửa | `3a209a7c4b118963d55ae2e9b90c070209beb13f868d4735ef69883c0aa839e8` |
| `test/screens/session_detail_screen_test.dart` | sửa | `79cef9918d82ea95ce403d85f771798e900aa6a147f0058fe3d4b3a3c8c0a70f` |

Cách nối: `main.dart` thêm `ChangeNotifierProvider(create: (context) => FinanceProvider(auth: context.read<AuthProvider>()))` sau `SessionProvider`. `session_detail_screen.dart` thêm thẻ **Tài chính & thu tiền** khi `Session.canViewFinance`, ngược lại **Phần phí của tôi** khi đã đăng nhập, mở `SessionFinanceScreen`. `clubs_screen.dart` đổi hai nút THU QUỸ/CHI QUỸ (trước là SnackBar placeholder thuộc BH-06) sang mở `ClubFundScreen`.

## 3. Đối chiếu yêu cầu phần C ([docs/24](../24_BH06_IMPLEMENTATION_HANDOFF.md) §3)

- **Nối phí/chi phí/miễn phí/chốt lại**: `session_finance_screen.dart` hiển thị trạng thái phí + tổng chi phí/tổng còn phải thu, danh sách chi phí, cho ghi chi phí và hoàn tác chi phí (kèm lý do), chốt/chốt lại phí (`finalizeCharges` với `expectedVersion` = `session.version` và `expectedBillingInputVersion` từ RPC). Miễn phí giữ nguyên ở luồng thêm người của BH-05 (`canSetFeeExempt`), không nhân đôi.
- **Gửi chuyển khoản chờ xác nhận**: nút **Tôi đã chuyển khoản** gọi `submitPayment` (method `bank_transfer`, amount = `outstanding`, reference từ RPC) → trạng thái `submitted`.
- **Finance confirm/reject/cash/reverse**: màn quản lý có **Xác nhận**, **Từ chối** (lý do), **Hoàn tác** (lý do) theo trạng thái payment, và **Thu tiền mặt** theo từng người.
- **Sổ quỹ theo role**: `club_fund_screen.dart` chỉ mở khi `Club.canViewBalance`; hiển thị số dư server-side, bút toán phân trang (`loadMoreLedger`, `hasMoreLedger`), ghi thu/chi thủ công và hoàn tác bút toán thủ công.
- **current/stale/not_finalized + nguồn/version**: chip trạng thái + `billing_input_version` + revision active (số revision, nguồn version, thời điểm chốt). Giữ lịch sử (chi phí/thanh toán đã hoàn tác/từ chối vẫn hiện). Khi **stale** chặn **thu mới** (xác nhận payment, ghi tiền mặt, gửi payment của người chơi) nhưng vẫn cho chốt lại phí và vẫn cho từ chối/hoàn tác.
- **QR theo receiver snapshot + outstanding > 0 + reference**: dựng URL bằng `VietQRHelper.generateQrUrl` từ `receiverSnapshot` + `outstandingVnd` + `reference`; hiển thị ngân hàng/số TK/chủ TK/số tiền/nội dung kèm nút **sao chép** (Clipboard) và `errorBuilder` fallback khi ảnh không tải. QR **không** xác nhận đã thu, không webhook/ngân hàng, không tự chuyển tiền (có dòng cảnh báo trong UI).
- **Loading/error/retry/empty/submitting + permission-denied**: vòng xoay khi tải, màn lỗi có **Thử lại**, trạng thái rỗng, khoá nút khi `isSubmitting`; người chơi không thấy thao tác tài chính; vai trò không đủ quyền ở sổ quỹ bị chặn và **không** gọi RPC.

Không tự tính số dư/outstanding ở client: số dư lấy từ `get_club_ledger`; outstanding hiển thị lấy từ RPC. Từ vòng sửa 2, “còn phải thu theo người” chỉ hiển thị khi trang payments đã đầy đủ, và prefill ô thu tiền mặt luôn đọc `get_payment_instructions` của đúng người; server vẫn là nguồn chặn cuối qua `PAYMENT_EXCEEDS_OUTSTANDING`.

## 4. Test mới và lệnh đã chạy

Trên cây `b123db9` (sạch):

- `flutter analyze` → **No issues found** (0 issue).
- `flutter test` → **181/181 PASS** (= 167 nền của B + 14 test mới).

14 test mới:

- `test/screens/session_finance_screen_test.dart` (6): manager hiện trạng thái + chốt phí gửi đúng `expectedVersion`/`expectedBillingInputVersion`/lý do; stale chặn `Xác nhận`/thu tiền mặt nhưng mở `Từ chối`/`Hoàn tác`; người chơi không thấy thao tác tài chính, thấy QR và gửi chờ xác nhận; chưa chốt phí thì không có QR/nút gửi; lỗi đọc hiện **Thử lại** và không hạ số về 0 rồi tải lại được; đang tải hiện vòng xoay.
- `test/screens/club_fund_screen_test.dart` (6): chủ nhiệm thấy số dư/giao dịch và nạp thêm trang (offset 0→20, gộp 21 bút toán); vai trò khác bị chặn và `verifyNever(getClubLedger)`; lỗi đọc có **Thử lại**; ghi thu thủ công đúng hướng/số tiền; hoàn tác bút toán thủ công kèm lý do; đang tải hiện vòng xoay.
- `test/screens/session_detail_screen_test.dart` (+2): quyền finance thấy **Tài chính & thu tiền**; người chơi chỉ thấy **Phần phí của tôi** và không thấy mục quản lý.
- `test/screens/clubs_screen_test.dart` (sửa 1): hai nút THU/CHI QUỸ mở `ClubFundScreen` (không còn SnackBar placeholder BH-06).

Ghi chú kỹ thuật cho reviewer:

- Test dùng `tester.view.physicalSize` cao (`1200×3200`) vì `ListView` dựng lười, nếu không các mục dưới màn hình sẽ không được dựng và `find.byKey` không thấy.
- Nút hành động có key ổn định: `bh06c-finalize`, `bh06c-add-expense`, `bh06c-cash-<playerId>`, `bh06c-confirm-<paymentId>`, `bh06c-reject-<paymentId>`, `bh06c-reverse-<paymentId>`, `bh06c-reverse-expense-<expenseId>`, `bh06c-submit-payment`, `bh06c-qr`, `bh06c-manual-income`, `bh06c-manual-expense`, `bh06c-ledger-more`, `bh06c-reverse-ledger-<txId>`.
- `Image.network` tới `img.vietqr.io` không được tải trong môi trường test; test chỉ chạy nhánh `errorBuilder` (fallback) chứ không xác nhận ảnh QR thật hiển thị.

## 5. Phần chưa kiểm chứng (NOT RUN)

- HTTP/JWT/PostgREST/Supabase Auth thật; `Image.network` tới `img.vietqr.io` thật; bank/VietQR và webhook thực tế.
- Thiết bị/browser e2e, apply staging/production, backup/restore, concurrency qua HTTP.
- Runner DB BH-06 **không chạy lại** ở lượt này vì không đổi DB/migration (baseline DB 335/335 thuộc các lượt A/B, không phải kết quả chạy trong lượt C).

## 6. Sửa theo review vòng 1 (20/10/2026)

- Review nguồn [review_af31e7b](review_af31e7b.md) (commit review `7c23bbb`); sửa **C1/C2 (P1)**, giữ **C3 (P2)** mở vì chưa có chỉ định của chủ dự án. Chi tiết: [bh06c_review_round1.md](bh06c_review_round1.md).
- Commit: `498d4d8` (test tái hiện — 3 FAIL) → `8e3cd83` (fix). `flutter analyze` 0 issue; `flutter test` **183/183 PASS**; không đổi DB nên runner DB không chạy lại.
- Phát lại probe C1 của reviewer: nguyên văn chỉ FAIL tại matcher `reference` (probe viết trước khi C2 đổi contract); đổi đúng matcher đó sang `null` thì PASS. Probe C3 vẫn FAIL như dự kiến (P2 chưa sửa).
- Trạng thái: **Chờ review vòng 2**.

## 7. Sửa theo review vòng 2 (20/10/2026)

- Chủ dự án giao sửa **toàn bộ P còn lại**: **C3 (P2)** và ca “trả thêm sau refinalize” mà review ghi NOT RUN. Đồng thời cập nhật quy trình để người triển khai sửa P0/P1/P2: `AGENTS.md` (nhánh này, commit `docs(process)` cùng lượt) và `docs/ai/IMPLEMENTER.md` (nhánh `chore/ai-roles`, `07b31d4`).
- C3: chỉ hiển thị “Còn phải thu” theo người khi trang payments đã đầy đủ (`payments.length < limit`); trang bị cắt thì hiển thị “Phải trả theo phí” theo revision hiện hành. Thu tiền mặt luôn đọc `outstandingVnd` của đúng người qua `get_payment_instructions` trước khi prefill; đã trả đủ thì báo và không mở hộp thoại. Không suy khoản nợ từ một trang lịch sử.
- C2 bổ sung: test “trả thêm sau refinalize” — outstanding 100.000 → 50.000 sau chốt lại; hai intent hai request ID, đều không gửi `p_reference`.
- Commit: `75aa95b` (test tái hiện — 2 FAIL đúng C3) → `5174e9d` (fix). `flutter analyze` 0 issue; `flutter test` **186/186 PASS**; không đổi DB nên runner DB không chạy lại. Chi tiết: [bh06c_review_round2.md](bh06c_review_round2.md).
- Probe C3 của reviewer có hai kỳ vọng mâu thuẫn (vừa “100,000” vừa “0”) nên nguyên văn không thể PASS; test hồi quy của tác giả kiểm hành vi thay thế đúng hướng dẫn reviewer (không suy nợ; prefill từ RPC; chặn khi đã trả đủ).
- Trạng thái: **Chờ review vòng 2** (vòng sửa 2/2). NOT RUN: refinalize ở mức RPC/DB, HTTP/JWT/Auth thật, thiết bị/browser, bank/VietQR thật, staging/production, backup/restore, concurrency HTTP.

Đây là bằng chứng phía tác giả; reviewer cần tự chạy lại trên đúng SHA và tự kết luận. Người triển khai không tự ghi Đạt và không chuyển sang phần tích hợp khi chưa có kết luận Đạt C.
