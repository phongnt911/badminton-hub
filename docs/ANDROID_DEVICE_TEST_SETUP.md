# Kết nối Android để kiểm thử BH-07

SDK được cài trên máy Windows hiện tại tại `D:\Development`: Flutter ở `flutter`, Android SDK ở `Android\Sdk`, Java ở `Java`. Mở terminal mới sau khi cài để nhận PATH người dùng.

Đã xác minh ngày10/11/2026: Flutter3.47.9, Dart3.13.7, Java21, Android platform36/build-tools36.0.0, NDK28.2.13676358 và CMake3.22.1. `flutter doctor` Android toolchain PASS, licenses accepted; `flutter pub get` thành công, `flutter analyze`0issues. Samsung SM-S926B Android17/API37 được ADB và Flutter nhận trạng thái `device` sau chủ máy chấp thuận USB debugging. Chưa build/cài/chạy app hoặc nghiệm thu V2/V2b trong lượt setup này. Thiếu Visual Studio chỉ ảnh hưởng build Windows desktop, không cản kiểm thử Android.

## Kết nối USB

1. Điện thoại: Cài đặt → Giới thiệu điện thoại → nhấn **Số bản dựng / Build number** 7 lần. Một số hãng đặt mục này trong Thông tin phần mềm.
2. Mở **Tùy chọn nhà phát triển → Gỡ lỗi USB / USB debugging**.
3. Dùng cáp USB truyền dữ liệu, mở khóa điện thoại; nếu cần chọn chế độ Truyền tệp.
4. Chấp thuận hộp thoại **Cho phép gỡ lỗi USB** trên điện thoại.
5. Trên PowerShell chạy:

```powershell
adb devices -l
flutter devices
flutter doctor -v
```

Thiết bị phải có trạng thái `device`. `unauthorized`: mở khóa và chấp thuận RSA trên điện thoại. Danh sách trống: thử cáp/cổng khác, kiểm tra USB debugging; nếu Windows chưa nhận ADB, cài USB driver chính thức của hãng. Không cần root hoặc mở khóa bootloader.

## Chạy dự án với backend thử local

Chỉ chạy sau khi backend local đã khởi động và có tài khoản Owner/Cohost/Member thử. `127.0.0.1` trên điện thoại là chính điện thoại; dùng USB reverse để chuyển cổng tới máy tính:

```powershell
cd C:\Users\PHONGNT\Documents\GitHub\badminton-hub
adb -s DEVICE_ID reverse tcp:54321 tcp:54321
flutter pub get
flutter run -d DEVICE_ID --dart-define=APP_ENV=test --dart-define=SUPABASE_URL=http://127.0.0.1:54321 --dart-define=SUPABASE_ANON_KEY=LOCAL_ANON_KEY
```

Thay `DEVICE_ID` bằng ID từ `flutter devices`, `LOCAL_ANON_KEY` bằng public anon key của backend thử; thay cổng nếu backend khác54321. Không dùng service-role key. Lệnh trên không tự khởi động backend. Chưa có kết nối backend thì chưa kiểm thử được đăng nhập/nghiệp vụ.

Khi cần đo Dart VM heap trên điện thoại, dùng cùng cấu hình với `flutter run --profile -d DEVICE_ID ...`, mở DevTools từ URL Flutter in ra. Việc chạy app được không tự chứng minh PASS V2/V2b; cần thực hiện kịch bản và lưu bằng chứng/review riêng. Android manifest/deep-link và truy cập HTTP local phải được kiểm tra khi chạy, không mặc nhiên coi đã hỗ trợ.

## Hoàn tất

```powershell
adb -s DEVICE_ID reverse --remove tcp:54321
```

Có thể tắt USB debugging sau khi kiểm thử. Không dùng dữ liệu tài chính thật hoặc tài khoản production.

Nguồn: [Flutter Android setup](https://docs.flutter.dev/platform-integration/android/setup), [Android hardware device](https://developer.android.com/studio/run/device), [OEM USB drivers](https://developer.android.com/studio/run/oem-usb).
