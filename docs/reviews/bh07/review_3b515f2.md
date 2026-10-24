# Review V5b BH-07 — 3b515f2 — vòng2/2

## Kết luận

**Chưa đạt V5b vòng2/2.** Còn **R1/P1 và R2/P2**; đóng R3 và R5, giữ R4 đóng trong phạm vi manifest/count/provenance được công bố. Không có P0 mới. **Dừng sau hai vòng và báo chủ dự án**, không tự giao vòng3 hoặc sửa source.

- Base review: `b4b1f9f4e688978b5f141208962ccc7e784eebb7`.
- Tested code: `3b515f21674972c0db5f082fa5a08e4cdea2de24`.
- Docs/evidence origin: `5df6c62f40926d736b6164203660b8c73a424931` (parent3b515f2). Checkout detached sạch trước review.
- Reviewer Codex tự kiểm, không viết bản sửa của người triển khai; không sửa runner/tests/app/DB. Chỉ thêm report/evidence reviewer và cập nhật trạng thái.

## Phát hiện còn mở

| Mức | file:dòng | Tái hiện / kỳ vọng / thực tế | Cách sửa để chủ dự án xem xét giao tiếp |
|---|---|---|---|
| **P1 — R1 còn hở sau start** | `scripts/bh07_reset/run_full_reset.py:696`, `:697` | Initial preflight đã fail-closed. Tuy nhiên p_owned sau CLI start vẫn check=False và không kiểm returncode. Probe nguyên main: preflight sạch, start0, owned inventory exit1/daemon failure/stdout rỗng, runner vẫn gọi db reset và finally stop với owned_containers=[] thay vì dừng trước thao tác phá dữ liệu. Positive inventory thành công vẫn tiến tới reset đúng. Đây chính là nhánh owned inventory error đã yêu cầu trong review19ab207, không phải lỗi preflight ban đầu tái xuất. | Kiểm returncode/exception và tính hợp lệ inventory sau start trước status/reset; không tiếp tục reset khi chưa xác minh resource/run ownership. Xác minh đúng project và target DB/container, không coi stdout rỗng khi lỗi là inventory hợp lệ. Cleanup sau start lỗi phải dựa resource/run identity đã chứng minh, không mặc nhiên suy scope sở hữu. Test main flow cho owned-list failure/empty/foreign và assert không gọi reset lên target chưa xác minh. |
| **P2 — R2 gateway variant chưa whitelist code** | `scripts/bh07_reset/run_full_reset.py:291`, `:300`, `:302` | Positive HTTP đã là request thật; XX000/hint/INVALID_INPUT/NOT_FOUND/404 cũ đã bị chặn. Nhưng no_apikey dùng else cho mọi code khác42501 không nằm blacklist4code. Gọi helper hiện hành với status401, body `{'code':'42P01','message':'No API key found in request'}` vẫn được nhận thành auth rejection, dù42P01 là lỗi SQL undefined_table, không thuộc tuple gateway/PostgREST được cho phép. Positive gateway code vắng mặt và SQLSTATE42501 đều được probe giữ PASS. | Whitelist đầy đủ tuple: nhánh gateway chỉ cho code vắng mặt hoặc code gateway được tài liệu hóa, status/message cụ thể; mọi SQLSTATE/code không thuộc auth/gateway phải FAIL dù message giống auth. Không dùng blacklist một số code rồi coi mọi code còn lại là gateway. Thêm42P01/23505/code lạ +message auth và gateway hợp lệ làm negative/positive controls. |

Không kết luận đã có data loss/ACL bug trên app hoặc production. Đây là hai gate của runner kiểm chứng còn nhận trạng thái không hợp lệ. Probe ownership dừng tại ranh giới gọi reset bằng exception giả, không thực thi reset thật.

Lệnh tái hiện: `PYTHONUTF8=1 python docs/reviews/bh07/review_3b515f2_evidence/independent_probes.py`. Script trích main/helper/finally nguyên AST của source hiện hành, chỉ stub Docker/socket/HTTP và dùng thư mục tạm giả. Exit0 nghĩa là tái hiện và đối chiếu đúng các case, **không phải V5b PASS**.

## Phát hiện đã đóng / giới hạn giữ rõ

