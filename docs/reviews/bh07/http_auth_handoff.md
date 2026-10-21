# BH-07 — kiểm chứng HTTP/Auth trên Supabase local

> **Trạng thái: Chờ review kiểm chứng HTTP/Auth BH-07 (21/10/2026).** Người triển khai không tự ghi Đạt. Base `593bea86ffb807675387dba6b0276b555fdc87a1`; tested source `3ad25a4ac8c2ee1beaa76b3810860ecde514d86e`; nhánh `feat/bh07-http-verification`. Kết quả dưới đây chỉ là kiểm chứng local, không thay đổi kết luận BH-07D tại `3d590a8` và không nghiệm thu toàn BH-07/pilot.

## 1. Phạm vi đã chạy

- Supabase local thật: GoTrue `v2.197.0`, PostgREST `v16.4`, PostgreSQL `17.11`; không mock repository, không Auth stub, không dùng staging/production.
- Bảy actor đăng nhập bằng mật khẩu qua GoTrue và nhận JWT thật: ownerA, financeA, cohostA, memberA, guestA, ownerB, outsider. Có kiểm tra sai mật khẩu bị từ chối.
- Dùng `AuthRepository`, `SessionRepository`, `FinanceRepository` và `SupabaseClient` thật qua HTTP/PostgREST. Service-role chỉ đọc bộ đếm side effect (audit, `operation_requests`, payment, ledger, revision, expense), không dùng để thực hiện mutation hay bỏ qua ACL.
- Ma trận **65 check**, nhóm: auth 8, ACL 9, privacy 4, scope 4, complete 10, finance 16, summary 3, history 10, list 1.
- Bao phủ: complete khi còn nợ, free-current, current/stale/version conflict, retry cùng `request_id`, cross-club, participant/guest/outsider, history/summary scope và privacy, payment/ledger sau complete, reject/reverse/refinalize, post-expense bị chặn, list/detail sau complete.
- Fixture application rows được seed bằng SQL xác định trên DB local sau reset. Đây là cách dựng dữ liệu test, không phải mock tầng repository/Auth; reviewer cần kiểm seed không vô tình bỏ qua precondition nghiệp vụ.

## 2. Kết quả

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| HTTP/Auth matrix | **65/65 PASS**, exit 0 | [`summary.json`](http_auth_evidence/summary.json), [`flutter_test.log`](http_auth_evidence/flutter_test.log) |
| `flutter analyze` | sạch, exit 0 | [`flutter_analyze.log`](http_auth_evidence/flutter_analyze.log) |
| `flutter test` toàn bộ | **240 pass + 1 skip**, exit 0 | [`flutter_test_full.log`](http_auth_evidence/flutter_test_full.log) |
| BH-07 DB runner | **23/23 PASS**, exit 0 | [`bh07_db_runner.log`](http_auth_evidence/bh07_db_runner.log), [`bh07_db_runner_results.json`](http_auth_evidence/bh07_db_runner_results.json) |
| Môi trường | tested `3ad25a4`, `worktree_dirty_before_run=false` | [`environment.json`](http_auth_evidence/environment.json) |
| Exit code | start/status/reset/auth/seed/HTTP test đều 0 | [`exits.json`](http_auth_evidence/exits.json) |
| Hash | phủ source, evidence và DB JSON | [`hashes.sha256`](http_auth_evidence/hashes.sha256) |

Lần chạy HTTP cuối được thực hiện trên checkout sạch tại `3ad25a4`; `environment.json` ghi `worktree_dirty_before_run=false`. DB runner cũng được chạy khi chỉ còn evidence chưa commit, nên JSON ghi `worktree_dirty=false`.

## 3. Lệnh tái lập (Windows, local only)

```powershell
# Reset local DB, tạo Auth user qua GoTrue Admin API, seed fixture,
# chạy HTTP/Auth matrix và ghi evidence.
powershell -ExecutionPolicy Bypass -File scripts\bh07_http\run.ps1

# Hồi quy Flutter (HTTP matrix tự skip nếu không đặt BH07_HTTP_TEST=1)
flutter analyze
flutter test

# Hồi quy DB BH-07 trên container PostgreSQL cô lập
python docs\reviews\bh07\run_bh07_tests.py
```

`run.ps1` chỉ chấp nhận `API_URL` host `127.0.0.1`, `localhost` hoặc `::1`; dừng ngay nếu không phải local. Runner dùng `npx --yes supabase@2.121.0 db reset --local --no-seed --yes`, nên **xoá dữ liệu Supabase local**. Không chạy lệnh này vào staging/production.

## 4. Điểm reviewer cần kiểm

1. `test/integration/bh07_http_auth_test.dart` có thực sự gọi repository/RPC thật qua HTTP, không mock, và 65 check không tự chứng minh điều đã giả định.
2. Idempotency `confirmPayment`: retry trả `alreadyConfirmed=false` nhưng vẫn idempotent — cùng payment ID, `payments=2`, `ledger=1`, `operations=1`, outstanding `100000`. Test không dùng cờ `alreadyConfirmed` làm bằng chứng.
3. Anonymous gọi `complete_session` bị chặn ở quyền function với `permission denied for function complete_session` (không phải `UNAUTHENTICATED`). Cần xác nhận đây là hành vi hợp lệ của contract/privilege hiện hành.
4. `list_session_players` yêu cầu quyền management; test dùng ownerA, không dùng treasurer.
5. History/summary chỉ trả projection an toàn; không lộ contact/phone/bank/account; management-only cohost thấy count nhưng mọi trường tiền là `null`.
6. Seed fixture không thay thế kiểm tra precondition: complete current/free/stale/version conflict vẫn đi qua RPC thật; các ca post-expense bị chặn không tạo side effect.
7. Runner redacted JWT/key trong log; `start.log` chỉ còn placeholder. Kiểm lại không có secret trước khi merge.

## 5. Giới hạn và NOT RUN

- Chưa kiểm concurrency qua HTTP/PostgREST thật (DB runner có ca đồng thời ở tầng PostgreSQL, không thay thế HTTP concurrency).
- Chưa kiểm browser/device thật, offline/reopen/deep link, mobile/web e2e.
- Chưa kiểm ngân hàng thật/webhook, real money.
- Chưa apply staging/production, chưa backup/restore, chưa deploy/merge main.
- Chưa rehearsal vận hành/pilot; chưa nghiệm thu toàn BH-07.
- Fixture dùng SQL seed trực tiếp cho dữ liệu ứng dụng; đây là giới hạn phạm vi kiểm chứng, không phải bằng chứng thay cho luồng onboarding đầy đủ.

## 6. Kết luận bàn giao

Đề nghị reviewer độc lập kiểm **ma trận HTTP/Auth local** và ghi kết luận Đạt/Chưa đạt cho phạm vi này. Trạng thái hiện hành là **Chờ review kiểm chứng HTTP/Auth BH-07**; không tự ghi Đạt, không merge main, không apply DB thật và không deploy.
