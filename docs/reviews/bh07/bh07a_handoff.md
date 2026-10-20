# BH-07A — bàn giao Chờ review (20/10/2026)

> **Reviewer 20/10/2026: Đạt phần A local tại `4512c3a`**, theo [review/bằng chứng](review_4512c3a.md). Chỉ DB/RPC/projection; B/C/D và pilot chưa nghiệm thu. Các trạng thái Chờ review và kết quả phía tác giả dưới đây giữ làm lịch sử. Không tự chuyển phần, merge main hoặc deploy.

**Trạng thái: Chờ review BH-07A.** Người triển khai không tự ghi Đạt/Done và không chuyển B/C/D.

- Nhánh: `feat/bh07a-db`
- Base SHA: `62d2c67dc66d512cf7f6f19932e2131ae060e2e9`
- Tested code SHA: `c339a47fdcb08e50811079bd89df7a1f9f53908a`
- Migration: `supabase/migrations/20261020180000_bh07_reads.sql`
- Runner: `docs/reviews/bh07/run_bh07_tests.py`
- Audit/contract: [bh07a_audit.md](bh07a_audit.md)

## 1. Thay đổi

Chỉ phần A, không đổi Flutter/UI, không merge main, không apply staging/production:

1. Thêm `public.get_session_summary(uuid)`:
   - management thấy present/no_show/confirmed count;
   - finance thấy thêm `billing_state`, revision, expenses, due, paid, outstanding;
   - management-only nhận khóa tiền `null`;
   - participant/outsider/cross-club/anon bị chặn;
   - không trả contact, bank, receiver, player list, charges/payments thô.
2. Thêm `public.list_my_session_history(limit, offset, club_id, from, to)`:
   - completed/cancelled, mới nhất trước, phân trang trước aggregate;
   - host/management/finance theo từng buổi;
   - filter CLB/khoảng ngày; whitelist field như `list_my_sessions`.
3. Giữ nguyên `complete_session`, `start_session`, `get_session_finance`, payment/ledger,
   refinalize, reverse expense và các gate hiện hành. Không nới quyền, không thêm cột/bảng/backfill.
4. Thêm runner BH-07 với 23 ca CLEAN + upgrade; test tái hiện trước migration được giữ trong
   `evidence/bh07_prefix.log` (9 PASS / 13 FAIL).

## 2. Lệnh đã chạy và kết quả

Môi trường: Windows, PostgreSQL 17 trong Docker `bh02-test-postgres`, `BH02_TEST_CONTAINER=bh02-test-postgres`, Auth stub + `SET ROLE`. Không phải HTTP/PostgREST/JWT thật.

| Lệnh | Exit | Kết quả |
|---|---:|---|
| `flutter analyze` | 0 | No issues found |
| `flutter test` | 0 | **190/190 PASS** |
| `python docs\reviews\bh07\run_bh07_tests.py` | 0 | **23/23 PASS** (21 CLEAN + 2 upgrade) |
| `python docs\reviews\bh02\run_rls_tests.py` | 0 | **33/33 PASS** |
| `python docs\reviews\bh02\extended_tests_15ef59b.py` | 0 | **14/14 PASS** |
| `python docs\reviews\bh03\run_bh03_tests.py` | 0 | **48/48 PASS** |
| `python docs\reviews\bh03\run_bh03_retry_tests.py` | 0 | **22/22 PASS** |
| `python docs\reviews\bh04\run_bh04_tests.py` | 0 | **44/44 PASS** |
| `python docs\reviews\bh05\run_bh05_tests.py` | 0 | **90/90 PASS** |
| `python docs\reviews\bh06\run_bh06_tests.py` | 0 | **84/84 PASS** |
| `python docs\reviews\bh06\integration_evidence\run_integration_tests.py` | 0 | **7/7 PASS** |
| `python docs\reviews\bh06\integration_evidence\run_upgrade_tests.py` | 0 | **3/3 PASS** |

Tổng hồi quy DB BH-02..06: **335/335** (33+14+48+22+44+90+84). Tổng kiểm tra mới BH-07:
**23/23**. Không dùng kết quả lịch sử BH-06 thay cho lần chạy này; các log/JSON dưới đây là lần chạy mới.

## 3. Bằng chứng

- `evidence/flutter_analyze.log`, `evidence/flutter_test.log`
- `evidence/bh07_prefix.log`, `evidence/bh07_prefix_results_20261020100620.json` (test-first FAIL)
- `evidence/bh07_final_run.log`, `bh07_test_results_20261020101646.json` (23/23, base_sha = tested code SHA, worktree sạch)
- `evidence/regression_bh02.log`, `regression_bh02_extended.log`
- `evidence/regression_bh03.log`, `regression_bh03_retry.log`
- `evidence/regression_bh04.log`, `regression_bh05.log`, `regression_bh06.log`
- `evidence/regression_bh06_integration.log`, `regression_bh06_upgrade.log`
- JSON tương ứng trong `evidence/regression_*_results.json`

## 4. Trọng tâm reviewer

1. `complete_session` vẫn chỉ `in_progress`, billing current, đúng management/version/idempotency;
   không bắt buộc thu đủ tiền; replay không lặp audit.
2. `list_my_session_history`: ACL theo từng buổi, chỉ completed/cancelled, phân trang đúng,
   `confirmed_count` sau trang, filter ngày/CLB, không lộ contact/bank.
3. `get_session_summary`: semantics `total_paid_vnd` (confirmed toàn buổi) và
   `outstanding_total_vnd` (active revision); management-only không thấy tiền; stale/not_finalized
   trả đúng nhãn; không rò dữ liệu riêng.
4. Sau complete: submit/confirm/cash/reject/reverse/refinalize giữ payment/ledger, không thu dư,
   không giảm due dưới paid; post expense thường vẫn bị chặn.
5. Migration forward-only, không backfill/ghi dữ liệu; dữ liệu completed cũ đọc được sau upgrade.

## 5. NOT RUN / giới hạn

- HTTP/PostgREST/JWT/Supabase Auth thật; Flutter repository/provider/UI thật.
- Thiết bị/browser/deep link, mất mạng/mở lại app.
- Ngân hàng/VietQR thật, webhook/chuyển tiền thật.
- Apply staging/production, backup/restore rehearsal, concurrency qua HTTP.
- Không chạy lại 2 probe độc lập lịch sử của reviewer BH-06.

Các kết quả chỉ có hiệu lực trong PostgreSQL local + Auth stub; không phải nghiệm thu pilot
hoặc cho phép deploy. Sau review, người triển khai sửa P0/P1/P2 theo AGENTS, tối đa 2 vòng.
