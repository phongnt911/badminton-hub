# Review bản sửa receipt FAIL V4 — 10/11/2026

**Đạt trong phạm vi delta receipt chẩn đoán source/test; runtime mới chờ chạy, toàn V4/BH-07/V8 chưa nghiệm thu.** Anti CLI triển khai trong conversation `1525e391-4d7c-42f7-a58e-662ee36e5b55`, Codex review và chạy test. Base `08c2069aaa111b7805c785bdf0af205a6b374ae8`; source/test được chốt bằng commit chứa báo cáo này, kiểm tra dưới đây trên working tree trước commit.

## Kiểm chứng

Codex chạy RED: 19 test, 5 test mới FAIL do thiếu diagnostics, 14 cũ PASS, exit 1. Sau Anti triển khai: runtime-collection **19/19**, concurrency **56/56**, supplemental **6/6** và standalone probe **49/49 controls**, tất cả exit 0. Log local `.build/v4-diagnostics-{red,green,concurrency,supplemental,probe}.log`; đây là synthetic/mocked orchestration, không phải DB/HTTP runtime mới.

Reviewer subagent chỉ đọc diff hai file runner/test và hồ sơ giao việc, tự chạy runtime-collection **19/19 PASS**, exit 0; không nêu P0/P1/P2 được đưa vào trong delta. Reviewer không triển khai và không chạy Docker. Codex đối chiếu diff: whitelist loại dump stdout/stderr, HTTP bodies và SQL thô; diagnostics gán trước raise, exporter poll được lấy một lần, không thay lịch writer/dump, validator, workload hoặc cleanup.

## Giới hạn giữ lại

Nếu `dump_with_writers()` raise trước khi trả về thì helper diagnostics mới chưa được gọi. Observation chỉ là mẫu đã được logic cũ chọn trong khoảng giao, không chứa toàn bộ mẫu backend. Reviewer tách hai hành vi collector cũ này khỏi delta receipt, vì sửa chúng sẽ mở rộng scope. Điều phối đồng ý giữ giới hạn công khai; không dùng receipt để khẳng định đã thu mọi dạng lỗi.

Dump nonzero trong test là CompletedProcess do mock trả về; không chứng minh đường command exception thật đã có diagnostics. Synthetic success control không chứng minh overlap runtime. Full Python/Flutter mới NOT RUN; app/schema không đổi. Runtime đầu trước sửa vẫn FAIL theo [báo cáo](v4_runtime_review_20261110.md), không retag source mới.

Bước kế tiếp: chạy cùng rehearsal trên candidate sạch, output mới trong `.build/`, giữ summary và kiểm cleanup; phân tích nhánh thất bại từ số đo rồi mới giao Anti sửa điều phối/workload. Không merge/deploy/pilot/BH-08.
