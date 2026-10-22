# BH-07 — kiểm chứng Concurrency HTTP/Auth trên Supabase local (Sửa vòng 1/2)

> **Trạng thái: Chờ review Concurrency HTTP/Auth BH-07 vòng 1/2 (22/10/2026).** Người triển khai không tự ghi Đạt. Base `a0f831ae3f47e305608bfa0dff19ae035b31f798` (gốc nhánh `4da6339a1a92bcf27675f50ca4b785fbb45f1e78`); tested source `cbcc46c2e125b156b53f4297ef864cf658855d37`; nhánh `feat/bh07-http-concurrency`. Kết quả dưới đây chỉ là kiểm chứng local, không thay đổi kết luận BH-07D và không tự nghiệm thu toàn BH-07/pilot.

## 1. Phạm vi sửa chữa vòng 1/2 (Khắc phục H1 & H2)

Theo biên bản review độc lập [review_2f0aa59.md](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/docs/reviews/bh07/review_2f0aa59.md), hai phát hiện P2 đã được xử lý triệt để:

### H1: Phân biệt drop sau commit với HTTP lỗi; kiểm chứng server commit trước khi retry
- **Vấn đề cũ:** `DropResponseAfterCommitClient` trước đây không kiểm tra `response.statusCode`, dẫn đến việc các response lỗi (ví dụ HTTP 400) cũng bị coi là drop sau commit. Kiểm chứng trong test chỉ đo sau retry nên không loại trừ trường hợp retry mới là lần đầu mutation xảy ra.
- **Khắc phục:**
  1. Trong `DropResponseAfterCommitClient`: Chỉ đánh dấu `dropped = true` và ném exception mô phỏng rớt mạng khi `response.statusCode == 200` (đúng contract thành công của RPC). Ghi nhận `droppedStatusCode = 200` và đảm bảo đã drain body stream (`drained = true`). Các response non-2xx được trả về nguyên trạng, không đánh dấu drop.
  2. **Trước khi retry**, dùng service-role (`admin`) xác nhận trực tiếp trong cơ sở dữ liệu:
     - Đúng 1 bản ghi `operation_requests` với `operation = 'record_cash_payment'` và `actor_user_id = dropActor.user.id`.
     - Đúng 1 bản ghi `payments` với trạng thái `confirmed`. Lưu lại `baselinePaymentId`.
     - Đúng 1 bản ghi sổ cái `club_transactions` tương ứng với `baselinePaymentId`.
     - Số dư công nợ session đã được trừ chính xác về 40.000 VNĐ.
  3. Thực hiện retry với cùng key + payload: đối chiếu kết quả trả về có `paymentId == baselinePaymentId`, và các số đếm operation, payment, ledger không bị tăng thêm (idempotent replay).
  4. Bổ sung negative control H1: Sử dụng mock client trả về HTTP 400 qua `DropResponseAfterCommitClient` để khẳng định non-2xx không bao giờ vượt qua gate drop sau commit.

### H2: Kiểm tra domain error có cấu trúc cho các request cạnh tranh
- **Vấn đề cũ:** Predicate complete trước đây chấp nhận chuỗi `P0001` hoặc `409`; predicate cash chấp nhận `P0001`, `22023` hoặc từ `amount`. Do đó một lỗi bất kỳ như `FORBIDDEN` (P0001) cũng bị nhận nhầm là conflict hợp lệ.
- **Khắc phục:**
  1. Xây dựng predicate có cấu trúc `isCompleteConflictError`: yêu cầu bắt buộc là `PostgrestException`, mã lỗi SQLSTATE/HTTP phải là `22023` hoặc `409`, và thông báo lỗi domain phải chứa `VERSION_CONFLICT` hoặc `INVALID_STATE`.
  2. Xây dựng predicate có cấu trúc `isCashOvercollectError`: yêu cầu bắt buộc là `PostgrestException`, mã lỗi SQLSTATE `22023`, và thông báo domain phải chứa `PAYMENT_EXCEEDS_OUTSTANDING`.
  3. Bổ sung negative controls H2 (`verifyH2NegativeControls()`): Thử nghiệm trực tiếp các lỗi không liên quan (`FORBIDDEN` 42501, `NOT_FOUND` P0002, `INVALID_INPUT` 22023, probe `FORBIDDEN` P0001 của reviewer, và transport error), xác nhận các predicate đều từ chối và trả về `false`.

