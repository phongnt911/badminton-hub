# Phân tích tĩnh Vmito APK

Nguồn: `/mnt/c/Users/POTA/Downloads/vmito-v1.0.0.apk`.
Công cụ: REA 6.5.0 (inspect-artifact, identify-flutter-build, inspect-dart-aot), JADX 1.5.6 bổ trợ.
Không cài/chạy APK, không gọi các endpoint tìm thấy.

## Nhận dạng
- Dung lượng: 155639491 bytes (~148.43 MiB).
- SHA-256: `8f2bfbce3637e2e44e3d95a7d64d2e921a54635279a05a3066205a0715afc2bf`.
- Nhãn: Vmito; package: `com.vmito.app`.
- Manifest: versionName `1.0.3`, versionCode `15`, khác tên file v1.0.0.
- minSdk 24, targetSdk 36, compileSdk 37.
- Flutter/Dart AOT; ABI: arm64-v8a, armeabi-v7a, x86_64. Có 3 DEX.
- Dart snapshot hash: `ace654289f5abc240509fc941453ebc5`; chưa xác định phiên bản SDK từ hash.
- Mã ứng dụng Flutter chủ yếu nằm trong libapp.so; MainActivity Java chỉ là lớp kế thừa.

## Chức năng và tích hợp quan sát được
- App Links cho vmito.com và www.vmito.com: sessions, venues, clubs, classes, tournament, newsfeed, leaderboard, user… Gợi ý tính năng cộng đồng/thể thao; chưa kiểm chứng hành vi runtime.
- Firebase Messaging, Google Maps/Places, ML Kit barcode, WebView, xác thực web, vị trí, chọn ảnh, chia sẻ và in tài liệu được khai báo trong manifest.
- Asset có Stream Chat và VietQR; chuỗi nhị phân có chat.stream-io-api.com và api.vietqr.io/v2/banks.
- Chuỗi API: https://vmito.com/api và https://vmito.com/api/sessions/available. Chuỗi tồn tại không chứng minh được gọi khi chạy.

## Quyền và bề mặt cần xem xét
- Vị trí chính xác/gần đúng, camera, microphone, sinh trắc học, thông báo, Internet.
- READ_EXTERNAL_STORAGE giới hạn SDK 32; WRITE_EXTERNAL_STORAGE giới hạn SDK 29; requestLegacyExternalStorage=true.
- allowBackup=false. Manifest không khai báo debuggable=true.
- MainActivity và callback đăng nhập được export; callback dùng scheme `vmito` và không giới hạn host/path trong intent filter. Cần kiểm tra xác thực state/PKCE và xử lý URI trước khi kết luận có lỗ hổng.
- Google Maps API key được đóng gói trong manifest. Đây là cấu hình client có thể quan sát, không tự chứng minh lộ bí mật; cần xác minh hạn chế package/chứng thư và API trên phía quản trị.
- Receiver Firebase export có quyền bảo vệ; việc export riêng lẻ không đủ để kết luận có lỗ hổng.
- Các quyền khai báo không chứng minh đã được cấp hoặc có hành vi thu thập dữ liệu.

## Giới hạn
REA inspect-android-package thiếu REA_JADX_MCP_JAR (jadx-headless-mcp 0.7.1), vì vậy manifest đọc bằng JADX có sẵn. JADX báo 51 lỗi giải mã; không xem đầu ra Java là đầy đủ. REA Dart string pool có coverage partial và bị giới hạn số lượng; chưa phục hồi toàn bộ Dart, chưa kiểm tra luồng đăng nhập, lưu token, TLS, quyền backend hoặc chữ ký APK. Chưa đủ bằng chứng kết luận APK an toàn hay độc hại.

## Tệp chứng cứ
- vmito-artifact.json: danh mục REA.
- vmito-flutter.json: nhận dạng Flutter và ABI.
- vmito-dart.json: snapshot AOT và chuỗi quan sát.
- vmito-package.json: lỗi phụ thuộc REA Android provider.
- vmito-urls.txt: URL trích từ các chuỗi ASCII libapp.so arm64.
- vmito-res/resources/AndroidManifest.xml: manifest đã giải mã.
- vmito-jadx/sources/: mã Java giải mã một phần.
