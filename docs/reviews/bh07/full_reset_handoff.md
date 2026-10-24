# Bàn giao kiểm chứng V5b — Full Supabase CLI Reset local BH-07 (Sửa R1–R4 vòng 1/2)

**V5b reset local Chưa đạt bản sửa vòng1/2 tại `19ab207`**, docs origin thực tế `e53f9944d3d599cf4183dfdbfb7d206306bb8e23`, theo [review](review_19ab207.md). **Đóng R4**:manifest12/12,đủ48 bảng/cycle,23 assertion vàdirty files trung thực. **Còn1 P1 R1 và3 P2 R2/R3/R5**:Docker returncode bị bỏ qua/ownership cleanup,positive giả +error-domain quá rộng,final inspect fail-open/che primary error,test không kiểm hành vi. Reviewer tự chạy tests4/4,analyze sạch,240 Flutter+1skip vàAST fault/mutant probes; full CLI runtime NOT RUN vìhost chỉ còn khoảng661MB. Giao AI triển khai sửa R1–R3/R5 vòng2/2; không sửa source trong vai reviewer. Giữ V1 Đạt local; toàn BH-07 chưa nghiệm thu; các cổng khác giữ NOT RUN. Không merge main/staging/production/deploy/pilot/BH-08.

> **Trạng thái: Chờ review độc lập V5b vòng 1/2 (24/10/2026).** Người triển khai không tự ghi Đạt.
> Base review: `a57f0c2c58956b5f047ffed365374470be702141` (review `0392e21`);
> Tested source SHA: `19ab207ea75023f8a21d15da01ebc20fc09b0db4`;
> Nhánh: `feat/bh07-full-reset-verification`.
> Kết quả dưới đây là kiểm chứng local trên project Supabase CLI test độc lập, không thay đổi kết luận các cổng khác và không tự nghiệm thu toàn BH-07/pilot/deploy.

---

## 1. Tóm tắt khắc phục phát hiện review `0392e21` (R1–R4)

| Mã | Phát hiện | Khắc phục đã thực hiện | Kiểm chứng / Tái hiện |
|---|---|---|---|
| **R1 (P1)** | Thiếu preflight ownership/resource, nguy cơ đụng chạm project có sẵn hoặc DB chung | Bổ sung hàm `preflight_ownership_check()` trước khi start/tạo tempdir: kiểm tra `docker ps -a` cho `bh07-reset-verify` và socket probe 8 port loopback (`56420–56429`). Nếu phát hiện tài nguyên tồn tại từ trước -> ABORT ngay lập tức. Sau khi start, lưu `owned_containers` để đảm bảo chỉ dọn dẹp tài nguyên thuộc quyền sở hữu của run này. | `tests/test_v5b_runner_flaws.py` (test_r1_preflight_ownership_flaw_and_fix) PASS; preflight PASS trên máy sạch. |
| **R2 (P2)** | Negative controls chỉ kiểm tra status code lỏng lẻo, nhận nhầm INVALID_INPUT/NOT_FOUND/404 | Siết chặt assertion negative controls: kiểm tra cả HTTP status (401/403) và mã lỗi PostgreSQL `42501` hoặc domain message (`FORBIDDEN`, `No API key found in request`), từ chối dứt khoát `INVALID_INPUT`, `NOT_FOUND`, `PGRST202`, `route 404`. Bổ sung positive baseline control với Owner A chứng minh endpoint/route và payload hoàn toàn hợp lệ. | `tests/test_v5b_runner_flaws.py` (test_r2_strict_negative_controls) PASS; runner log ghi nhận mã lỗi 42501 cho cả 3 ca negative auth. |
| **R3 (P2)** | Cleanup chỉ `docker ps -q` (bỏ qua stopped containers), không fail-closed, nuốt primary error | Viết lại toàn bộ khối `finally`: dùng `docker ps -a` để phát hiện và force-remove mọi container (kể cả stopped), xóa thư mục tạm `temp_dir`, ghi nhận `cleanup_errors`. Nếu có `primary_error` từ khối `try`, bảo lưu và re-raise `primary_error` để không bị lỗi cleanup che giấu. | `tests/test_v5b_runner_flaws.py` (test_r3_cleanup_fail_closed_and_primary_error) PASS; đã chứng minh re-raise primary_error khi gặp lỗi. |
| **R4 (P2)** | Manifest thiếu 7 file log do `.gitignore`, lệch count 23/24, Oracle chỉ lưu mẫu 5 bảng | Force-add (`git add -f`) đầy đủ 7 file log vào Git repository; gộp mục kiểm tra nợ trong `verify_db_assertions()` để thống nhất đúng chuẩn 23/23 assertions (chi tiết 23 assertions lưu trong `summary.json`); lưu toàn bộ số liệu 48/48 bảng của cả 2 chu kỳ vào `snapshot_comparison.json`; ghi nhận `git_dirty` và danh sách dirty files trung thực trong `environment.json`. | Manifest 12/12 files audit PASS 100%, 0 missing, 0 extra, 0 hash mismatch. |