- **R3 đóng:** probe inspection nonzero → cleanup fail; final inspect exception khi đã có primary → vẫn primary; foreign ID không bị docker rm-f, owned ID được chọn đúng. Positive cleanup sạch vẫn đúng. Không coi unknown inspection là clean nữa.
- **R5 đóng:** tác giả8/8 test hiện thực thi hàm/AST, không chỉ literal/source string. Reviewer chạy nguyên suite trên temp mutant làm preflight return PASS sớm:8 test chạy,3 FAIL,0 ERROR; mutant bị suite bắt thật. Không sửa expectation hay file nguồn repo.
- **R4 giữ đóng về nội dung được giao:** manifest12/12,0missing/extra/mismatch; verify readonly giữ nguyên hash cả13 file gồm manifest; strict UTF8 không BOM/LF;0 secret theo regex yêu cầu/verifier. Oracle có48 bảng mỗi cycle, các count vàschema hash trùng;23 assertion detail PASS, cycle1/2 đều ghi23.
- **Giới hạn binding runtime source:** environment và summary công bố tested_sha=b4b1f9f, git_dirty=true, dirty_files có runner vàtests. Đây là thông tin trung thực đã giữ nguyên, nhưng **không chứng minh hai reset chạy từ checkout sạch3b515f2** và không có runtime source hashes để bind workingtree đó với commit cuối. Reviewer không viết lại SHA/dirty hoặc gọi log đó là lần chạy mới trên3b515f2. Việc R4 packaging được giữ đóng không xóa giới hạn này.

## Kiểm chứng reviewer tự chạy

| Kiểm tra | Kết quả |
|---|---|
| Fetch/checkout |Đúng5df6c62, source3b515f2; worktree sạch trước review |
| `PYTHONUTF8=1 python tests/test_v5b_runner_flaws.py` |Exit0,8/8 test |
| Independent AST main/helper/finally probes |Exit0; R1 owned-list error vẫn reset; R2 unknown SQLSTATE vẫn accepted; positive/old invalid controls vàR3 đúng |
| Whole-suite mutant |8 tests,3 FAIL/0 ERROR như kỳ vọng; source repo không đổi |
| Flutter analyze |Exit0,0 issue; Flutter3.47.7/Linux |
| Flutter test |Exit0,240 PASS+1 skip — lần chạy mới reviewer |
| Evidence audit +verify |Exit0,12/12;0missing/extra/mismatch/regexsecret;hash trước/sau không đổi |
| Docker ps-a filter bh07-reset-verify |Exit0,không có container trên máy reviewer; không chứng minh thay trạng thái máy Windows của tác giả |
| Full CLI2 reset |NOT RUN lượt này:32GB filesystem còn khoảng660MB; image pull của lượt reviewer trước đã fail do thiếu đĩa. Không retry làm đầy đĩa/không giả stack dựng tay thànhCLI reset |

Source commit chỉ sửa runner/Python tests; docs commit không sửa runtime/app/migration/contract. Không dùng số test/CLI Windows của tác giả làm số reviewer tự chạy. Các log/error codes được đọc đối chiếu và số liệu ghi rõ nguồn kế thừa. Bằng chứng/script mới ở `review_3b515f2_evidence/`; không ghi đè evidence tác giả.

## NOT RUN / không nghiệm thu

- Reviewer chưa chạy full CLI2 reset/18 migration/seed/HTTP Auth và23 DB assertions thực trên bản3b515f2; runtime dirty workingtree của tác giả có giới hạn binding nêu trên.
- V2/V2b device/browser khác/offline/deep link/private heap; V3 managed Supabase/PITR/offsite/encryption/retention; V4 concurrent writers; V5 staging/production/restore/deploy thật; V6 banking/webhook; V7 tải/pilot; V8 nghiệm thu toàn BH-07.
- Fault ownership/Docker/permission thật: chỉ dependency-injection/AST, không gây data loss trên resource thật. Không chạy335 DB vì app/backend không đổi. V1 Đạt local giữ nguyên.

## Dừng theo quy trình

[AGENTS.md](../../../AGENTS.md) quy định: **“tối đa 2 vòng. Còn lỗi sau 2 vòng thì dừng và báo chủ dự án.”** Reviewer ghi đủ hai phát hiện, cách sửa và giới hạn để chủ dự án quyết định bước tiếp; không tự mở vòng3, không tự sửa source hoặc cấp waiver cho lỗi kỹ thuật đang FAIL.

**Chưa đạt V5b vòng2/2 — dừng và báo chủ dự án.** Không merge main/staging/production/deploy/pilot/BH-08.
