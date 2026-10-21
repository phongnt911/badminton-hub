# BH-07 — kiểm chứng Concurrency HTTP/Auth trên Supabase local

> **Trạng thái: Chờ review Concurrency HTTP/Auth BH-07 (21/10/2026).** Người triển khai không tự ghi Đạt. Base `4da6339a1a92bcf27675f50ca4b785fbb45f1e78`; tested source `2f0aa5930d8d1d982ced3bcda82b22b899e5881a`; nhánh `feat/bh07-http-concurrency`. Kết quả dưới đây chỉ là kiểm chứng local, không thay đổi kết luận BH-07D và không tự nghiệm thu toàn BH-07/pilot.

## 1. Phạm vi kiểm chứng Concurrency HTTP/Auth

Chỉ bổ sung test / script / fixture kiểm chứng local. Không sửa migration, RPC, model, repository, provider, UI hay contract; giữ nguyên hợp đồng và kiến trúc hiện có.

Gói kiểm chứng sử dụng Supabase local thật, JWT thật qua GoTrue Admin API và hai client độc lập (`ownerB1`, `ownerB2`) chạy đồng thời:

1. **Cùng `request_id` + payload (Idempotent replay đồng thời):**
   - `complete_session`: hai request đồng thời cùng `request_id` nhận kết quả giống nhau, chỉ tạo 1 bản ghi `audit_events` và 1 bản ghi `operation_requests`, version tăng đúng 1 lần (v3 → v4).
   - `record_cash_payment`: hai request ghi tiền mặt đồng thời cùng `request_id` trả cùng `payment_id`, tạo đúng 1 bản ghi `payments`, 1 bản ghi `club_transactions` (sổ cái) và 1 bản ghi `operation_requests`.
   - `confirm_payment`: hai request xác nhận đồng thời cùng `request_id` cho khoản thanh toán member submit (`MEMBER-A-CLEAR-DEBT`), tạo đúng 1 bản ghi ledger và 1 operation request, tất toán công nợ về 0.

2. **Request cạnh tranh khác key/version (Conflict & No-overcollect):**
   - `complete_session`: hai request đồng thời với hai `request_id` khác nhau trên cùng session v3. Chỉ một request thành công chuyển sang `completed` (v4), request còn lại bị từ chối với `VERSION_CONFLICT` hoặc `INVALID_STATE` (409/22023), `audit_events` chỉ ghi đúng 1 lần.
   - `record_cash_payment` (không thu vượt): session nợ còn 100.000 VNĐ, hai client cạnh tranh gửi hai request khác nhau mỗi bên đòi thu 70.000 VNĐ. Một bên thành công thu 70.000 VNĐ, bên còn lại bị server từ chối ngay lập tức với lỗi vượt nợ (`PAYMENT_EXCEEDS_OUTSTANDING`, 22023). Số tiền đã thu đúng 120.000 VNĐ (gồm 50.000 VNĐ trước đó), nợ còn lại được bảo toàn chính xác 30.000 VNĐ.

3. **Mô phỏng mất response sau khi server commit (Transport drop & Retry):**
   - Dùng custom HTTP client `DropResponseAfterCommitClient` kế thừa `http.BaseClient`. Sau khi server PostgREST/Kong xử lý và trả status 200, proxy gọi `drain()` stream response và ném `http.ClientException` mô phỏng mất kết nối mạng phía client. Proxy thuần tuý can thiệp tầng transport, tuyệt đối không mock hay giả lập logic nghiệp vụ.
   - Retry lại qua client bình thường với cùng `request_id`: nhận kết quả thành công, xác nhận trực tiếp trong DB chỉ có đúng 1 payment, 1 ledger entry, 1 operation request và công nợ giảm chính xác.

4. **Kế thừa và bảo toàn 70 check HTTP/Auth cũ:**
   - Giữ nguyên 70 check HTTP/Auth đã đạt ở vòng trước cùng các controls H1 (charge0 cho free session) và H2 (raw privacy whitelist / recursion).
   - Toàn bộ 4 fixture session concurrency được đưa vào `v_club_b` do `v_owner_b` làm host với trạng thái ban đầu `in_progress`. Nhờ đó, các assertion về danh sách history của `ownerA`, `cohostA`, `memberA`, `outsider` và `ownerB` trong 70 check cũ hoàn toàn không bị lệch số lượng hay thứ tự.
   - Tổng ma trận nâng lên **76 checks**.

## 2. Kết quả kiểm chứng

