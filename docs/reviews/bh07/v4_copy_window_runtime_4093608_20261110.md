# Runtime COPY-window `4093608` — 10/11/2026

**FAIL, exit1; V4/BH-07/V8 chưa nghiệm thu.** Codex chạy candidate `4093608`, checkout sạch, run `0c24d95f`, output `.build/v4-runtime-20261110-copy-window`. Source/test CW1–CW4 giữ kết luận đã đóng; đây là phát hiện runtime mới, không retag synthetic thành runtime PASS.

Padding40.000 dòng/39.680.000 byte, digest nội dung `ba818c38a576623314f70b7db59e4d9c`. Dump exit0, lifetime `1794292028.5122879`–`1794292029.6722262` (~1.160s), exporter còn sống. Initial COPY sample backend409, quan sát từ `1794292028.6372006` đến `1794292028.8271687` (~190ms). Hai HTTP writer đã gửi và trả200:

- A: `1794292028.827756`–`1794292028.9075356` (~79.8ms).
- B: `1794292028.828551`–`1794292028.8653798` (~36.8ms).

Giao hai HTTP interval ~36.8ms, nhưng selected overlap observation null; gate vẫn FAIL. Kết luận giới hạn: fixture đã tạo được initial COPY window và HTTP commits, nhưng observer subprocess roundtrip lớn hơn khoảng giao ở lần đo này; chưa đủ receipt theo contract. Không thay cổng thành chỉ initial sample hoặc dump lifetime.

Restore/replay NOT RUN; elapsed62.422s. Lượt sửa kế tiếp giao Anti kết nối psql observer giữ mở để giảm chi phí spawn, giữ nguyên HTTP workload, gate và timeout/cleanup fail-closed. Tính là correction **vòng3/3** của nhiệm vụ COPY-window; nếu vẫn chưa đạt thì dừng theo AGENTS, không tự mở vòng4. Anti chạy không timeout, chỉ review sau bàn giao.

[Summary nguyên byte](v4_runtime_20261110_evidence/copy_window_summary.json), SHA-256 `1c619e7ca877a3627daa9ad1c6a68c7c9ce26ff35c2a1e83e86bcd4661e9d5d4`. Receipt cleanup ok true,7 container+1network verified absent, private dumps removed true. Codex kiểm inventory riêng sau đó: không có container, networks chỉ bridge/host/none.
