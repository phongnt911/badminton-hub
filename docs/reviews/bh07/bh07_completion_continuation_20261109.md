# BH-07 — tiếp tục Anti CLI / Codex review ngày 09/11/2026

## Ủy quyền và mốc bắt đầu

Chủ dự án giao: “giao việc cho anti cli và review hoàn thành bh07”. Anti CLI triển khai; Codex kiểm chứng và review. Tiếp tục nhánh `feat/bh07-completion-local`, base `b72c563d9e519986dbd88ec98bcc3f015a41a442`; working tree sạch trước khi bắt đầu. Giữ kết luận ledger sentinel tại `b25aaef` và các bằng chứng lịch sử.

Yêu cầu này không phải chấp nhận rủi ro từng cổng hoặc phê duyệt merge/push/deploy/pilot/BH-08. Áp dụng [V8](bh07_readiness.md#411-v8--nghiệm-thu-toàn-bh-07), [ma trận hiện hành](bh07_completion_status_20261108.md) và [kế hoạch](../../superpowers/plans/2026-11-08-bh07-local-completion.md). Không mở lại các lỗi ledger đã đóng hay làm lại bằng chứng đã chốt khi chưa có lý do mới.

## Giao việc đầu tiên

- Anti conversation: `ba716cd0-af96-4dbb-8be9-2f1a230d9c1d`.
- Phạm vi đề xuất: V4 rehearsal Docker local cô lập, backup đồng thời với ít nhất hai writer HTTP/PostgREST xác thực; thiết lập mốc snapshot/commit và kiểm finance/ledger/audit sau restore.
- Trước triển khai: Anti đọc công cụ hiện có, bàn giao thiết kế tối thiểu, quyền sở hữu file, test tái hiện, lệnh runtime và điều kiện môi trường; Codex review thiết kế trước khi cho thực thi.
- Anti headless từ chối `RunCommand` ở lượt đầu, không có kết quả thiết kế. Đã yêu cầu tiếp tục bằng công cụ đọc file trực tiếp; lệnh kiểm chứng do Codex chạy, không gọi là self-check của Anti.
- Không sửa app/schema/migration, thêm dependency, ghi lại evidence cũ hoặc tác động DB dev đang chạy. Tài nguyên rehearsal phải tạo mới, kiểm sở hữu và cleanup xác minh.

## Điều kiện review V4

1. Hai HTTP writer thực sự thực thi trong khoảng backup; timestamps đơn thuần hoặc writer bị dừng không đủ chứng minh overlap.
2. Snapshot có ranh giới xác định; phân biệt commit trước snapshot, trong backup và sau snapshot. Không yêu cầu dữ liệu ngoài snapshot xuất hiện trong restore.
3. Dùng RPC nghiệp vụ thật và actor được xác thực; không dùng SQL postgres thay writer rồi gọi là HTTP/Auth PASS.
4. Restore kiểm payment/ledger/audit, tổng tiền, uniqueness/FK và retry/idempotency theo workload; oracle phải từ chối thiếu bằng chứng hoặc dữ liệu mâu thuẫn.
5. Cleanup chỉ xóa tài nguyên sở hữu; lỗi inspect/daemon/permission và cleanup chưa xác minh đều làm lần chạy thất bại. Không log secrets, JWT hoặc dump riêng tư.
6. Reviewer tự chạy kiểm chứng phù hợp trên source cụ thể; ghi rõ test, runtime, phần kế thừa và NOT RUN. Tối đa ba vòng sửa theo AGENTS hiện hành.

## Trạng thái

Anti đã trả thiết kế ở lượt 3; Codex chấp thuận phạm vi với yêu cầu sửa: export snapshot từ transaction giữ mở và truyền `pg_dump --snapshot`, không suy visibility từ HTTP timestamp/LSN; writer phải là Owner/Treasurer, không dùng Member cho quyền tài chính. Kiểm exact cardinality/amount/hash và replay cho payment/ledger/audit/operation_requests; fail-closed khi thiếu overlap, snapshot boundary, receipt hay cleanup.

Anti được giao viết test trước, chưa viết runner, để Codex chạy RED độc lập. Quyền sở hữu: bốn file mới `scripts/bh07_backup/run_v4_concurrent_rehearsal.py`, `scripts/bh07_backup/v4_concurrent_probe.py`, `tests/test_bh07_v4_backup_concurrency.py`, `docs/reviews/bh07/v4_concurrent_backup_handoff.md`. Không sửa file hiện có. Session-only settings chỉ cho phép các MCP đọc context, không bật bỏ qua toàn bộ quyền và không đổi cấu hình global. Lệnh/test/DB do Codex thực thi.

Codex baseline: `python -m unittest discover -s tests` trên source ban đầu **437 PASS**, exit0, 261.777s, archive `f7f178da1f5aa7a8`; không nhận là kết quả sau patch V4. Anti tạo 13 test; Codex chạy `python tests/test_bh07_v4_backup_concurrency.py -v` **13 FAIL**, exit1, đúng missing implementation. Đây là RED, không phải regression verdict của bản triển khai hoàn chỉnh. Lệnh discover có `-p` bị lean-ctx nhận nhầm là inline-code flag; dùng file test trực tiếp, không đổi policy.

Codex review test draft yêu cầu bổ sung relational records/hash và exact amount/ID thay vì chỉ tin cờ/row count; thêm malformed/type/timing/snapshot/source/cleanup mutants và kiểm activity DB thật. Đã giao Anti triển khai runner/probe/handoff và tăng cường test, chưa có runtime V4 mới.

Audit V8 độc lập đã đối chiếu tám cổng core, 28/28 đường dẫn local trong ba hồ sơ hiện hành và các SHA tham chiếu. P2 V8-D1 (dự thảo còn ghi ledger chưa có verdict) được Codex sửa một hàng và reviewer độc lập chốt đóng; xem [audit và phần đóng](v8_readiness_audit_20261109.md). Toàn BH-07/V8 vẫn chưa nghiệm thu; chưa có quyết định chấp nhận rủi ro cho các cổng chưa chạy.

Anti đã bàn giao candidate V4 bốn file mới, chưa chạy kiểm chứng. Source admission đang bị gateway giữ lại với `secret.redacted/redaction.incomplete`; Codex chưa đọc được runner nên chưa chạy Docker rehearsal. Đã yêu cầu Anti bỏ credential/token literal, sinh credential disposable ở runtime, không đổi/bỏ qua gateway, sửa SHA giả và link tương đối trong handoff. Chưa nhận unit test hay runtime PASS từ lời bàn giao; chờ source review thực tế.

Review chức năng đầu tiên đã tái hiện P1 validator fail-open và hai P2 provenance/publication; [review R1](review_v4_concurrent_backup_r1.md) có giới hạn, đính chính và capture synthetic mới với input/output/source hashes. Candidate hiện 27 test V4/1 FAIL; probe tác giả 21 controls PASS không thay verdict. Chưa chạy full suite sau patch hoặc Flutter/runtime mới.

Lượt sửa 1/3 ở conversation `ba716cd0-af96-4dbb-8be9-2f1a230d9c1d` bị API network timeout, chưa có bàn giao sửa hoàn chỉnh. Phiên context ngắn mới `05505acc-f3db-49b5-8d16-ac5d0b65e29c` bị print timeout 3 phút trước khi có edit (mtime runner/test không đổi); đã tiếp tục cùng vòng sửa với thời hạn 10 phút. Không tính lỗi kết nối/timeout thành một vòng review mới và không suy ra lỗi ứng dụng. Không có process Anti của lượt timeout còn chạy tại kiểm tra sau đó.

**Cập nhật sau sửa vòng 1/3:** Anti đã bàn giao; Codex tự chạy **40/40 V4 tests PASS**, **35 controls tác giả PASS** và kiểm lại probe reviewer hiện hành positive PASS/11 mutant FAIL (canonical đã thay đổi, không gọi exact replay). Hai control độc lập mới vẫn PASS sai: writers nối tiếp trong khoảng dump và cleanup liệt kê tài nguyên không liên quan. [Review sau vòng 1](review_v4_concurrent_backup_after_r1.md), [capture synthetic cố định mới](v4_review_r1_evidence/post_r1_capture_20261109.json). Đã giao sửa vòng 2/3 cho Anti, giữ probe/capture reviewer nguyên bản. R1 relational evidence chưa đủ để đóng toàn bộ; R2/R3 hết triệu chứng trong control đã chạy. Full suite sau patch đang chạy; source gateway vẫn giữ runner, chưa có Docker runtime hoặc toàn BH-07/V8 Đạt.

Full suite vòng 1 sau đó kết thúc **477/477 PASS**, 245.580s, exit0, archive `28be337a99df8f16`; hash runner/test kiểm sau suite còn khớp capture vòng 1. Không gán kết quả cho vòng 2 chưa bàn giao. Bổ sung giới hạn hash-before-import của control mới trong review; giữ nguyên capture và báo cáo lịch sử.

Codex chạy kiểm tra ứng dụng mới trong lượt này: `flutter analyze` **0 issue**, 38.9s; `flutter test` **247 PASS +1 SKIP**, exit0, archive `c6bf57e63de74c51`. `git diff --name-only -- lib test supabase web pubspec.yaml pubspec.lock` trước/sau không có thay đổi. Đây là regression app trên cùng source ứng dụng, không phải HTTP/heap/backup runtime mới; không gán thành self-check của Anti.

**Cập nhật sau vòng 2/3:** Codex **49/49 V4 tests PASS**, **44 controls tác giả PASS**. Control độc lập mới dùng digest tính lại, source/restore cùng row sai: ledger amount/audit request sai đã bị chặn, nhưng stored request trỏ sang payment khác và hai replay fingerprint không phải digest nhưng bằng nhau vẫn PASS. [Review sau vòng 2](review_v4_concurrent_backup_after_r2.md) và hai capture mới giữ nguyên bytes; hash trước cả import/fixture load và kiểm lại sau. Đã giao Anti sửa **vòng 3/3 cuối cùng**, tập trung remaining R1 stored result/replay evidence; không có quyền mở vòng 4. Source gateway vẫn giữ runner; full source/DB/HTTP/dump/restore/cleanup runtime V4 NOT RUN. Kết quả 477 thuộc vòng 1, không gán cho vòng 2/3.

Vòng 3 ban đầu bị Anti headless auto-deny MCP trước edit; mtime runner/test vẫn của vòng 2. Lượt diagnostic không dùng tool xác định chính xác target `lean-ctx_lean-ctx/ctx_glob`, nhằm tìm migration đọc RPC. Mẫu allow wildcard-server ban đầu không khớp; Codex sửa session-only settings sang năm đích đọc context có tên server chính xác và tiếp tục **cùng vòng 3**, không mở vòng 4. Không sửa global config, không bật skip-permissions hoặc thay source-admission gateway. Bản thân source runner vẫn chưa được Codex đọc qua gateway.

**Kết thúc vòng 3/3 — CHƯA ĐẠT, DỪNG:** Anti đã sửa/bàn giao. Codex **56/56 targeted PASS**; standalone probe **exit1 tại positive** do fingerprint fixture không khớp; control độc lập cuối **exit1** với 1 positive PASS, 7 mutant chặn đúng và 3 mutant vẫn PASS (nested stored result sai trạng thái, thiếu result, sai operation). [Review chốt](review_v4_concurrent_backup_final_20261109.md), [capture cuối](v4_review_r1_evidence/final_capture_20261109.json). R1 P1 còn mở, V4-R6 P2 mới; không mở vòng 4, không tự đổi reviewer thành implementer. Full suite candidate cuối đang chờ kết thúc; số liệu sẽ được ghi rõ trong review. Source gateway vẫn giữ runner; V4 runtime/toàn BH-07/V8 chưa nghiệm thu. Mọi thay đổi còn local/uncommitted, không merge/push/deploy/pilot/BH-08.

**Suite cuối đã kết thúc:** `python -m unittest discover -s tests` **493/493 PASS**, exit0, 300.616s, archive `dda516cc1529656f`; hash runner/test sau suite khớp capture cuối. Đây là working-tree check, không retag thành clean checkout. Probe/control reviewer vẫn FAIL như kết luận trên; lỗi còn mở không bị suite xanh ghi đè. Không còn process Anti ở kiểm tra sau bàn giao. [QA tài liệu độc lập](v4_test_design_review_20261109.md) xác nhận phạm vi synthetic, P1/P2 và điểm dừng; không gọi đó là source/runtime QA.

## Ủy quyền mới và bản sửa Codex

Sau điểm dừng, owner giao rõ **“codex tự sửa”**. Codex thực hiện bản sửa có giới hạn cho ba false-PASS stored result/operation và fixture fingerprint probe; đây không phải tự mở Anti vòng 4 hay thay quy tắc chung tối đa ba vòng. [Handoff sửa bổ sung](codex_v4_supplemental_handoff.md), [review độc lập](codex_v4_supplemental_review.md).

RED sáu test mới: 27 subtest/entrypoint failures; GREEN sáu test mới, 56 test V4 cũ, probe 49 controls. Full Python **499 PASS** do Codex chạy và **499 PASS riêng của reviewer**; root replay 11 input immutable cũ đều đúng kỳ vọng, reviewer thêm 48 mutant bị chặn. Analyze **0 issue**, Flutter **247 PASS +1 SKIP** mới trên app không đổi. Reviewer chốt **Đạt phần guard/probe sửa bổ sung**, không còn P0/P1/P2 trong delta được xem xét.

Gateway tiếp tục giữ full runner sau sửa, nên **full source/runtime V4 NOT RUN**. Phép edit AST có hash pin xác nhận byte ngoài guard giữ nguyên; không dùng hash làm chứng minh đã review nội dung code cũ. Toàn V4/BH-07/V8 vẫn chưa nghiệm thu; các cổng môi trường/quyết định risk acceptance chưa được ký, không merge/push/deploy/pilot/BH-08. Mọi thay đổi vẫn local/uncommitted; báo cáo/capture trước sửa giữ nguyên kết luận lịch sử.

## Giao tiếp theo: tiền kiểm runtime V4

Theo yêu cầu “giao việc tiếp tục”, giao Anti CLI conversation `71eb2541-a4eb-4c37-bead-20c09fb2402a` lập duy nhất `v4_runtime_preflight_20261109.md`; Codex review báo cáo sau bàn giao. Đây là nhiệm vụ tiền kiểm mới, không mở vòng sửa thứ tư hoặc sửa lại guard/probe đã chốt. Quyền sở hữu chỉ báo cáo mới; không sửa source/test, chạy command, cài công cụ, thay policy, đọc source bằng đường khác, tác động DB/Docker hoặc commit/push/deploy.

Codex cung cấp [metadata tiền kiểm chỉ đọc](v4_runtime_preflight_codex_evidence_20261109.json): Docker server 29.9.2 truy cập được, 11 container Supabase hiện có/0 container V4, khoảng 80.7 GB trống, bốn image ứng viên đã cache; scanner gitleaks/trufflehog không có trên PATH. Đây không phải runtime V4 hoặc xác nhận đúng dependency runner. Source vẫn bị gateway giữ với nguyên nhân UNKNOWN, working tree còn dirty và chưa có candidate sạch đã review toàn source.

Lượt đầu Anti thử lệnh khám phá tên file nên bị headless từ chối; diagnostic xác định chính xác `Get-ChildItem docs\\reviews\\bh07\\*readiness*`. Codex cung cấp đường dẫn trực tiếp và tiếp tục cùng assignment bằng MCP được giới hạn, không cấp quyền command. Báo cáo phải phân biệt bằng chứng Codex với kiểm tra Anti, giữ runtime NOT RUN và nêu điều kiện source admission/review, tài nguyên cô lập, snapshot/writer/restore/replay và cleanup trước khi chạy. Trạng thái giao: đang thực hiện, chưa có verdict review báo cáo.

**Review bàn giao tiền kiểm:** Anti đã tạo [báo cáo](v4_runtime_preflight_20261109.md); Codex [review](v4_runtime_preflight_review_20261109.md) chưa chốt, giao sửa tài liệu PF1–PF4 trong cùng conversation (job `shell_82370cdc2a089dbd`). Cần làm rõ cleanup ownership/absence, chứng minh writer overlap trong dump và snapshot visibility, bỏ khẳng định port bindings chưa đo, sửa đơn vị/attribution/link. Đây chỉ sửa báo cáo, không mở vòng implementation mới. Codex kiểm lại runner hash vẫn `53dc32fd1e647e2f0d7252fc513f85872c7250cea9b2c7d7b463289c17f7949d`, diff app/schema rỗng; không chạy suite/runtime mới. Full source admission và runtime vẫn chưa giải quyết; toàn BH-07/V8 chưa nghiệm thu.

**Chốt tiền kiểm sau sửa:** Codex đọc lại báo cáo Anti, đóng PF1–PF4 trong [review chốt](v4_runtime_preflight_review_20261109.md#chốt-bản-sửa-tiền-kiểm). Runner hash giữ nguyên, diff app/schema rỗng. Inventory Docker mới phân biệt đúng host publish 54321/54322/54323/54324/54327 và Auth 9999 nội bộ; chưa chứng minh cổng ứng viên trống. Báo cáo tiền kiểm Đạt, không phải full runner/runtime Đạt. Đã ghi handoff cụ thể cho quản trị source-admission trong review; cần admission chính thống và review full source trước rehearsal. Không lặp thêm vòng tài liệu hoặc bypass gateway. Full V4 runtime NOT RUN, BH-07/V8 chưa nghiệm thu, không merge/push/deploy/pilot/BH-08.

**Ủy quyền giao tiếp theo:** Owner yêu cầu “giao việc và tiếp tục”. Giao Anti cùng conversation đọc tài liệu/cấu hình gateway qua `ctx_read` nếu được admission, chỉ tìm nguyên nhân và hành động khắc phục chính thống; báo cáo sở hữu `v4_gateway_diagnostic_20261109.md`, job `shell_8beab127e4a16ef1`. Đây là chẩn đoán config mới, không lặp sửa tiền kiểm. Cấm shell command, retry doctor đã bị chặn, sửa policy/config/source, đọc runner bằng đường thay thế, xuất config/secret hoặc chạy runtime. Nếu config cũng bị giữ thì ghi UNKNOWN và dừng đường đó. Codex review sau bàn giao; chưa có kết quả chẩn đoán hoặc thay đổi admission tại lúc giao.
