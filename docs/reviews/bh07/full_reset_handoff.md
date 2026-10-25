# Bàn giao kiểm chứng V5b — Full Supabase CLI Reset local BH-07 (Đính chính H6 docs-only và QA runtime)

Ngày 25/10/2026 (Asia/Saigon). Người triển khai/QA tự đính chính H6 (docs-only) và hoàn tất full runner kiểm chứng 2 chu kỳ reset từ source sạch `8c107e9` theo [review 8c107e9](review_8c107e9.md). **Người triển khai tự sửa/tự kiểm — Chờ review độc lập**, KHÔNG tự ghi "Đạt".

- Base review thực tế / commit cha: **`a55c2d2416f37a0bb8ac985e80bdee579b40774b`** ([review cad3fa0](review_cad3fa0.md)).
  *(Ghi chú đính chính H6: SHA `a55c2d22b27bc89d53f58a74b0fa038ff31c0396` ghi trong tài liệu trước đây là lỗi typo/nhầm lẫn trong docs/prompt, đã bị runner từ chối với exit 1 trước preflight khi reviewer thử nghiệm theo review 8c107e9. Đã đính chính base đúng `a55c2d2416f37a0bb8ac985e80bdee579b40774b`).*
- Baseline origin: `6e5dba6c1b67c06bf98283b6bacac47ae2be3dc6`.
- Tested source SHA: **`8c107e9692b89f4a0aadeafc0ae139736f9b2622`**, worktree sạch (`git_dirty=false`, `dirty_files=[]`).
- Nhánh: `feat/bh07-full-reset-verification`.
- Bundle bằng chứng mới riêng biệt: [`full_reset_8c107e9_evidence/`](full_reset_8c107e9_evidence/). Giữ nguyên vẹn toàn bộ các bundle evidence lịch sử (`full_reset_evidence`, `codex_v5b_fix_evidence`, `review_8e26e06_evidence`, `review_19ab207_evidence`, `review_3b515f2_evidence`, `full_reset_p2_fix_evidence`, `review_8c107e9_evidence`).
- Giữ nguyên các gate R1/R2/R3/R5, P2-1..P2-7 và H1–H5 đã đóng: ownership, inventory fail-closed, cleanup, primary_error, strict auth tuple, timeout process isolation, finite deadlines, honest audit.
- Phạm vi: Chỉ đính chính docs và xuất bundle evidence mới từ source sạch `8c107e9`. Tuyệt đối không thay đổi code H1–H5 đã đóng (`scripts/bh07_reset/run_full_reset.py`, `tests/test_v5b_runner_flaws.py`), không đổi `lib/`, `test/` Flutter, migrations, RPC, contract hay fixture nghiệp vụ.
- Toàn bộ BH-07 chưa nghiệm thu; V1 giữ Đạt local; các cổng khác giữ NOT RUN; không merge main, staging, production, deploy, pilot hay BH-08.

---

## 1. Bảng khắc phục chi tiết H1–H6

