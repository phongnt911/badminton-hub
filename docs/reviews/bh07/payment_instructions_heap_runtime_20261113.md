# PaymentInstructions synthetic map heap — runtime 13/11/2026

**Phạm vi hiện tại: PASS_NARROW_RPC_PAYLOAD_ONLY; PaymentInstructions attribution gate UNKNOWN/NOT_RUN. Toàn V2b/BH-07/V8 chưa nghiệm thu.**

Source `39302fe81e9c7494d54338eaa4f27de1bc4c8705`, git_dirty=false. Codex chạy real Edge headless trên Flutter Web profile, Supabase bốn container local. Source app/backend/migration không đổi từ app commit aa755b5. Build/served39artifact khớp; main.dart.js SHA256 `a20b3d22a011fb511a76ee4daa11167410a6a61a2aba3f796f8ae0e1e65fe83e`.

## Lượt gốc R1

[Bundle giữ nguyên verdict/bytes](instructions_heap_r1_20261113_evidence/manifest.json). Hai chu kỳ Owner→logout→Cohost/Member, mỗi chu kỳ baseline/owner_active/post_logout/post_actor, cùng timeOrigin1794581989440.7. Owner mở finance của session dùng một lần thuộc private club riêng, bấm Thu tiền mặt rồi Huỷ; không ghi thanh toán. Hai UUID canary tổng hợp chỉ nằm trong receiver_snapshot extra map fields; không đưa vào page evaluate/input hoặc UI render. Probe control riêng có chủ đích nằm trên window, không phải finance canary.

Ở cả hai owner_active, hai canary có mặt/reachable từ GC root, mỗi giá trị1string node. Path21/20 cạnh lần lượt đi qua inherited Provider holder, `_provider$_value`, `_instructions`, `receiverSnapshot`, map cell tới string. Ở hai baseline, hai post_logout và hai post_actor, cả hai canary vắng/unreachable. Raw snapshots60–86MB được stream ngoài repo, parse rồi xóa.

Matcher source39302fe yêu cầu tên field `_finance_provider$_instructions`; path thực tế dùng `_instructions`. Vì vậy child/auditor0 chỉ xác nhận scope payload hẹp; strict `--require-dto-attribution` exit1 đúng kỳ vọng. Không retag artifact gốc thành DTO PASS. Constructor trong artifact profile có `FinanceProvider` dùng `_instructions`, `PaymentInstructions` dùng `receiverSnapshot`; cần binding chính xác với served artifact trước khi tự động kết luận attribution. Đây là sai khác matcher, chưa kết luận minification là nguyên nhân.

## DB và cleanup

Helper và root kiểm tra riêng baseline21bảng public/94dòng/schema/roles/other sequences khớp; Auth refresh sequence75→79, Auth rows loại riêng theo hợp đồng. payments/club_transactions/audit_events/operation_requests của fixture đều0. Private club/session và các child rows được dọn, xác minh vắng; heap dump dir/browser profile/state không còn. Không reset/reseed DB hoặc thay remote.

## Giới hạn

Chỉ hai giá trị JSON tổng hợp không render trong Web V8 profile; không chứng minh toàn bộ PaymentInstructions model, rendered bank/receiver/reference, listener graph, Dart VM/native/Firefox/Safari sạch. Người chạy runtime là Codex; reviewer kiểm source/control/artifact, chưa có independent browser/DB runtime. Full V2b/BH-07/V8 chưa nghiệm thu, không merge/deploy/pilot/BH-08.

Reviewer riêng xác minh parent manifest5/5, original bốn-file bundle trong `run/` qua auditor source39302fe với zero problems; đối chiếu tám timeOrigins, path và cleanup/DB receipt. Không có P0/P1/P2 trong layout artifact R1 đã sửa. Receipt root bổ sung và parent manifest nằm ngoài directory original auditor để không thay byte/contract bundle gốc.
