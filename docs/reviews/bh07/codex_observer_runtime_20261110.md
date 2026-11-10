# Codex observer runtime và điều chỉnh tải — 10/11/2026

Owner giao “codex tự sửa”; cleanup CW5/CW4 đã được review delta tại `2bc90b2`. Codex chạy Docker thật trên checkout sạch source này, run `831e2039`, output `.build/v4-runtime-20261110-codex-observer`, elapsed89.953s, exit1 **FAIL**. Full V4/BH-07/V8 chưa nghiệm thu.

[Summary nguyên byte](v4_runtime_20261110_evidence/codex_observer_summary.json), SHA-256 `1b758d997e423ba5272daa752d221dea01e89bc9ab8f65e02e7473ae43c91cf0`.

## Quan sát thật

- Dump exit0: `1794299509.0713844`–`1794299509.7845545` (~0.713s); exporter còn sống.
- Initial backend490: `1794299509.2417955`–`1794299509.24577` (~3.97ms).
- Selected COPY sample backend490: `1794299509.2499084`–`1794299509.2546868` (~4.78ms), nằm trong giao HTTP thật.
- A200: `1794299509.2482605`–`1794299509.2665606`; B200: `1794299509.2499084`–`1794299511.9866486` (~2.737s).

Observer đã giảm roundtrip đủ để bắt được sample giao HTTP ở lần đo này, nhưng B hoàn tất sau khi dump kết thúc; `overlap_verified:false` đúng contract. Không nới gate hoặc lấy sample này làm PASS. Main dừng trước restore/replay; không có runtime restore mới. Cleanup receipt ok true, private dumps removed và8/8 owned resource absent.

## Điều chỉnh tải có giới hạn

Codex tăng default padding40.000→260.000 dòng =257.920.000 payload byte (~246MiB), vẫn dưới trần256MiB. Giữ nguyên HTTP intents, native host timestamps, observer và gate; mục tiêu là có dump lifetime phủ được latency writer thực, không giả mốc hoặc trì hoãn HTTP. Không bảo đảm thời lượng từ kích thước.

Host free-disk preflight tăng512MiB→2GiB để dự phòng source/target/dump/WAL; không coi đây là đo Docker VM capacity hoặc bound tổng disk/memory. Test preflight1GiB RED trước sửa, GREEN sau sửa; resource happy path4GiB. Synthetic stats dùng default động, không thêm fallback hoặc thay oracle.

Codex42 runtime-collection và49controls PASS trên delta config. Reviewer độc lập đọc delta và tự chạy42/42 PASS, không thấy P0/P1/P2; scoped GO cho đo runtime mới. Full Python541test/537PASS+4SKIP thuộc source2bc90b2 trước đổi config. [Runtime/full-suite mới source46c9d98](codex_bounded_runtime_review_20261110.md): overlap thật/target fingerprint đã có, nhưng Docker lỗi sau restore và full suite mới có1FAIL V5b harness; không retag bằng chứng cũ thành PASS. Không merge/deploy/pilot/BH-08.
