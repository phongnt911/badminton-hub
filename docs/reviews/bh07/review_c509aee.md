# Review V2b retained paths — sửa RP3-C

- Ngày: 27/10/2026, Asia/Saigon. Reviewer: Codex; không sửa source triển khai/app/backend/DB.
- Base review: `ba90ac5c0a5b76d06d3d9d9cefce6249f24c8682` ([review trước](review_04d1ea9.md)).
- Tested source: `29f44a8e8f86ff68e3ebe54f981cbb73ea5ceb2b`.
- Docs/checkout: `c509aeeebf9e978992e93f7ac79f2aa677f0ffac`, worktree sạch trước kiểm chứng.
- Phạm vi: chốt lỗi publisher RP3-C theo bàn giao bổ sung; giữ các gate đã đóng, không coi đây là runtime app-profile độc lập mới.

## Kết luận

**Đạt bản sửa RP3-C trong phạm vi script/tooling đã kiểm chứng.** Không còn phát hiện P0/P1/P2 mở trong phạm vi này. RP3-C đóng; RP1/RP2/RP3-B/RP4/RP5/RP6 giữ kết luận trước đó, có hồi quy control. Không đóng toàn bộ V2b §4.4 hoặc nghiệm thu BH-07.

Runtime evidence vẫn là `retained_path_r1_evidence/`, source **`86181de1df03e11b3ad537f1024405724db83bfb`**. Không có lần runtime mới cho29f44a8; không đổi nhãn provenance của bundle cũ. Các kết quả runtime R1 là của người triển khai, chưa thay bằng lượt runtime độc lập của reviewer. Provider/tooling,V1,V5b giữ kết luận local trước đó. Không merge main/staging/production, deploy/pilot/BH-08.

## Phát hiện

| Mức | file:dòng | Kết luận trong phạm vi |
| --- | --- | --- |
| P0 | — | Không có phát hiện mở |
| P1 | — | Không có phát hiện mở |
| P2 | scripts/bh07_appheap/run_app_profile_heap.js:816, :823–830 | RP3-C đóng; không có yêu cầu sửa thêm |

RP3-C được phát lại bằng probe reviewer nguyên bản `review_04d1ea9_evidence/json_structure_probe.js`, không sửa kỳ vọng: positive ordinary và hai short-string true/false đều `summary_json_valid=true`, không có placeholder thay boolean. Test actual writer bổ sung kiểm tra kiểu boolean/number/null, parse artifact FAIL và giữ cleanup receipt/Markdown protocol. Làm sạch structured string fields trước serialize; log free-text được xử lý riêng; JSON không còn bị replacement mù trên văn bản đã serialize. Không suy diễn kết quả này thành app không leak.

## Bằng chứng reviewer tự chạy

Evidence riêng: [review_c509aee_evidence/](review_c509aee_evidence/); lệnh, khác biệt môi trường và retry do setup ở [commands.md](review_c509aee_evidence/commands.md). Numeric exits được lưu trực tiếp, không lấy log tác giả.

| Kiểm tra | Exit / kết quả |
| --- | --- |
| Python discover | 0; 312/312 |
| Flutter analyze (có pub) | 0; no issues |
| Flutter test (có pub) | 0; 247 passed, 1 skipped HTTP/Auth disabled |
| JSON structure probe nguyên bản | 0; 3/3 JSON hợp lệ |
| Redaction / publication probes nguyên bản | 0/0; full/prefix20/40/60 mask trọn, artifact FAIL không còn fragment |
| Graph / fixture probes nguyên bản | 0/0; node thứ9 reachable; collision POST0/DELETE0, row giữ nguyên |
| Fixture controls / oracle self-test | 0/0; 6/6 và34/34 |
| Node syntax | 0 |
| Auditor bundle R1 | 0 |
| Auditor hai bundle cũ | 1/1 có chủ ý; bị từ chối |
| Integrity ba bundle lịch sử | Mỗi bundle3/3 payload hash khớp manifest/Git; byte không đổi từ base |

Diff code chỉ publisher và test kiểm chứng; oracle/auditor/app/backend không đổi. Docs tip không đổi source so với29f44a8. Tất cả probe giả lập chỉ phục vụ control, không phải real Auth/HTTP/runtime app. Manifest reviewer21/21 PASS, strict UTF-8 LF,0 secret/JWT; đối chiếu hash trước/sau verify không đổi. Audit756 link Markdown tồn tại; git diff --check sạch. Không chạy generate trên bundle tác giả.

## NOT RUN

| Hạng mục | Trạng thái / điều kiện đóng |
| --- | --- |
| Runtime reviewer cho source29f44a8 và query DB fixture vắng | NOT RUN; không có API local54321, chỉ còn650932224 bytes lúc preflight; cần máy đủ đĩa, stack local cô lập, profile build mới và evidence riêng |
| Toàn coverage V2b §4.4 | NOT RUN; hiện chỉ gate hai expense ID, chưa chứng minh mọi finance model/cache/listener; charge/payment/bank thật/receiver chưa được chứng minh. Pattern bank cũ không chứng minh field bank thật |
| Rendered title retained / identity notes | Chưa kết luận nguyên nhân hoặc quyền; attribution unattributed, không mặc định engine-only/authorized, không coi là đã xử lý hết residual risk |
| Dart VM desktop/mobile, browser khác, thiết bị/offline/deep link | NOT RUN trong lượt này |
| DB/HTTP/Auth/concurrency mới | NOT RUN; giữ kết quả local trước, không nhập control stub làm bằng chứng HTTP thật |
| Managed backup/PITR/offsite/encryption/retention, concurrent writers | NOT RUN |
| Banking/webhook, staging/production/restore thật, tải/rehearsal/pilot, nghiệm thu toàn BH-07 | NOT RUN |

Bước tiếp: giao QA độc lập chạy runtime retained-path trên source mới, không chỉ phát lại bank-pattern cũ. Giữ riêng mọi bằng chứng lịch sử; nếu không đủ môi trường phải ghi NOT RUN, không tự sửa source để làm xanh.
