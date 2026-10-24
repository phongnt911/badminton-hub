# Review V5b BH-07 — 0392e21

## Kết luận

**Chưa đạt trong phạm vi kỹ thuật V5b full Supabase CLI reset local.** Còn1 P1 và3 P2 dưới đây. Không phát hiện P0. Không nghiệm thu toàn BH-07, không đổi verdict V1, không merge main/deploy/pilot/BH-08.

- Base: `6e5dba6c1b67c06bf98283b6bacac47ae2be3dc6`.
- Tested source: `0392e2166bc0c33b3170e6919d86470d193d6301`.
- Docs/evidence thực tế trên origin: **`c3cda7108809037ee884ca9c769a7264f13a9530`**, parent trực tiếp0392e21. SHA yêu cầu `c3cda717540236a9b407b489811f97464b73b22e` không tồn tại trong Git sau fetch; không gán SHA sai cho evidence. Kết luận này áp dụng đúng source0392e21 và docs origin thực tế.
- Reviewer Codex không viết/sửa2 file V5b của người triển khai. Chỉ thêm probe/report/evidence và trạng thái review, giữ evidence tác giả nguyên bytes.

## Phát hiện

| Mức | file:dòng | Mô tả và tái hiện | Kỳ vọng / cách sửa |
|---|---|---|---|
| **P1 — R1** | `scripts/bh07_reset/run_full_reset.py:46`, `:565`, `:587`, `:724` | Project ID cố định `bh07-reset-verify`, không preflight resource/ownership trước start. CLI có thể dùng lại project đã tồn tại; runner tiếp tục db reset và finally stop --no-backup mà không biết resource của run nào. Probe AST nguyên main với marker project có sẵn cho thấy reset và stop đều được gọi, không có inspect trước start. Không dùng project thật để chứng minh lỗi phá dữ liệu. | Phải từ chối project/resource/port đã có trước run hoặc dùng ID/port riêng từng run; xác nhận mapping config→project/container; chỉ reset/stop/delete resource đã chứng minh thuộc run. Thêm positive project mới, negative project sẵn có và start lỗi chưa có ownership; phải không gọi reset/stop lên resource không sở hữu. Đây là nguy cơ phá dữ liệu của project test/lượt chạy khác, không phải bằng chứng đã chạm production. |
| **P2 — R2** | `scripts/bh07_reset/run_full_reset.py:677`, `:687`, `:703` | Negative controls chỉ kiểm nhóm status. Cùng nguyên AST, response400 INVALID_INPUT cho tất cả RPC vẫn “ALL PASS”; outsider403 NOT_FOUND cũng PASS; thiếu apikey404 route không tồn tại cũng PASS. Payload thiếu apikey còn thiếu expected_version/request_id nên có thể fail vì signature trước khi chứng minh quyền. | Assert status + mã/domain/message đúng tầng thật của stack; dùng payload hợp lệ chỉ bỏ credential và positive cùng payload có credential. Từ chối INVALID_INPUT/NOT_FOUND/PGRST202/route404/transport khi đang kiểm quyền. Ghi rõ variant gateway được phép và chứng minh positive route tồn tại; loopback guard tiếp tục dùng hàm nguồn. Không chấp nhận mọi4xx là bằng chứng ACL/API key. |
| **P2 — R3** | `scripts/bh07_reset/run_full_reset.py:724`, `:731`, `:741` | Cleanup chỉ `docker ps -q`, không `-a`, nên không đếm container đã dừng; rmtree(ignore_errors=True) không kiểm path còn. Fault probe chạy nguyên finally báo0 remaining dù model còn container stopped hoặc working dir vẫn tồn tại. Nếu stop lỗi, finally dừng ngay, không kiểm/dọn tiếp và lỗi cleanup ghi đè lỗi chạy chính (probe OriginalRunFailure→CleanupStopFailure). | Gate fail-closed trên resource thật: running+stopped containers, resource owned liên quan và temp path; kiểm lỗi Docker/inspect không phải absence; tiếp tục best-effort sau lỗi, giữ primary error, lưu stage/exit/cleanup_errors kể cả run FAIL. Thêm negative stopped container, remove noop, private delete fail, stop/inspect error, lỗi chính kèm cleanup lỗi; không log credential. Không chỉ đổi ps thànhps-a mà bỏ các lỗi còn lại. |
| **P2 — R4** | `docs/reviews/bh07/full_reset_evidence/hashes.sha256:1`, `environment.json:5`, `summary.json:9`; `scripts/bh07_reset/run_full_reset.py:752`; `docs/reviews/bh07/full_reset_handoff.md:39` | Manifest khai12 file nhưng repo chỉ có5 nội dung+manifest. **Thiếu7 log**: auth_seed_cycle1/2.log, negative_controls.log, reset_cycle1/2.log, start.log, stop.log; không thể verify12/12 như bàn giao. environment git_dirty=true không kèm danh sách/hash thay đổi; summary ghi24 assertions/cycle trong khi handoff/trạng thái ghi23. Oracle chỉ publish sample5 table_stats, không đủ48 bảng/cả2 cycle; kết quả schema/HTTP và chi tiết DB assertions không được lưu đầy đủ. | Khôi phục log gốc đúng hash nếu còn; nếu không, ghi mất file và chạy lại source sạch vào bundle mới, không chế log. Force-add log bị ignore, audit manifest cả missing/extra/hash/secret trước bàn giao. Ghi dirty paths/source hashes thực tế, không sửa true thànhfalse; run mới sạch phải có provenance riêng. Lưu full schema/count comparison2 cycle, target DB identity và toàn bộ HTTP/DB assertion results; thống nhất23/24 theo thực tế. Người triển khai ghi tự kiểm PASS/Chờ review, không tự cấp verdict nghiệm thu. |

