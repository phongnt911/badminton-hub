# Codex tự sửa observer cleanup — 10/11/2026

Owner yêu cầu rõ “codex tự sửa” sau điểm dừng COPY-window vòng3/3. Đây là ngoại lệ cụ thể cho CW5/CW4, không giao Anti vòng4 hoặc bỏ giới hạn sửa chung. Base `47e3f65`, nhánh `feat/bh07-completion-local`. Codex triển khai/self-check; reviewer subagent riêng review delta và kiểm chứng độc lập.

## Thay đổi

- CW5: close kiểm trạng thái process sau graceful shutdown/kill/wait, join reader có timeout trước khi đóng stdout, không đóng buffered stdout đang bị reader giữ lock. Process/reader còn sống hoặc trạng thái/handle chưa xác minh gây RuntimeError `cleanup unverified`; không trả thành công. Lỗi workload gốc được giữ trong exception context.
- Khi đóng buffered stdin của child đã thoát, Windows có thể báo lỗi flush dù handle đã đóng. Chỉ chấp nhận trường hợp thuộc tính `closed is True`; lỗi chưa xác minh handle vẫn được báo. Không ghi raw command/credential vào lỗi cleanup mới.
- CW4: handoff loại claim1–2ms và bảo đảm cleanup mọi môi trường; latency Docker mới phải được đo.
- Không thay workload, padding, RPC/app/schema, timestamp predicate hoặc gate overlap. Không sửa evidence lịch sử; [review dừng trước sửa](v4_copy_window_review_final_20261110.md) giữ kết luận theo thời điểm đó.

## TDD và review

Thêm6 test lifecycle: kill-denial/live process, final-wait timeout, reader còn sống (không close stdout có thể block), stream-close failure, cleanup lỗi khi body đã lỗi, và verified cleanup gọi lại. RED6 test =5FAIL+1PASS (exit1) trước sửa. Sau sửa42 runtime-collection PASS bao gồm pipe thật EOF/timeout. Log local `.build/v4-codex-cleanup-{red,green}.log`.

Codex chạy thêm56 concurrency,6 supplemental,49 probe controls PASS. Reviewer độc lập đọc delta và tự chạy42 runtime-collection PASS; không nêu P0/P1/P2 còn mở trong delta, cho phép bước đo runtime trên source sạch. Đây không phải Docker QA mới của reviewer.

Full Python mới đã kết thúc: **541 test =537 PASS+4 SKIP**, exit0,140.614s; log `.build/v4-codex-cleanup-full-python.log`. Tổng targeted104PASS và49controls PASS. Replay control reviewer cũ không đổi source nay trả `close_outcome: RuntimeError` khi fake process không dừng; không tạo tiến trình thật. [Review delta](codex_observer_cleanup_review_20261110.md).

Flutter mới NOT RUN; app không đổi. Docker candidate mới NOT RUN; full V4/BH-07/V8 chưa nghiệm thu. Commit/push tiến độ được ủy quyền riêng, không merge/deploy/pilot/BH-08.
