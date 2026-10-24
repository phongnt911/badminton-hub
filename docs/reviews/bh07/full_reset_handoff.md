# Bàn giao kiểm chứng V5b — Full Supabase CLI Reset local BH-07 (Sửa R1/R2/R3/R5 vòng 2/2)

**Theo ủy quyền bổ sung “giao reviewer sửa”, Codex đã sửa trực tiếp R1/R2 tại `8e26e06`**, base `6a13901`; [bàn giao tự kiểm](codex_v5b_fix_handoff.md). Codex tự sửa/tự kiểm, **KHÔNG phải review độc lập**. Inventory sau start lỗi/trống bị chặn trước reset; mỗi run dùng project UUID riêng; gateway chỉ nhận tuple đã whitelist.11/11 tests,14 scenario controls và3 mutant gates đúng;analyze sạch,240 Flutter+1skip. Evidence cũ12/10/8/8 verify readonly không đổi. **V5b Chờ kiểm chứng sau bản sửa trực tiếp; full CLI runtime source8e26e06 NOT RUN do thiếu đĩa**, không retag evidence runtime cũ. Đây là ủy quyền trực tiếp sau dừng hai vòng,không tự mở vòng3. V1 giữ Đạt local; toàn BH-07 chưa nghiệm thu,các cổng khác giữ NOT RUN. Không merge main/staging/production/deploy/pilot/BH-08.

**(Lịch sử dừng trước ủy quyền trực tiếp) V5b Chưa đạt vòng2/2 tại `3b515f2` — DỪNG theo AGENTS**, docs/evidence `5df6c62`, theo [review chốt](review_3b515f2.md). Còn1 P1 R1 (owned inventory sau start lỗi vẫn reset) và1 P2 R2 (gateway variant nhận code SQL ngoài whitelist). Đóng R3/R5, giữ R4 packaging/count/trung thực dirty; runtime tác giả là b4b1f9f dirty source/tests, không tự gán thành clean3b515f2. Reviewer tự chạy8/8 tests,mutant suite8 test bắt3 FAIL,analyze sạch,240 Flutter+1skip,manifest12/12 readonly vàAST probes. Full CLI runtime NOT RUN do thiếu đĩa. **Không tự mở vòng3/sửa source; báo chủ dự án quyết định bước tiếp.** Giữ V1 Đạt local; toàn BH-07 chưa nghiệm thu,các cổng khác giữ NOT RUN. Không merge main/staging/production/deploy/pilot/BH-08.

> **Lịch sử bàn giao trước Codex sửa: Chờ review độc lập V5b vòng 2/2 (24/10/2026).** Người triển khai không tự ghi Đạt.
> Base review: `b4b1f9f4e688978b5f141208962ccc7e784eebb7` (review `19ab207`);
> Nhánh: `feat/bh07-full-reset-verification`.
> Kết quả dưới đây là kiểm chứng local trên project Supabase CLI test độc lập, không thay đổi kết luận các cổng khác và không tự nghiệm thu toàn BH-07/pilot/deploy.

---

## 1. Tóm tắt khắc phục phát hiện review `19ab207` (R1/R2/R3/R5) và giữ R4 đã đóng