| Mã | Mức | Phát hiện review | Thay đổi đã thực hiện | Test kiểm chứng / Tái hiện | Bằng chứng (Evidence) | Giới hạn |
|---|---|---|---|---|---|---|
| **H1** | **P1** | Subprocess timeout thiếu `start_new_session`; `os.killpg` gửi SIGTERM giết cả process group cha (test runner/reviewer), returncode -15, bỏ qua cleanup. | Thêm `start_new_session=True` (POSIX) và `creationflags=CREATE_NEW_PROCESS_GROUP` (Windows) trong `run_cmd()`; trong `kill_proc_tree()` kiểm tra `pgid = os.getpgid(pid)`, nếu `pgid == parent_pgid` thì chỉ kill child PID đơn lẻ, tuyệt đối không kill process group cha. | Test `test_h1_parent_and_sibling_survive_child_timeout` trong `tests/test_v5b_runner_flaws.py`: tạo sibling process nền, kích hoạt child timeout, xác nhận runner nhận `TimeoutError` và sibling process vẫn sống bình thường. | [`tests/test_v5b_runner_flaws.py`](../../../tests/test_v5b_runner_flaws.py), runner stdout | Cơ chế dựa vào process group tách biệt giữa parent và child subprocess. Đã đóng tại review `8c107e9`. |
| **H2** | **P2** | Timeout có đường treo vô hạn: child bỏ qua SIGTERM khiến `proc.communicate()` sau kill chờ vĩnh viễn; `taskkill` không timeout; `sql_run`/`sql_as` gọi raw `subprocess.run` không có timeout. | Áp dụng bounded termination: gửi SIGTERM, chờ tối đa 0.5s; nếu chưa dừng thì fallback ngay sang `SIGKILL` (hoặc `taskkill /F /T` với `timeout=5s`); bọc `proc.communicate(timeout=2s)` chống treo; đưa `sql()`, `sql_run()` và `sql_as()` qua `run_cmd` với `timeout=60s`. | Test `test_h2_child_ignoring_sigterm_terminated_within_deadline` (child bắt SIG_IGN vẫn bị kết thúc dưới 2.5s) và `test_h2_sql_helpers_have_timeout_and_use_run_cmd` (xác nhận SQL helpers dùng `run_cmd` có timeout). | [`scripts/bh07_reset/run_full_reset.py`](../../../scripts/bh07_reset/run_full_reset.py), runner stdout | Timeout 60s cho mỗi truy vấn SQL là đủ dài cho migrate/seed và đủ ngắn để chống treo. Đã đóng tại review `8c107e9`. |
| **H3** | **P2** | Claim audit lịch sử 100% không đúng: `review_8e26e06_evidence` trên Git chỉ có 5/12 file (thiếu 7 file log do `.gitignore` không force add), `bundle_hashes.sha256` chỉ có 18/32 file. | Đính chính claim audit trong `manifest_readonly.json` và handoff: công bố minh bạch `review_8e26e06_evidence` có 5/12 file (hashes.sha256) và 18/32 file (bundle_hashes.sha256) được track trên Git; 4 bundle khác (12/12, 10/10, 8/8, 8/8) đầy đủ 100%. Tuyệt đối không chế tạo log giả hay sửa manifest cũ. | Audit script `docs/reviews/bh07/review_cad3fa0_evidence/audit_bundles.py` đối chiếu trạng thái thực tế. | [`manifest_readonly.json`](full_reset_8c107e9_evidence/manifest_readonly.json) | Thiếu log trên Git là kế thừa lịch sử từ commit reviewer `8e26e06`, không quy lỗi cho lượt sửa hiện tại. Đã đóng tại review `8c107e9`. |
| **H4** | **P2** | `hashes.sha256` và `manifest_readonly.json` có CRLF (`\r\n`), strict verifier `clean_and_manifest.py --verify` thất bại (exit 1). | Chuẩn hóa toàn bộ file trong bundle mới sang định dạng UTF-8 LF (không BOM, không CRLF). Tính lại hash và ghi `hashes.sha256` bằng strict LF (`newline='\n'`). | Chạy `python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/full_reset_8c107e9_evidence` đạt ALL CHECKS PASSED (exit 0). | [`hashes.sha256`](full_reset_8c107e9_evidence/hashes.sha256), `clean_and_manifest.py` stdout | Strict verifier yêu cầu không chứa bất kỳ ký tự `\r` nào trong bundle. Đã đóng tại review `8c107e9`. |
| **H5** | **P2** | Test exact fixture P2-5 chỉ kiểm chuỗi tĩnh, không bắt sai count/target khi mutant code (`pay_cnt == 2` -> `pay_cnt == 999`). | Bổ sung test hành vi thực thi `test_h5_db_assertions_behavior_catches_wrong_counts_and_aggregates`: gọi hàm `verify_db_assertions()` với stub SQL query-scoped; kiểm tra positive baseline 23 assertions PASS; các đột biến sai count (`pay_cnt=999`), duplicate (`pay_cnt=3`), sai chi phí (`charges_sum=160000`), sai thanh toán (`payments_sum=50000`), sai tx (`tx_cnt=3`), và mutant source code `pay_cnt == 999` đều bị bắt và raise `AssertionError`. | Chạy `python -m unittest tests/test_v5b_runner_flaws.py` (21/21 tests PASS). | [`tests/test_v5b_runner_flaws.py`](../../../tests/test_v5b_runner_flaws.py) | Test hành vi thực thi trực tiếp logic AST của hàm, không dựa vào so sánh chuỗi literal. Đã đóng tại review `8c107e9`. |
| **H6** | **P2** | Base SHA trong handoff/AGENTS ghi nhầm `a55c2d22b27bc89d53f58a74b0fa038ff31c0396` không tồn tại trên Git; runner từ chối exit 1 trước preflight khi reviewer thử nghiệm. | **Docs-only**: Đính chính base review thành `a55c2d2416f37a0bb8ac985e80bdee579b40774b` trong thông tin hiện hành, tài liệu bàn giao và prompt. Chạy full runner trên source sạch `8c107e9` với base đúng, xuất bundle riêng `full_reset_8c107e9_evidence/`. | Lệnh `git cat-file -e a55c2d2416f37a0bb8ac985e80bdee579b40774b^{commit}` xác nhận tồn tại; runner chạy thành công exit 0. | [`full_reset_8c107e9_evidence/`](full_reset_8c107e9_evidence/), [`summary.json`](full_reset_8c107e9_evidence/summary.json) | Không thay đổi code logic runner hay migrations. Giữ ghi chú tham số sai từng được truyền/reviewer đã từ chối. |

