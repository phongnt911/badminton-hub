# Review V5b BH-07 — 19ab207 — vòng1/2

## Kết luận

**Chưa đạt bản sửa V5b vòng1/2.** Đóng R4 về đóng gói/evidence; R1–R3 chưa triệt để, thêm R5 về test không kiểm hành vi. Còn **1 P1 +3 P2**, không phát hiện P0 trong phạm vi. Không sửa source triển khai, không merge main/staging/production/deploy/pilot/BH-08; V1 giữ Đạt local, toàn BH-07 chưa nghiệm thu.

- Base review: `a57f0c2c58956b5f047ffed365374470be702141`.
- Tested source: `19ab207ea75023f8a21d15da01ebc20fc09b0db4`.
- Docs/evidence origin thực tế: **`e53f9944d3d599cf4183dfdbfb7d206306bb8e23`**, parent19ab207; checkout sạch trước review. SHA dài yêu cầu `e53f99479b18a667ec3ec5caae5dd271b8be8ea4` không tồn tại sau fetch. Kết luận áp dụng source19ab207 và docs origin thực tế, không gán sai SHA.
- Theo AGENTS/docs/ai/REVIEWER.md; reviewer không viết bản fix của người triển khai. Fault injection chạy nguyên AST bằng tài nguyên giả; không sửa file source hay gây lỗi DB/Docker thật.

## Phát hiện còn mở

| Mức | file:dòng | Mô tả / tái hiện | Cách sửa |
|---|---|---|---|
| **P1 — R1** | `scripts/bh07_reset/run_full_reset.py:212`, `:630`, `:862` | Preflight chạy docker ps với check=False nhưng không kiểm returncode. Docker lỗi/không kiểm được inventory, stdout rỗng vẫn PASS và cho phép start/reset. owned_containers được ghi sau start nhưng không dùng để giới hạn cleanup; source vẫn docker rm-f mọi ID khớp substring project. Probe: Docker list exit1/daemon failure vẫn preflight PASS; cleanup thấy foreign-id ngoài owned-id thì xóa foreign-id. Preflight đã chặn được trường hợp inventory thành công thấy resource, nhưng chưa bảo đảm ownership khi inventory thất bại/race. | Fail-closed cho preflight/owned inventory error; không bắt đầu reset khi chưa chứng minh inventory sạch. Dùng ID/label/run identity được kiểm chứng cho quyền cleanup, không xóa mù ID từ name-filter. Test list lỗi/exception, foreign resource, preflight conflict, start lỗi/chưa sở hữu; foreign resource không được reset/stop/rm. Không gây data loss thật để tái hiện. |
| **P2 — R2** | `scripts/bh07_reset/run_full_reset.py:736`, `:740`, `:758`, `:783`, `:810` | Positive baseline mới không gọi HTTP: tokens_ownera không được gán trong main, nhánh else tự tạo `(200, {'can_view_finance': True})`; pos_st/pos_b cũng không được assert. Predicate negative còn tìm auth words trên toàn JSON, gồm hint. Response403 codeXX000/message unrelated database failure + hint chứa “JWT api key FORBIDDEN permission denied” được nhận domain_verified=true cho cả3 controls. Probe giữ positive hợp lệ, INVALID_INPUT cũ đã bị chặn, nhưng XX000 sai miền vẫn PASS. Không kết luận verify_http_and_auth trước đó là mock; lỗi nằm ở baseline mới và predicate này. | Bỏ response200 giả; dùng HTTP result thật đã assert (có thể tái dùng kết quả thật có provenance từ smoke) hoặc thực hiện baseline thật và assert nó. Chỉ chấp nhận tuple status/code/message đúng contract/stack, đọc trường cụ thể; không dùng hint/detail/substringjwt hayapikey để cứu code lạ. Có helper/predicate hiện hành cho tests: XX000/INVALID_INPUT/NOT_FOUND/PGRST202/route404/transport phải fail, known SQLSTATE/domain/gateway variants mới pass. |
| **P2 — R3** | `scripts/bh07_reset/run_full_reset.py:858`, `:867`, `:884` | Các lệnh inspection check=False tiếp tục bỏ returncode. Nếu docker ps trước/cuối đều exit1 stdout rỗng, cleanup_errors=[] và clean=true, nên có thể báo PASS khi không xác minh được absence. p_final ở ngoài try: exception từ final inspect ghi đè primary_error trước khi tới raise primary_error. Probe: inventory errors vẫn clean=true; FinalInspectError thay PrimaryError. Các ca private-delete failure và stop error thông thường đã chặn/giữ primary đúng, nhưng nhánh này còn hở. | Kiểm exit/exception mọi bước inspection/removal, kể cả final; unknown inventory là cleanup failure, không phải0 resource. Bảo đảm xử lý final inspect trong best-effort scope và luôn giữ primary error nếu có; log cleanup_errors an toàn, không chứa secret. Test initial/recheck/final nonzero và exception, primary+final failure, stopped/remaining resource, private failure. |
| **P2 — R5 (mới)** | `tests/test_v5b_runner_flaws.py:32`, `:45`, `:72` | Test chủ yếu assert chuỗi source và tự so sánh literal. R2 không hề gọi predicate nguồn; R1 không thực thi preflight hay kiểm vị trí gọi trước prepare/start (chỉ tìm tên trong assignment). Mutant thêm return PASS trước toàn bộ kiểm preflight, giữ source text phía sau: cả4 test vẫn xanh. Không thể dùng “R1–R4 Verified” từ suite này làm chứng cứ tái hiện/sửa gate. | Chuyển sang test behavior của hàm/AST/helper hiện hành, inject Docker/socket/HTTP dependencies, so expected với kết quả thật. Giữ positive và negative controls, assert thứ tự/no unsafe side effects, thêm mutant kiểm suite phải fail khi gate bị vô hiệu. Không copy predicate vào test, không sửa kỳ vọng để nhận lỗi. |

