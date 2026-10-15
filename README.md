# Badminton Hub

Ứng dụng Flutter + Supabase giúp host quản lý CLB, lịch sinh hoạt, đăng ký vãng lai, điểm danh, chốt phí và thu/chi. Thị trường pilot: Nha Trang.

## Tài liệu để triển khai

Bắt đầu tại **[docs/00_START_HERE.md](docs/00_START_HERE.md)**. Bộ đặc tả v1.1 ngày 14/10/2026 gồm:

- [Yêu cầu sản phẩm](docs/01_PRD_SPEC.md).
- [Kiến trúc tổng thể](docs/02_ARCHITECTURE.md).
- [Cơ sở dữ liệu, ERD và phân quyền](docs/03_DATABASE.md).
- [Quy tắc cho Antigravity/AI](docs/04_LLM_RULES.md).
- [Hợp đồng thao tác nghiệp vụ](docs/08_DOMAIN_CONTRACTS.md).
- [Backlog và nghiệm thu](docs/09_IMPLEMENTATION_PLAN.md).
- [Luồng màn hình](docs/10_SCREEN_FLOWS.md).
- [Rà soát code và tham khảo Vmito](docs/07_HOST_FIRST_REVIEW.md).

Code hiện tại là demo, chưa hoàn thành yêu cầu v1.1. Đợt cập nhật tài liệu chưa đổi ứng dụng hoặc database live. SQL 05/06 là legacy; không chạy để tạo schema mới hoặc vào production.

## Chạy dự án hiện có

Cài Git, Flutter SDK tương thích `pubspec.yaml`, VS Code/extensions nếu cần. Clone repo và mở thư mục:

```bash
git clone https://github.com/phongnt911/badminton-hub.git
cd badminton-hub
flutter pub get
flutter run -d chrome
# Windows: flutter run -d windows
# macOS: flutter run -d macos
# Mobile: flutter devices rồi chọn thiết bị
```

## Cấu hình môi trường & Supabase

Dự án sử dụng `AppConfig` (`lib/core/app_config.dart`) để quản lý cấu hình kết nối. Mặc định kết nối tới môi trường dev, có thể ghi đè linh hoạt qua cờ `--dart-define`:

```bash
flutter run --dart-define=SUPABASE_URL=https://your-project.supabase.co --dart-define=SUPABASE_ANON_KEY=your-anon-key
```

### Công cụ dòng lệnh tương tác trực tiếp với Supabase
Để kiểm tra kết nối hoặc truy vấn dữ liệu từ terminal mà không cần khởi động toàn bộ app:

```bash
# Kiểm tra kết nối REST API và Auth API
dart run scripts/supabase_client.dart ping

# Truy vấn nhanh dữ liệu bảng (ví dụ: venues)
dart run scripts/supabase_client.dart query venues

# Xem thông tin cấu hình dự án
dart run scripts/supabase_client.dart info
```

## Kiểm tra chất lượng (Quality Assurance)

```bash
flutter analyze
flutter test
```

- **BH-01 (Auth & Cấu hình)**: Đã hoàn thành. Toàn bộ 28 bài unit & widget tests kiểm thử `AuthRepository`, `AuthProvider`, `AuthGuard`, `AuthScreen`, `AccountScreen` và Public Read đều vượt qua (100% pass), không gọi tới Supabase production trong test.
- **BH-02 (Schema nền, Migrations & Phân quyền RLS)**: Đã hoàn thành file migration `supabase/migrations/20261015051808_init_schema_v1_1.sql` (21 bảng, RLS, projections, idempotency, audit trail, tương thích dữ liệu cũ). 9/9 schema unit tests đạt (tổng 37/37 tests pass toàn bộ dự án, analyze 0 lỗi).
- **`flutter analyze`**: 0 lỗi, 0 cảnh báo.

## Dùng với Antigravity

Mở đúng checkout repo, đọc `AGENTS.md` và `docs/00_START_HERE.md`, rồi yêu cầu từng ticket (tiếp theo là BH-03 sau khi BH-01 và BH-02 đã hoàn thành). Nếu làm trên máy cá nhân khác, dùng GitHub Desktop Pull hoặc `git pull --ff-only` trên nhánh main trước khi yêu cầu code; file trong cloud workspace không tự xuất hiện ở checkout máy cá nhân.

## Đầu bài Antigravity v1.1

- [ADR và đánh đổi](docs/11_ARCHITECTURE_DECISIONS.md).
- [Prompt từng bước và tiêu chí báo cáo](docs/12_ANTIGRAVITY_PROMPTS.md).

Bắt đầu AG-00 để ghi baseline và môi trường test, sau đó AG-01 trở đi theo phụ thuộc. Phát hiện P1/P2 được chuyển thành yêu cầu và test; code/DB chưa tự thay đổi khi tài liệu được cập nhật.
