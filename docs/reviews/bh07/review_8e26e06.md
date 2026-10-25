# Review V5b BH-07 — `8e26e06` — QA/reviewer khác

## 1. Kết luận

**Chưa đạt để chốt V5b.** Không có P0/P1 mới; **R1/R2 đã đóng** bằng probe độc lập; R3/R5 giữ đóng. Full Supabase CLI2 reset trên source `8e26e06` **PASS**: 2 chu kỳ, 18 migration/chu kỳ, 23/23 assertion/chu kỳ, HTTP/Auth pass, Oracle 48 bảng, cleanup sạch. Tuy nhiên còn **7 P2** về oracle/evidence/provenance/reproducibility và độ mạnh assertion; theo quy trình phải đóng các P2 này trước khi ghi Đạt.

- Source review: `8e26e066e18a2b73cdedd45e5fd223a201d01a04`.
- Docs/evidence tip: `20f2605` (trên `8e26e06`; chỉ sửa docs).
- Base review: `6a13901f06b8ba88975538c8b6104590c9ec31b7` ([handoff Codex](codex_v5b_fix_handoff.md#L5)).
- Reviewer: QA/reviewer khác, **không tham gia sửa bản Codex V5b**; không sửa code/app/migration/DB; chỉ thêm report và evidence reviewer.
- Worktree nguồn: `C:\Users\POTA\Documents\GitHub\Open-Multi-agent-Pipeline\.review-bh07\worktree-8e26e06`, detached `8e26e06`, **sạch trước khi chạy**; `environment.json` ghi `git_dirty=false`.
- Môi trường: Windows, Docker 29.8.2, Supabase CLI 2.122.0, PostgreSQL 17.11; host 31,7 GB RAM, 81,8 GB đĩa trống trước chạy.
- Evidence mới: [`review_8e26e06_evidence/`](review_8e26e06_evidence/). Không ghi đè `full_reset_evidence/` cũ; bundle cũ verify readonly 12/10/8/8 tại [`manifest_readonly.json`](review_8e26e06_evidence/manifest_readonly.json).

## 2. Phát hiện P0/P1/P2

### P2-1 — Oracle chỉ so row count, không so `sha256`; tài liệu claim 100% sha256 là sai

- `scripts/bh07_reset/run_full_reset.py:785-792` chỉ đối chiếu `stat1['count']` với `stat2['count']`; không so `table_stats[*]['sha256']`.
- [`snapshot_comparison.json`](review_8e26e06_evidence/snapshot_comparison.json) của chính lượt này có **24/48 bảng khác `sha256`** giữa cycle 1 và cycle 2 (gồm `auth.users`, `public.sessions`, `public.payments`, `public.audit_events`, ...), dù count đều khớp.
- [`full_reset_handoff.md:35`](full_reset_handoff.md#L35) và [`full_reset_handoff.md:56`](full_reset_handoff.md#L56) claim "đối chiếu tuyệt đối 100% ... `table_stats`" / "48/48 bảng trùng count và sha256 100%"; claim này **không đúng** với code và evidence.
- Hệ quả: `oracle_repeat_match=true` trong [`summary.json`](review_8e26e06_evidence/summary.json#L7) chỉ có nghĩa schema hash + count khớp, không phải dữ liệu khớp. Cần hoặc (a) so `sha256` với seed deterministic (loại timestamp/UUID ngẫu nhiên, hoặc canonical hóa), hoặc (b) sửa claim/tên field thành "schema + row count oracle" và thêm assertion/test cho đúng phạm vi.

### P2-2 — `base_sha` hardcode sai, không phải base review `6a13901`

- `scripts/bh07_reset/run_full_reset.py:58` hardcode `BASE_SHA = '6e5dba6c...'`; `6e5dba6` là ancestor cách `8e26e06` 10 commit, không phải base review `6a13901`.
- [`environment.json:3`](review_8e26e06_evidence/environment.json#L3) và [`summary.json:5`](review_8e26e06_evidence/summary.json#L5) ghi `base_sha=6e5dba6...`, lệch với [`codex_v5b_fix_handoff.md:5`](codex_v5b_fix_handoff.md#L5) (`6a13901...`).
- Đề nghị: nhận base SHA từ CLI/git (`git merge-base`), hoặc bỏ field nếu không xác định; ghi đúng base review trong evidence.

### P2-3 — Không persist HTTP/Auth detail và assertion detail cycle 2

- `scripts/bh07_reset/run_full_reset.py:1010-1025` chỉ ghi `db_assertions_detail` của cycle 1; [`summary.json:9`](review_8e26e06_evidence/summary.json#L9) chỉ có count cycle 2, [`summary.json:11`](review_8e26e06_evidence/summary.json#L11) chỉ có detail cycle 1.
- Bundle không có file HTTP status/body theo request; `http_auth_audit.json` phải ghi `raw_http_response_log_persisted=false`. Exit 0 chứng minh các assertion HTTP trong code đã pass, nhưng auditor không thể kiểm lại status 200/401/403, replay, cash payment hay ACL nếu không chạy lại.
- Đề nghị: ghi `http_cycle1.json`, `http_cycle2.json` (status/code/actor, không chứa token), `db_assertions_cycle2.json`; đưa tất cả vào manifest.

### P2-4 — Cổng S3 `56428` được claim/check nhưng không được cấu hình

- `scripts/bh07_reset/run_full_reset.py:335` thay `port = 54328`, nhưng `supabase/config.toml` **không có** dòng `port = 54328` (S3 protocol đi qua Kong); generated config không bind `56428`.
- [`environment.json:18`](review_8e26e06_evidence/environment.json#L18) vẫn ghi `"s3": 56428`; preflight kiểm tra port này dù stack không dùng, còn `start.log` cho `STORAGE_S3_URL` trên `56421`.
- Đề nghị: bỏ port/claim 56428 hoặc thêm cấu hình S3 thật; assert generated config chứa đúng port trước khi start.

### P2-5 — Assertion DB yếu hơn claim exact; `req_orig` không deterministic

- Claim trong handoff là count/giá trị cụ thể (`count=1`, `count=2`, `charges=150000`, `payments=70000`, `court_count=4`), nhưng code chỉ kiểm:
  - `run_full_reset.py:553` `op_cnt >= 1`;
  - `run_full_reset.py:557` `pay_cnt >= 1`;
  - `run_full_reset.py:561` `tx_cnt >= 1`;
  - `run_full_reset.py:566` `charges_sum > 0 and payments_sum >= 20000`;
  - `run_full_reset.py:615` `v_court > 0`;
  - `run_full_reset.py:623` visibility chỉ thuộc enum.
- Các assertion này có thể pass khi có bản ghi dư/trùng hoặc giá trị khác claim. Nên kiểm exact theo fixture, hoặc ghi rõ đây là invariant tối thiểu (không phải exact count).
- `run_full_reset.py:596-602`: `req_orig = ... operation='complete_session' LIMIT 1` không lọc `session_id`, không `ORDER BY`; sau khi free session complete có 2 operation request `complete_session`, nên assertion #13 có thể chọn nhầm request và flake. Cần lọc theo session/payload hoặc `ORDER BY created_at, id`.

### P2-6 — Provenance runtime chưa bị bind: CLI không pin, thiếu image digest, schema hash drift

- `run_full_reset.py:661,689,720,751,896` gọi `npx supabase` không pin version; nếu cache npx không có, runner có thể dùng CLI khác. `environment.json` chỉ ghi version sau khi chạy, không pin.
- `environment.json` không ghi Docker image digest. Cùng `reset_cycle1.log` byte-identical (18 migration) nhưng `schema_sha256` cũ `95b4634f...` khác mới `745aa053...`; evidence hiện có cả `postgres:17.11.0.004` và `.006`, nhưng không chứng minh được lượt chạy dùng digest nào. Đây là rủi ro reproducibility, không phải lỗi runtime của lượt này.
- Đề nghị: pin `supabase@2.122.0` và image tag/digest; ghi digest vào `environment.json`; assert schema hash hoặc ghi rõ oracle chỉ có giá trị trong cùng môi trường.

### P2-7 — `run_cmd` dùng `shell=is_batch` và không có timeout (tồn tại trước, ngoài phạm vi sửa R1/R2)

- `run_full_reset.py:97-113`: `shell=is_batch`; trên Windows `npx` resolve thành `npx.cmd` nên thực tế dùng `shell=True`. `subprocess.run` không có `timeout`, không có cơ chế dừng cây tiến trình.
- Đây là vấn đề process/security **có trước `8e26e06`**, không do bản sửa R1/R2 gây ra; không làm thay đổi kết luận R1/R2 nhưng cần ticket riêng trước khi coi runner là hardening đầy đủ. Đề nghị truyền argv trực tiếp (không shell), thêm timeout và kill process tree.

## 3. Đã đóng / xác minh độc lập

### R1 — Inventory sau start fail-closed

Probe độc lập [`independent_probes.log`](review_8e26e06_evidence/independent_probes.log):

| Case | Kỳ vọng | Thực tế |
|---|---|---|
| `docker ps` exit 1, stdout rỗng | RuntimeError, không reset | RuntimeError, `reset_attempted=false` |
| `docker ps` exit 1, stdout có ID | RuntimeError, không reset | RuntimeError, `reset_attempted=false` |
| `docker ps` exit 0, inventory rỗng | RuntimeError, không reset | RuntimeError, `reset_attempted=false` |
| `docker ps` exit 0, inventory có owned ID | tới boundary reset | ResetBoundary, `reset_attempted=true` |

`run_full_reset.py:696-702` kiểm returncode trước khi dùng stdout và từ chối inventory rỗng. **Đóng R1.**

### Project UUID riêng

- `run_full_reset.py:44`: `bh07-reset-verify-<uuid4 hex 16>`; probe 32/32 giá trị unique, prefix đúng.
- `prepare_project_dir` thay `project_id` trong config và copy đủ 18 migration; probe xác nhận generated config dùng UUID mới, không còn `project_id = "badminton-hub"`.
- Runtime dùng `bh07-reset-verify-ddcc615aacfe4e5c`; container/volume/network được dọn sạch.

### R2 — Gateway/PostgREST tuple strict

Probe độc lập 17/17 case đúng:

- Nhận: gateway 401 không có field `code`, message `No API key found in request` (casefold); PostgREST 42501 status 401/403 với `permission denied`.
- Từ chối: gateway 403; code `42P01`/`XX000`/`INVALID_INPUT`/`NOT_FOUND`/`PGRST202`; field `code` rỗng/`None`; message thêm prefix/suffix; route 404; `XX000` có hint chứa từ khóa auth.
- `run_full_reset.py:302` kiểm đúng status/code/message gateway; không còn nhận SQLSTATE ngoài whitelist. **Đóng R2.**

### R3/R5

- R3 cleanup fail-closed/giữ primary error: probe 4 case (positive, inspection nonzero, final inspect raise + primary, foreign container) đúng; foreign không bị xóa, owned bị xóa.
- R5: `tests/test_v5b_runner_flaws.py` 11/11 PASS; mutant preflight bị bắt 3 FAIL; mutant owned-inventory 1 FAIL; mutant gateway 9 FAIL.
- `codex_fix_controls.py` exit 0: 14 scenario controls + 3 mutant gates đúng.

### R4 manifest

- `full_reset_evidence` 12/12, `codex_v5b_fix_evidence` 10/10, `review_19ab207_evidence` 8/8, `review_3b515f2_evidence` 8/8; 0 missing/extra/mismatch; old bundle không đổi.
- Source hashes khớp `codex_v5b_fix_evidence/summary.json`: runner `d5e27ce9...`, tests `576d97f1...`.
- Tuy nhiên claim Oracle sha256 ở P2-1 làm R4 "oracle content" chưa đóng hoàn toàn.

## 4. Full CLI2 reset — kết quả reviewer tự chạy

Chạy trong worktree riêng, source `8e26e06`, checkout sạch:

```powershell
$env:PYTHONUTF8='1'
python -u scripts/bh07_reset/run_full_reset.py
```

| Hạng mục | Kết quả | Evidence |
|---|---|---|
| Exit | 0 | [`exits.json`](review_8e26e06_evidence/exits.json), `full_reset_runtime.log` |
| Chu kỳ | 2 | `summary.json` |
| Migration | 18/18 mỗi chu kỳ, cùng thứ tự | [`reset_cycle1.log`](review_8e26e06_evidence/reset_cycle1.log), [`reset_cycle2.log`](review_8e26e06_evidence/reset_cycle2.log) |
| Auth seed | 7 user/chu kỳ | [`auth_seed_cycle1.log`](review_8e26e06_evidence/auth_seed_cycle1.log), [`auth_seed_cycle2.log`](review_8e26e06_evidence/auth_seed_cycle2.log) |
| Schema | 21 core table/12 RPC/RLS pass | `summary.json` `schema_valid=true` |
| HTTP/Auth | pass theo assertion trong script; không có raw HTTP log (P2-3) | `run_full_reset.py:424-527`, [`http_auth_audit.json`](review_8e26e06_evidence/http_auth_audit.json) |
| DB assertions | 23/23 cycle 1; 23/23 cycle 2 (detail cycle 2 không persist — P2-3) | [`db_assertions_audit.json`](review_8e26e06_evidence/db_assertions_audit.json) |
| Negative controls | 4/4 | [`negative_controls.log`](review_8e26e06_evidence/negative_controls.log) |
| Oracle | 48/48 bảng, schema hash khớp, count khớp; 24/48 sha256 khác (P2-1) | [`oracle_audit.json`](review_8e26e06_evidence/oracle_audit.json), [`snapshot_comparison.json`](review_8e26e06_evidence/snapshot_comparison.json) |
| Cleanup | stop exit 0; 0 container/volume/network/temp | [`cleanup_check.txt`](review_8e26e06_evidence/cleanup_check.txt), [`stop.log`](review_8e26e06_evidence/stop.log) |
| Source | `tested_sha=8e26e06`, `git_dirty=false` | [`environment.json`](review_8e26e06_evidence/environment.json) |
| Old evidence | 12/10/8/8 readonly, không ghi đè | [`manifest_readonly.json`](review_8e26e06_evidence/manifest_readonly.json) |

- DB metadata: PostgreSQL 17.11; `inet_server_addr()`/`inet_server_port()` trả null vì chạy qua `docker exec` Unix socket. Điều này không chứng minh container/port trong metadata; target được xác định bởi `CONTAINER_DB` từ project UUID.
- Negative controls runtime: anon `complete_session` 401/42501; no-apikey 401/42501; outsider summary 403/42501; loopback guard pass.
- Không chạm shared stack `supabase_db_badminton-hub` (vẫn chạy); không chạm `bh07ir-*` hay DB dev/staging/production.

## 5. NOT RUN / giới hạn

- **Flutter analyze/test**: không chạy lại trong lượt review này; chỉ đọc log tác giả (`0 issue`, `240 pass + 1 skip`), không dùng làm kết quả reviewer.
- **Fault injection thật** lên Docker daemon/permission/transport: chỉ chạy AST/simulated probe; không gây lỗi trên resource thật.
- **HTTP/Auth raw audit**: không chạy lại request độc lập sau reset; chỉ xác nhận script exit 0 và assertion trong code. Đây là P2-3.
- **V2/V2b** device/browser khác/offline/deep link/private heap; **V3** managed Supabase/PITR/offsite/encryption/retention; **V4** concurrent writers; **V5** staging/production restore/deploy thật; **V6** banking/webhook; **V7** tải/pilot; **V8** nghiệm thu toàn BH-07: giữ **NOT RUN**.
- **Merge main/staging/production/deploy/pilot/BH-08**: không thực hiện, không cấp phép.

## 6. Đề nghị bước tiếp

1. Sửa P2-1/P2-2/P2-3/P2-4/P2-6 trong evidence/docs (không cần đổi runtime nếu chỉ sửa claim) và bổ sung manifest.
2. Sửa P2-5/P2-7 trong code runner + test hồi quy; chạy lại 11 tests, controls, full CLI2 reset trên worktree sạch.
3. Giữ V5b **Chưa đạt** đến khi các P2 được đóng và có review/verify lại; không chuyển Đạt chỉ dựa trên runtime PASS.
4. Không merge main/deploy/pilot; giữ V1 Đạt local và các cổng khác NOT RUN.

**Kết luận cuối: Chưa đạt V5b tại `8e26e06` — runtime PASS, còn 7 P2 evidence/provenance/assertion.**
