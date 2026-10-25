# Reviewer commands — V5b source `8e26e06`

Ngày 25/10/2026 (Asia/Saigon). Reviewer/QA khác, không tham gia sửa bản Codex V5b.
Worktree nguồn: `C:\Users\POTA\Documents\GitHub\Open-Multi-agent-Pipeline\.review-bh07\worktree-8e26e06` (detached `8e26e06`, sạch trước khi chạy).

## 1. 11 behavior tests

```powershell
Set-Location <worktree-8e26e06>
$env:PYTHONUTF8='1'
python -u tests/test_v5b_runner_flaws.py
```

Kết quả: `Ran 11 tests ... OK`, exit 0. Log: `tests_11.log` (raw PowerShell capture: `tests_11_raw.log`).

## 2. Codex post-fix controls

```powershell
Set-Location <docs-20f2605>
$env:PYTHONUTF8='1'
python -u docs/reviews/bh07/codex_v5b_fix_evidence/codex_fix_controls.py
```

Kết quả: exit 0; 14 scenario controls đúng; whole-suite mutant 11 tests/3 FAIL/0 ERROR; owned-inventory mutant 1 FAIL; gateway mutant 9 FAIL. Log: `codex_fix_controls.log`.

## 3. Manifest verification (read-only)

```powershell
python <verify-manifests script>
```

Kết quả: `full_reset_evidence` 12/12, `codex_v5b_fix_evidence` 10/10, `review_19ab207_evidence` 8/8, `review_3b515f2_evidence` 8/8; 0 missing/extra/mismatch. Log: `verify_manifests.log`, `manifest_readonly.json`.

## 4. Independent reviewer probes

```powershell
Set-Location <worktree-8e26e06>
$env:PYTHONUTF8='1'
python <.review-bh07\logs\independent_probes.py>
```

Kết quả: 32/32 `PROJECT_ID` unique; `prepare_project_dir` thay project ID, copy 18 migrations; inventory exit 1/empty không gọi reset, positive tới boundary; 17/17 gateway/PostgREST tuple cases đúng. Log/script: `independent_probes.log`, `independent_probes.py`.

## 5. Full CLI2 reset (worktree riêng)

```powershell
Set-Location <worktree-8e26e06>
$env:PYTHONUTF8='1'
python -u scripts/bh07_reset/run_full_reset.py
```

Kết quả: exit 0; 2 cycles; 18 migrations/cycle; 23/23 assertions/cycle; HTTP/Auth pass; 48 tables; cleanup 0 container/volume/network/temp. Output chuyển UTF-8: `full_reset_runtime.log`. Runtime evidence 12 file + `hashes.sha256` (12/12 verify): `summary.json`, `snapshot_comparison.json`, `environment.json`, `exits.json`, `start.log`, `reset_cycle1.log`, `reset_cycle2.log`, `auth_seed_cycle1.log`, `auth_seed_cycle2.log`, `negative_controls.log`, `stop.log`, `commands.md`.

## 6. Cleanup / isolation check

```powershell
docker ps -a --filter "name=bh07-reset-verify"
docker volume ls | Select-String bh07-reset-verify
docker network ls | Select-String bh07-reset-verify
Test-Path "$env:TEMP\bh07-reset-verify-ddcc615aacfe4e5c"
```

Kết quả: không còn container/volume/network/temp; shared stack `supabase_db_badminton-hub` vẫn chạy, không bị chạm. Log: `cleanup_check.txt`.

## 7. Evidence bundle

`hashes.sha256` = manifest runtime 12 file (read-only verify trong `runtime_manifest_verify.json`). `bundle_hashes.sha256` = manifest toàn bundle reviewer (gồm runtime + audit/probe/log). Không ghi đè `full_reset_evidence` cũ; bundle cũ verify 12/10/8/8 trong `manifest_readonly.json`.