---

## 2. Phạm vi kiểm chứng V5b

Cổng V5b được thực hiện theo đúng đặc tả kỹ thuật tại mục 4.8 của [bh07_readiness.md](bh07_readiness.md):
- **Môi trường/đầu vào:** Project Supabase CLI local độc lập hoàn toàn (`project_id = "bh07-reset-verify"`, dải port riêng biệt `56420–56429`, container DB `supabase_db_bh07-reset-verify`), tuyệt đối không chạm vào DB chính của repo (`badminton-hub` trên 54321) hay bất kỳ DB dev/staging/production dùng chung nào.
- **Áp dụng tuần tự 18 migrations:** từ migration khởi tạo schema ban đầu (`20261015051808_init_schema_v1_1.sql`) đến migration mới nhất của BH-07 (`20261020180000_bh07_reads.sql`).
- **Seed fixture:** Nạp 7 Auth users qua GoTrue Admin API và nạp dữ liệu chuẩn hóa qua `scripts/bh07_reset/seed.sql` (17.7 KB).
- **Thực thi lặp lại 2 chu kỳ (Repeat Reset Oracle):**
  + Cycle 1: `supabase db reset --local --no-seed` -> nạp seed -> xác minh schema -> xác minh HTTP/Auth RPC -> xác minh 23 DB invariant assertions -> trích xuất DB snapshot fingerprint.
  + Cycle 2: `supabase db reset --local --no-seed` -> nạp seed -> xác minh schema -> xác minh HTTP/Auth RPC -> xác minh 23 DB invariant assertions -> trích xuất DB snapshot fingerprint.
  + So sánh Oracle: Đối chiếu tuyệt đối 100% về `schema_sha256` và `table_stats` của toàn bộ 48 bảng giữa 2 chu kỳ.
- **Negative Controls:** Kiểm tra từ chối caller ẩn danh (anon), từ chối request thiếu API key, từ chối outsider truy cập private summary, và guard loopback security URL; kiểm tra mã lỗi và domain message thật của stack.
- **Dọn dẹp:** Tiêu hủy hoàn toàn container test stack và thư mục làm việc tạm thời (`0 remaining containers`).

Không sửa app (`lib/`), migrations (`supabase/migrations/`), contract hay production DB.

---

## 3. Kết quả kiểm chứng chi tiết

| Hạng mục kiểm chứng | Kết quả thực thi | Exit | Bằng chứng |
|---|---|---|---|
| **Preflight Ownership Check** | 0 container trùng lặp, 8/8 port loopback khả dụng | 0 | [`summary.json`](full_reset_evidence/summary.json), runner stdout |
| **Cycle 1 Reset & Migration** | Exit 0, 18/18 migrations áp dụng thành công | 0 | [`reset_cycle1.log`](full_reset_evidence/reset_cycle1.log) |
| **Cycle 1 Auth & Seed** | Tạo 7 GoTrue Auth users + nạp seed.sql không lỗi | 0 | [`auth_seed_cycle1.log`](full_reset_evidence/auth_seed_cycle1.log) |
| **Cycle 1 Schema Verification** | Đủ 21 core tables, 12 RPC functions, RLS enforced | 0 | [`summary.json`](full_reset_evidence/summary.json) |
| **Cycle 1 HTTP/Auth Smoke** | Login 7 actors, HTTP complete_session (200 + replay 200), HTTP cash payment 200, summary ACL (Owner 200, Cohost 200 count-only, Member 403 Forbidden, Finance 200) | 0 | [`summary.json`](full_reset_evidence/summary.json) |
| **Cycle 1 DB Assertions** | **23/23 assertions PASS** trực tiếp trên target DB | 0 | [`summary.json`](full_reset_evidence/summary.json) |
| **Cycle 2 Reset & Migration** | Exit 0, hash log trùng 100% với Cycle 1 | 0 | [`reset_cycle2.log`](full_reset_evidence/reset_cycle2.log) |
| **Cycle 2 Auth & Seed** | Tạo 7 GoTrue Auth users + nạp seed.sql không lỗi | 0 | [`auth_seed_cycle2.log`](full_reset_evidence/auth_seed_cycle2.log) |
| **Cycle 2 Schema & DB Assertions** | **23/23 assertions PASS**, schema hợp lệ | 0 | [`summary.json`](full_reset_evidence/summary.json) |
| **Repeat Reset Oracle** | `schema_sha256` trùng khớp (`95b4634f...`), 48/48 bảng trùng count và sha256 100% giữa 2 lần reset | 0 | [`snapshot_comparison.json`](full_reset_evidence/snapshot_comparison.json) |
| **Negative Controls** | Anon complete_session bị từ chối (401, code 42501), request thiếu apikey bị từ chối (401, code 42501), outsider bị Forbidden (403, code 42501, message 'FORBIDDEN'), guard loopback PASS | 0 | [`negative_controls.log`](full_reset_evidence/negative_controls.log) |
| **Teardown & Cleanup** | `supabase stop --no-backup`, 0 container sót lại (quét `docker ps -a`), tempdir purged, 0 cleanup errors | 0 | [`stop.log`](full_reset_evidence/stop.log), `exits.json`, `summary.json` |
| **Manifest Check** | 12/12 files khớp SHA-256 (kể cả 7 log files) | 0 | [`hashes.sha256`](full_reset_evidence/hashes.sha256) |
| **Secret Scan** | 0 JWT 3 đoạn, 0 sb_secret, 0 private keys | 0 | Quét regex tự động |
| **Test tái hiện R1–R4** | 4/4 tests PASS | 0 | [`tests/test_v5b_runner_flaws.py`](../../tests/test_v5b_runner_flaws.py) |
| **Repo Baseline Health** | `flutter analyze` 0 issues; `flutter test` 240 passed, 1 skipped | 0 | Lệnh trực tiếp local |

