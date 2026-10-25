# Bàn giao kiểm chứng V5b — Full Supabase CLI Reset local BH-07 (Sửa P2-1..P2-7)

Ngày 25/10/2026 (Asia/Saigon). Người triển khai tự sửa và tự kiểm chứng dứt điểm 7 điểm P2 (P2-1 đến P2-7) theo [review 8e26e06](review_8e26e06.md). **Người triển khai tự sửa/tự kiểm — Chờ review độc lập**, KHÔNG tự ghi "Đạt".

- Base review: **`e00db30d018da86f8fa94250a000f0bf825fc139`** ([review 8e26e06](review_8e26e06.md)).
- Baseline origin: `6e5dba6c1b67c06bf98283b6bacac47ae2be3dc6`.
- Tested source SHA: **`cad3fa0a7c57410af648ef214c02289021c1deea`**, worktree sạch (`git_dirty=false`).
- Nhánh: `feat/bh07-full-reset-verification`.
- Bundle bằng chứng mới riêng biệt: [`full_reset_p2_fix_evidence/`](full_reset_p2_fix_evidence/). Giữ nguyên vẹn toàn bộ 5 bundle evidence lịch sử (`full_reset_evidence`, `codex_v5b_fix_evidence`, `review_8e26e06_evidence`, `review_19ab207_evidence`, `review_3b515f2_evidence`) đã được xác minh readonly 100%.
- Giữ nguyên các gate R1/R2/R3/R5 đã đóng và các gate ownership, inventory fail-closed, cleanup, primary_error, strict auth tuple.
- Phạm vi: Chỉ sửa runner kiểm chứng `scripts/bh07_reset/run_full_reset.py`, suite test `tests/test_v5b_runner_flaws.py`, tài liệu bàn giao và bundle bằng chứng. Tuyệt đối không thay đổi `lib/`, `test/` Flutter, migrations, RPC, contract hay fixture nghiệp vụ.
- Toàn bộ BH-07 chưa nghiệm thu; V1 giữ Đạt local; các cổng khác giữ NOT RUN; không merge main, staging, production, deploy, pilot hay BH-08.

---

## 1. Bảng khắc phục chi tiết P2-1 đến P2-7 theo review `8e26e06`

