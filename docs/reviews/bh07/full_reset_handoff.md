# Bàn giao kiểm chứng V5b — Full Supabase CLI Reset local BH-07

> **Trạng thái: Chờ review độc lập V5b — Full Supabase CLI Reset local (24/10/2026).** Người triển khai không tự ghi Đạt. Base: `6e5dba6c1b67c06bf98283b6bacac47ae2be3dc6`; tested source SHA `0392e2166bc0c33b3170e6919d86470d193d6301`; nhánh `feat/bh07-full-reset-verification`. Kết quả dưới đây chỉ là kiểm chứng local trên project test sạch, không thay đổi kết luận các cổng khác và không tự nghiệm thu toàn BH-07/pilot/deploy.

---

## 1. Phạm vi kiểm chứng V5b

Cổng V5b được thực hiện theo đúng đặc tả kỹ thuật tại mục 4.8 của [bh07_readiness.md](bh07_readiness.md):
- **Môi trường/đầu vào:** Project Supabase CLI local độc lập hoàn toàn (`project_id = "bh07-reset-verify"`, dải port riêng biệt `56420–56429`, container DB `supabase_db_bh07-reset-verify`), tuyệt đối không chạm vào DB chính của repo (`badminton-hub` trên 54321) hay bất kỳ DB dev/staging/production dùng chung nào.
- **Áp dụng tuần tự 18 migrations:** từ migration khởi tạo schema ban đầu (`20261015051808_init_schema_v1_1.sql`) đến migration mới nhất của BH-07 (`20261020180000_bh07_reads.sql`).
- **Seed fixture:** Nạp 7 Auth users qua GoTrue Admin API và nạp dữ liệu chuẩn hóa qua `scripts/bh07_reset/seed.sql` (17.7 KB).
- **Thực thi lặp lại 2 chu kỳ (Repeat Reset Oracle):**
  + Cycle 1: `supabase db reset --local --no-seed` -> nạp seed -> xác minh schema -> xác minh HTTP/Auth RPC -> xác minh 23 DB invariant assertions -> trích xuất DB snapshot fingerprint.
  + Cycle 2: `supabase db reset --local --no-seed` -> nạp seed -> xác minh schema -> xác minh HTTP/Auth RPC -> xác minh 23 DB invariant assertions -> trích xuất DB snapshot fingerprint.
  + So sánh Oracle: Đối chiếu tuyệt đối 100% về `schema_sha256` và `table_counts` của toàn bộ 48 bảng giữa 2 chu kỳ.
- **Negative Controls:** Kiểm tra từ chối caller ẩn danh (anon), từ chối request thiếu API key, từ chối outsider truy cập private summary, và guard loopback security URL.
- **Dọn dẹp:** Tiêu hủy hoàn toàn container test stack và thư mục làm việc tạm thời (`0 remaining containers`).

Không sửa app (`lib/`), migrations (`supabase/migrations/`), contract hay production DB.

---

## 2. Kết quả kiểm chứng chi tiết

| Hạng mục kiểm chứng | Kết quả thực thi | Exit | Bằng chứng |
|---|---|---|---|
| **Cycle 1 Reset & Migration** | Exit 0, 18/18 migrations áp dụng thành công | 0 | [`reset_cycle1.log`](full_reset_evidence/reset_cycle1.log) |
| **Cycle 1 Auth & Seed** | Tạo 7 GoTrue Auth users + nạp seed.sql không lỗi | 0 | [`auth_seed_cycle1.log`](full_reset_evidence/auth_seed_cycle1.log) |
| **Cycle 1 Schema Verification** | Đủ 21 core tables, 12 RPC functions, RLS enforced | 0 | [`summary.json`](full_reset_evidence/summary.json) |
| **Cycle 1 HTTP/Auth Smoke** | Login 7 actors, HTTP complete_session (200 + replay 200), HTTP cash payment 200, summary ACL (Owner 200, Cohost 200 count-only, Member 403 Forbidden, Finance 200) | 0 | [`summary.json`](full_reset_evidence/summary.json) |
| **Cycle 1 DB Assertions** | **23/23 assertions PASS** trực tiếp trên target DB | 0 | [`summary.json`](full_reset_evidence/summary.json) |
| **Cycle 2 Reset & Migration** | Exit 0, hash log trùng 100% với Cycle 1 | 0 | [`reset_cycle2.log`](full_reset_evidence/reset_cycle2.log) |
| **Cycle 2 Auth & Seed** | Tạo 7 GoTrue Auth users + nạp seed.sql không lỗi | 0 | [`auth_seed_cycle2.log`](full_reset_evidence/auth_seed_cycle2.log) |
| **Cycle 2 Schema & DB Assertions** | **23/23 assertions PASS**, schema hợp lệ | 0 | [`summary.json`](full_reset_evidence/summary.json) |
| **Repeat Reset Oracle** | `schema_sha256` trùng khớp (`95b4634f...`), 48/48 table counts khớp 100% giữa 2 lần reset | 0 | [`snapshot_comparison.json`](full_reset_evidence/snapshot_comparison.json) |
| **Negative Controls** | Anon complete_session bị từ chối (401), request thiếu apikey bị từ chối (404), outsider bị Forbidden (403), guard loopback PASS | 0 | [`negative_controls.log`](full_reset_evidence/negative_controls.log) |
| **Teardown & Cleanup** | `supabase stop --no-backup`, 0 container sót lại | 0 | [`stop.log`](full_reset_evidence/stop.log), `exits.json` |
| **Manifest Check** | 12/12 files khớp SHA-256 | 0 | [`hashes.sha256`](full_reset_evidence/hashes.sha256) |
| **Secret Scan** | 0 JWT 3 đoạn, 0 sb_secret, 0 private keys | 0 | Quét regex tự động |
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