| Mã | Mức | Phát hiện review `19ab207` | Khắc phục đã thực hiện trong vòng 2/2 | Kiểm chứng hành vi / Tái hiện |
|---|---|---|---|---|
| **R1** | **P1** | Preflight bỏ qua returncode != 0 của Docker list (`accepted=True`); Cleanup xóa mù container lạ không thuộc sở hữu nếu trùng tên. | Sửa `preflight_ownership_check()`: kiểm tra `p_check.returncode != 0` -> ném `RuntimeError` ngay (fail-closed mọi lỗi daemon/inventory). Sửa khối cleanup: chỉ xóa container thuộc `owned_containers`, từ chối xóa và ghi nhận cleanup error nếu phát hiện container lạ (`foreign_ids`). | `test_r1_preflight_fail_closed_on_docker_error` và `test_r1_cleanup_only_removes_owned_containers` trong `tests/test_v5b_runner_flaws.py` PASS. |
| **R2** | **P2** | Positive baseline dùng mock tuple; negative controls nhận nhầm `XX000` nội bộ nếu hint/detail có từ khóa auth; error-domain quá rộng. | Thêm hàm `assert_negative_auth_rejection()`: kiểm tra chặt chẽ bộ ba `(status, code, message)` trên các trường top-level; từ chối dứt khoát `XX000` (bất kể hint/detail chứa từ khóa auth nào), từ chối `INVALID_INPUT`, `NOT_FOUND`, route 404. Positive baseline HTTP thực hiện request thật với token của Owner A (trả về status 200, `can_view_finance=True`). | `test_r2_negative_controls_rejects_xx000_with_auth_words` PASS; request thật trả status 401/403 với mã lỗi PostgreSQL `42501` và domain message chuẩn. |
| **R3** | **P2** | Final inspection trong cleanup bị fail-open nếu returncode != 0; ngoại lệ ở final inspect che khuất `primary_error`. | Bọc `final_remaining` trong khối try-except: nếu `p_final.returncode != 0` thì thêm vào `cleanup_errors` thay vì coi là clean (fail-closed). Đặt bước re-raise `primary_error` ở cuối khối `finally` trước khi ném lỗi cleanup, bảo đảm `primary_error` luôn được bảo lưu nguyên vẹn. | `test_r3_cleanup_preserves_primary_error_when_final_inspect_raises` và `test_r3_cleanup_fail_closed_on_final_inspect_nonzero` PASS. |
| **R4** | **P2** | *(Đã đóng từ vòng 1/2)* Manifest 12/12 files, Oracle đủ 48/48 bảng/cycle, 23/23 assertions, git_dirty trung thực. | **Giữ nguyên trạng thái R4 đã đóng**: Manifest 12/12 files (bao gồm 7 file log gốc) đạt 100% hash match, `snapshot_comparison.json` lưu đủ 48/48 bảng cho cả 2 chu kỳ, 23/23 DB assertions, `environment.json` ghi nhận đầy đủ dirty status và danh sách file thay đổi. | Manifest verification PASS 100% (12 files, 0 missing, 0 extra, 0 mismatch). |
| **R5** | **P2** | Test chỉ kiểm tra chuỗi tĩnh (AST/literal), không kiểm tra hành vi thực thi thực tế; mutant vô hiệu gate không làm suite fail. | Viết lại `tests/test_v5b_runner_flaws.py` thành bộ kiểm thử hành vi thực thi thật (8/8 test methods). Test `test_r5_mutant_detection` chèn mutant vô hiệu hóa preflight và chứng minh test behavior phát hiện và đánh bại mutant ngay lập tức. | `tests/test_v5b_runner_flaws.py` 8/8 tests PASS. |

---

## 2. Phạm vi kiểm chứng V5b

Cổng V5b được thực hiện theo đúng đặc tả kỹ thuật tại mục 4.8 của [bh07_readiness.md](bh07_readiness.md):
- **Môi trường/đầu vào:** Project Supabase CLI local độc lập hoàn toàn (`project_id = "bh07-reset-verify"`, dải port riêng biệt `56420–56429`, container DB `supabase_db_bh07-reset-verify`), tuyệt đối không chạm vào DB chính của repo (`badminton-hub` trên 54321) hay bất kỳ DB dev/staging/production dùng chung nào.
- **Áp dụng tuần tự 18 migrations:** từ migration khởi tạo schema ban đầu (`20261015051808_init_schema_v1_1.sql`) đến migration mới nhất của BH-07 (`20261020180000_bh07_reads.sql`).
- **Seed fixture:** Nạp 7 Auth users qua GoTrue Admin API và nạp dữ liệu chuẩn hóa qua `scripts/bh07_reset/seed.sql`.
- **Thực thi lặp lại 2 chu kỳ (Repeat Reset Oracle):**
  + Cycle 1: `supabase db reset --local --no-seed` -> nạp seed -> xác minh schema -> xác minh HTTP/Auth RPC -> xác minh 23 DB invariant assertions -> trích xuất DB snapshot fingerprint.
  + Cycle 2: `supabase db reset --local --no-seed` -> nạp seed -> xác minh schema -> xác minh HTTP/Auth RPC -> xác minh 23 DB invariant assertions -> trích xuất DB snapshot fingerprint.
  + So sánh Oracle: Đối chiếu tuyệt đối 100% về `schema_sha256` và `table_stats` của toàn bộ 48 bảng giữa 2 chu kỳ.
- **Positive & Negative Controls:** Positive baseline request HTTP thật trả về status 200. Negative controls kiểm tra từ chối caller ẩn danh (anon), từ chối request thiếu API key, từ chối outsider truy cập private summary, và guard loopback security URL; kiểm tra mã lỗi `42501` và domain message thật của stack.
- **Dọn dẹp:** Tiêu hủy hoàn toàn container test stack và thư mục làm việc tạm thời (`0 remaining containers`, 0 cleanup errors).

