# V5b — Codex sửa trực tiếp R1/R2 theo ủy quyền bổ sung

Ngày24/10/2026 (Asia/Saigon). Chủ dự án giao trực tiếp **“giao reviewer sửa”** sau khi dừng hai vòng. Lượt này là **Codex tự sửa/tự kiểm, KHÔNG phải review độc lập**, không phải tự mở vòng3 của AI triển khai cũ.

- Base: `6a13901f06b8ba88975538c8b6104590c9ec31b7` ([review trước](review_3b515f2.md)).
- Tested source: **`8e26e066e18a2b73cdedd45e5fd223a201d01a04`**, worktree sạch khi chạy checks cuối; docs/evidence commit sau không đổi source.
- Chỉ sửa `scripts/bh07_reset/run_full_reset.py` và `tests/test_v5b_runner_flaws.py`; không đổi app/unit Flutter/migration/RPC/fixture/contract.
- **R1/R2 đã sửa và tự kiểm PASS trong phạm vi hai gate. V5b Chờ kiểm chứng/chốt sau bản sửa trực tiếp**; không tự ghi Đạt toàn V5b/BH-07, không cấp phép merge/deploy/pilot.

## Sửa nguyên nhân

**R1 — inventory sau start:** kiểm returncode trước khi dùng stdout; lỗi dù có output trông hợp lệ cũng raise, inventory trống cũng raise. Không tới status/reset khi chưa có inventory hợp lệ. Mỗi process tạo project ID `bh07-reset-verify-<UUID16hex>` riêng và temp path theo ID này. Vì CLI start/stop dùng config với ID riêng, khi inventory lỗi cleanup chỉ có thể stop scope của lượt đó, không dùng chung project ID cố định của run khác. Port preflight, kiểm container ban đầu, cleanup chọn owned IDs, fail-closed và giữ primary error cũ được giữ nguyên.

**R2 — gateway tuple:** chỉ nhận (401, **không có field code**, message đúng `No API key found in request`, so casefold). PostgREST SQLSTATE42501 vẫn giữ hai status401/403 và message quyền đã có. Mọi code lạ/kể cảNone/rỗng nhưng field tồn tại, status403 kiểu gateway, message thêm prefix/suffix đều bị từ chối. Không thêm auth variant bằng keyword/hint.

Không tạo helper/framework hoặc đổi business assertion. Unique project scope tránh phải xóa resource không xác định khi xử lý lỗi sau start; không dùng dữ liệu thật để thử fault.

## Red → green và bằng chứng tự chạy

| Kiểm tra | Exit | Kết quả |
|---|---|---|
| New tests trên source trước sửa |1|11 tests,13 failures; lỗi được tái hiện trước thay đổi runner |
| Tests cuối trên source8e26e06 sạch |0|11/11 PASS, có positive owned inventory vàgateway/PostgREST variants |
| Old review_3b515f2 probe nguyên file |1 có chủ ý|Assertion lịch sử còn đòi unknown SQLSTATE được nhận PASS; sau sửa nó bị chặn. Không sửa file/input/kỳ vọng trong evidence reviewer cũ |
| Control hậu sửa cùng AST/scenario cũ |0|14 scenario đúng post-fix oracle; case auth sai vàowned-list lỗi không còn false success; positive/R3 controls giữ nguyên |
| Whole-suite preflight mutant |Kỳ vọng đỏ|11 tests,3 FAIL/0 ERROR; mutant bị bắt |
| Owned-inventory guard mutant |Kỳ vọng đỏ|11 tests,1 FAIL/0 ERROR; mutant bị bắt |
| Gateway tuple guard mutant |Kỳ vọng đỏ|11 tests,9 FAIL/0 ERROR; mutant bị bắt |
| Flutter analyze |0|0 issue, Flutter3.47.7/Linux |
| Flutter test |0|240 PASS+1 skip; lần chạy mới |
| Evidence cũ verify readonly |0|12/12,10/10,8/8,8/8; mọi hash trước/sau không đổi |

Test mới chạy nguyên AST main tới ranh giới reset bằng transport giả; positive cho phép đi tới boundary, inventory fail/empty cấm đi tới boundary. Test tuple gọi helper nguồn thật; không copy predicate. Test ID đánh giá biểu thức PROJECT_ID hai lần và kiểm hai identity khác nhau. Control hậu sửa chỉ đổi oracle tái hiện lỗi của script cũ sang oracle sửa lỗi (các declared expected input giữ nguyên), không chấp nhận input xấu. Toàn bộ mutants dùng temp file, không sửa source repo; test suite thực thi bình thường phải đỏ khi guard tương ứng bị bỏ qua.

Red được chạy khi tests mới còn workingtree, script nguồn vẫn là baseline6a13901; không giả đây là checkout sạch. Checks cuối sau source commit ghi rõ8e26e06 và clean; không retag log cũ thành source mới. Raw red harness ban đầu giữ ở scratch; log red công bố là lần cùng kỳ vọng đã phân loại unexpected reset thành assertion FAIL (13FAIL/0ERROR), trước mọi sửa runner.

Bằng chứng mới: [codex_v5b_fix_evidence/](codex_v5b_fix_evidence/). Evidence tác giả vàreviewer trước không ghi đè. Manifest bundle mới được lập từ các file tự kiểm, sau đó verify readonly. Source hashes/diff app boundary/provenance ở summary. Raw log có thể có whitespace từ tool; không sửa nội dung log để làm sạch diff. `git diff --check` của hai file code từbase đếnsource commit sạch.

## NOT RUN / giới hạn

- **Full Supabase CLI2 reset trên source8e26e06 NOT RUN**: host32GB còn khoảng659MB, lượt trước CLI pull đã fail thiếu đĩa. Không đổi stack dựng tay thành full CLI, không xóa cache/resource có sẵn để ép chạy.
- Không có23 DB assertions/HTTP smoke/migration/oracle48/48 mới từ runtime source8e26e06; dữ liệu cũ cómetadata b4b1f9f+dirty source/tests vẫn giữ nguyên, không được gán thành runtime bản mới.
- Kiểm chứng độc lập bản Codex sửa: **Chờ reviewer/QA khác**, chưa được thay bằng tự kiểm này. Sau khi có bằng chứng độc lập, điều phối chốt trong phạm vi rõ ràng.
- V2/V2b device/browser khác/offline/deep link/private heap; V3 managed Supabase/PITR/offsite/encryption/retention; V4 concurrent writers; V5 staging/production/restore/deploy; V6 banking/webhook; V7 tải/pilot vàV8 nghiệm thu toàn BH-07 đều giữ NOT RUN. V1 Đạt local giữ nguyên.

## Bàn giao kiểm chứng

Dùng source8e26e06 và doc/evidence commit chứa file này. Chạy11 tests, control hậu sửa, verify manifest mới readonly vàkiểm scope. Reviewer đủ đĩa chạy full CLI2 reset trên **worktree riêng**, để output mặc định chỉ ghi vào bản copy của full_reset_evidence; export kết quả sang bundle reviewer riêng, không commit đè evidence cũ. Ghi đúng source SHA/dirty/hash/CLI version và2 reset/18 migration/23 assertions/48table oracle/HTTP/cleanup. Chưa đủ tài nguyên thì ghi NOT RUN, không dùng runtime trước để kết luận source mới đã chạy.

**Hoàn tất phần sửa trực tiếp R1/R2 theo tự kiểm; V5b Chờ kiểm chứng sau bản Codex sửa, không độc lập.** Không merge main/staging/production/deploy/pilot/BH-08.
