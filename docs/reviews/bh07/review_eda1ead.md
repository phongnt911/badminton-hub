# Review retention attribution — sửa AT1–AT6 vòng1/2

- Ngày28/10/2026 Asia/Saigon; Codex reviewer, không sửa source triển khai/app/backend/DB.
- Checkout/source/docs: `eda1eadd6de1c58ed336bf79eb8e7bc7917ec065`, sạch trước review; base `272bb29d2960959cb856771e8b95c16f140645f4`.
- Đối chiếu [review37b4954](review_37b4954.md), [bàn giao](retention_attribution_handoff.md). Runtime QA cũ sourceb13e468 không bị retag thành phép đo mới.

## Kết luận

**Chưa đạt vòng1/2: còn AT1 P1 và AT2 P2. Đóng AT3/AT4/AT5/AT6 trong phạm vi đã yêu cầu.** Giao sửa vòng2/2 chỉ gói kiểm chứng/docs; không sửa app/backend hoặc mở gate khác.

Giữ Đạt QA runtime local hai expense-ID b13e468 và tooling RP3-C,V1,V5b,Provider. Rendered residual risk vẫn unattributed; toàn V2b/BH-07 chưa nghiệm thu. Không merge main/staging/production,deploy/pilot/BH-08.

## Rà soát AT1–AT6

| Mục | Kết quả |
| --- | --- |
| AT1 P1 | Còn mở: ba mutant gốc chặn đúng, nhưng validator vẫn nhận thiếu/mâu thuẫn evidence ở các record khác |
| AT2 P2 | Còn mở: narrative đã thu hẹp, machine fields và một số khuyến nghị còn kết luận dứt khoát |
| AT3 P2 | Đóng: field DTO được sửa,listener Web object graph NOT RUN; đây không phải full coverage Đạt |
| AT4 P2 | Đóng: run.log đã track;5/5 payload khớp Git/manifest,verify0; không nhận là browser/runtime mới |
| AT5 P2 | Đóng:84 link tương đối trong3doc tồn tại,không còn link Markdown tới máy cá nhân |
| AT6 P2 | Đóng: raw seed-title/prefix trong các dòng bị review đã được thay bằng identifier/hash/length |

## Phát hiện còn mở

### AT1 — P1: Chỉ kiểm một phần record nhưng chấp nhận toàn bộ attribution

- File:dòng: `scripts/bh07_appheap/audit_retention_attribution.py:282–309` (chỉ đọc rendered expense ở post_logout),`:214` (risk matrix ghi đè key),`:258–277` (missing occurrences mặc định0),`:320–340` (preconditions).
- Tái hiện: `python docs/reviews/bh07/review_eda1ead_evidence/extra_controls.py`, không sửa source/kỳ vọng/probe cũ.
- Positive vẫn exit0. Bốn mutant đều **exit0**, `valid=true`, status supported-hypothesis:
  1. Bỏ toàn bộ path expense2 ở hai mốc sau logout, cả2chu kỳ.
  2. Bỏ cả2 rendered paths ở post_actor của cả2chu kỳ.
  3. Thay danh sách8 residual risk bằng8 bản sao của cùng1record (count vẫn8; key matrix bị ghi đè).
  4. Bỏ occurrences của cả2peer tại post_logout (missing được coi là0).
- Kỳ vọng: mỗi record bắt buộc tồn tại,đủ đúng8 tổ hợp cycle×epoch×sentinel,không trùng;metadata/path/count phải khớp nguồn. Thiếu/sai phải FAIL/UNKNOWN vàCLI khác0,không công bố xác nhận attribution cho cả8record.
- Cách sửa: kiểm đầy đủ8risk/paths và các peer mốc bắt buộc,không dùng count tổng thay identity/coverage;không default thiếu count thành0;đối chiếu risk record với snapshot/path tương ứng. Có thể tái sử dụng semantic auditor hiện hành cho preconditions rồi thêm kiểm cần riêng,không copy gate yếu hơn. Giữ positive và cả3 mutant cũ;thêm bốn control trên với expectation bị chặn. JSON/verdict/Markdown/exit cùng dữ liệu validated.
- Ba mutant reviewer gốc đã đúng CLI1; không coi đó là bằng chứng toàn wrapper fail-closed.317tests hiện xanh vì chưa assert bốn ca mới.

### AT2 — P2: Trường JSON và khuyến nghị vẫn suy “app sạch/engine nguyên nhân” vượt bằng chứng

- File:dòng: `scripts/bh07_appheap/audit_retention_attribution.py:356–360`,`:380–383`; `docs/reviews/bh07/retention_attribution_evidence/summary.json:33` (`models_released=true`); report `retention_attribution_report.md:189`.
- Tái hiện: chạy CLI positive ra thư mục temp hoặc đọc extra_controls.json/attribution_audit.json. Phần limits nói secondary_app_paths_possible=true,nhưng app_model_retention/app_model_instance_retained lại false. summary nói models_released=true;report vẫn khẳng định thiết kế nội tại engine nên không cần sửa app.
- Kỳ vọng: boolean false sạch toàn app phải là chưa xác định,hoặc thay bằng claim có tên đúng phạm vi hai ID. Path qua cache và2ID mất không loại được app giữ title string/copy riêng hoặc path khác;không có raw whole-object proof/native measurement.
- Cách sửa: đồng bộ structured JSON/report/handoff/map:observed peer IDs absent;app-wide retention unknown;engine cache là supported hypothesis,official residual risk unattributed. Tách xác nhận gate ID khỏi kết luận model/controller/widget toàn app;không dùng lời khuyên “không cần sửa app” như attribution đã chứng minh. Native giữ NOT RUN. Test assert machine fields không mâu thuẫn limits trên positive,mọi failure và bản summary được publish. Không cần sửa app hay bắt chạy native chỉ để đính chính claim.

## Reviewer tự chạy

- Python discover317/317;Flutter analyze0 issue;Flutter247passed+1skip. Numeric exits/log trực tiếp trong [evidence](review_eda1ead_evidence/);không dùng log tác giả thay lượt chạy.
- Probe cũ nguyên bản:positive0,peer-retained1,wrong-environment1,missing-all-paths1.
- Extra controls:positive0,bốn incomplete/mismatched evidence đều0 sai kỳ vọng như AT1.
- Bundle mới5/5;4bundle lịch sử3/3 mỗi bundle,khớp Git/hash,readonly trước/sau;byte lịch sử không đổi từ base. QA semantic auditor0;full runtime/DB mới NOT RUN.
- Chỉ script kiểm chứng/test/docs thay đổi;lib/test/supabase không đổi;git diff --check sạch. Manifest reviewer được verify readonly riêng;không regenerate bundle tác giả.

## NOT RUN

Runtime/SQL mới,exact-engine source mapping/exhaustive retained paths;full V2b private models/cache/listener/charge/payment/bank thật/receiver/ledger;Dart VM desktop/mobile,browser khác/đa tab/tải thật. Managed backup/PITR/offsite/encryption/retention,concurrent writers,staging/production/restore thật,banking/webhook,rehearsal/pilot và toàn BH-07 giữ NOT RUN. Không biến accepted local hai ID hoặc residual-risk acceptance thành PASS cho các phần này.
