# Reviewer evidence — V5b `8e26e06`

Bundle này do QA/reviewer khác tạo ngày 25/10/2026, không tham gia sửa bản Codex V5b.

## Runtime evidence (12 file + manifest)

`hashes.sha256` là manifest runtime gốc do `run_full_reset.py` tạo; verify 12/12 tại `runtime_manifest_verify.json`. Các file runtime:

`summary.json`, `snapshot_comparison.json`, `environment.json`, `exits.json`, `start.log`, `reset_cycle1.log`, `reset_cycle2.log`, `auth_seed_cycle1.log`, `auth_seed_cycle2.log`, `negative_controls.log`, `stop.log`, `commands.md`.

## Reviewer artifacts

- `tests_11.log`, `tests_11_raw.log`: 11/11 behavior tests.
- `codex_fix_controls.log`: 14 scenario controls + 3 mutant gates, exit 0.
- `verify_manifests.log`, `manifest_readonly.json`: verify readonly 12/10/8/8 cho bundle cũ.
- `independent_probes.py`, `independent_probes.log`: probe độc lập R1/UUID/R2 (17 case).
- `full_reset_runtime.log`: output full CLI2 reset (UTF-8, đã chuẩn hóa từ capture PowerShell).
- `oracle_audit.json`: 48/48 count, schema hash khớp, 24/48 sha256 khác.
- `db_assertions_audit.json`: 23/23 cycle 1; cycle 2 count 23, detail không được runner persist.
- `http_auth_audit.json`: assertion HTTP pass theo script; raw response không persist.
- `cleanup_check.txt`: 0 container/volume/network/temp sau cleanup.
- `scope.txt`: scope diff, source hash, 18 migration, old evidence unchanged.
- `environment_reviewer.json`: môi trường reviewer, image digest quan sát, giới hạn binding.
- `reviewer_commands.md`: lệnh đã chạy.

## Kết luận

Runtime PASS, nhưng review kết luận **Chưa đạt** do 7 P2 evidence/provenance/assertion. Xem `../review_8e26e06.md`.

`bundle_hashes.sha256` là manifest toàn bundle (trừ chính nó); `hashes.sha256` giữ nguyên phạm vi runtime 12 file.
