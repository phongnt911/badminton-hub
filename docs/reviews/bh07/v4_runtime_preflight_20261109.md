# Báo cáo tiền kiểm preflight và điều kiện tiên quyết V4 Runtime — 09/11/2026

## 1. Trạng thái & Bối cảnh nhiệm vụ
- **Nhiệm vụ giới hạn**: Khảo sát điều kiện tiên quyết tiền kiểm (preflight prerequisites) cho V4 runtime; **không phải vòng sửa thứ 4** (NOT correction4).
- **Nhánh**: `feat/bh07-completion-local`, base `b72c563d9e519986dbd88ec98bcc3f015a41a442`.
- **Working tree**: Uncommitted / dirty. Yêu cầu tiên quyết bắt buộc trước khi chạy runtime là phải có một ứng viên bất biến (immutable clean reviewed candidate) được rà soát đầy đủ và chốt manifest/hash; **báo cáo này hoàn toàn không tự cấp quyền commit, push, merge hay kích hoạt runtime**.
- **Bản sửa guard/probe Codex trước đó**: Đã nghiệm thu trong phạm vi giới hạn (LIMITED SCOPE) theo review bổ sung ngày 09/11/2026 ([codex_v4_supplemental_review.md](codex_v4_supplemental_review.md)) và bàn giao ([codex_v4_supplemental_handoff.md](codex_v4_supplemental_handoff.md)).
- **Runner hash**: SHA256 của `scripts/bh07_backup/run_v4_concurrent_rehearsal.py` là `53dc32fd1e647e2f0d7252fc513f85872c7250cea9b2c7d7b463289c17f7949d`. Đây là kết quả do **Codex kiểm tra lại độc lập** trong metadata tiền kiểm ([v4_runtime_preflight_codex_evidence_20261109.json](v4_runtime_preflight_codex_evidence_20261109.json)), không phải Anti tự chạy lệnh hay tự chứng minh byte. Không sửa runner, guards, probe, tests, app, schema, dependencies.
- **Nghiệm thu V4 / BH-07 / V8**: Toàn bộ V4, BH-07 và V8 **CHƯA NGHIỆM THU (UNACCEPTED)**. Các rủi ro vận hành chưa được chủ dự án phê duyệt (owner risks unapproved). Không merge, không push, không deploy, không pilot, không BH-08.
- **Runtime V4**: **NOT RUN**. Bộ test 499 Python PASS không thay thế được runtime DB/Docker thực tế.

## 2. Chuẩn đoán tiếp nhận mã nguồn (Source Admission Diagnostic)
- **Công cụ & mode**: `ctx_read` với chế độ `signatures` (fresh request) và lần thử `ctx_compose` tổng hợp đều bị giữ lại (`withheld`) do không xác minh được authority.
- **Trạng thái**: Tiếp tục bị chặn với các cờ `["secret.redacted", "redaction.incomplete"]`.
- **Nguyên nhân (Cause)**: **UNKNOWN**. Không suy diễn false positive hay kết luận "không có secret".
- **Ranh giới an toàn (Safety Boundaries)**:
  - Tuyệt đối KHÔNG bypass bằng cách dùng công cụ đọc khác, bản sao đã sanitize, in AST source, obfuscation, hay thay đổi cấu hình gateway/quyền hạn.
  - Không tạo dump mã nguồn thay thế.
  - Không cài đặt scanner bên ngoài; công cụ quét secret (`gitleaks`, `trufflehog`) chỉ được kết luận là **không có trên biến môi trường PATH** (`false` trên PATH), không cài đặt mới.

## 3. Dữ liệu môi trường độc lập (Ghi nhận từ Codex Metadata)
*Lưu ý: Toàn bộ thông số môi trường dưới đây được trích xuất từ dữ liệu kiểm tra read-only độc lập của Codex ([v4_runtime_preflight_codex_evidence_20261109.json](v4_runtime_preflight_codex_evidence_20261109.json)), không phải lệnh thực thi của Anti CLI:*
- **Docker Server Version**: `29.9.2` (khả dụng).
- **Tình trạng container hiện có**: 11 container Supabase đang tồn tại (không có container nào thuộc V4).
- **Trạng thái port bindings hiện tại**: **UNKNOWN** (chưa được đo đạc trong metadata kiểm tra; bắt buộc phải đo loopback port bindings thực tế trước khi cấu hình dịch vụ cô lập).
- **Baseline không liên quan**: `supabase_vector_badminton-hub` đang trong trạng thái restarting (không can thiệp).
- **Dung lượng đĩa khả dụng (Ổ C:)**: `80,743,747,584` bytes (xấp xỉ **75.2 GiB**, tương đương **80.7 GB** tính theo hệ thập phân).
- **Ảnh Docker cached khả dụng (Candidate images)**:
  - `postgres:17` (`sha256:b8faeff7712663c2773a190181e1246e37e364b887611c04658c28b44e2408fe`)
  - `ghcr.io/supabase/gotrue:v2.197.0` (`sha256:1736a63078f5922b198c4cbe50f80ab9a2d3b54fe8b7b6cfb2e9dc5dbbc12c6b`)
  - `ghcr.io/supabase/postgrest:v16.4` (`sha256:d155c6718ed9a9f990d159a2ab7c0a3f16944dbb6d0a0344557421042acfe0df`)
  - `ghcr.io/supabase/kong:2.8.1` (`sha256:1b53405d8680a09d6f44494b7990bf7da2ea43f84a258c59717d4539abf09f6d`)
