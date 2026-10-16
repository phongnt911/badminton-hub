# BH-06B — bàn giao người triển khai (model/repository/provider tài chính)

> **Hiện hành 16/10/2026: Chưa đạt B** tại `d00a121` theo [review độc lập](review_d00a121.md), còn B1/B2 P2. Chờ review bên dưới là snapshot tác giả trước kết luận; A vẫn Đạt, chưa chuyển C.

Ngày 16/10/2026 (Việt Nam). Vai trò: người triển khai (DeepSeek) theo `docs/ai/IMPLEMENTER.md`. Phần A BH-06 đã **Đạt** tại `706bd73` ([review_706bd73.md](review_706bd73.md)); nhánh B tách từ bản A đã Đạt `48d45d2`. Trạng thái phần B: **Chờ review** — người triển khai không tự ghi Đạt.

## 1. Nhánh, SHA phụ thuộc

| Mục | Giá trị |
|---|---|
| Nhánh | `feat/bh06b-data` |
| Tách từ (dependency) | `48d45d2` (bản A đã Đạt; `706bd73` + commit kết luận của reviewer) |
| Base `main` trong chuỗi | `c35dd27` (gián tiếp, qua A) |
| Commit mã/test | `a794a91` (`a794a912e04f49e55867d94dc35e7c3a9213cb8c`) |
| Commit docs/bàn giao | commit tip của nhánh `feat/bh06b-data` (ngay sau `a794a91`) |

Không sửa migration/RPC của A, không merge `main`, không deploy, không áp dụng remote DB.

## 2. Phạm vi và file

Chỉ làm phần B theo [đầu bài](../24_BH06_IMPLEMENTATION_HANDOFF.md) §3.B; **không** làm C (UI VietQR/sổ quỹ) và không nối `main.dart`.

| File | Vai trò |
|---|---|
| `lib/models/finance.dart` | DTO typed: `PaymentInstructions`, `SessionFinance` (+`FinanceRevision`, `FinanceExpense`, `FinanceCharge`, `FinancePayment`), `ClubLedger` (+`ClubLedgerEntry`), và kết quả mutation `ExpenseResult`, `RevisionResult`, `PaymentResult`, `ClubTransactionResult`. sha256 `3a5cfb5b3f72783f170b0f250743d3d9fd535d3190b8822bfa565a7df660cda0`. |
| `lib/data/finance_repository.dart` | RPC wrappers, tên tham số khớp đúng chữ ký A; kẹp `p_limit` 1..100, `p_offset` ≥ 0. sha256 `646af8026a97e2a8697a476ee0ce60a3dd5e161d606e5789c5fcc3a5e097691d`. |
| `lib/providers/finance_provider.dart` | `ChangeNotifier`: đọc/QR/tài chính/quỹ + mutation, giữ/xoay `request_id`, isolation, bỏ phản hồi trễ. sha256 `41ace8e19201bce5ec3937c1748dc12a607cf1c8a3114c79a339f84e197199de`. |
| `test/models/finance_test.dart` | 9 test đọc JSON (đủ/thiếu snapshot, stale/not_finalized, ledger, kết quả mutation). |
| `test/providers/finance_provider_test.dart` | 17 test hành vi provider. |

RPC dùng (đúng chữ ký/ACL đã review ở [docs/08 §13](../08_DOMAIN_CONTRACTS.md)): `get_payment_instructions`, `get_session_finance`, `get_club_ledger`, `post_session_expense`, `reverse_session_expense`, `finalize_session_charges`, `complete_session`, `submit_payment`, `confirm_payment`, `reject_payment`, `reverse_payment`, `record_cash_payment`, `post_manual_club_transaction`, `reverse_club_transaction`. Không gọi function chưa có.

## 3. Hành vi then chốt của provider

- **Retry/replay**: một ý định giữ cùng UUID qua lỗi/timeout; payload đổi tạo ý định mới; key xoá ngay sau khi server xác nhận, **trước** khi làm mới.
- **Double-submit**: `isSubmitting` chặn lần nhấn lặp.
- **Làm mới lỗi**: mutation đã commit vẫn thành công; lỗi đọc được giữ ở trạng thái read riêng (`financeErrorMessage`/`ledgerErrorMessage`), **không** thành `submitErrorMessage`.
- **Isolation**: logout/đổi actor → `clearAll()` (tăng generation, xoá key, xoá mọi state); đổi buổi/CLB → xoá dữ liệu cũ + vô hiệu phản hồi đang bay bằng serial.
- **Không hạ về 0 do lỗi**: lỗi đọc (kể cả thiếu quyền) giữ nguyên số dư/công nợ cũ, chỉ đặt lỗi; lỗi QR (`not_finalized`/`stale`) giữ lỗi, không coi "chưa cần trả".
- **Phân trang**: `get_session_finance`/`get_club_ledger` truyền `limit`/`offset`; `loadMoreLedger()` nối trang kế theo `offset = entries.length`.
- **Stale/idempotency**: mã domain (`BILLING_STALE`, `BILLING_NOT_FINALIZED`, `PAYMENT_EXCEEDS_OUTSTANDING`, `IDEMPOTENCY_CONFLICT`, …) map qua `domainErrorMessage`, không lộ chi tiết Postgres.

## 4. Lệnh đã chạy và kết quả

Trên cây mã `a794a91` (chỉ `docs/09_IMPLEMENTATION_PLAN.md` còn đang sửa dở; phần Dart/test đã commit):

| Lệnh | Kết quả |
|---|---|
| `flutter analyze` | **0 issue** |
| `flutter test` | **163/163 PASS** = 137 nền (không đổi) + 26 test mới của B |
| `python docs/reviews/bh06/run_bh06_tests.py` | **NOT RUN** — phần B không đổi DB/migration; baseline DB 335/335 của A giữ nguyên |

`flutter --version`: 3.47.7 / Dart 3.13.5. Không sửa/bỏ test BH-02..05; chỉ thêm test mới.

## 5. NOT RUN

HTTP/PostgREST/JWT thật, thiết bị/browser e2e, apply staging/production, backup/restore, concurrency qua HTTP, UI phần C (VietQR render/fallback, sổ quỹ), và nối provider vào widget tree. Chưa có bằng chứng client↔RPC qua PostgREST thật.

## 6. Ghi chú cho reviewer

- Kiểm `lib/data/finance_repository.dart` khớp tên tham số `p_*` với `docs/08 §13` và migration A.
- Kiểm `lib/providers/finance_provider.dart`: thứ tự xoá key trước refresh; refresh lỗi không làm mutation thất bại; isolation theo generation/serial; lỗi đọc không hạ số dư về 0.
- Test tái hiện: `test/providers/finance_provider_test.dart` (retry/replay, double-submit, stale, idempotency, isolation, phân trang, refresh lỗi).
- Không suy Đạt B từ Đạt A; phần C và tích hợp cần review riêng.
