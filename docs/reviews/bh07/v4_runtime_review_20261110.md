# V4 Docker local — runtime 10/11/2026

**FAIL, exit 1; toàn V4/BH-07/V8 chưa nghiệm thu.** Codex chạy runtime trên HEAD `08c2069aaa111b7805c785bdf0af205a6b374ae8`, checkout sạch lúc runner bắt đầu. Code MC1–MC6 kế thừa candidate `704a326`; đây là lượt runtime mới, không thay kết luận review source/test cũ.

## Môi trường và lệnh

Docker cài per-user tại `%LOCALAPPDATA%/Programs/DockerDesktop`. Terminal cũ chưa có Docker trên PATH. Khởi động Docker Desktop bằng executable đã cài; `docker version` xác nhận Desktop 4.99.0, client/server Engine 29.9.3, context desktop-linux, Linux amd64. Trước chạy không có container/image; ổ C còn 11,442,176,000 byte. Không sửa PATH hệ thống hay cấu hình gateway.

Thêm thư mục Docker CLI vào PATH chỉ trong process rồi chạy Python bundled:

```text
python scripts/bh07_backup/run_v4_concurrent_rehearsal.py --out tmp/v4-runtime-20261110-docker
```

Runner tải postgres:17, GoTrue v2.197.0, PostgREST v16.4 và Kong 2.8.1. Không tác động DB dev hoặc chạy production.

## Quan sát và giới hạn

- Run ID `fb0f22dc`, elapsed 85.265 giây theo summary; lần tải image đầu nằm trong thời gian này.
- Source stack khởi động, migrations/seed và Auth users được tạo. HTTP P0 Owner trả 200; collector đọc payment 10.000 VND, ledger/audit/request liên kết thực.
- Snapshot `00000041-00000002-1` đã export; summary ghi transaction giữ mở và tham số pg_dump tương ứng.
- Runner dừng tại `ValueError: No verified concurrent HTTP commits during active snapshot dump`.
- Không có receipt writer/dump trong summary. Code main raise trước khi chép `measured` vào summary khi overlap không đạt hoặc exporter đã thoát. Vì vậy artifact này **không đủ phân biệt** không bắt được COPY, writer không overlap, HTTP lỗi hoặc exporter thoát. Dump nhanh trên seed nhỏ là giả thuyết, chưa phải nguyên nhân đã chứng minh. Không nhận các finding thiếu dữ liệu của validator thành từng lỗi DB độc lập.
- Restore, target Auth và replay **NOT RUN**. Không suy runtime FAIL thành bằng chứng app làm mất dữ liệu.

## Cleanup và bằng chứng

[Summary nguyên byte](v4_runtime_20261110_evidence/summary.json), SHA-256 `1924e96cd592bf1ebf52dae98ea1a3015a4ca382a072de93f3fdf54c2bd090fe`. Bản gốc đã chuyển vào `.build/v4-runtime-20261110-docker-original/summary.json` khi tiếp tục; hash sau chuyển giữ nguyên.

Receipt cleanup: ok true, 7 container và 1 network trong manifest đều verified absent, private dumps removed true, không cleanup error. Codex kiểm thêm bằng Docker sau runtime: `docker ps -a` rỗng; networks chỉ còn bridge/host/none. Bốn image tải mới được giữ cache; không prune. Ổ C còn 12,934,955,008 byte tại kiểm tra sau.

Không sửa source/test/app/schema hoặc evidence lịch sử trong lượt này. Không chạy lại Python/Flutter suite; các count lịch sử giữ nguyên attribution. Đây là runtime của Codex, không phải QA runtime độc lập mới.

## Bước tiếp

Cần giữ receipt `measured` (mốc dump, exit code, observation và kết quả writer đã lọc thông tin riêng) cả trên nhánh FAIL, đồng thời ghi rõ trạng thái exporter. Sau khi xác định nhánh thất bại thực mới chọn workload/cơ chế điều phối cho cửa sổ COPY đo được; không sleep giả làm bằng chứng overlap, bỏ gate hoặc dựng receipt.

Đây là phát hiện runtime tiếp theo sau delta MC1–MC6 đã chốt. Chưa tự mở vòng sửa Anti thứ tư hoặc sửa thêm source trong lượt kiểm môi trường/runtime. Không merge/deploy/pilot/BH-08; owner risk acceptance chưa có.