- **Phạm vi dependency**: Đây là ảnh từ tài liệu bàn giao trước; các dependency chính xác bên trong runner chưa thể rà soát mã nguồn đầy đủ do gateway withheld.

## 4. Các điều kiện tiên quyết bị chặn (Blocked Conditions) trước Runtime
Trước khi có thể chạy rehearsal runtime V4, bắt buộc phải thỏa mãn 2 điều kiện cốt lõi:
1. **Source Full Review**: Toàn bộ mã nguồn runner phải được mở khóa qua cổng chính thống (sanctioned gateway admission) để rà soát độc lập toàn diện, không chỉ dừng ở metadata/hash/delta guard.
2. **Immutable Clean Reviewed Candidate**: Working tree hiện tại đang uncommitted/dirty. Cần có một commit ứng viên bất biến (immutable clean candidate) được rà soát đầy đủ và xác thực hash trước khi kích hoạt bất kỳ runtime nào (nhưng báo cáo này không tự cấp quyền tạo commit).

## 5. Đề xuất các lệnh kiểm tra Preflight / Root Verification (Read-Only)
Các lệnh đề xuất kiểm tra độc lập, chỉ đọc, không làm thay đổi hệ thống (khi được môi trường hỗ trợ):
- Kiểm tra Docker daemon & container:
  `docker version --format '{{.Server.Version}}'`
  `docker ps --format '{{.Names}} | {{.Status}}'`
- Kiểm tra ảnh Docker:
  `docker image inspect postgres:17 ghcr.io/supabase/gotrue:v2.197.0 ghcr.io/supabase/postgrest:v16.4 ghcr.io/supabase/kong:2.8.1 --format '{{.Id}} {{json .RepoTags}}'`
- Đo đạc thực tế các cổng loopback đang lắng nghe (trước khi chọn cổng cô lập):
  *Lệnh kiểm tra cổng phụ thuộc nền tảng; trạng thái bindings hiện tại là UNKNOWN cho đến khi được đo trực tiếp.*
- Kiểm tra dung lượng đĩa:
  `Get-PSDrive C | Select-Object Name,Free`
- Kiểm tra hash runner và git tree:
  `Get-FileHash scripts/bh07_backup/run_v4_concurrent_rehearsal.py -Algorithm SHA256`
  `git status --short`
  `git diff --name-only -- lib test supabase web pubspec.yaml pubspec.lock`
*(Nếu lệnh nào không được hệ thống hỗ trợ, trạng thái ghi nhận là UNKNOWN kèm điều kiện tiên quyết ngoại vi).*

