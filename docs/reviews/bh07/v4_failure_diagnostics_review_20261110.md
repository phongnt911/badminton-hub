# Review bản sửa receipt FAIL V4 — 10/11/2026

**Đạt trong phạm vi delta receipt chẩn đoán source/test; runtime mới chờ chạy, toàn V4/BH-07/V8 chưa nghiệm thu.** Anti CLI triển khai trong conversation `1525e391-4d7c-42f7-a58e-662ee36e5b55`, Codex review và chạy test. Base `08c2069aaa111b7805c785bdf0af205a6b374ae8`; source/test được chốt bằng commit chứa báo cáo này, kiểm tra dưới đây trên working tree trước commit.

## Kiểm chứng

Codex chạy RED: 19 test, 5 test mới FAIL do thiếu diagnostics, 14 cũ PASS, exit 1. Sau Anti triển khai: runtime-collection **19/19**, concurrency **56/56**, supplemental **6/6** và standalone probe **49/49 controls**, tất cả exit 0. Log local `.build/v4-diagnostics-{red,green,concurrency,supplemental,probe}.log`; đây là synthetic/mocked orchestration, không phải DB/HTTP runtime mới.

Reviewer subagent chỉ đọc diff hai file runner/test và hồ sơ giao việc, tự chạy runtime-collection **19/19 PASS**, exit 0; không nêu P0/P1/P2 được đưa vào trong delta. Reviewer không triển khai và không chạy Docker. Codex đối chiếu diff: whitelist loại dump stdout/stderr, HTTP bodies và SQL thô; diagnostics gán trước raise, exporter poll được lấy một lần, không thay lịch writer/dump, validator, workload hoặc cleanup.

## Giới hạn giữ lại

Nếu `dump_with_writers()` raise trước khi trả về thì helper diagnostics mới chưa được gọi. Observation chỉ là mẫu đã được logic cũ chọn trong khoảng giao, không chứa toàn bộ mẫu backend. Reviewer tách hai hành vi collector cũ này khỏi delta receipt, vì sửa chúng sẽ mở rộng scope. Điều phối đồng ý giữ giới hạn công khai; không dùng receipt để khẳng định đã thu mọi dạng lỗi.

Dump nonzero trong test là CompletedProcess do mock trả về; không chứng minh đường command exception thật đã có diagnostics. Synthetic success control không chứng minh overlap runtime. Full Python/Flutter mới NOT RUN; app/schema không đổi. Runtime đầu trước sửa vẫn FAIL theo [báo cáo](v4_runtime_review_20261110.md), không retag source mới.

Bước kế tiếp: chạy cùng rehearsal trên candidate sạch, output mới trong `.build/`, giữ summary và kiểm cleanup; phân tích nhánh thất bại từ số đo rồi mới giao Anti sửa điều phối/workload. Không merge/deploy/pilot/BH-08.

## Runtime trên candidate sạch `55834ee`

Codex chạy rehearsal mới bằng Docker local, output `.build/v4-runtime-20261110-diagnostics`, run ID `72e1c969`, `git_dirty: false`, elapsed 63.469s, exit 1. [Summary nguyên byte](v4_runtime_20261110_evidence/diagnostics_summary.json), SHA-256 `c4ebc0226073213bfbd4662dff693aff0ae64bec5540b69f8555c94c6de669af`.

Diagnostics đã được giữ trên nhánh FAIL: dump exit 0, start `1794285799.6068027`, end `1794285800.0093772` (khoảng 0.402575s), observation null, cả hai writer null, overlap false, exporter returncode null. Đối chiếu nhánh `dump_with_writers`: không bắt được COPY ban đầu nên không gửi writer. Không phải bằng chứng HTTP writer trả lỗi hay exporter đã chết. Chưa chứng minh cấu hình workload mới sẽ tạo cửa sổ đủ dài.

P0/snapshot đã qua; restore/replay NOT RUN. Receipt cleanup ok true, 8/8 tài nguyên trong manifest verified absent và private dumps removed true. Đã giao Anti cùng conversation **plan-only** phương án padding hữu hạn trong DB rehearsal dùng một lần, không sửa migration/app/schema nghiệp vụ, giữ quan sát COPY thật và HTTP writer thật; chờ review thiết kế trước triển khai.

Lượt plan-only tiếp theo trả exit 1 `DEADLINE_EXCEEDED/print_timeout` sau giới hạn 2 phút, response rỗng; không có thiết kế hoặc edit mới, không nhận là bàn giao hoặc vòng sửa thất bại. Không cho triển khai điều phối/workload từ suy đoán. Kiểm Docker riêng sau runtime: `docker ps -a` rỗng, networks chỉ bridge/host/none. Điểm tiếp tục: giao Anti thiết kế fixture tải hữu hạn bằng phiên ngắn, rồi review thiết kế, test RED và rehearsal mới; không chạy lặp cùng workload 0.4s để tìm PASS ngẫu nhiên.
