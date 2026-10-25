# Review V5b BH-07 — 8c107e9

## Kết luận

**Chưa đạt để chốt V5b local. Đóng H1–H5 trong phạm vi kiểm tra bên dưới; còn 1 P2 tài liệu H6 và full CLI runtime reviewer NOT RUN.** Không xác định thêm P0/P1 trong bản sửa được giao. Không yêu cầu sửa lại logic H1–H5 đã được kiểm chứng.

- Ngày: 25/10/2026 (Asia/Saigon).
- Tested source: `8c107e9692b89f4a0aadeafc0ae139736f9b2622`.
- Docs/evidence được kiểm: `8d48cdc6feb60b7b6479bb8792f1e8a759aa4cf8` (origin khi fetch).
- Base review thực tế/commit cha: **`a55c2d2416f37a0bb8ac985e80bdee579b40774b`**. SHA `a55c2d22b27bc89d53f58a74b0fa038ff31c0396` trong yêu cầu không tồn tại trên Git được fetch; không giả định hai SHA là một.
- Checkout detached docs tip sạch trước kiểm; scripts/tests/lib/test/supabase bằng tree tested source. Reviewer không sửa source, app/backend, fixture hoặc bundle tác giả trong lượt này.
- Codex từng sửa baseline `8e26e06`, **không độc lập với toàn bộ lịch sử V5b**; không tham gia viết bản sửa `8c107e9`. Báo cáo công bố giới hạn này, tách lần chạy mới khỏi log tác giả.

## Rà soát H1–H5

| Cổng | Kết luận trong phạm vi đã kiểm | Bằng chứng reviewer mới |
|---|---|---|
| H1 | Đóng POSIX/code path; Windows thật NOT RUN | 21/21 tests hoàn tất; parent/sibling sống; probe command PGID khác reviewer; child/grandchild bỏ qua SIGTERM đều ngừng chạy. |
| H2 | Đóng POSIX và wiring SQL; Windows thật NOT RUN | Timeout child/grandchild kết thúc khoảng 1 giây; reap có deadline; cả sql/sql_run/sql_as thực thi qua fake run_cmd với timeout60 (4 calls gồm lookup actor). taskkill code có timeout5. |
| H3 | Đóng phần đính chính claim | JSON công bố đúng 5/12 runtime và 18/32 whole bundle cũ, giữ nguyên missing logs; bốn bundle khác 12/12,10/10,8/8,8/8. Không diff năm bundle lịch sử từ base thực tế đến docs tip. |
| H4 | Đóng | Strict readonly verifier exit0, **17/17**, UTF-8 LF, 0 secret/JWT ngoài allowlist; hash toàn thư mục trước/sau bằng nhau. |
| H5 | Đóng | Test thực thi DB function positive 23 assertions, wrong/duplicate count, aggregate, tx và source mutant. Probe riêng thay pay_cnt == 2 thành == 999 làm positive fixture raise AssertionError. |

Trong probe process-tree, child leader đã được reap; grandchild ở trạng thái **Z** sau SIGKILL (đã ngừng chạy, chờ hệ điều hành reap). Không diễn giải kết quả này thành chứng minh mọi PID đã biến mất hoặc thành cleanup Docker thật.

## Gate cũ

| Nhóm | Kết luận/giới hạn |
|---|---|
| R1 ownership/inventory và R2 auth tuple | Giữ đóng theo code diff và các behavior tests trong suite 21/21; không có sửa app/RPC/ACL. |
| R3 primary_error/cleanup và R5 test hành vi | Giữ đóng theo tests thực thi; timeout mới không giết runner Linux. Không fault-inject Docker daemon thật. |
| P2-1 Oracle | Giữ scope schema_sha256_and_row_counts; mismatch schema/count tests PASS; snapshot tác giả công bố 24 bảng khác data hash. Không claim data hash bằng nhau. |
| P2-2 provenance | Resolver xác minh commit thật; probe từ chối SHA sai. Evidence runtime dùng đúng base thực tế và tested source; H6 thuộc tài liệu bàn giao. |
| P2-3 audit HTTP/DB | Có 23 DB assertion details và 16 sanitized HTTP records/chu kỳ; hash/secret audit PASS. Chỉ audit dữ liệu tác giả, không gọi là HTTP runtime reviewer. |
| P2-4 ports và P2-6 CLI/images | Giữ S3 qua Kong, CLI pin2.122.0 và metadata image thực trong bundle. Không thay config/migration/fixture. |
| P2-5/P2-7 | Giữ code exact predicates + deterministic req_orig; behavior regression/timeout controls nay PASS theo H1/H2/H5. |

## Phát hiện còn mở

### H6 — P2: Base SHA trong handoff/AGENTS không tồn tại, mâu thuẫn evidence

- File:dòng: `docs/reviews/bh07/full_reset_handoff.md:5`, `docs/reviews/bh07/full_reset_handoff.md:87`, `AGENTS.md:1` (tại docs tip được review).
- Tái hiện:
  ```bash
  git cat-file -e 'a55c2d22b27bc89d53f58a74b0fa038ff31c0396^{commit}'
  git rev-parse '8c107e9^'
  python -u scripts/bh07_reset/run_full_reset.py --base-review a55c2d22b27bc89d53f58a74b0fa038ff31c0396 --evidence-dir /tmp/v5b-invalid-base-check
  ```
