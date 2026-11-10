# Review delta Codex CW5/CW4 — 10/11/2026

**Đạt trong phạm vi delta source/test CW5/CW4; chưa nghiệm thu runtime/toàn V4/BH-07/V8.** Owner yêu cầu “codex tự sửa”; Codex triển khai, reviewer subagent riêng không triển khai và chỉ đọc delta trước kiểm chứng độc lập. Không nhận self-check của Codex là review độc lập.

Base `47e3f65`, candidate là commit chứa source/test và báo cáo này. SHA-256 working-tree sau kiểm chứng: runner `dd7da07bc29c672258d5d57021de6b653bb12638eb3d204a8dba2fa001cede23`; test runtime-collection `d6d18ab23de7209861eb9b07b97bd63823238dca376f7aa8c36615b0de84f872`.

Reviewer độc lập xác nhận cleanup không còn trả thành công khi termination, reader hoặc stream chưa được xác minh; join reader trước close stdout tránh lock của readline. Lỗi cleanup khi body đã lỗi giữ exception context gốc. Claim latency chưa đo đã bỏ. Reviewer không nêu P0/P1/P2 còn mở trong delta, tự chạy42 runtime-collection PASS, có pipe EOF/timeout thật. Gate/time bounds/workload không đổi.

Codex self-check: RED6test/5FAIL+1PASS trước sửa; GREEN42 runtime-collection,56concurrency,6supplemental (=104PASS),49probe controls PASS. Full Python **541test/537PASS+4SKIP**, exit0,140.614s. Test fake cleanup không tạo child thật, không được dùng để khẳng định Docker cleanup đã chạy. Reviewer cũng chưa chạy Docker. Flutter mới NOT RUN, app/schema không đổi.

Giới hạn: kiểm local observer process/reader không chứng minh mọi backend/service bên ngoài đã dừng; rehearsal vẫn có bước xóa và verify toàn stack riêng. Actual COPY/HTTP overlap và latency persistent observer chưa đo trên source này. Bước kế tiếp được phép là chốt candidate sạch, rehearsal local output mới và kiểm cleanup; không merge/deploy/pilot/BH-08, không thay owner risk acceptance.