| Mã | Mức | Phát hiện review `8e26e06` | Thay đổi đã thực hiện | Test kiểm chứng / Tái hiện | Bằng chứng (Evidence) | Giới hạn |
|---|---|---|---|---|---|---|
| **P2-1** | **P2** | Oracle chỉ so row count, không so `sha256`; tài liệu claim "100% sha256" là sai vì 24/48 bảng khác data hash do dynamic timestamp/UUID. | Thêm hàm `compare_oracle_snapshots()`: xác định rõ phạm vi đối chiếu `oracle_scope = "schema_sha256_and_row_counts"`; kiểm tra nghiêm ngặt `schema_sha256` và row counts 48/48 bảng (bất kỳ mismatch nào đều FAIL); liệt kê và công bố minh bạch 24 bảng có dynamic data differences. Sửa toàn bộ claim trong tài liệu. | Test `test_p2_1_oracle_schema_and_counts_scope_and_mismatch_failure` trong `test_v5b_runner_flaws.py` (tái hiện count/schema mismatch phải FAIL). | [`snapshot_comparison.json`](full_reset_p2_fix_evidence/snapshot_comparison.json), [`summary.json`](full_reset_p2_fix_evidence/summary.json) | Oracle xác nhận tính lặp lại của schema DDL và tổng số dòng sau seed/hoàn tất buổi, không áp dụng cho các trường thời gian thực/UUID ngẫu nhiên của GoTrue. |
| **P2-2** | **P2** | `base_sha` hardcode `6e5dba6...` không phải base review `6a13901...` hay `e00db30...`. | Thêm hàm `resolve_base_review()`: nhận base review linh hoạt qua tham số CLI `--base-review <sha>` hoặc biến môi trường `BASE_REVIEW_SHA`; xác minh commit SHA có tồn tại qua `git rev-parse --verify`; phân biệt rõ ràng `baseline_origin_sha`, `base_review_sha` và `tested_source_sha`. | Test `test_p2_2_base_review_resolution_and_validation` (kiểm tra CLI argument parsing và từ chối SHA không tồn tại). | [`environment.json`](full_reset_p2_fix_evidence/environment.json), [`summary.json`](full_reset_p2_fix_evidence/summary.json) | Cần môi trường git khả dụng để resolve SHA. |
| **P2-3** | **P2** | Không persist chi tiết DB assertions cho Cycle 2; thiếu file HTTP audit chi tiết từng request. | Thêm hàm `sanitize_http_audit_record()`: ghi nhận an toàn từng request HTTP (`actor_alias`, `operation`, `http_status`, `pass`, `error_code`, `notes`), tuyệt đối không chứa token, password, contact/bank; lưu `http_audit_cycle1.json` và `http_audit_cycle2.json`; lưu chi tiết 23 DB assertions cho cả 2 chu kỳ: `db_assertions_cycle1.json` và `db_assertions_cycle2.json`. | Test `test_p2_3_evidence_persistence_and_sanitization` (kiểm tra loại bỏ token/password/secret khỏi audit record). | [`http_audit_cycle1.json`](full_reset_p2_fix_evidence/http_audit_cycle1.json), [`http_audit_cycle2.json`](full_reset_p2_fix_evidence/http_audit_cycle2.json), [`db_assertions_cycle1.json`](full_reset_p2_fix_evidence/db_assertions_cycle1.json), [`db_assertions_cycle2.json`](full_reset_p2_fix_evidence/db_assertions_cycle2.json) | Không lưu raw secret HTTP bodies để tránh rò rỉ token. |
| **P2-4** | **P2** | Cổng S3 `56428` được claim/check nhưng không được cấu hình (S3 đi qua Kong). | Loại bỏ `PORT_S3 = 56428` và port check 56428 khỏi preflight; ghi đúng endpoint S3 qua Kong gateway (`http://127.0.0.1:56421/storage/v1/s3`); thêm assertion kiểm tra `config.toml` sinh ra khớp chính xác các cổng thực dùng (56420–56429) và không còn default port 54321/54322/54323. | Test `test_p2_4_s3_storage_routing_and_config_port_assertion` (kiểm tra loại bỏ PORT_S3 và preflight chỉ kiểm 7 port thực dùng). | [`environment.json`](full_reset_p2_fix_evidence/environment.json), [`start.log`](full_reset_p2_fix_evidence/start.log) | Cổng S3 dùng chung cổng Kong HTTP API 56421. |
| **P2-5** | **P2** | Assertion DB yếu (`>=`, `>`); `req_orig` dùng `LIMIT 1` không xác định có thể chọn nhầm session khác. | Thay đổi toàn bộ các điều kiện yếu bằng giá trị exact theo fixture: `charges == 150000`, `payments == 70000`, `pay_cnt == 2`, `tx_cnt == 2`, `court_count == 4`, `visibility == 'public'`. Sửa truy vấn `req_orig`: lọc chính xác theo `result->>'id' = '{session_debt}'` và `ORDER BY created_at ASC, request_id ASC` để chọn đúng request ban đầu và deterministic. | Test `test_p2_5_db_assertions_exact_fixture_and_req_orig_deterministic` (kiểm tra loại bỏ các điều kiện yếu và bắt buộc query binding). | [`db_assertions_cycle1.json`](full_reset_p2_fix_evidence/db_assertions_cycle1.json), [`db_assertions_cycle2.json`](full_reset_p2_fix_evidence/db_assertions_cycle2.json) | Bắt buộc 23/23 assertions phải khớp chính xác giá trị kỳ vọng. |
| **P2-6** | **P2** | Provenance chưa bind: CLI không pin version, thiếu image digest của owned containers, schema hash drift giữa các môi trường. | Khai báo hằng số `SUPABASE_CLI_PIN = 'supabase@2.122.0'` và pin toàn bộ các lệnh gọi CLI (`npx --yes supabase@2.122.0 ...`); thêm hàm `inspect_container_images()` trích xuất `image_tag`, `image_id` và `repo_digests` thực tế từ `docker inspect`; phân biệt rõ oracle schema hash cùng môi trường với hash xuyên môi trường. | Test `test_p2_6_reproducibility_pinning_and_image_metadata` (kiểm tra CLI call pinned và helper inspect). | [`environment.json`](full_reset_p2_fix_evidence/environment.json) | RepoDigest phụ thuộc vào việc image có được pull từ remote registry hay build local. |
| **P2-7** | **P2** | `run_cmd` dùng `shell=is_batch` và không có timeout; rủi ro treo process vĩnh viễn trên Windows. | Loại bỏ `shell=is_batch` và `shell=True`, thiết lập `shell=False` tuyệt đối; thêm timeout hữu hạn cho từng loại lệnh (default 300s, status 60s, psql 30s); thêm hàm `kill_proc_tree()` dừng sạch process tree của chính lượt chạy khi timeout; timeout được fail-closed, vẫn teardown cleanup và giữ nguyên `primary_error`. | Test `test_p2_7_process_execution_no_shell_timeout_and_special_args` (kiểm tra timeout raising TimeoutError, shell=False và truyền an toàn đối số chứa ký tự đặc biệt). | [`environment.json`](full_reset_p2_fix_evidence/environment.json), [`exits.json`](full_reset_p2_fix_evidence/exits.json) | Sử dụng `taskkill /F /T /PID` trên Windows để dừng triệt để cây tiến trình con. |