---

## 2. Kết quả kiểm chứng Full Supabase CLI Reset (2 chu kỳ)

Quá trình thực thi hai chu kỳ reset trên stack local cô lập (`PROJECT_ID = "bh07-reset-verify-b7c271296ef940fa"`, dải port `56420–56429`):

| Hạng mục kiểm chứng | Kết quả thực thi | Exit | Bằng chứng |
|---|---|---|---|
| **Preflight Ownership Check** | 0 container trùng lặp, 7/7 port loopback khả dụng (56420, 56421, 56422, 56423, 56424, 56427, 56429) | 0 | [`summary.json`](full_reset_8c107e9_evidence/summary.json), runner stdout |
| **Supabase CLI Pinning** | `npx --yes supabase@2.122.0 --version` trả về đúng `2.122.0` | 0 | [`environment.json`](full_reset_8c107e9_evidence/environment.json) |
| **Cycle 1 Reset & Migration** | Exit 0, 18/18 migrations áp dụng thành công từ zero | 0 | [`reset_cycle1.log`](full_reset_8c107e9_evidence/reset_cycle1.log) |
| **Cycle 1 Auth & Seed** | Tạo 7 GoTrue Auth users + nạp seed.sql thành công | 0 | [`auth_seed_cycle1.log`](full_reset_8c107e9_evidence/auth_seed_cycle1.log) |
| **Cycle 1 Schema Verification** | Schema hợp lệ, SHA256: `745aa0535c0642c3...`, tổng 48 bảng | 0 | [`summary.json`](full_reset_8c107e9_evidence/summary.json) |
| **Cycle 1 HTTP Audit** | 13/13 operations PASS (login 7 actors, complete_session 200, replay 200, cash payment 200, summary ACL: Owner 200, Cohost 200 count-only, Member 403 Forbidden, Finance 200) | 0 | [`http_audit_cycle1.json`](full_reset_8c107e9_evidence/http_audit_cycle1.json) |
| **Cycle 1 DB Assertions** | **23/23 assertions PASS** exact (charges=150000, payments=70000, pay_cnt=2, tx_cnt=2, courts=4, visibility='public') | 0 | [`db_assertions_cycle1.json`](full_reset_8c107e9_evidence/db_assertions_cycle1.json) |
| **Cycle 2 Reset & Migration** | Exit 0, 18/18 migrations áp dụng thành công (hash log trùng 100% với Cycle 1) | 0 | [`reset_cycle2.log`](full_reset_8c107e9_evidence/reset_cycle2.log) |
| **Cycle 2 Auth & Seed** | Tạo 7 GoTrue Auth users + nạp seed.sql thành công | 0 | [`auth_seed_cycle2.log`](full_reset_8c107e9_evidence/auth_seed_cycle2.log) |
| **Cycle 2 Schema & DB Assertions** | **23/23 assertions PASS**, schema SHA256: `745aa0535c0642c3...` | 0 | [`db_assertions_cycle2.json`](full_reset_8c107e9_evidence/db_assertions_cycle2.json) |
| **Repeat Reset Oracle** | Scope: `schema_sha256_and_row_counts`. Schema SHA256 khớp 100%, 48/48 bảng trùng khớp 100% về số dòng. Công bố 24 bảng có data SHA256 khác do trường dynamic. | 0 | [`snapshot_comparison.json`](full_reset_8c107e9_evidence/snapshot_comparison.json) |
| **Positive Baseline HTTP** | Gửi token Owner A thật đến RPC `get_session_summary`: status 200, `can_view_finance=True` | 0 | Runner stdout, [`summary.json`](full_reset_8c107e9_evidence/summary.json) |
| **Negative Controls** | Anon complete_session bị từ chối (401, code 42501), no-apikey bị từ chối (401, code 42501), outsider bị Forbidden (403, code 42501, message 'FORBIDDEN'), guard loopback PASS | 0 | [`negative_controls.log`](full_reset_8c107e9_evidence/negative_controls.log) |
| **Teardown & Cleanup** | `supabase stop --no-backup`, 0 container sót lại (quét `docker ps -a`), tempdir purged, 0 cleanup errors | 0 | [`stop.log`](full_reset_8c107e9_evidence/stop.log), [`exits.json`](full_reset_8c107e9_evidence/exits.json) |
| **Manifest & Strict LF** | 17/17 files trong bundle mới khớp SHA-256; `clean_and_manifest.py --verify` ALL CHECKS PASSED; các bundle cũ được audit minh bạch | 0 | [`hashes.sha256`](full_reset_8c107e9_evidence/hashes.sha256), [`manifest_readonly.json`](full_reset_8c107e9_evidence/manifest_readonly.json) |
| **Secret Scan** | 0 JWT 3 đoạn ngoài allowlist, 0 passwords, 0 sb_secret, 0 private keys | 0 | Quét regex tự động 100% clean |
| **Python Behavior Tests** | **21/21 tests PASS** trong `tests/test_v5b_runner_flaws.py` (bao gồm H1, H2, H5) | 0 | Lệnh trực tiếp local |
| **Flutter Analyze & Test** | `flutter analyze --no-pub`: 0 issues; `flutter test --no-pub`: 240 passed, 1 skipped | 0 | Lệnh trực tiếp local |

