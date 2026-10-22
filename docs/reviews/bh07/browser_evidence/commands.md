# Lệnh tái lập kiểm chứng Browser / Offline / Reopen BH-07 Local

Reviewer độc lập thực thi các lệnh sau từ thư mục gốc của repository để kiểm chứng độc lập.

## 1. Chuẩn bị môi trường & build Flutter Web

```bash
# Đảm bảo Supabase local đang chạy
npx supabase status

# Build bản Flutter Web độc lập trỏ vào Supabase local
flutter build web --dart-define=APP_ENV=test --dart-define=SUPABASE_URL=http://127.0.0.1:54321 --dart-define=SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
```

## 2. Khởi chạy web server phục vụ web bundle

```bash
# Phục vụ static web bundle trên cổng local 8088 (chạy background hoặc cửa sổ riêng)
python -m http.server 8088 --directory build/web
```

## 3. Chạy ma trận kiểm chứng browser tự động

Script sẽ tự động seed fixtures, khởi chạy Google Chrome headless độc lập qua CDP, thực thi 11/11 kịch bản và xuất 17 ảnh screenshot cùng log:

```bash
node scripts/bh07_browser/run_browser_verification.js
```

## 4. Các lệnh kiểm thử nền tảng (Flutter & DB)

```bash
# Phân tích tĩnh code Flutter
flutter analyze

# Chạy toàn bộ test suite Flutter (240 tests + 1 skip)
flutter test

# Chạy test suite DB BH-07 (23 tests)
node scripts/bh07_db_runner.js
```