---

## 2. Kết quả kiểm chứng Full Supabase CLI Reset (2 chu kỳ)

Quá trình thực thi hai chu kỳ reset trên stack local cô lập (`PROJECT_ID = "bh07-reset-verify-f03bae2b91234e47"`, dải port `56420–56429`):

| Hạng mục kiểm chứng | Kết quả thực thi | Exit | Bằng chứng |
|---|---|---|---|
| **Preflight Ownership Check** | 0 container trùng lặp, 7/7 port loopback khả dụng (56420, 56421, 56422, 56423, 56424, 56427, 56429) | 0 | [`summary.json`](full_reset_p2_fix_evidence/summary.json), runner stdout |
| **Supabase CLI Pinning** | `npx --yes supabase@2.122.0 --version` trả về đúng `2.122.0` | 0 | [`environment.json`](full_reset_p2_fix_evidence/environment.json) |
| **Cycle 1 Reset & Migration** | Exit 0, 18/18 migrations áp dụng thành công từ zero | 0 | [`reset_cycle1.log`](full_reset_p2_fix_evidence/reset_cycle1.log) |
| **Cycle 1 Auth & Seed** | Tạo 7 GoTrue Auth users + nạp seed.sql thành công | 0 | [`auth_seed_cycle1.log`](full_reset_p2_fix_evidence/auth_seed_cycle1.log) |
| **Cycle 1 Schema Verification** | Schema hợp lệ, SHA256: `745aa0535c0642c3...`, tổng 48 bảng | 0 | [`summary.json`](full_reset_p2_fix_evidence/summary.json) |
| **Cycle 1 HTTP Audit** | 13/13 operations PASS (login 7 actors, complete_session 200, replay 200, cash payment 200, summary ACL: Owner 200, Cohost 200 count-only, Member 403 Forbidden, Finance 200) | 0 | [`http_audit_cycle1.json`](full_reset_p2_fix_evidence/http_audit_cycle1.json) |
| **Cycle 1 DB Assertions** | **23/23 assertions PASS** exact (charges=150000, payments=70000, pay_cnt=2, tx_cnt=2, courts=4, visibility='public') | 0 | [`db_assertions_cycle1.json`](full_reset_p2_fix_evidence/db_assertions_cycle1.json) |
| **Cycle 2 Reset & Migration** | Exit 0, 18/18 migrations áp dụng thành công (hash log trùng 100% với Cycle 1) | 0 | [`reset_cycle2.log`](full_reset_p2_fix_evidence/reset_cycle2.log) |
| **Cycle 2 Auth & Seed** | Tạo 7 GoTrue Auth users + nạp seed.sql thành công | 0 | [`auth_seed_cycle2.log`](full_reset_p2_fix_evidence/auth_seed_cycle2.log) |
| **Cycle 2 Schema & DB Assertions** | **23/23 assertions PASS**, schema SHA256: `745aa0535c0642c3...` | 0 | [`db_assertions_cycle2.json`](full_reset_p2_fix_evidence/db_assertions_cycle2.json) |
| **Repeat Reset Oracle** | Scope: `schema_sha256_and_row_counts`. Schema SHA256 khớp 100%, 48/48 bảng trùng khớp 100% về số dòng. Công bố 24 bảng có data SHA256 khác do trường dynamic. | 0 | [`snapshot_comparison.json`](full_reset_p2_fix_evidence/snapshot_comparison.json) |
| **Positive Baseline HTTP** | Gửi token Owner A thật đến RPC `get_session_summary`: status 200, `can_view_finance=True` | 0 | Runner stdout, [`summary.json`](full_reset_p2_fix_evidence/summary.json) |
| **Negative Controls** | Anon complete_session bị từ chối (401, code 42501), no-apikey bị từ chối (401, code 42501), outsider bị Forbidden (403, code 42501, message 'FORBIDDEN'), guard loopback PASS | 0 | [`negative_controls.log`](full_reset_p2_fix_evidence/negative_controls.log) |
| **Teardown & Cleanup** | `supabase stop --no-backup`, 0 container sót lại (quét `docker ps -a`), tempdir purged, 0 cleanup errors | 0 | [`stop.log`](full_reset_p2_fix_evidence/stop.log), [`exits.json`](full_reset_p2_fix_evidence/exits.json) |
| **Manifest & Readonly** | 17/17 files trong bundle mới khớp SHA-256; 5 bundle cũ (`full_reset_evidence` 12/12, `codex_v5b_fix_evidence` 10/10, `review_8e26e06_evidence` 12/12, `review_19ab207_evidence` 8/8, `review_3b515f2_evidence` 8/8) verified readonly 100% | 0 | [`hashes.sha256`](full_reset_p2_fix_evidence/hashes.sha256), [`manifest_readonly.json`](full_reset_p2_fix_evidence/manifest_readonly.json) |
| **Secret Scan** | 0 JWT 3 đoạn, 0 passwords, 0 sb_secret, 0 private keys | 0 | Quét regex tự động 100% clean |
| **Python Behavior Tests** | 17/17 tests PASS trong `tests/test_v5b_runner_flaws.py` | 0 | Lệnh trực tiếp local |
| **Flutter Analyze & Test** | `flutter analyze` 0 issues; `flutter test` 240 passed, 1 skipped | 0 | Lệnh trực tiếp local |

