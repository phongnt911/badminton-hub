# Codex tự sửa MC1–MC6 — 10/11/2026

Owner yêu cầu “codex tự sửa”, ngoại lệ cụ thể sau mốc dừng Anti ba vòng. Base `d2f6b079a7a6f7521d04b88ac6eb780db5718a56`, nhánh `feat/bh07-completion-local`. Đây là implementation/self-check của Codex, không tự nhận review độc lập hoặc V4 runtime PASS.

Candidate code/test được pin tại **`704a32658353a2148b1f94619db1e991b5562713`**. Bốn Git blob nguồn ở commit này khớp `source_after` trong summary của lượt chạy trước commit; không diễn giải thành lượt chạy full suite mới trên checkout sạch. Đối chiếu với base xác nhận lib/test/supabase và hai bundle lịch sử không có diff. Bundle bằng chứng mới giữ raw Windows log bytes bằng `-text`; thuộc tính whitespace chỉ chấp nhận CR cuối dòng, không chuẩn hóa lại log.

## Thay đổi

- MC1/MC6: collector đọc row thật theo schema migration, khóa actor/operation/request và payment; thiếu/trùng row hoặc sai quan hệ bị chặn. Receipt giữ alias cũ nhưng lấy `session_player_id`, `amount_vnd` và request liên kết từ dữ liệu persisted. Audit không lấy theo thứ tự hoàn tất. Fingerprint/count restore có scope workload để không đếm nhầm seed sẵn có.
- MC2: psql `-X -qAt` và marker SNAPSHOT; đọc pipe bằng thread/queue có timeout thật, kiểm exporter còn sống, đóng transaction và child process khi kết thúc/lỗi.
- MC3: observer loại backend của chính nó, chỉ lấy pg_dump active/COPY. Dump timestamp lấy ngay trong worker; cần hai HTTP call thành công hoàn toàn nằm trong dump lifetime và mẫu backend thật trong khoảng giao. Không có observation thì không gửi writer và không cấp PASS.
- MC4: đọc fingerprint fresh trước và sau replay, bao gồm dữ liệu public/auth và schema; thay đổi cùng row count cũng bị chặn. Auditor kiểm toàn map before/after và digest payment tương ứng, không chấp nhận cờ hardcode.
- MC5: chỉ collector hoàn tất không lỗi mới đưa candidate cho auditor; lỗi thực thi không được nâng thành PASS. Main yêu cầu source sạch trước khi tạo output và không thay đổi DB app/schema.

Tham khảo cú pháp chính thống: [psql PostgreSQL 17](https://www.postgresql.org/docs/17/app-psql.html), [pg_dump --snapshot](https://www.postgresql.org/docs/17/app-pgdump.html), [pg_stat_activity](https://www.postgresql.org/docs/17/monitoring-stats.html). Không đổi dependency, RPC hoặc migration.

## TDD và kiểm chứng

Test mới nằm `tests/test_bh07_v4_runtime_collection.py`: DB/HTTP giả, subprocess pipe thật; có orchestration main giả lập đầy đủ. Không gọi là DB/browser/runtime e2e.

- Lượt RED ban đầu: boundary tests lỗi vì logic cũ nằm trong main, chưa có API collector/snapshot có thể kiểm riêng; không nhận các AttributeError đó là tái hiện DB/runtime thật.
- Sau tách/sửa collector, hai control semantic mới tái hiện PASS sai của auditor: ledger hash đổi nhưng payment digest giữ nguyên, và sample ngoài khoảng giao writer. [Log RED](codex_mc_fixes_20261110_evidence/red_validator.log): 13 test, 2 FAIL, exit 1 trước sửa auditor. Cả hai sau sửa đều PASS.
- 14/14 test mới và 76/76 targeted V4 PASS. Full Python **513 test = 509 PASS +4 SKIP**, exit 0 (131.094s), probe **49/49 controls PASS**, exit 0. [Runner kiểm chứng](codex_mc_fixes_20261110_evidence/run_checks.py), [JSON/hash nguồn](codex_mc_fixes_20261110_evidence/summary.json), [log full suite](codex_mc_fixes_20261110_evidence/full_python.log), [log targeted](codex_mc_fixes_20261110_evidence/targeted.log), [log probe](codex_mc_fixes_20261110_evidence/probe.log). Hash nguồn trước/sau kiểm chứng trùng; không gộp skip thành PASS hoặc probe thành runtime.
- Lượt full suite đầu: 509 test, 4 FAIL +1 ERROR +4 SKIP, do bundle Git bị checkout CRLF và thiếu build/Python PATH; không diễn giải là PASS. Khôi phục đúng canonical blob HEAD của tám file evidence (chỉ khác line ending), tạo build bị ignore, dùng Python bundled trên PATH. [Tiền kiểm checkout](codex_mc_fixes_20261110_evidence/checkout_preflight.json); không viết lại manifest hay nội dung historical evidence. Tám kiểm tra liên quan đã chạy lại PASS.

## Review và giới hạn

Reviewer subagent độc lập đã đọc delta/schema và tự chạy 14/14 test mới, không nêu P0/P1/P2 trong phạm vi source/test đã xem. [Review chốt `704a326`](review_704a326_mc_fixes.md) xác nhận Đạt phần sửa MC1–MC6 trong phạm vi source/test. Đây không phải reviewer chạy Docker/HTTP/DB thật; full-suite là Codex implementer self-check.

**Đạt phần sửa MC1–MC6 trong phạm vi source/test theo review độc lập; toàn V4/BH-07/V8 chưa nghiệm thu.** Flutter analyze/test mới NOT RUN (SDK không có trên PATH); Docker cũng không có trên PATH hoặc đường cài chuẩn đã kiểm tra. Docker/DB/HTTP/Auth/dump/restore/cleanup rehearsal V4 mới, staging/production, thiết bị/mobile/native và pilot đều NOT RUN. Giữ bằng chứng cũ theo SHA, không retag runtime cũ thành source sửa mới. Không merge/deploy hoặc chấp nhận rủi ro thay owner.
