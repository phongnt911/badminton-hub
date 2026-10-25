# Review chốt V5b BH-07 — b036e9e

## Kết luận

**Đạt V5b local** tại tested source `8c107e9692b89f4a0aadeafc0ae139736f9b2622`, QA/docs `b036e9e65c3065e90454a6e645960599e633757b`, base review/commit cha `a55c2d2416f37a0bb8ac985e80bdee579b40774b`. Ngày 25/10/2026 (Asia/Saigon). **Đóng H6; giữ H1–H5 và các gate cũ đã đóng. Không có P0/P1/P2 còn mở được xác định trong phạm vi bàn giao này.** Toàn BH-07 chưa nghiệm thu.

Đây là kết luận dựa trên reviewer tự chạy tests/analysis/audit và đối chiếu chi tiết **runtime QA** từ bundle mới, không phải reviewer tự chạy thêm full CLI. Yêu cầu lượt này cho phép không chạy full runner nếu thiếu đĩa; máy reviewer chỉ còn khoảng653MB, nên lần full CLI reviewer mới giữ **NOT RUN**. Không thay QA log thành log reviewer, không suy thành nghiệm thu production.

Codex từng sửa baseline `8e26e06`, không tham gia viết source `8c107e9`; **không tuyên bố độc lập với toàn bộ lịch sử V5b**. Giới hạn độc lập và việc QA tự chạy runtime vẫn được giữ nguyên. Không sửa runner/tests/app/backend/fixture trong lượt chốt.

## Rà soát các cổng

| Cổng | Kết luận và bằng chứng |
|---|---|
| H6 | **Đóng**. Base hiện hành trong AGENTS, docs09, handoff/prompt và metadata đều đúng; git cat-file thành công, bằng cha của8c107e9. SHA typo trước đây chỉ còn dưới nhãn đính chính/lịch sử; trace lần exit1 vẫn giữ. |
| H1/H2 | **Giữ đóng**, suite21/21 thực thi timeout parent/sibling và ignore-SIGTERM; source không đổi so với review8c107e9. SQL timeout60, taskkill deadline5, bounded reap giữ nguyên. Windows fault injection mới NOT RUN. |
| H3/H4 | **Giữ đóng**. Audit lịch sử công bố đúng missing logs, không chế tạo. Bundle QA mới17/17 hash +strict UTF-8 LF +secret scan PASS; fingerprint trước/sau readonly bằng nhau. |
| H5 | **Giữ đóng**, test hành vi exact count/aggregate/target và source mutant trong suite21 PASS. |
| R1/R2/R3/R5 | **Giữ đóng**: ownership/inventory fail-closed, strict auth tuple, cleanup/primary_error và behavioral controls. Source tree bằng bản đã review; tests21 PASS. |
| P2-1 | **Giữ đóng**: oracle chỉ schema SHA256 +row counts; đối chiếu thực 48 bảng hai cycle, 24 data hash khác được công bố. Không claim dữ liệu byte-identical. |
| P2-2 | **Giữ đóng**: baseline/base review/tested source phân biệt; metadata dùng đúng base thực tế; git_dirty=false, dirty_files=[] là QA khai báo trong checkout nguồn. |
| P2-3/P2-5 | **Giữ đóng**: 23 assertion details/chu kỳ, exact charges150000/payments70000/payments2/ledger2/courts4/public; HTTP audit16 records/chu kỳ với projection an toàn và pass flags. Scoped deterministic request query giữ nguyên. |
| P2-4/P2-6/P2-7 | **Giữ đóng**: S3 qua Kong, pin CLI2.122.0; metadata12 image tag/ID/RepoDigests; timeout/group isolation không thay đổi. Oracle không dùng để claim schema hash xuyên môi trường. |

## Phát hiện P0/P1/P2

Không có phát hiện mới trong diff docs/evidence bàn giao. Các kết luận Chưa đạt trước đây là lịch sử đúng tại thời điểm đó, không sửa/xóa báo cáo hay bundle cũ. Thiếu log lịch sử review8e26e06 được công bố, không giả định các file thiếu đã được phục hồi.

## Reviewer tự chạy

Evidence riêng: [review_b036e9e_evidence/](review_b036e9e_evidence/).