---

## 3. Tái lập kiểm chứng độc lập dành cho Reviewer

Reviewer độc lập có thể tự tái lập toàn bộ quy trình kiểm chứng bằng các lệnh sau trên nhánh `feat/bh07-full-reset-verification`:

```powershell
# 1. Chạy toàn bộ 17 behavioral và defect tests (R1, R2, R3, R5, P2-1..P2-7)
python -m unittest tests/test_v5b_runner_flaws.py

# 2. Chạy full runner kiểm chứng V5b reset 2 chu kỳ trên stack local cô lập
python -u scripts/bh07_reset/run_full_reset.py --base-review e00db30d018da86f8fa94250a000f0bf825fc139

# 3. Kiểm tra tính toàn vẹn của manifest bằng chứng mới và tính bất biến của các bundle lịch sử
python -c "
import hashlib
from pathlib import Path
ev_dir = Path('docs/reviews/bh07/full_reset_p2_fix_evidence')
manifest = (ev_dir / 'hashes.sha256').read_text(encoding='utf-8')
for line in manifest.strip().splitlines():
    h, name = line.split(None, 1)
    actual = hashlib.sha256((ev_dir / name).read_bytes()).hexdigest()
    assert actual == h, f'Mismatch in {name}'
print('Manifest verification: ALL PASS')
"

# 4. Quét bí mật tự động trên bundle mới
python -c "
import re
from pathlib import Path
files = list(Path('docs/reviews/bh07/full_reset_p2_fix_evidence').glob('*'))
pats = [re.compile(r'ey[A-Za-z0-9_-]{20,}\.ey[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}'), re.compile(r'password[\"\'\s:=]+[A-Za-z0-9_!@#$%^&*]{8,}', re.I)]
found = []
for f in files:
    if f.name == 'hashes.sha256': continue
    txt = f.read_text(encoding='utf-8', errors='ignore')
    for p in pats:
        m = p.search(txt)
        if m and 'synthetic' not in m.group(0).lower() and 'none' not in m.group(0).lower():
            found.append((f.name, m.group(0)[:30]))
assert len(found) == 0, f'Secrets found: {found}'
print('Secret scan: ALL PASS')
"

# 5. Xác minh dọn dẹp sạch sẽ, không rò rỉ container hay tài nguyên
docker ps -a --filter "name=bh07-reset-verify"
```