Lệnh tái hiện toàn bộ: `python docs/reviews/bh07/review_19ab207_evidence/independent_probes.py`. Script chỉ đọc source/tests và tạo file/thư mục giả tạm; trích AST nguyên gốc. Mutant nằm ở temp file, tests tác giả được chạy nguyên nội dung chỉ đổi RUNNER_SRC sang temp mutant; source repo không sửa. Exit0 của probe nghĩa là các fault được tái hiện đúng, **không phải V5b PASS**.

## R4 — Đóng trong phạm vi được giao

- Manifest12/12,0 missing/extra/mismatch;7 log trước thiếu nay có trong Git.
- UTF8 không BOM/LF; regex yêu cầu và verifier không thấy JWT/key/password fixture trong evidence đã publish; verify readonly, hash cả13 file gồm manifest trước/sau giống nhau.
- Oracle lưu đủ48 table_stats/cycle, tên bảng và count từng bảng trùng giữa hai chu kỳ, schema hash trùng. Không yêu cầu row hash Auth có UUID/time ngẫu nhiên phải trùng; oracle của cổng là schema/count theo đặc tả.
- Summary23/23 mỗi cycle,23 assertion detail đều pass; source có23 check calls. Gộp hai điều kiện bằng AND không bỏ điều kiện cũ. git_dirty=true được giữ và có danh sách dirty paths; các path công bố chỉ docs/evidence, không tự sửa thànhfalse. Đây là evidence tác giả đã kiểm, không là lần chạy DB của reviewer.
- Không dùng trạng thái PASS tự kiểm trong summary để thay verdict reviewer; handoff hiện ghi Chờ review.

## Kiểm chứng độc lập lượt này

| Kiểm tra | Exit / kết quả |
|---|---|
| Fetch/checkout đúng source và docs origin thực tế | Source19ab207, docs e53f9944; worktree sạch trước review |
| `PYTHONUTF8=1 python tests/test_v5b_runner_flaws.py` |Exit0,4/4 tests xanh; suite không bắt mutant như R5 |
| Independent AST probes |Exit0, tái hiện R1–R3/R5, positive controls đúng, source không đổi |
| Manifest audit + `--verify` |Exit0,12/12,0missing/extra/mismatch,0secret theo mẫu, readonly |
| Flutter analyze |Exit0,0 issue, Flutter3.47.7/Linux |
| Flutter test |Exit0,240 PASS+1 skip — lần chạy mới reviewer |
| Runtime CLI2 reset |**NOT RUN lượt này**: host32GB còn khoảng661MB; lượt trước image pull đã fail vì thiếu đĩa. Yêu cầu cho phép audit/AST thay runtime khi thiếu tài nguyên; không lặp pull để làm đầy đĩa hoặc dùng stack dựng tay thay CLI |
| Scope |Source chỉ2 file runner/Python test; docs commit không đổi source. lib/test/supabase/migration không đổi |

Đọc raw reset/auth/stop logs và full JSON để đối chiếu tuyên bố tác giả; không dùng chúng làm kết quả tự chạy runtime. Evidence scan không bảo đảm tuyệt đối mọi loại secret. `git diff --check base..HEAD` có whitespace ở code/test và blank EOF trong log; không sửa raw log/source ở vai reviewer. Đây không thêm một finding correctness riêng.

Bằng chứng/script/log của reviewer nằm `review_19ab207_evidence/`. Source/fixture và evidence cũ giữ nguyên; chỉ bổ sung report/status/evidence reviewer.

## NOT RUN

- Full CLI2 reset,18 migration/seed/Auth/23 DB assertions và HTTP smoke thực thi lại bởi reviewer trên bản19ab207 do thiếu đĩa; cần môi trường đủ dung lượng sau khi sửa để xác minh runtime. Kiểm JSON tác giả không đổi trạng thái này thành PASS.
- V2/V2b device/browser khác/offline/deep link/private heap; V3 managed Supabase/PITR/offsite/encryption/retention; V4 concurrent writers; V5 staging/production/restore thật; V6 banking/webhook; V7 tải/pilot; V8 nghiệm thu toàn BH-07.
- Fault Docker/ownership/permission thật: chỉ dependency-injection/AST với data giả, không phá resource thật. Không chạy lại335 DB vì không đổi backend.

**Chưa đạt V5b vòng1/2 — giữ R4 đóng, giao AI triển khai sửa R1–R3 và R5 vòng2/2; reviewer chốt lại.** Không tự mở phần tiếp theo hoặc sửa source thay người triển khai.