---

## 3. Tái lập kiểm chứng độc lập dành cho Reviewer

Reviewer độc lập có thể tự tái lập toàn bộ quy trình kiểm chứng bằng các lệnh sau trên nhánh `feat/bh07-full-reset-verification`:

```powershell
# 1. Chạy toàn bộ 21 behavioral và defect tests (R1, R2, R3, R5, P2-1..P2-7, H1, H2, H5)
python -m unittest tests/test_v5b_runner_flaws.py

# 2. Kiểm tra analyze và test Flutter
flutter analyze --no-pub
flutter test --no-pub

# 3. Chạy full runner kiểm chứng V5b reset 2 chu kỳ trên stack local cô lập với base đúng
python -u scripts/bh07_reset/run_full_reset.py --base-review a55c2d2416f37a0bb8ac985e80bdee579b40774b --evidence-dir docs/reviews/bh07/full_reset_8c107e9_evidence

# 4. Kiểm tra strict UTF-8 LF và tính toàn vẹn của bundle mới qua tool chuẩn
python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/full_reset_8c107e9_evidence

# 5. Xác minh dọn dẹp sạch sẽ, không rò rỉ container hay tài nguyên
docker ps -a --filter "name=bh07-reset-verify"
```

---

## 4. Prompt cho Reviewer độc lập (Codex)

