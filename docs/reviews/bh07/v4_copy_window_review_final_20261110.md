# Review cuối COPY-window vòng3/3 — 10/11/2026

**Chưa đạt, DỪNG sau vòng3/3.** Anti triển khai, Codex và reviewer subagent riêng review sau khi Anti CLI trả result thành công. Không timeout hoặc ngắt phiên đang xử lý; không tự sửa code thay Anti hoặc mở vòng4. Base `4093608`, candidate là commit chứa bản source/test và báo cáo này. Toàn V4/BH-07/V8 chưa nghiệm thu.

Hash source/test working-tree được kiểm: runner `fbf3aac01f88149a478ae8bb68cd6b5c51bfedd560fc5e48a65442db50c0f2d3`, runtime-collection test `0ea5513b5ca0edbfb9223ef7b4c300bbecd3b3361416bf135dcbdc1d016fda04` (SHA-256).

## Phát hiện còn mở

- **CW5 P2 — runner:520–548, đặc biệt532–539:** `PersistentDumpObserver.close()` nuốt lỗi kill và lần wait cuối, không xác minh poll đã thoát/reader đã dừng. Context có thể trả bình thường dù cleanup observer chưa được xác minh, nên đường dump thành công có thể tiếp tục. Control synthetic của Codex gán poll=None, hai wait đều TimeoutExpired, kill PermissionError: close trả không lỗi, still_alive true, wait2/kill1. Reviewer subagent tái hiện riêng bằng mock; đây là lỗi quản lý lifecycle, không khẳng định có tiến trình thật bị leak trong lượt kiểm này. Cần propagation/receipt fail-closed khi cleanup không xác minh được, kể cả đường không có lỗi chính; test termination-denial/hung-process phải tái hiện trước sửa.
- **CW4 P2 tái mở — handoff:28,36–38:** claim roundtrip xuống ~1–2ms và bảo đảm cleanup mọi trường hợp chưa có runtime cho revision này; cleanup còn lỗi CW5. Cần thu hẹp thành giả thuyết trước số đo và bỏ bảo đảm vượt bằng chứng. Không dùng pipe/mock test làm timing Docker.

Không có P0/P1 được phát hiện trong delta đã xem. CW1/CW2/CW3 và regex32/64 vẫn giữ đóng trong phạm vi review trước. Host bounds và predicate overlap nghiêm ngặt giữ nguyên, warmup/sequence/JSON/EOF/queue timeout đã có.

## Kiểm chứng và attribution

Codex chạy **36 runtime-collection +56 concurrency +6 supplemental =98 PASS**, probe **49/49 controls PASS**, exit0. Reviewer tự chạy **36/36 runtime-collection PASS**, exit0, và direct cleanup probe xác nhận CW5. Các test xanh không có control termination-failure nên không đóng CW5. [Control reviewer chạy lại được](v4_copy_window_r3_review_evidence/cleanup_control.py) không tạo process thật hoặc dùng Docker.

Log local `.build/v4-copy-window-*-after-r3.log`, Anti stream `.build/anti-v4-copy-window-r3-events.jsonl`. Full Python sau vòng1 là525 test/521PASS+4SKIP, không retag sang vòng3. Full Python/Flutter và Docker **mới** vòng3 NOT RUN. Không chạy Docker khi source lifecycle chưa Đạt.

Runtime mới nhất vẫn **4093608 FAIL**, theo [runtime review](v4_copy_window_runtime_4093608_20261110.md) và [summary](v4_runtime_20261110_evidence/copy_window_summary.json): initial COPY và hai HTTP200 có thật, không có selected overlap sample; restore/replay NOT RUN. Không retag runtime đó thành source observer mới. Container/network/private dump của lượt đó đã cleanup theo receipt và kiểm inventory riêng.

## Quyết định điều phối

Ngừng giao thêm correction: nhiệm vụ COPY-window đã hết3 vòng. Báo owner hai P2 và lưu tiến độ commit/push trên nhánh theo ủy quyền đồng bộ hiện có; commit không phải nghiệm thu. Cần owner giao ngoại lệ cụ thể nếu muốn mở thêm vòng sửa. Không merge/deploy/pilot/BH-08 hoặc ký risk acceptance thay owner.