---

## 2. Kiểm chứng Test đỏ (Red run) trước khi sửa

Đã viết test probe tái hiện lỗi trên code cũ:
- Probe H1: `DropResponseAfterCommitClient` nhận HTTP 400 và tự động coi là drop sau commit -> **FAIL (Red)**.
- Probe H2: Các predicate cũ chấp nhận `FORBIDDEN` kèm `P0001` -> **FAIL (Red)**.
- Bằng chứng Red run lưu tại: [`red_probe.log`](http_concurrency_evidence/red_probe.log).
- Sau khi áp dụng code sửa, probe kiểm tra chuyển sang **5/5 PASS (Green)**: [`green_probe.log`](http_concurrency_evidence/green_probe.log).

---

## 3. Kết quả kiểm chứng độc lập

| Hạng mục | Kết quả | Exit | Bằng chứng |
|---|---|---|---|
| HTTP/Auth Concurrency matrix | **76/76 PASS**, exit 0 | 0 | [`summary.json`](http_concurrency_evidence/summary.json), [`flutter_test.log`](http_concurrency_evidence/flutter_test.log) |
| `flutter analyze` | 0 issues | 0 | [`flutter_analyze.log`](http_concurrency_evidence/flutter_analyze.log) |
| Full Flutter suite | **240 pass + 1 skip** | 0 | [`flutter_test_full.log`](http_concurrency_evidence/flutter_test_full.log) |
| BH-07 DB runner | **23/23 PASS** | 0 | [`bh07_test_results_20261022122614.json`](bh07_test_results_20261022122614.json), [`bh07_db_runner.log`](http_concurrency_evidence/bh07_db_runner.log) |
| Manifest SHA-256 LF | 19/19 files khớp 100%, CRLF = 0 | 0 | [`hashes.sha256`](http_concurrency_evidence/hashes.sha256) |
| Secret scan | 0 secrets (không có JWT 3 đoạn, sb_secret, private key) | 0 | Quét regex tự động |

Phân bổ 76 checks:
- auth: 8
- ACL: 9
- privacy: 5
- scope: 4
- complete: 11
- finance: 16
- summary: 5
- history: 11
- list: 1
- concurrency: 6
  - `concurrency.complete.replay-idempotent` (PASS)
  - `concurrency.complete.competing-conflict` (PASS — kiểm domain error cấu trúc + negative controls H2)
  - `concurrency.cash.replay-idempotent` (PASS)
  - `concurrency.cash.competing-no-overcollect` (PASS — kiểm domain overcollect cấu trúc + negative controls H2)
  - `concurrency.confirm.replay-idempotent` (PASS)
  - `concurrency.drop-response.retry-no-duplicate` (PASS — gate status 200 + pre-retry DB commit verification + baseline ID match + negative control H1)

---

## 4. Lệnh thực thi cho Reviewer

```powershell
# Chạy toàn bộ ma trận HTTP/Auth Concurrency (tự reset DB local, tạo user GoTrue, nạp seed.sql, chạy test):
powershell -ExecutionPolicy Bypass -File scripts/bh07_http/run.ps1 -BaseSha a0f831ae3f47e305608bfa0dff19ae035b31f798

# Chạy kiểm tra tĩnh và toàn bộ suite:
flutter analyze
flutter test
python docs/reviews/bh07/run_bh07_tests.py
```

---

## 5. Giới hạn và NOT RUN

- Chưa chạy trên thiết bị di động thật (iOS/Android), chưa kiểm tra browser UI e2e hay offline sync/deep link.
- Chưa kết nối dịch vụ ngân hàng thật, VietQR đối soát hoặc webhook thanh toán thực tế.
- Chưa triển khai lên môi trường staging/production/cloud, chưa diễn tập backup/restore hay rehearsal/pilot.
- Không tự ý merge vào nhánh `main` hoặc đánh dấu hoàn thành toàn bộ ticket BH-07.
