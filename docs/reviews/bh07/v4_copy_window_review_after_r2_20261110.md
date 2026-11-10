# Review chốt source/test COPY-window — 10/11/2026

**Đạt trong phạm vi delta source/test CW1–CW4, chưa có runtime PASS.** Anti CLI triển khai, Codex review/chạy kiểm chứng; reviewer subagent riêng đọc delta và phát hiện thêm lỗ độ dài digest rồi xác nhận đóng sau sửa vòng2/3. Không còn P0/P1/P2 trong phạm vi đã review. Không tự mở vòng3.

Base `5db7e93`, candidate là commit chứa source và báo cáo này. Hash working-tree trước commit: runner SHA-256 `f50072607db2ce8e1d74ca4640059b2bd6985eaf83864ee04aceea3fc549748e`, test runtime-collection `29a63efe8a62f41dd985882f9a2588c42e12bf90e3869754b868165be6152aae`.

## Thay đổi và kiểm chứng

Padding40.000 dòng trong schema riêng của DB Docker dùng một lần, bounded ~37.8MiB payload, pg_dump không nén; không sửa app/RPC/migration/public/auth schema. Source/target stats thật gồm rows/bytes/ordered digest ID+payload; parse hỏng và mismatch bị từ chối, không còn fallback dựng dữ liệu. Receipt target được giữ ở summary cuối. Diagnostics phân biệt initial COPY sample với selected overlap sample; gate vẫn yêu cầu mẫu thật nằm trong giao writer/dump, không chấp nhận initial sample thay thế. Thời gian COPY mới là giả thuyết cần đo.

Codex chạy candidate sau vòng2: **27 runtime-collection +56 concurrency +6 supplemental =89 PASS**, **49/49 probe controls PASS**, exit0; log `.build/v4-copy-window-*-after-r2.log`. Reviewer subagent direct probe parser và auditor full source/target matching: độ dài32/64 accepted,33/40/63 rejected. Không nhận self-check của Anti thành kiểm chứng đã chạy; Anti không có shell và báo RED/GREEN NOT RUN.

Full Python của source sau vòng1 (trước regex2-site fix và test bổ sung cuối): **525 test =521 PASS+4 SKIP**, exit0,156.436s, `.build/v4-copy-window-full-python.log`. Hash source/test bản đó `7c8bdc41e8844583f80ead8c174a4f20a60bec657599953477c6ac4baebd28ab` / `b0bbb80f6116830729039907e45d1451fddc0781b651ca2ffb2d840aac7d48b5`. Không retag kết quả này thành full suite candidate sau vòng2. Không chạy lại full suite khi thay đổi hẹp đã được controls/targeted xác minh. Flutter mới NOT RUN; app không đổi.

## Phạm vi và bước kế

Host disk preflight không xác lập dung lượng trong Docker VM; giới hạn payload không phải giới hạn toàn bộ disk footprint. Replay data fingerprint vẫn public/auth + schema; padding được đối chiếu source/target lúc restore, không gọi là đo toàn bộ schema data ngoài phạm vi đó. Existing subprocess timeout behavior không thuộc delta. Chỉ runtime mới quyết định load có đủ cửa sổ COPY/HTTP overlap hay không. Reviewer Docker NOT RUN.

Tuân thủ yêu cầu owner: cả lượt implementation và correction dùng `--print-timeout 0`, chỉ theo dõi PID/log/tool state, không ngắt/review source khi Anti đang sửa. Conversation `34c06b11-57b4-4d1d-97d5-6133f87255c0`; log `.build/anti-v4-copy-window{-r1,-r2}-events.jsonl`. Hai review trước giữ kết luận lịch sử: [R1](v4_copy_window_review_r1_20261110.md), [sau vòng1](v4_copy_window_review_after_r1_20261110.md).

Chốt candidate sạch rồi chạy Docker local với output mới; giữ bằng chứng lịch sử, xác minh cleanup. Toàn V4/BH-07/V8 chưa nghiệm thu, risk acceptance chưa có; không merge/deploy/pilot/BH-08.
