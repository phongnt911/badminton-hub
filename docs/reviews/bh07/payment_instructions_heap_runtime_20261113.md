# PaymentInstructions synthetic map heap — runtime 13/11/2026

**Hiện tại: PASS local cho hai synthetic receiverSnapshot map values, với attribution path binding theo artifact. Không phải whole-model/whole-field PASS; toàn V2b/BH-07/V8 chưa nghiệm thu.**

Codex chạy real Edge headless trên Flutter Web profile, Supabase bốn container local. Source app/backend/migration không đổi từ app commit aa755b5. Build/served39artifact khớp; main.dart.js SHA256 `a20b3d22a011fb511a76ee4daa11167410a6a61a2aba3f796f8ae0e1e65fe83e`.

## Lượt mới với source binding — R2

Tested source `4433b153e86a3ede7ac3362c1da2b5125c6777cd`, git_dirty=false. [Bundle mới](instructions_heap_bound_20261113_evidence/manifest.json) giữ riêng5file original trong `run/`, receipt root ngoài `run/`; parent manifest6hashes. Child RUN/PASS_DTO_ATTRIBUTED; strict auditor `--build-dir build/web --require-dto-attribution` exit0. Thiếu build artifact để tái tính binding phải reject, không chỉ tin constructor snippets trong companion.

Hai chu kỳ Owner→logout→Cohost/Member × bốn epochs, cùng document. Cả bốn Owner paths exact/untruncated đi qua `_provider$_value`→`_instructions`→`receiverSnapshot`→map cell→string; các baseline/logout/actor vắng/unreachable. Field names gắn với FinanceProvider/PaymentInstructions constructors và executable field uses trong đúng artifact main.dart.js; binding SHA256 `7c1b10030ed6509f5fc5cb52b902fb6afea2242b8b9dc0c9a02cab5ba99d4d84`. Comment/literal không là code proof; source repair sau Anti vòng3 đã qua RED→GREEN và21Python/8Node groups PASS ở Codex. Reviewer độc lập kiểm lexical regression và controls.

Fixture private club/session mới dùng một lần; zero payments/club_transactions/audit_events/operation_requests. Helper baseline21public/94rows/schema/roles/other sequences khớp, Auth79→83. Root kiểm riêng public/schema/roles/other sequences vẫn khớp từ preflight75→83 qua cả hai lượt; không nhầm overall receipt với sequence riêng R2. Fixture/dump/profile/state dọn và xác minh vắng.

Reviewer riêng xác minh6/6parent hashes, original bundle hashes,39/39local artifact hashes; strict auditor0, thiếu --build-dir exit1, R1 nguyên5/5. Không có P0/P1/P2 trong package được review. Đây là source/control/artifact review, không independent browser/DB runtime. Kết luận chỉ cho hai giá trị JSON tổng hợp đã đo; không suy ra các field thật hoặc toàn DTO sạch.

## Lượt gốc R1

Source `39302fe81e9c7494d54338eaa4f27de1bc4c8705`, git_dirty=false; verdict gốc giữ nguyên payload hẹp/instructions UNKNOWN.

[Bundle giữ nguyên verdict/bytes](instructions_heap_r1_20261113_evidence/manifest.json). Hai chu kỳ Owner→logout→Cohost/Member, mỗi chu kỳ baseline/owner_active/post_logout/post_actor, cùng timeOrigin1794581989440.7. Owner mở finance của session dùng một lần thuộc private club riêng, bấm Thu tiền mặt rồi Huỷ; không ghi thanh toán. Hai UUID canary tổng hợp chỉ nằm trong receiver_snapshot extra map fields; không đưa vào page evaluate/input hoặc UI render. Probe control riêng có chủ đích nằm trên window, không phải finance canary.

Ở cả hai owner_active, hai canary có mặt/reachable từ GC root, mỗi giá trị1string node. Path21/20 cạnh lần lượt đi qua inherited Provider holder, `_provider$_value`, `_instructions`, `receiverSnapshot`, map cell tới string. Ở hai baseline, hai post_logout và hai post_actor, cả hai canary vắng/unreachable. Raw snapshots60–86MB được stream ngoài repo, parse rồi xóa.

Matcher source39302fe yêu cầu tên field `_finance_provider$_instructions`; path thực tế dùng `_instructions`. Vì vậy child/auditor0 chỉ xác nhận scope payload hẹp; strict `--require-dto-attribution` exit1 đúng kỳ vọng. Không retag artifact gốc thành DTO PASS. Constructor trong artifact profile có `FinanceProvider` dùng `_instructions`, `PaymentInstructions` dùng `receiverSnapshot`; cần binding chính xác với served artifact trước khi tự động kết luận attribution. Đây là sai khác matcher, chưa kết luận minification là nguyên nhân.

## DB và cleanup

Helper và root kiểm tra riêng baseline21bảng public/94dòng/schema/roles/other sequences khớp; Auth refresh sequence75→79, Auth rows loại riêng theo hợp đồng. payments/club_transactions/audit_events/operation_requests của fixture đều0. Private club/session và các child rows được dọn, xác minh vắng; heap dump dir/browser profile/state không còn. Không reset/reseed DB hoặc thay remote.

## Giới hạn

Chỉ hai giá trị JSON tổng hợp không render trong Web V8 profile; không chứng minh toàn bộ PaymentInstructions model, rendered bank/receiver/reference, listener graph, Dart VM/native/Firefox/Safari sạch. Người chạy runtime là Codex; reviewer kiểm source/control/artifact, chưa có independent browser/DB runtime. Full V2b/BH-07/V8 chưa nghiệm thu, không merge/deploy/pilot/BH-08.

Reviewer riêng xác minh parent manifest5/5, original bốn-file bundle trong `run/` qua auditor source39302fe với zero problems; đối chiếu tám timeOrigins, path và cleanup/DB receipt. Không có P0/P1/P2 trong layout artifact R1 đã sửa. Receipt root bổ sung và parent manifest nằm ngoài directory original auditor để không thay byte/contract bundle gốc.