| Hạng mục | Kết quả | Exit | Bằng chứng |
|---|---|---|---|
| HTTP/Auth Concurrency matrix | **76/76 PASS**, exit 0 | 0 | [`summary.json`](http_concurrency_evidence/summary.json), [`flutter_test.log`](http_concurrency_evidence/flutter_test.log) |
| `flutter analyze` | sạch, không issue (0 warnings) | 0 | [`flutter_analyze.log`](http_concurrency_evidence/flutter_analyze.log) |
| Full Flutter suite | **240 pass + 1 skip** | 0 | [`flutter_test_full.log`](http_concurrency_evidence/flutter_test_full.log) |
| BH-07 DB runner | **23/23 PASS**, timestamp `20261021103824` | 0 | [`bh07_db_runner_results.json`](http_concurrency_evidence/bh07_db_runner_results.json), [`bh07_db_runner.log`](http_concurrency_evidence/bh07_db_runner.log) |
| Red run trước khi nạp fixture | **70/76 PASS, đúng 6 FAIL** nhóm concurrency | 1 | [`red_run_summary.json`](http_concurrency_evidence/red_run_summary.json), [`red_run_flutter_test.log`](http_concurrency_evidence/red_run_flutter_test.log), [`red_run_exits.json`](http_concurrency_evidence/red_run_exits.json) |

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
  - `concurrency.complete.competing-conflict` (PASS)
  - `concurrency.cash.replay-idempotent` (PASS)
  - `concurrency.cash.competing-no-overcollect` (PASS)
  - `concurrency.confirm.replay-idempotent` (PASS)
  - `concurrency.drop-response.retry-no-duplicate` (PASS)

## 3. Lệnh thực thi

```powershell
# Chạy toàn bộ ma trận HTTP/Auth Concurrency (tự reset DB local, tạo user GoTrue, nạp seed.sql, chạy test):
.\scripts\bh07_http\run.ps1

# Chạy kiểm tra tĩnh và toàn bộ suite:
flutter analyze
flutter test
python docs\reviews\bh07\run_bh07_tests.py
```

## 4. Môi trường kiểm chứng

- Supabase local chạy qua Docker/Kong: GoTrue `v2.197.0`, PostgREST `v16.4`, PostgreSQL `17.11.0.004`; kết nối qua `http://127.0.0.1:54321`.
- Không mock repository hay Auth: dùng `SupabaseClient`, `AuthRepository`, `SessionRepository`, `FinanceRepository` thật.
- Bảy tài khoản người dùng đăng nhập qua GoTrue Admin API và cấp JWT thật.
- Hai client riêng biệt `ownerB1` và `ownerB2` được khởi tạo với HTTP client riêng để thực hiện các cuộc gọi đồng thời (`Future.wait`).
- Chi tiết cấu hình và môi trường: [`environment.json`](http_concurrency_evidence/environment.json).

## 5. Bằng chứng và Manifest LF

- Danh mục bằng chứng: [`http_concurrency_evidence/`](http_concurrency_evidence/).
- Toàn bộ file log, JSON và manifest đều được chuẩn hóa kết thúc dòng LF (`\n`).
- Manifest SHA-256: [`hashes.sha256`](http_concurrency_evidence/hashes.sha256).

## 6. Giới hạn và NOT RUN

- Chưa chạy trên thiết bị di động thật (iOS/Android), chưa kiểm tra browser UI e2e hay offline sync/deep link.
- Chưa kết nối dịch vụ ngân hàng thật, VietQR đối soát hoặc webhook thanh toán thực tế.
- Chưa triển khai lên môi trường staging/production/cloud, chưa diễn tập backup/restore hay rehearsal/pilot.
- Không tự ý merge vào nhánh `main` hoặc đánh dấu hoàn thành toàn bộ ticket BH-07.

## 7. Hướng dẫn Reviewer

Reviewer độc lập cần tự thực hiện:
1. Fetch nhánh `feat/bh07-http-concurrency` và kiểm tra diff so với base SHA `4da6339a1a92bcf27675f50ca4b785fbb45f1e78`.
2. Xác nhận không có thay đổi nào trong `supabase/migrations`, RPC, model, repository, provider, hay UI contract.
3. Tự chạy `.\scripts\bh07_http\run.ps1` trên môi trường Supabase local và xác nhận đạt 76/76 checks.
4. Tự chạy `flutter analyze` (0 issues), `flutter test` (240 pass + 1 skip), và `python docs/reviews/bh07/run_bh07_tests.py` (23/23 pass).
5. Kiểm tra tính toàn vẹn của manifest LF và quét secret.
6. Lập báo cáo review độc lập tại `docs/reviews/bh07/review_<sha>.md` theo quy trình hai AI.
