# Review V5b BH-07 — cad3fa0

## Kết luận

**Chưa đạt V5b local** tại source `cad3fa0a7c57410af648ef214c02289021c1deea`, docs/evidence `55716e2f82425ee449adf4210420c998ae1fb651`, base review `e00db30d018da86f8fa94250a000f0bf825fc139`. Ngày 25/10/2026 (Asia/Saigon). Còn **1 P1 và 4 P2** bên dưới; không có P0 được xác định trong phạm vi kiểm tra.

Codex không viết/sửa bản `cad3fa0`; lượt này chỉ thêm báo cáo/evidence và trạng thái. **Codex từng sửa baseline `8e26e06`, vì vậy không tuyên bố độc lập với toàn bộ lịch sử V5b.** Các probe/kết quả mới tách riêng, không dùng log tác giả thay kết quả reviewer. Full CLI runtime của bản mới **NOT RUN** trong lượt này; runtime PASS của người triển khai chưa được tái lập tại đây.

## Bảng P2-1..P2-7

| Điểm gốc | Kết quả | Phạm vi/giới hạn |
|---|---|---|
| P2-1 | Đóng trong phạm vi code/audit | Oracle schema hash + row counts, mismatch test thực thi; bundle công bố 24 bảng data hash khác. Không suy thành dữ liệu giống tuyệt đối. |
| P2-2 | Đóng trong phạm vi code/audit | CLI/env resolve commit, phân biệt baseline/base review/tested source. |
| P2-3 | Đóng trong phạm vi code/audit | Có 23 assertion chi tiết và 16 HTTP audit records/chu kỳ, projection an toàn theo các caller hiện hành. Runtime mới NOT RUN. |
| P2-4 | Đóng trong phạm vi code/audit | Bỏ PORT_S3/preflight 56428; endpoint qua Kong, generated config có kiểm tra. |
| P2-5 | Còn mở phần test hồi quy | Exact predicates và scoped deterministic req_orig đã sửa; test mới vẫn chỉ tìm chuỗi, mutant sai target được nhận PASS (H5). |
| P2-6 | Đóng trong phạm vi code/audit | CLI pin 2.122.0; bundle ghi 12 image tag/ID/RepoDigests. Không khẳng định tái lập runtime xuyên môi trường. |
| P2-7 | Còn mở | Timeout giết process group cha, kill không hữu hạn và SQL helpers bỏ qua timeout (H1/H2). |

Giữ các kết luận R1/R2/R3/R5 cũ theo phạm vi đã kiểm; H1/H2 là regression của cơ chế process mới, không phải mở lại auth tuple hay ownership đã đóng. H3/H4 là lỗi bundle/claim mới, tách khỏi 7 điểm gốc.

## Phát hiện

### H1 — P1: Timeout trên POSIX giết cả runner/reviewer, bỏ qua finally cleanup

- File:dòng: `scripts/bh07_reset/run_full_reset.py:122`, `scripts/bh07_reset/run_full_reset.py:144`.
- Tái hiện: từ repo chạy `python docs/reviews/bh07/review_cad3fa0_evidence/run_isolated_tests.py` trên Linux. Script supervisor tạo session riêng để không làm chết terminal. Nó chạy nguyên lệnh yêu cầu `python -m unittest tests/test_v5b_runner_flaws.py`, không đổi test/kỳ vọng.
- Kỳ vọng: 17 test hoàn tất; timeout chỉ dừng cây tiến trình được tạo bởi lệnh, runner nhận TimeoutError và còn thực thi cleanup.
- Thực tế: subprocess không có `start_new_session`; child và runner chung PGID. `os.killpg(os.getpgid(pid), SIGTERM)` giết cả test runner sau output `......`, returncode **-15**. Lệnh trực tiếp lần đầu exit **143**. Probe kiểm PGID thực cũng xác nhận bằng nhau. Không có 17/17 PASS trên Linux; nếu timeout xảy ra trong full runner thì process bị kết thúc trước finally.
- Cách sửa: tạo session/process group riêng cho từng lệnh trên POSIX, chỉ signal group thuộc lệnh đó; giữ cơ chế Windows tương ứng. Test cần chứng minh parent/sibling sống, child/grandchild bị dừng, TimeoutError được nhận và cleanup thực thi.

### H2 — P2: Timeout vẫn có đường treo vô hạn

