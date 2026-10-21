# BH-07 — kiểm chứng HTTP/Auth trên Supabase local

> **Trạng thái: Chờ review HTTP/Auth BH-07 vòng 1/2 (21/10/2026).** Người triển khai không tự ghi Đạt. Base `593bea86ffb807675387dba6b0276b555fdc87a1`; tested source `f9159dd483baf2dd219b2854fd8ab08d1e5f0330`; nhánh `feat/bh07-http-verification`. Kết quả dưới đây chỉ là kiểm chứng local, không thay đổi kết luận BH-07D tại `3d590a8` và không nghiệm thu toàn BH-07/pilot.

## 1. Phạm vi vòng 1/2

Chỉ sửa gói kiểm chứng theo H1/H2 P2 của [review vòng 1](review_3ad25a4.md). Không sửa migration, RPC, model, repository, provider, UI hay contract; không đổi hành vi backend.

- **H1 — free-current charge0:** seed thêm một `session_charges` amount `0` cho đúng player `30000000-0000-4000-8000-000000000003` và revision `40000000-0000-4000-8000-000000000002`. Precondition kiểm player exempt/present, revision current, đúng một charge 0. Sau complete + retry, kiểm lại finance và đọc DB: revision active và đúng một charge 0 vẫn còn, không bị mất/zero giả.
- **H2 — raw privacy:** kiểm whitelist chính xác từng row `list_my_session_history`; kiểm raw `get_session_summary` cho finance và cohost/management. Cohost phải có đủ 8 finance key với giá trị `null`. Quét đệ quy key private (`contact`, `phone`, `bank`, `account`, `receiver`).
- **Negative control:** payload tổng hợp có bank/account/receiver ở top-level, trong object lồng nhau và ở row thứ hai đều phải bị validator từ chối. Đây là kiểm logic validator, không phải tuyên bố server thật đã rò dữ liệu.
- **Seed private giả:** member contact, bốn player contact, club bank, host bank và receiver snapshot giả để chứng minh projection không rò dữ liệu nguồn thật. Test kiểm các marker này tồn tại trong bảng nguồn.
- Giữ nguyên toàn bộ check/control cũ, repository/Auth/HTTP thật và các kết luận A/B/C/D local.

## 2. Kết quả

| Hạng mục | Kết quả | Exit | Bằng chứng |
|---|---|---|---|
| HTTP/Auth matrix | **70/70 PASS** tại `f9159dd`, `worktree_dirty_before_run=false` | 0 | [`summary.json`](http_auth_evidence/summary.json), [`flutter_test.log`](http_auth_evidence/flutter_test.log) |
| `flutter analyze` | sạch, không issue | 0 | [`flutter_analyze.log`](http_auth_evidence/flutter_analyze.log) |
| Full Flutter suite | **240 pass +1 skip** | 0 | [`flutter_test_full.log`](http_auth_evidence/flutter_test_full.log) |
| BH-07 DB runner | **23/23 PASS**, `worktree_dirty=false`, timestamp `20261021083531` | 0 | [`bh07_db_runner_results.json`](http_auth_evidence/bh07_db_runner_results.json), [`bh07_db_runner.log`](http_auth_evidence/bh07_db_runner.log) |
| Red run trước seed fix | **67/70**, đúng 3 FAIL H1/H2 | 1 | [`red_run_summary.json`](http_auth_evidence/red_run_summary.json), [`red_run_flutter_test.log`](http_auth_evidence/red_run_flutter_test.log) |

Nhóm 70 check: auth 8, ACL 9, privacy 5, scope 4, complete 11, finance 16, summary 5, history 11, list 1.

Ba FAIL của red run: `privacy.fixture-private-data`, `complete.free-current.precondition`, `complete.free-current.charge-preserved`. Red run dùng seed cũ + test mới trên working tree tại `bd747a4` (dirty), trước khi seed charge0/private fixture; không phải bằng chứng green và không được dùng thay kết quả `f9159dd`.

## 3. Lệnh đã chạy

```powershell
# Green HTTP/Auth: local-only guard, reset DB local, tạo Auth users qua GoTrue,
# seed.sql, rồi chạy test HTTP thật.
.\scripts\bh07_http\run.ps1

flutter analyze
flutter test
python docs\reviews\bh07\run_bh07_tests.py
```

Red run được tạo bằng cách tạm hoàn nguyên `scripts/bh07_http/seed.sql` về bản trước sửa, chạy `.\scripts\bh07_http\run.ps1 -EvidenceDir <temp>`, rồi phục hồi seed mới. Không dùng lại kết quả red cho green.

## 4. Môi trường

- Supabase local thật qua Kong: GoTrue `v2.197.0`, PostgREST `v16.4`, PostgreSQL `17.11.0.004`; không mock repository/Auth, không dùng staging/production.
- Flutter `3.47.6` stable; Windows/PowerShell; Supabase CLI local `2.121.0`; Docker `29.8.2`.
- Bảy actor đăng nhập mật khẩu qua GoTrue và nhận JWT thật: ownerA, financeA, cohostA, memberA, guestA, ownerB, outsider. Sai mật khẩu bị từ chối.
- Service-role chỉ đọc fixture nguồn/bộ đếm side effect; không dùng để mutation hoặc bỏ qua ACL.
- Chi tiết máy/phiên bản: [`environment.json`](http_auth_evidence/environment.json).

## 5. Bằng chứng và manifest

- [`commands.md`](http_auth_evidence/commands.md), [`exits.json`](http_auth_evidence/exits.json), [`hashes.sha256`](http_auth_evidence/hashes.sha256).
- Log HTTP, analyze, full test, DB runner, red run và JSON kết quả nằm trong [`http_auth_evidence/`](http_auth_evidence/).
- Manifest SHA-256 dùng LF, phủ source test/seed/runner, handoff và toàn bộ file evidence; không còn ngoại lệ CRLF.

## 6. Giới hạn và NOT RUN

- Chưa chạy đồng thời/concurrency qua HTTP thật; chưa có browser/device/offline/deep link e2e.
- Chưa kiểm ngân hàng thật/VietQR/webhook; chưa apply staging/production, backup/restore, rehearsal/pilot.
- Bằng chứng `confirmPayment` idempotent vẫn dựa trên payment ID/count, không dựa `alreadyConfirmed`.
- Từ chối anonymous `complete_session` vẫn là `permission denied for function complete_session` như các vòng trước.
- Recipe Windows/full Supabase CLI có thể khác reviewer Linux; cần reviewer tự chạy lại và ghi khác biệt môi trường.
- Toàn BH-07/pilot chưa nghiệm thu. Không merge main, apply DB thật hoặc deploy.

## 7. Trọng tâm reviewer vòng 1/2

1. Kiểm H1: charge0 đúng player/revision, precondition đầy đủ, charge còn sau complete/retry ở cả DTO và DB.
2. Kiểm H2: whitelist thật sự áp cho **mọi** history row và raw summary finance/cohost; cohost có đủ finance key null; negative control thực sự bắt top-level/nested/later-row.
3. Kiểm seed private giả có tồn tại trong bảng nguồn và không xuất hiện trong projection.
4. Tự chạy lại HTTP matrix, analyze, full Flutter và DB runner; đối chiếu SHA, exit, count, manifest LF và secret scan.
5. Ghi kết luận Đạt/Chưa đạt cùng P0/P1/P2/NOT RUN; người triển khai không tự ghi Đạt.