Reviewer độc lập hãy sử dụng prompt sau để kiểm tra và đưa ra kết luận kỹ thuật:

```text
Bạn là AI reviewer độc lập (Codex) kiểm chứng chốt gói V5b — Full Supabase CLI Reset local BH-07 sau đính chính H6 docs-only và QA runtime.

Nhánh: feat/bh07-full-reset-verification
Base review: a55c2d2416f37a0bb8ac985e80bdee579b40774b (review cad3fa0)
Tested source SHA: 8c107e9692b89f4a0aadeafc0ae139736f9b2622

Đọc AGENTS.md, docs/reviews/bh07/review_8c107e9.md, và docs/reviews/bh07/full_reset_handoff.md.

PHẠM VI REVIEW
Kiểm tra việc đính chính H6 docs-only và kết quả QA runtime trong bundle mới full_reset_8c107e9_evidence/:
1. H6 (P2): Base review đã được đính chính thành a55c2d2416f37a0bb8ac985e80bdee579b40774b trong tài liệu bàn giao, AGENTS.md và prompt; git cat-file -e a55c2d2416f37a0bb8ac985e80bdee579b40774b^{commit} thành công; metadata environment.json và summary.json khớp commit cha thực tế.
2. Source tested: Source sạch 8c107e9692b89f4a0aadeafc0ae139736f9b2622 (git_dirty=false), không đổi code runner H1–H5 đã đóng.
3. Runtime 2 chu kỳ: 18 migrations/chu kỳ, 23/23 assertions/chu kỳ exact fixture, Oracle 48 bảng row count + schema match 100%, real HTTP/Auth/negative controls, cleanup sạch 0 container.
4. Strict LF: Bundle full_reset_8c107e9_evidence/ đạt clean_and_manifest.py --verify ALL CHECKS PASSED (exit 0).
5. Giữ nguyên các gate R1/R2/R3/R5, P2-1..P2-7 và H1–H5 đã đóng.

LỆNH REVIEWER PHẢI TỰ CHẠY
1. python -m unittest tests/test_v5b_runner_flaws.py (xác nhận 21/21 tests PASS).
2. flutter analyze --no-pub (xác nhận 0 issues).
3. flutter test --no-pub (xác nhận 240 PASS, 1 skip).
4. python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/full_reset_8c107e9_evidence (xác nhận exit 0).
5. python -u scripts/bh07_reset/run_full_reset.py --base-review a55c2d2416f37a0bb8ac985e80bdee579b40774b --evidence-dir docs/reviews/bh07/full_reset_8c107e9_evidence (xác nhận exit 0 nếu máy đủ đĩa).
6. docker ps -a --filter "name=bh07-reset-verify" (xác nhận 0 container).

BÁO CÁO REVIEW
Tạo docs/reviews/bh07/review_<sha>.md theo mẫu:
- Kết luận: Đạt / Chưa đạt cho V5b local.
- Bảng rà soát H6 và các gate H1–H5, R1/R2/R3/R5, P2-1..P2-7.
- Danh sách phát hiện mới nếu có (P0/P1/P2) theo file:dòng.
- Giữ V1 Đạt local; các cổng khác giữ NOT RUN; không merge main/staging/production/deploy/pilot/BH-08.
```