- Kỳ vọng: base bàn giao resolve được, trùng commit cha/review cad3fa0 và metadata runtime.
- Thực tế: SHA trên không tồn tại, runner đúng đắn từ chối **exit1 trước preflight/reset**. Commit cha thực tế, recipe executable trong handoff, environment.json và summary.json cùng là **`a55c2d2416f37a0bb8ac985e80bdee579b40774b`**. Phần thông tin đầu và prompt bàn giao vẫn ghi SHA sai (cũng được lặp trong yêu cầu user).
- Ảnh hưởng: người nhận copy base từ phần thông tin/prompt thì không tái lập được; nguồn gốc runtime bị mô tả mâu thuẫn dù metadata thực tế đúng.
- Cách sửa: **docs-only**, đính chính SHA base trong thông tin hiện hành và prompt; giữ ghi chú tham số sai từng được truyền/reviewer đã từ chối, không sửa metadata runtime đúng hoặc lịch sử bằng chứng để che lỗi. Không cần thay logic runner, migration hay chạy lại source để sửa riêng H6.

## Reviewer tự chạy

Evidence riêng: [review_8c107e9_evidence/](review_8c107e9_evidence/).

| Kiểm tra | Exit/kết quả |
|---|---|
| python -m unittest tests/test_v5b_runner_flaws.py | **0 — 21/21 PASS** |
| flutter analyze --no-pub | **0 — 0 issue** |
| flutter test --no-pub | **0 — 240 PASS +1 skip**, quyền loopback local cho test harness |
| Independent process/SQL/base probes | **0**, group cô lập, bounded timeout, SQL60, base thật resolve, base sai bị chặn |
| Source mutant exact target | Sai pay_cnt999 bị test hành vi từ chối; repo không bị sửa |
| Strict verifier bundle tác giả | **0 — 17/17**, readonly trước/sau bằng nhau |
| Audit năm bundle lịch sử | Counts đúng theo H3; lịch sử giữ nguyên, không normalize/regenerate manifest cũ |
| Full runner với base sai đúng yêu cầu | **1 — ValueError invalid commit**, 0 chu kỳ/0 stack được khởi tạo; log riêng, không coi là full runtime PASS |
| Full runner với base đã đính chính | **NOT RUN**: chỉ còn khoảng 654 MB đĩa; không pull image/khởi tạo stack gây đầy đĩa. Không thay log tác giả cho lần chạy reviewer. |
| docker ps -a --filter name=bh07-reset-verify | **0**, không có container khớp trên daemon local reviewer; lượt này không tạo container |
| Scope | Base thực tế..source chỉ runner và Python tests; source..docs không đổi runtime tree; lib/test/supabase rỗng |

Audit bundle tác giả: source8c107e9, git_dirty=false, base thực tế đúng; 2 chu kỳ ×18 migrations, 23 assertions/chu kỳ, 16 HTTP records/chu kỳ, Oracle48 bảng/schema+counts match, negative/cleanup PASS. Đây là **kết quả tác giả được audit**, không phải lần chạy full CLI độc lập mới. Không có log analyze/Flutter tác giả được dùng thay các lần chạy reviewer ở bảng trên.

## NOT RUN

- Full Supabase CLI2 reset, 18 migrations/chu kỳ, 23 exact DB assertions, real HTTP/Auth/negative controls và cleanup Docker của **source mới trên stack reviewer**: chưa tái lập do giới hạn đĩa. Lệnh base sai thất bại ở resolve commit không chứng minh runtime đúng base.
- Windows taskkill/npx.cmd/process tree thật; Docker daemon/permission/transport fault injection thật. Linux controls không chứng minh nhánh Windows.
- Các file thiếu của bundle review8e26e06: không thể quét/verify nội dung không có trên Git; đã công bố H3, không tạo log thay thế.
- V2/V2b device/browser khác/offline/deep link/private Dart heap; V3 managed Supabase backup/PITR/offsite/encryption/retention; V4 concurrent writers.
- V5 staging/production restore/deploy thật; V6 banking/webhook; V7 tải/rehearsal/pilot; V8 nghiệm thu toàn BH-07.

## Bước tiếp

Không giao viết lại H1–H5. Chỉ cần AI thực thi đính chính H6 docs-only, sau đó QA trên máy đủ đĩa chạy đúng base thực tế, source8c107e9 từ worktree sạch, xuất bundle reviewer riêng và xin chốt theo bằng chứng mới. Không tự mở vòng sửa source vượt giới hạn AGENTS. Không merge main/staging/production/deploy/pilot/BH-08; **V1 giữ Đạt local**, toàn BH-07 chưa nghiệm thu.

**Kết luận cuối: Chưa đạt điều kiện chốt V5b local; H1–H5 đã đóng trong phạm vi đã kiểm.**
