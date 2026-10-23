# Bàn giao backup/restore rehearsal BH-07 local

**Kết quả review hiện hành: Chưa đạt R1 P2; xem [review_b626a78.md](review_b626a78.md). Bàn giao ban đầu dưới đây giữ làm lịch sử, không còn là trạng thái chờ kết luận.**

**Chờ review độc lập. Codex triển khai/tự kiểm, không phải review độc lập.** Bước tiếp theo được chủ dự án giao sau khi đóng browser. Không tự ghi hoàn thành toàn BH-07, không merge main/deploy/pilot.

- Nhánh: `feat/bh07-backup-rehearsal`.
- Base browser đã đóng: `74305bb343fbaf548cb5eea38a77475cc3a21b39`.
- Tested source: `b626a7852401e91db436ecc70134150f4c87c06f`, worktree sạch.
- Chỉ source mới: `scripts/bh07_backup/run_local_rehearsal.py`; docs/evidence commit sau không sửa source. Runbook: [26](../../26_BH07_OPERATIONS_REHEARSAL.md).
- Environment: Linux/Docker, PostgreSQL17.11, GoTrue2.197.0, PostgREST16.4, Kong2.8.1; Flutter3.47.7. Supabase component stack thật local; không dùng managed project/production.

## Kết quả tự chạy

| Lệnh | Exit | Kết quả |
|---|---|---|
| `python -u scripts/bh07_backup/run_local_rehearsal.py --out /workspace/scratch/bh07-backup-run-01` |0|13/13 check, dump/key tạm đã xóa|
| `flutter analyze` |0|0 issue|
| `flutter test` |0|240 PASS,1 skip|
| `BH02_TEST_CONTAINER=bh07-backup-regression python -u docs/reviews/bh07/run_bh07_tests.py` |0|23/23 DB; Auth stub riêng, không phải bằng chứng GoTrue|

Log gốc và JSON trong `backup_restore_evidence/`. Lần DB đầu exit1 vì container mới thiếu role anon; log `db_preflight_failure.log` giữ nguyên. Sau bootstrap `anon/authenticated/service_role` mới chạy lại xanh; không sửa runner/app. DB JSON ghi đúng tested SHA, dirty=false. Source rehearsal capture dirty trước khi tạo output; output ngoài repo. Khởi tạo nguồn dùng recipe đã có `late_response_evidence/run_local_stack.py` (không sửa recipe); generated private copy chỉ đổi root/out/private. Seed SQL trực tiếp cho application fixture; thao tác thanh toán và quyền khôi phục được thực hiện HTTP thật, không mock.

## Cần review

Tự chạy rehearsal từ checkout sạch và output mới; lệnh tạo/xóa chỉ container fixture của chính nó. Phải không có stack `bh07-http-review-*` có sẵn. Không nhận remote URL. Kiểm dump globals/DB, restore sang cluster mới, data/schema/roles/sequences fingerprint khớp trước Auth restart, Owner/cohost/outsider/anonymous và sai mật khẩu, replay cùng payment ID/1 ledger/1 operation, aggregate server giữ nguyên. Review3 negative controls: corrupt archive, audit row bị xóa dùng cùng snapshot comparator, RPC grant bị thu hồi dùng cùng HTTP oracle. Không suy privacy đầy đủ chỉ từ8 tiền null; privacy sâu đã ở gói HTTP/browser cũ, không chạy lại trong rehearsal.

Backup0,369giây, recovery đến Auth/ACL/replay11,386giây là số đo fixture quiesced, không là production SLA. Toàn bộ bảng Auth/public có counts+hash, không công bố row payload/dump/password/JWT. Các JSON/hash không phải backup có thể phục hồi; archive thực chỉ giữ tạm rồi xóa. Nguồn GoTrue dừng trước snapshot; restore fingerprint so trước login mới vì login thay Auth/session rows. Negative tamper dùng public fingerprint sau smoke để tránh Auth write noise.

Manifest UTF8/LF/secret kiểm bằng:

```bash
python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/backup_restore_evidence
```

Reviewer chỉ verify readonly; so hash toàn thư mục trước/sau. Flutter/DB có thể tự chạy lại; khi tạo container DB mới phải tạo3 roles fixture nêu trên trước runner. Không chạy recipe vào stack dùng chung.

## NOT RUN

Review độc lập của gói mới; backup toàn bộ managed Supabase/Storage objects/Edge Functions/Realtime/external secrets; PITR/offsite/encryption/retention automation; backup cùng concurrent writer; browser/device/offline/deep link ở gói này; ngân hàng/webhook; staging/production/restore thật; rehearsal tải thật/pilot và nghiệm thu toàn BH-07. Không suy rộng local PostgreSQL/Auth thành hoàn tất các cổng này.

Kiểm đóng gói: manifest11/11, UTF8 không BOM/LF,0 secret/JWT ngoài allowlist PASS, exit0. Hash tất cả file evidence trước/sau verify giống nhau (readonly PASS). `git diff 74305bb -- lib test supabase` rỗng; `git diff --check` sạch. Không chạy lại browser vì bước này chỉ bổ sung runner backup và docs; browser giữ nguyên kết luận đóng.