Không sửa app (`lib/`), migrations (`supabase/migrations/`), contract hay production DB.

---

## 3. Kết quả kiểm chứng chi tiết vòng 2/2

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
| **Positive Baseline HTTP** | Gửi token Owner A thật đến RPC get_session_summary: status 200, can_view_finance=True | 0 | Runner stdout, [`summary.json`](full_reset_evidence/summary.json) |
| **Negative Controls** | Anon complete_session bị từ chối (401, code 42501), request thiếu apikey bị từ chối (401, code 42501), outsider bị Forbidden (403, code 42501, message 'FORBIDDEN'), guard loopback PASS | 0 | [`negative_controls.log`](full_reset_evidence/negative_controls.log) |
| **Teardown & Cleanup** | `supabase stop --no-backup`, 0 container sót lại (quét `docker ps -a`), tempdir purged, 0 cleanup errors | 0 | [`stop.log`](full_reset_evidence/stop.log), `exits.json`, `summary.json` |
| **Manifest Check** | 12/12 files khớp SHA-256 (kể cả 7 log files) | 0 | [`hashes.sha256`](full_reset_evidence/hashes.sha256) |
| **Secret Scan** | 0 JWT 3 đoạn, 0 sb_secret, 0 private keys | 0 | Quét regex tự động 100% clean |
| **Test hành vi R1–R3, R5** | 8/8 tests PASS, mutant bị phát hiện | 0 | [`tests/test_v5b_runner_flaws.py`](../../../tests/test_v5b_runner_flaws.py) |
| **Repo Baseline Health** | `flutter analyze` 0 issues; `flutter test` 240 passed, 1 skipped | 0 | Lệnh trực tiếp local |

---

## 4. Chứng minh DB assertions kiểm tra chính database vừa reset

Không dùng một database độc lập khác làm bằng chứng duy nhất:
1. **Thông tin định danh server/database:**
   Lệnh `SELECT json_build_object('database', current_database(), 'user', current_user, 'server_version', version(), 'container', inet_server_addr()::text, 'port', inet_server_port())::text;` được thực thi trực tiếp trên container `supabase_db_bh07-reset-verify` vừa reset, xác nhận kết nối vào cơ sở dữ liệu `postgres` trên PostgreSQL 17.11 của stack cô lập.
2. **Khớp nối dữ liệu giữa HTTP và DB assertion:**
   - Dòng HTTP gọi `complete_session` trên buổi `10000000-0000-4000-8000-000000000001` qua port 56421: DB assertion truy vấn trực tiếp và xác nhận `lifecycle = 'completed'`, bản ghi `audit_events` với action `SESSION_COMPLETED` được tạo đúng 1 lần, và bản ghi `operation_requests` được lưu trữ.
   - Dòng HTTP gọi `record_cash_payment` thu 20,000 VND tiền mặt: DB assertion kiểm tra và xác nhận tồn tại payment status `confirmed` và bản ghi sổ cái `club_transactions` tương ứng với `source_type = 'payment'`.
   - Dữ liệu hoàn toàn mới được sinh ra trong chính chu kỳ reset và được DB assertion đọc ra ngay tức thì.

---

## 5. Tái lập kiểm chứng độc lập

Reviewer có thể tự chạy lại toàn bộ quy trình kiểm chứng bằng lệnh sau trên nhánh `feat/bh07-full-reset-verification`:

```powershell
# 1. Chạy bộ test hành vi R1-R3, R5
$env:PYTHONUTF8="1"; python tests/test_v5b_runner_flaws.py

# 2. Chạy runner kiểm chứng V5b full reset
$env:PYTHONUTF8="1"; python -u scripts/bh07_reset/run_full_reset.py

# 3. Kiểm tra tính toàn vẹn của manifest bằng chứng
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

# 4. Quét bí mật trên thư mục bằng chứng
python -c "
import re
from pathlib import Path
files = list(Path('docs/reviews/bh07/full_reset_evidence').glob('*'))
pats = [re.compile(r'eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}'), re.compile(r'sb_secret_[a-zA-Z0-9_\-]+')]
found = [f.name for f in files if f.is_file() for p in pats if p.findall(f.read_text(encoding='utf-8', errors='ignore'))]
assert len(found) == 0, f'Secrets found: {found}'
print('Secret scan: ALL PASS')
"

# 5. Kiểm tra không rò rỉ container
docker ps -a --filter "name=bh07-reset-verify"
```