### Lệnh tái hiện probe

```bash
python docs/reviews/bh07/review_0392e21_evidence/reviewer_probes.py
```

Probe trích nguyên negative-control block, main và finally từ source hiện hành bằng AST. Không copy predicate hay sửa kỳ vọng. Chỉ stub transport/Docker với response/tài nguyên giả, không mutation DB thật hoặc chứa secret. Có positive control; ba negative lỗi sai ngữ nghĩa bị nhận thành công, hai cleanup fault false-success, ownership fault và primary-error masking được tái hiện. Probe exit0 nghĩa là tái hiện đúng lỗi đang review, không phải runner V5b Đạt. Các dependency fault là mô phỏng, không giả thành sự cố thật trên stack.

## Reviewer tự chạy

- Checkout main reviewc3cda710 sạch; tạo **worktree riêng source0392e21** để runner không ghi đè `full_reset_evidence` tác giả. Runner luôn ghi thư mục này theo ROOT, không có --out.
- CLI **2.122.0** pin qua wrapper npx ngoài repo; Docker28.4.0/Linux. `db reset --help` xác nhận --local/--no-seed/--yes/--workdir. DO_NOT_TRACK=1 và npm cache/temp riêng trong workspace để tránh filesystem home readonly. Wrapper chỉ pin executable, không đổi source/assertion/CLI business args. Khác Windows/Docker29.8.2 của tác giả.
- Đã chạy `python -u scripts/bh07_reset/run_full_reset.py` trên worktree source sạch; log ghi SHA0392e21, dirty=False. **Exit1 tại supabase start do image pull “no space left on device”**. Host filesystem32GB, còn khoảng643MB sau failure. **0 reset cycle hoàn tất**; không có23/24 DB assertion, HTTP smoke hoặc oracle48/48 mới của reviewer. Không gọi lỗi dung lượng là lỗi migration và không dùng log tác giả thay lần chạy.
- Runner finally stop --no-backup thành công. Kiểm riêng bằng docker ps-a/network/volume theo project ID cho kết quả rỗng sau run. Không prune image/cache hay xóa resource có sẵn để ép full run; không retry bằng cách tắt bớt gate/service hoặc đổi thành stack dựng tay.
- 5 file tác giả hiện có khớp hash;7 entry missing, nên manifest tổng **FAIL**. Scan file thực có không thấy secret/JWT theo mẫu; không thể scan7 log chưa publish. File tác giả không đổi trước/sau audit. Source0392e21 chỉ thêm2 script/fixture; docs commit chỉ docs/evidence, lib/test/supabase/migration không đổi.
- Không chạy lại Flutter/335 DB regression vì không đổi app/backend; số240 Flutter+1skip và2 reset của tác giả không được tính là reviewer chạy lại. Raw logs Flutter tác giả không nằm trong gói này; không xác minh count đó bằng log gốc.

Bằng chứng mới tại `review_0392e21_evidence/`: manifest audit, AST probe/source/output, CLI help/version, captured run redacted, cleanup state và metadata. Captured CLI stdout/stderr được redact JWT/key/connection-password và chuyển LF trước publish; raw capture giữ ngoài repo, không lộ credentials. Không thay missing log tác giả bằng log reviewer. Tài liệu Supabase online không truy cập được trong môi trường này; đối chiếu CLI --help tại đúng phiên bản, không tự đoán flag.

## NOT RUN

- Reviewer chưa hoàn tất18 migration,7 Auth users/seed,2 reset cycles, oracle48 bảng,DB assertions vàHTTP smoke trên full CLI stack do lỗi dung lượng lúc start. Cần môi trường đủ đĩa để đóng V5b sau khi sửa findings; không cần quyền production.
- Managed Supabase/PITR/offsite/encryption/retention; concurrent writers; staging/production/restore/deploy thật.
- Browser/device/offline/deep link và private heap trong lượt này; banking/webhook; tải/pilot và nghiệm thu toàn BH-07.
- Fault phá resource có sẵn, xóa lỗi hoặc permission lỗi thật: chỉ dependency injection/AST, không gây data loss trên máy.

**Chưa đạt V5b — giao AI triển khai sửa R1–R4 rồi review lại.** Không tự sửa source trong vai reviewer.