- File:dòng: `scripts/bh07_reset/run_full_reset.py:118`, `scripts/bh07_reset/run_full_reset.py:158`, `scripts/bh07_reset/run_full_reset.py:194`, `scripts/bh07_reset/run_full_reset.py:212`.
- Tái hiện: `python docs/reviews/bh07/review_cad3fa0_evidence/timeout_resistance.py`; tiếp theo `python docs/reviews/bh07/review_cad3fa0_evidence/probes.py` để kiểm call options của SQL helpers.
- Kỳ vọng: deadline hữu hạn ngay cả khi child bỏ qua SIGTERM hoặc kill lỗi; mọi lệnh Docker/psql của runner có timeout; giữ primary_error.
- Thực tế: child bỏ qua SIGTERM khiến `proc.communicate()` sau kill chờ không giới hạn; probe deadline 0.2s chưa kết thúc sau 2s, supervisor phải SIGKILL riêng group probe. `taskkill` cũng không timeout và lỗi bị nuốt. `sql_run`/`sql_as` gọi `subprocess.run` trực tiếp, không có timeout, thay vì đi qua wrapper mới.
- Cách sửa: bounded terminate → kill fallback → bounded reap, kiểm tra kill failure; cho taskkill deadline; đưa SQL helpers vào cùng cơ chế. Không nuốt lỗi kill hoặc thay thế primary_error. Thêm child-ignore-TERM, kill failure và SQL deadline controls.

### H3 — P2: Claim audit lịch sử 100% không đúng bundle đã push

- File:dòng: `docs/reviews/bh07/full_reset_p2_fix_evidence/manifest_readonly.json:18`, `docs/reviews/bh07/full_reset_handoff.md:10`.
- Tái hiện: `python docs/reviews/bh07/review_cad3fa0_evidence/audit_bundles.py` trên checkout Git mới.
- Kỳ vọng: claim 12/12 cho `review_8e26e06_evidence` phải có đủ file; audit đúng cả manifest runtime và manifest toàn bundle, công bố thiếu hụt.
- Thực tế: runtime manifest 12 entries chỉ có **5/12**, thiếu 7 log. Manifest toàn bundle `bundle_hashes.sha256` 32 entries chỉ có **18/32**, thiếu 14 file log. JSON mới vẫn `all_hashes_match=true`, `missing_or_mismatch=[]`, `extra_files=[]`. Bốn bundle khác 12/12,10/10,8/8,8/8 đúng. **Không có diff bundle lịch sử từ e00db30 đến 55716e2**: thiếu log là kế thừa, không quy lỗi bản mới đã xóa chúng; lỗi mới là khẳng định verify đủ từ bundle không đầy đủ trên Git.
- Cách sửa: khôi phục đúng byte log từ QA nguồn nếu còn, không chế tạo log/thay hash để xanh; hoặc công bố thiếu hụt và kết quả audit thực trong bundle đính chính mới, nêu điều kiện đóng. Không sửa manifest/bằng chứng lịch sử để che thiếu file.

### H4 — P2: Manifest và audit mới không đạt LF/read-only verifier

- File:dòng: `docs/reviews/bh07/full_reset_p2_fix_evidence/hashes.sha256:1`, `docs/reviews/bh07/full_reset_p2_fix_evidence/manifest_readonly.json:1`.
- Tái hiện: `python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/full_reset_p2_fix_evidence`.
- Kỳ vọng: strict UTF-8 không BOM, LF; verify exit0 và evidence không đổi.
- Thực tế: manifest có **17 CRLF**, JSON có **39 CRLF**. Hash dữ liệu vẫn đúng **17/17**, không có missing/extra/hash mismatch trong audit tên-file-relative phù hợp bundle. Strict verifier exit1 vì CRLF; các thông báo EXTRA tiếp theo là hệ quả parser từ chối manifest, không phải 17 lỗi missing độc lập. Audit hash trước/sau giữ nguyên.
- Cách sửa: chuẩn hóa hai file mới sang LF, cập nhật manifest bundle mới trong vai người triển khai; kiểm strict readonly và hash trước/sau. Không normalize bundle lịch sử để ghi đè chứng cứ.

### H5 — P2: Test exact fixture kiểm chuỗi nên không bắt sai count

- File:dòng: `tests/test_v5b_runner_flaws.py:443`.
- Tái hiện: `python docs/reviews/bh07/review_cad3fa0_evidence/probes.py`. Probe dùng AST trong bộ nhớ, giữ nguyên repo; thay duy nhất `pay_cnt == 2` thành `pay_cnt == 999`, rồi chạy nguyên test P2-5.
- Kỳ vọng: test tái hiện exact fixture phải thất bại khi target sai; duplicate payments/ledger, sai aggregate và chọn nhầm request đều phải bị bắt; có positive fixture.
- Thực tế: test vẫn PASS vì chỉ cấm một số chuỗi `>=` cũ; không chạy DB assertion hay kiểm exact target. Không nói code hiện tại đang dùng 999: đây là mutant chứng minh regression test chưa bảo vệ thay đổi được giao.
- Cách sửa: thực thi hàm/assertion hiện hành với fixture/stub SQL được scope theo câu query hoặc DB local; kiểm positive và count/aggregate/request sai. Mutant sai target hoặc bỏ predicate phải làm test fail, không chỉ bổ sung thêm string matching.

