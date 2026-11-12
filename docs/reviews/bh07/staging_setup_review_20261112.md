# Review độc lập tài liệu staging — 12/11/2026

**Không có P1/P2 cần mở trong delta tài liệu được review.** Phạm vi: [hồ sơ staging](staging_setup_20261112.md) và [ma trận BH-07](bh07_completion_status_20261110.md), theo source được ghi `c960c2d968f913a9075f65852ba7e0c36ed49180`. Reviewer chỉ đọc tài liệu và viết báo cáo này; không chạy code/DDL/DB/deploy hoặc tự kiểm lại remote project.

- Phạm vi owner duyệt được ghi đúng: staging test riêng, **0 USD/tháng**, `phongnt911's Org`, Singapore; không paid PITR/add-ons và không tác động project cũ.
- Project `mxqpukhfiugdwsjsbihj`, 18 migration và 21 bảng public RLS rỗng được mô tả là setup/quan sát của người triển khai, không phải bằng chứng V3/V5/V7 PASS. Lịch sử collision/retry migration và cảnh báo mapping version được giữ rõ.
- Health không notice không bị đồng nhất với security đã đạt. Hai definer views, hai mutable search paths và 19 anon/62 authenticated-callable SECURITY DEFINER functions vẫn chờ triage; grant inspection không bị gọi là chứng minh authorization đầy đủ. Tài liệu yêu cầu triage trước fixture provisioning.
- Ma trận giữ V3/V5/V7 NOT RUN, ghi staging mới có sẵn nhưng release/window/rollback/workload/SLO/pilot/support và bằng chứng vận hành còn thiếu. Listing một project INACTIVE trước đây được đánh dấu lịch sử trước setup mới.
- Không có risk acceptance được tự ký, không đổi các cổng chưa đo thành PASS, không tuyên bố nghiệm thu BH-07/V8 hoặc cấp quyền deploy/pilot/BH-08.

Đây là review tính nhất quán và phạm vi của tài liệu, không phải security clearance hay nghiệm thu staging runtime. Các finding advisor phải được đánh giá riêng trước bước cấp fixture; toàn BH-07/V8 vẫn chưa nghiệm thu. Session config `.codex/anti-v4-read-session.local.json` không thuộc báo cáo/source candidate và không được sửa hoặc commit trong lượt review này.

## Bổ sung review packet/triage/receipt

Đã đọc [bảng quyết định cập nhật](bh07_v8_risk_decision_packet_20261110.md), [security triage](staging_security_triage_20261112.md) và [setup receipts](staging_setup_receipts_20261112.json). Không có P1/P2 cần mở trong delta tài liệu bổ sung. Packet phân biệt rõ phê duyệt tạo môi trường với năm quyết định risk acceptance vẫn **CHƯA PHÊ DUYỆT**.

Receipt chứa 18 migration thành công, inventory21bảng/21RLS và các count Auth/profile/session/payment bằng0; không coi các count chọn lọc này là kiểm chứng mọi bảng hoặc isolation có dữ liệu. Bốn HTTP baseline khớp triage: summary200/0row, outstanding401/42501, helper zero-UUID200/false và bank401/42501. Chúng chứng minh phạm vi response/grant trên project rỗng, không chứng minh đã lộ dữ liệu người dùng thật hoặc authorization đầy đủ.

Triage giữ đúng tính chất đề xuất: chưa có security fix được triển khai/nghiệm thu; helper caller-binding concern dựa trên phân tích source được báo cáo, còn populated isolation/guest compatibility cần kiểm riêng. Anti CLI reconnaissance và lỗi kết nối không bị ghi là implementation PASS hay QA runtime độc lập. Reviewer không đọc private logs/config, không chạy lại HTTP/SQL hoặc sửa source. Security/V3/V5/V7/BH-07/V8 không được đóng bởi lượt bổ sung này.

Đã kiểm đoạn đầu AGENTS.md và ba link mới trong staging setup: đích tài liệu tồn tại, phạm vi0USD/test/Singapore và quyền đọc headless theo phiên được ghi nhất quán; không có P1/P2 trong delta docs này, còn security finding/candidate vẫn mở và chưa được review triển khai.