---

## 4. Prompt cho Reviewer độc lập (Codex)

Reviewer độc lập hãy sử dụng prompt sau để kiểm tra và đưa ra kết luận kỹ thuật:

```text
Bạn là AI reviewer độc lập (Codex) kiểm chứng gói V5b — Full Supabase CLI Reset local BH-07.

Nhánh: feat/bh07-full-reset-verification
Base review: e00db30d018da86f8fa94250a000f0bf825fc139
Tested source SHA: cad3fa0a7c57410af648ef214c02289021c1deea

Đọc AGENTS.md, docs/reviews/bh07/review_8e26e06.md, và docs/reviews/bh07/full_reset_handoff.md.

PHẠM VI REVIEW
Kiểm tra việc khắc phục 7 điểm P2 (P2-1 đến P2-7) trong review_8e26e06.md:
1. P2-1: Oracle scope là schema_sha256_and_row_counts; công bố minh bạch 24 bảng khác data hash. Test mismatch count/schema phải FAIL.
2. P2-2: Base review nhận qua tham số CLI/env, xác minh commit tồn tại; phân biệt rõ baseline gốc, base review và tested source.
3. P2-3: Persist chi tiết 23 DB assertions cho cả 2 chu kỳ; persist HTTP audit sanitized (không token, password, contact/bank).
4. P2-4: Bỏ cổng/claim S3 56428 không cấu hình; kiểm config generated khớp các port thực dùng.
5. P2-5: Thay điều kiện >=/> bằng exact count/giá trị theo fixture (charges=150000, payments=70000, pay_cnt=2, tx_cnt=2, court_count=4, visibility='public'); req_orig lọc chính xác theo result->>'id'='10000000-0000-4000-8000-000000000001' và ORDER BY created_at, request_id.
6. P2-6: Pin Supabase CLI 2.122.0; trích xuất image tag/ID/RepoDigests thực tế từ docker inspect; phân biệt oracle cùng môi trường.
7. P2-7: run_cmd loại bỏ shell=True/is_batch (dùng shell=False); timeout hữu hạn theo loại lệnh; kill_proc_tree dừng process tree của lượt chạy khi timeout; timeout fail-closed và giữ primary_error.

LỆNH REVIEWER PHẢI TỰ CHẠY
1. python -m unittest tests/test_v5b_runner_flaws.py (xác nhận 17/17 tests PASS).
2. flutter analyze (xác nhận 0 issues).
3. flutter test (xác nhận 240 PASS, 1 skip).
4. python -u scripts/bh07_reset/run_full_reset.py --base-review e00db30d018da86f8fa94250a000f0bf825fc139 (xác nhận exit 0, 2 chu kỳ reset 18 migration, 23/23 assertions, negative controls, cleanup sạch 0 container).
5. Kiểm tra tính toàn vẹn manifest 17/17 files trong full_reset_p2_fix_evidence/ và 5 bundle lịch sử readonly.
6. Quét bí mật tự động (0 secrets).

BÁO CÁO REVIEW
Tạo docs/reviews/bh07/review_<sha>.md theo mẫu:
- Kết luận: Đạt / Chưa đạt cho V5b local.
- Bảng rà soát P2-1..P2-7 (Đóng / Còn mở).
- Danh sách phát hiện mới nếu có (P0/P1/P2) theo file:dòng.
- Giữ V1 Đạt local; các cổng khác giữ NOT RUN; không merge main/staging/production/deploy/pilot/BH-08.
```