## Reviewer tự chạy

Evidence riêng: [review_cad3fa0_evidence](review_cad3fa0_evidence/).

| Lệnh/kiểm tra | Kết quả mới |
|---|---|
| Checkout | Detached docs 55716e2 sạch trước kiểm; scripts/tests/lib/test/supabase tree bằng tested source cad3fa0. Không sửa triển khai. |
| Python suite nguyên lệnh | Exit143 trực tiếp; chạy trong session riêng returncode -15. Chưa hoàn tất 17 tests. |
| 16 tests còn lại, bỏ riêng timeout nguy hiểm | 16/16 PASS; không gọi đây là toàn suite PASS. |
| PGID/SQL/mutant probes | Cùng PGID; SQL thiếu timeout; mutant exact target được chấp nhận, theo probes.json. |
| Child-ignore-TERM | Không kết thúc trong deadline supervisor; chỉ cây probe được force-kill. |
| Analyze | `flutter analyze --no-pub`: exit0, 0 issue. Lệnh không --no-pub ban đầu dừng khi dependency resolution trong sandbox, không gán thành PASS. |
| Flutter | `flutter test --no-pub` với quyền bind loopback local: exit0, **240 PASS +1 skip**. Lần sandbox trước exit1 vì không bind test socket; giữ log. |
| Bundle mới | 17/17 raw hash khớp, 0 missing/extra; có CRLF ở hai file, strict verify exit1. |
| Bundle cũ | 12/12,10/10,5/12 runtime (18/32 whole reviewer bundle),8/8,8/8; không sửa bundle cũ. |
| Readonly | Sáu bundle có fingerprint toàn thư mục trước/sau bằng nhau. |
| Secret scan | 0 mẫu JWT ba đoạn/sb_secret/password fixture/private-key trong các file hiện có của sáu bundle; không khẳng định quét được file thiếu. |
| Scope | e00db30..cad3fa0 chỉ runner + Python tests; lib/test/supabase diff rỗng. cad3fa0..55716e2 chỉ docs/evidence. |
| Whitespace | Code diff có trailing whitespace/blank EOF; ghi nhận, không nâng thành lỗi riêng. |
| Docker inventory | Kiểm chỉ đọc local không có container tên bh07-reset-verify; lượt này không tạo stack. |

Các log reviewer lưu UTF-8 LF; CRLF/progress carriage returns của output capture được chuẩn hóa khi đóng gói, không sửa log tác giả. Các probe AST/mutant chỉ là fault controls, không thay thế HTTP/Auth/DB thật.

## NOT RUN

- Full CLI2 reset source cad3fa0, 18 migrations/chu kỳ, 23 DB assertions và HTTP/Auth/negative controls trên stack thật **trong lượt reviewer này**: không chạy; host chỉ còn khoảng 657 MB, thêm H1/H2 khiến timeout chưa an toàn. Không pull image/khởi tạo stack, không xóa cache/resource khác để ép chạy. Bundle tác giả có kết quả hai chu kỳ, chỉ được audit, không gọi đó là lần chạy reviewer.
- Windows taskkill/npx.cmd và process-tree termination trên Windows thật; Docker daemon/permission/transport faults thật. Linux probes không chứng minh các nhánh này.
- V2/V2b: device/browser khác/offline/deep link/private Dart heap.
- V3: managed Supabase backup/PITR/offsite/encryption/retention; V4 concurrent writers.
- V5 staging/production restore/deploy thật; V6 banking/webhook; V7 tải/rehearsal/pilot; V8 nghiệm thu toàn BH-07.
- Không merge main/staging/production/deploy/pilot/BH-08. **V1 giữ Đạt local**, toàn BH-07 chưa nghiệm thu.

## Bước tiếp

Giao AI thực thi sửa H1–H5, giữ các gate đã đóng và bằng chứng lịch sử. Cần red/green behavior tests, deadline/process ownership controls và audit bundle từ checkout mới; sau source commit chạy full CLI từ worktree sạch trên máy đủ đĩa. Đây là yêu cầu sửa để review lại, không cho phép tự ghi Đạt hoặc bỏ giới hạn vòng sửa của AGENTS. Không tự sửa source trong lượt review này.

**Kết luận cuối: Chưa đạt V5b local tại cad3fa0.**
