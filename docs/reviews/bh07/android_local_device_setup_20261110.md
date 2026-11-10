# Android local device setup — 10/11/2026

**Build/install/launch debug hoàn tất; chưa nghiệm thu V2/V2b/BH-07/V8.** Owner đồng ý tiếp tục khởi động backend và chạy điện thoại sau cài Flutter. Source HEAD `1d4cce2`; app/backend/migrations không sửa, generated plugin files chỉ đổi line ending do Flutter và đã khôi phục CRLF sau khi kiểm nội dung bằng HEAD.

## Môi trường và kết quả

- Windows, Flutter3.47.9/Dart3.13.7, Java21, SDK36/build-tools36.0.0, NDK28.2.13676358; Gradle9.3.1.
- Samsung SM-S926B, Android17/API37, arm64; owner chấp thuận RSA USB; ADB và Flutter nhận trạng thái device.
- Backend local4container `bh07-android-db/auth/rest/kong`, network `bh07-android-network`, API chỉ bind127.0.0.1:54321. Dùng recipe `late_response_evidence/run_local_stack.py` thích ứng đường dẫn Windows/tên resource trong `.build/start_android_local_fixture.py`; migrations và HTTP/UI fixture của repo, không remote project. Không phải full managed Supabase; Storage/Realtime không chạy.
- HTTP smoke trên host: password login Owner200, authenticated REST clubs200,2club nhìn thấy. Token không ghi vào smoke artifact. Đây là kiểm tra host, chưa phải đăng nhập thành công trong UI điện thoại.
- APK debug cấu hình APP_ENV=test, URL127.0.0.1:54321 và **public anon key local** qua ignored JSON. USB reverse54321→54321. Không đưa service-role key vào app.
- Build đầu kiểm toolchain327.0s; build cấu hình local thật17.2s, install10.3s; Flutter báo sync files và VM service. APK SHA256 `2d2c05e6314aefa6fc1414f1bdbe56b7ec0040abe32243f43db2506dd5f64b77`.
- Sau đó Flutter báo Lost connection to device; ADB vẫn device và PID app còn. Explicit launch MainActivity trả Status:ok (intent delivered to existing instance). Không coi debugger ổn định đã PASS.
- Owner báo đã mở app; lúc kiểm giao diện sau đó điện thoại tự khóa. Chưa xác nhận màn hình login/nghiệp vụ/HTTP từ app. Không lưu screenshot màn hình khóa vào hồ sơ.

## Trạng thái để tiếp tục

Backend giữ chạy và USB reverse giữ nguyên có chủ đích để owner dùng dữ liệu thử. Mật khẩu fixture có sẵn trong recipe local; tài khoản Owner/Cohost/Member đã cấp trong hội thoại. Anon JWT của recipe có hạn2giờ từ lúc khởi động; không coi đây là cấu hình vận hành lâu dài. Private env/config chỉ ở ignored `.build/android-local-private` và `.build/android-local-runtime`; không commit vào evidence.

Log local: `.build/android-first-build.log`, `.build/android-device-run.log`, `.build/android-local-start.log`; HTTP status/count `.build/android-local-runtime/http-smoke.json`. Thử tiếp UI đăng nhập rồi kịch bản V2; đo heap cần profile mode và receipt/review riêng. Chưa tự động mở pilot/deploy hoặc ký risk acceptance.

Khi xong có thể dừng đúng4container trên và gỡ USB reverse; không reset/delete resource khác. [Hướng dẫn](../../ANDROID_DEVICE_TEST_SETUP.md), [ma trận hiện hành](bh07_completion_status_20261110.md). V2/V2b vẫn chưa đóng; V3/V5/V7 chưa có môi trường/quyết định owner.