## 6. Yêu cầu tài nguyên cô lập, kiểm tra va chạm và biên lai dọn dẹp (PF1 & PF3)
Để đảm bảo an toàn tuyệt đối cho 11 container Supabase và môi trường hiện có:
- **Kiểm tra va chạm trước thực thi (Preflight collision fail-closed)**: Trước khi khởi tạo, phải kiểm tra va chạm tên container, volume, network và port. Nếu phát hiện bất kỳ tài nguyên nào đã tồn tại từ trước hoặc trùng tên/cổng, hệ thống phải **dừng ngay lập tức (fail-closed)**; tuyệt đối không tái sử dụng, không ghi đè, và không nhận tài nguyên có trước làm của mình.
- **Định danh và nhãn sở hữu chính xác (Exact ownership ID / label / token)**: Mỗi phiên runtime phải sinh một session token duy nhất (ví dụ `v4_run_<uuid>`), gắn nhãn Docker metadata (`bh07.v4.owner_id = <uuid>`) lên mọi container, volume và network được tạo ra.
- **Chỉ xóa đúng tài nguyên sở hữu (Only own resources)**: Quá trình dọn dẹp chỉ được phép xóa các tài nguyên khớp chính xác với session token / nhãn của phiên đó. Không được chạm vào 11 container Supabase có trước.
- **Lỗi inspect phải FAIL (Fail on inspect error/unknown)**: Khi kiểm tra hoặc dọn dẹp tài nguyên, nếu việc inspect gặp lỗi hoặc trả về trạng thái không xác định, quy trình phải báo FAIL ngay lập tức, không được bỏ qua.
- **Xác minh vắng mặt sau dọn dẹp (Verified absence post-cleanup)**: Sau khi xóa tài nguyên, phải thực hiện kiểm tra độc lập (inspect absence) để xác minh tài nguyên đó đã hoàn toàn biến mất khỏi hệ thống. Biên lai `cleanup.ok: true` chỉ hợp lệ khi có kèm danh sách ID tài nguyên đã tạo, thời gian, và kết quả xác minh vắng mặt không phát sinh lỗi.
- **Cổng dịch vụ (Port bindings)**: Hiện trạng cổng của 11 container là **UNKNOWN**; bắt buộc phải đo đạc cổng loopback thực tế trước khi gán cổng thử nghiệm riêng biệt, tránh xung đột.

## 7. Yêu cầu bằng chứng Concurrency & Snapshot (PF2)
Runtime V4 chỉ được xem xét nghiệm thu khi cung cấp đầy đủ các bằng chứng chuẩn xác sau:
1. **Hoạt động đồng thời thực sự của hai writer (Two active writers overlap during dump)**: Phải cung cấp bằng chứng đồng bộ / rào cản hoạt động thực tế (activity barrier / synchronization trace) chứng minh 2 active concurrent writers thực sự chạy đan xen/chồng lấn (overlap) trong suốt khoảng thời gian tiến trình backup/dump đang đọc dữ liệu, không chỉ dựa vào client HTTP timestamps.
2. **Snapshot transaction mở và truyền vào pg_dump (Held export-snapshot transaction & pg_dump snapshot)**: Bắt buộc phải sử dụng cơ chế transaction snapshot của PostgreSQL: mở một transaction ở mức `REPEATABLE READ` (hoặc `SERIALIZABLE`), gọi `pg_export_snapshot()`, giữ transaction này mở liên tục (`held export-snapshot transaction`) trong khi truyền snapshot ID đó vào `pg_dump` qua tham số `--snapshot=<snapshot_id>`.
3. **Ranh giới hiển thị theo snapshot PostgreSQL (Snapshot visibility, not HTTP timestamps)**: Việc xác định dữ liệu nào thuộc bản snapshot phải dựa trên cơ chế hiển thị (snapshot isolation / visibility) của PostgreSQL tại thời điểm snapshot được export, không suy đoán từ thời điểm client nhận HTTP response `status=confirmed`.
4. **Bảo toàn bất biến nghiệp vụ khi restore & replay (Business restore / replay invariants)**:
   - Bản restore không bắt buộc phải chứa tất cả các transaction commit trong khoảng thời gian chạy dump (vì những transaction commit sau khi snapshot được tạo sẽ không hiển thị trong snapshot theo đúng ngữ nghĩa snapshot visibility).
   - Nghiệp vụ restore phải kiểm chứng đúng các bất biến:
     - Giao dịch tiền đề `P0 precommit` (`record_cash_payment`) bắt buộc phải có mặt đầy đủ trong bản restore.
     - Các giao dịch đồng thời `P1a concurrent`, `P1b concurrent` phải tuân thủ nhất quán theo snapshot visibility: nếu commit trước snapshot thì phải xuất hiện đầy đủ trong restore; nếu commit sau snapshot thì không xuất hiện trong snapshot restore nhưng phải được xử lý và kiểm chứng tính toàn vẹn khi replay nghiệp vụ.
     - Toàn vẹn sổ cái (ledger), số dư tài chính, log kiểm toán (audit log), và tính lũy kế/idempotency phải được đối soát khớp 100% giữa snapshot và restored database.

## 8. Kết luận & Sẵn sàng bàn giao Codex Review
- Báo cáo preflight này đã cập nhật đầy đủ các điểm PF1–PF4 theo review ([v4_runtime_preflight_review_20261109.md](v4_runtime_preflight_review_20261109.md)), hoàn toàn phi phá hủy (non-destructive), không thực hiện bất kỳ lệnh shell, Docker mutation, DB mutation hay thay đổi mã nguồn/test nào.
- Trạng thái V4 runtime: **NOT RUN**.
- Bàn giao báo cáo để Codex độc lập rà soát.