| Kiểm tra | Kết quả mới |
|---|---|
| Checkout/provenance | Detached b036e9e sạch trước kiểm; runtime tree/scripts/tests/lib/test/supabase bằng tested source8c107e9; runner/tests SHA256 khớp Git blob. |
| Python unittest | **Exit0,21/21 PASS** |
| flutter analyze --no-pub | **Exit0,0 issue** |
| flutter test --no-pub | **Exit0,240 PASS+1 skip**, loopback harness local; HTTP integration mặc định skip, không gọi là realHTTP mới |
| Strict verify bundle QA | **Exit0,17/17**, 0 secret/JWT ngoài allowlist, UTF-8 LF; readonly fingerprint không đổi |
| Detailed QA audit | **Exit0**, kiểm độc lập nội dung và consistency theo bảng bên dưới; script không chạy reset hay sửa bundle |
| git cat-file / parent | Base resolve được và bằng8c107e9^ |
| Docker local | docker ps -a filter bh07-reset-verify exit0, không có container khớp; reviewer không tạo stack |
| Scope/history | f6451a7..b036e9e chỉ docs/bundle mới; tám bundle lịch sử được kiểm không có diff; không đổi source |

## Runtime QA được đối chiếu, không phải lần chạy runtime reviewer

Bundle [full_reset_8c107e9_evidence/](full_reset_8c107e9_evidence/) là lượt QA Windows mới, timestamp20261025T141311Z, project `bh07-reset-verify-b7c271296ef940fa`, CLI2.122.0, Docker29.8.2, PostgreSQL17.11.0.006. Audit thực hiện các kiểm tra sau thay vì chỉ đọc status PASS:

- Mỗi log reset có **đúng18 tên migration và đúng thứ tự trong Git**, khớp repository migrations; mỗi log Auth có7 user được tạo.
- Mỗi JSON DB có **đủ23 tên/detail/pass**, exact charges150000/payments70000, payments2/ledger2, courts4/public. Summary và hai file details cùng23/23.
- Mỗi HTTP JSON có16 records (7login +9RPC/history/finance), mọi pass=true; status200 và Member403/42501 phù hợp code; replay được kiểm trong runner. HTTP helper thực gọi loopback Auth/RPC, không mock trong full runner. Đây là audit log/code, không HTTP replay mới của reviewer.
- Hai snapshot có **cùng tập48 bảng**, tất cả row counts khớp, schema SHA256 khớp; tính lại từ JSON được24 bảng data hash khác, đúng disclosure.
- Negative controls đủ4: anon401/42501, no-apikey401/42501, outsider403/42501, loopback guard. Strict predicate đang được behavioral suite bảo vệ.
- Exits start/reset1/reset2/stop đều0; summary cleanup_success=true, stop.log cùng project ID với environment/commands. Theo code hiện hành, summary chỉ xuất sau final Docker all-container inventory bằng0 và cleanup không lỗi. Reviewer không có quyền truy cập Docker host QA để kiểm inventory Windows hiện tại; inventory local reviewer là phép kiểm riêng.
- Environment ghi đúng tested source/base, git_dirty=false/[] và12 image tag/ID/RepoDigests. Không giả định manifest tự nó chứng minh quá trình chạy hay chữ ký bên thứ ba; chốt dựa trên consistency, code, tests và hồ sơ QA đã bàn giao.

## NOT RUN và giới hạn giữ nguyên

- **Full CLI reset mới của reviewer** trên source8c107e9: không chạy do thiếu đĩa (~653MB). Không chạy lệnh ghi đè bundle QA. Việc rerun là tùy điều kiện đĩa theo yêu cầu lượt này; runtime local được chốt từ bundle QA mới đã audit chi tiết.
- Windows taskkill/process-tree fault injection, Docker daemon/permission/transport faults thật trong lượt reviewer này; không suy từ Linux tests thành các phép thử đó đã chạy.
- Nội dung file log thiếu trong bundle lịch sử review8e26e06 không thể quét/verify; H3 đã công bố phạm vi thay vì làm giả chứng cứ.
- V2/V2b: mobile/device/browser khác/offline/deep link/private Dart heap.
- V3: managed Supabase backup/PITR/offsite/encryption/retention; V4 concurrent writers.
- V5: staging/production restore/deploy thật; V6 banking/webhook; V7 tải/rehearsal/pilot; V8 nghiệm thu toàn BH-07.

**Đóng công việc V5b local trên nhánh, giữ Git ref chưa merge. V1 giữ Đạt local. Không merge main/staging/production/deploy/pilot/BH-08.** Bước local tiếp theo có thể giao V2b theo mục4.4 readiness; chưa chạy hay chuyển bất kỳ cổng nào trong lượt chốt này.

**Kết luận cuối: Đạt V5b local trong phạm vi và giới hạn nêu trên.**
