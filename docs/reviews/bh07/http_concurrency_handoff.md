# BH-07 — kiểm chứng Concurrency HTTP/Auth trên Supabase local (Sửa vòng 2/2)

> **Trạng thái: Chờ review Concurrency HTTP/Auth BH-07 vòng 2/2 (22/10/2026).** Người triển khai không tự ghi Đạt. Base thực tế: `a0f831af47f98c7649e0c80dce4d5f13004a0db2` (commit cha trực tiếp của tested source `cbcc46c2e125b156b53f4297ef864cf658855d37`, đính chính từ tham số ban đầu `a0f831ae3f47e305608bfa0dff19ae035b31f798`); tested source `cbcc46c2e125b156b53f4297ef864cf658855d37`; nhánh `feat/bh07-http-concurrency`. Kết quả dưới đây chỉ là kiểm chứng local, không thay đổi kết luận BH-07D và không tự nghiệm thu toàn BH-07/pilot.

## 1. Phạm vi xử lý vòng 2/2 (Khắc phục H3 & H4; bảo toàn H1 & H2)

Theo biên bản review độc lập [review_cbcc46c.md](file:///c:/Users/POTA/Documents/GitHub/badminton-hub/docs/reviews/bh07/review_cbcc46c.md), hai phát hiện kỹ thuật **H1** và **H2** đã được xác nhận **ĐÓNG**. Vòng 2/2 xử lý triệt để hai phát hiện tài liệu/bằng chứng **H3** và **H4**:

### H1 & H2 (Đã Đóng ở vòng 1/2)
- **H1 (Đã Đóng):** Phân biệt drop sau commit với HTTP lỗi; `DropResponseAfterCommitClient` chỉ drop khi `response.statusCode == 200`, drain body stream; kiểm chứng DB server đã commit (operation, payment confirmed, ledger, outstanding) trước khi retry; negative control HTTP 400 không vượt gate.
- **H2 (Đã Đóng):** Predicate có cấu trúc `isCompleteConflictError` (SQLSTATE/HTTP 22023/409 kèm domain `VERSION_CONFLICT`/`INVALID_STATE`) và `isCashOvercollectError` (SQLSTATE 22023 kèm domain `PAYMENT_EXCEEDS_OUTSTANDING`); negative controls loại bỏ toàn bộ lỗi ngoài luồng (FORBIDDEN, NOT_FOUND, INVALID_INPUT, sai SQLSTATE, transport).

### H3: Giải mã đúng encoding nguồn, chuẩn hóa UTF-8 và LF ở cấp text
- **Vấn đề cũ:** Sáu file log (`bh07_db_runner.log`, `flutter_analyze.log`, `flutter_test_full.log`, `green_probe.log`, `red_probe.log`, `seed.log`) được PowerShell redirect tạo ra dưới dạng UTF-16 LE có BOM. Phép thay thế byte ASCII `replace(b'\r\n', b'\n')` trước đây không bắt được chuỗi byte UTF-16, khiến file tuy khớp manifest raw bytes nhưng vẫn chứa CRLF ở cấp text Unicode.
- **Khắc phục:**
  1. Giữ nguyên 100% nội dung log, đọc và decode theo đúng BOM/encoding nguồn (UTF-16 LE / UTF-8-sig).
  2. Chuẩn hóa ở cấp text chuỗi Unicode (`text.replace('\r\n', '\n')`), loại bỏ triệt để mọi ký tự `\r`.
  3. Ghi lại sang UTF-8 thuần nhất quán (không BOM, kết thúc dòng LF).
  4. Kiểm toán cấp text: Khẳng định số lượng CRLF = 0 và CR = 0 trên toàn bộ 19 file bằng chứng.
  5. Quét secret sau decode: Quét regex trên văn bản UTF-8 thuần khẳng định không có JWT 3 đoạn, sb_secret, service_role key hay private key.
  6. Tính lại toàn bộ mã băm SHA-256 trong `hashes.sha256` với đường dẫn forward-slash (`/`).

### H4: Đính chính Base SHA thực tế trong metadata và commands, lưu vết tham số ban đầu
- **Vấn đề cũ:** Tham số `-BaseSha a0f831ae3f47e305608bfa0dff19ae035b31f798` trong yêu cầu ban đầu bị lệch vài ký tự cuối so với commit cha thực tế của tested source `cbcc46c` trên git (`a0f831af47f98c7649e0c80dce4d5f13004a0db2`).
- **Khắc phục:**
  1. Cập nhật `base_sha` thành commit thực tế `a0f831af47f98c7649e0c80dce4d5f13004a0db2` trong `environment.json`, `summary.json`, `commands.md` và `http_concurrency_handoff.md`.
  2. Lưu vết trung thực tham số ban đầu qua trường `base_sha_initial_parameter: "a0f831ae3f47e305608bfa0dff19ae035b31f798"` và `base_sha_note` trong metadata JSON; không giả mạo lịch sử thực thi lệnh.
  3. Cập nhật lệnh tái lập trong `commands.md` và handoff sử dụng full base SHA thực tế.

Tested source SHA **`cbcc46c2e125b156b53f4297ef864cf658855d37`** được bảo toàn nguyên vẹn, không thay đổi mã nguồn ứng dụng hay logic kiểm thử.

---

## 2. Kết quả kiểm chứng độc lập

| Hạng mục | Kết quả | Exit | Bằng chứng |
|---|---|---|---|
| HTTP/Auth Concurrency matrix | **76/76 PASS**, exit 0 | 0 | [`summary.json`](http_concurrency_evidence/summary.json), [`flutter_test.log`](http_concurrency_evidence/flutter_test.log) |
| `flutter analyze` | 0 issues | 0 | [`flutter_analyze.log`](http_concurrency_evidence/flutter_analyze.log) |
| Full Flutter suite | **240 pass + 1 skip** | 0 | [`flutter_test_full.log`](http_concurrency_evidence/flutter_test_full.log) |
| BH-07 DB runner | **23/23 PASS** | 0 | [`bh07_test_results_20261022122614.json`](bh07_test_results_20261022122614.json), [`bh07_db_runner.log`](http_concurrency_evidence/bh07_db_runner.log) |
| Manifest SHA-256 LF | 19/19 files khớp 100%, CRLF = 0 cả raw & decoded text, UTF-8 no BOM | 0 | [`hashes.sha256`](http_concurrency_evidence/hashes.sha256) |
| Secret scan (sau decode) | 0 secrets (không có JWT 3 đoạn, sb_secret, private key) | 0 | Quét regex tự động |

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

## 3. Lệnh thực thi cho Reviewer

```powershell
# Chạy toàn bộ ma trận HTTP/Auth Concurrency (tự reset DB local, tạo user GoTrue, nạp seed.sql, chạy test):
powershell -ExecutionPolicy Bypass -File scripts/bh07_http/run.ps1 -BaseSha a0f831af47f98c7649e0c80dce4d5f13004a0db2

# Chạy kiểm tra tĩnh và toàn bộ suite:
flutter analyze
flutter test
python docs/reviews/bh07/run_bh07_tests.py
```

---

## 4. Giới hạn và NOT RUN

- Chưa chạy trên thiết bị di động thật (iOS/Android), chưa kiểm tra browser UI e2e hay offline sync/deep link.
- Chưa kết nối dịch vụ ngân hàng thật, VietQR đối soát hoặc webhook thanh toán thực tế.
- Chưa triển khai lên môi trường staging/production/cloud, chưa diễn tập backup/restore hay rehearsal/pilot.
- Không tự ý merge vào nhánh `main` hoặc đánh dấu hoàn thành toàn bộ ticket BH-07.