---

## 3. Chứng minh DB assertions kiểm tra chính database vừa reset

Không dùng một database độc lập khác làm bằng chứng duy nhất:
1. **Thông tin định danh server/database:**
   Lệnh `SELECT json_build_object('database', current_database(), 'user', current_user, 'server_version', version(), 'container', inet_server_addr()::text, 'port', inet_server_port())::text;` được thực thi trực tiếp trên container `supabase_db_bh07-reset-verify` vừa reset, xác nhận kết nối vào cơ sở dữ liệu `postgres` trên PostgreSQL 17.11 của stack cô lập.
2. **Khớp nối dữ liệu giữa HTTP và DB assertion:**
   - Dòng HTTP gọi `complete_session` trên buổi `10000000-0000-4000-8000-000000000001` qua port 56421: DB assertion truy vấn trực tiếp và xác nhận `lifecycle = 'completed'`, bản ghi `audit_events` với action `SESSION_COMPLETED` được tạo đúng 1 lần, và bản ghi `operation_requests` được lưu trữ.
   - Dòng HTTP gọi `record_cash_payment` thu 20,000 VND tiền mặt: DB assertion kiểm tra và xác nhận tồn tại payment status `confirmed` và bản ghi sổ cái `club_transactions` tương ứng với `source_type = 'payment'`.
   - Dữ liệu hoàn toàn mới được sinh ra trong chính chu kỳ reset và được DB assertion đọc ra ngay tức thì.

---

## 4. Tái lập kiểm chứng độc lập

Reviewer có thể tự chạy lại toàn bộ quy trình kiểm chứng bằng lệnh sau trên nhánh `feat/bh07-full-reset-verification`:

```powershell
# Chạy runner kiểm chứng V5b full reset
python -u scripts/bh07_reset/run_full_reset.py

# Kiểm tra tính toàn vẹn của manifest bằng chứng
python -c "
import hashlib
from pathlib import Path
ev_dir = Path('docs/reviews/bh07/full_reset_evidence')
manifest = (ev_dir / 'hashes.sha256').read_text(encoding='utf-8')
for line in manifest.strip().splitlines():
    h, name = line.split(None, 1)
    actual = hashlib.sha256((ev_dir / name).read_bytes()).hexdigest()
    assert actual == h, f'Mismatch in {name}'
print('Manifest: ALL PASS')
"

# Quét bí mật trên thư mục bằng chứng
python -c "
import re
from pathlib import Path
files = list(Path('docs/reviews/bh07/full_reset_evidence').glob('*'))
pats = [re.compile(r'eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}'), re.compile(r'sb_secret_[a-zA-Z0-9_\-]+')]
found = [f.name for f in files if f.is_file() for p in pats if p.findall(f.read_text(encoding='utf-8', errors='ignore'))]
assert len(found) == 0, f'Secrets found: {found}'
print('Secret scan: ALL PASS')
"

# Kiểm tra không rò rỉ container
docker ps -a --filter "name=bh07-reset-verify"
```
