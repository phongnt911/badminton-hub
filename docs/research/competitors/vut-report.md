# Phân tích tĩnh Vụt – Cầu lông 1.0.4

## Kết quả chính

Vụt là ứng dụng React Native/Expo dùng Hermes, package `truong.vut`. Đã phân tích XAPK do người dùng tải về, không cài hoặc chạy ứng dụng và không gửi yêu cầu tới backend. Bằng chứng hiện có mô tả cấu trúc và các điểm cần kiểm chứng, chưa chứng minh ứng dụng an toàn hay độc hại.

## Nguồn và tính toàn vẹn

- File nguồn: `/mnt/c/Users/POTA/Downloads/Vụt+-+Cầu+lông_1.0.4_APKPure.xapk`.
- Trang phân phối: https://apkpure.net/v%E1%BB%A5t-c%E1%BA%A7u-l%C3%B4ng/truong.vut/download
- SHA-256 XAPK: `c9826b2a72b0f74d8279f8b8934a04117f8d06e32de989ee7bbc1805a770e37e`, khớp giá trị trang APKPure đã công bố trong lần tra cứu trước.
- Có 4 APK: `truong.vut.apk`, `config.arm64_v8a.apk`, `config.en.apk`, `config.mdpi.apk`.
- Base APK: 65.224.195 byte; SHA-256 `62f93a1468cf90a091b76033ef485023cf2379411595ba5028d90e3a91d2136d`.
- Cả 4 APK chứa cùng chứng thư trong signing block v2/v3: SHA-256 `9106d1b224f8ec30721d117a772d1d0fdca5872b1e1ccc8de1795b691ec400bb`; SHA-1 `337f245ec6fa90daa840edc7d02d179e44800bdd`, khớp giá trị “Signature” APKPure đã niêm yết.
- Chỉ trích và đối chiếu chứng thư, chưa xác minh mật mã toàn bộ chữ ký APK bằng apksigner, cũng chưa đối chiếu trực tiếp chứng thư với Google Play. Hash khớp nguồn tải không phải chứng nhận an toàn.

Chi tiết từng APK: [apk-identities.json](apk-identities.json).

## Phiên bản và kiến trúc

| Thuộc tính | Quan sát |
|---|---|
| Android package | truong.vut |
| Android versionName / versionCode | 1.0.4 / 21 |
| minSdk / targetSdk / compileSdk | 24 / 36 / 36 |
| Cấu hình Expo version | 1.0.7 |
| Expo SDK trong app.config | 54.0.0 |
| newArchEnabled | true |
| ABI trong bộ XAPK này | arm64-v8a |
| JavaScript bundle | assets/index.android.bundle, 4.870.892 byte |
| Định dạng bundle | Hermes bytecode, version 96 |

Sai khác 1.0.4 và 1.0.7 là sai khác giữa hai nguồn metadata trong cùng gói, không đủ bằng chứng kết luận gian lận hoặc xác định cơ chế phát hành. Bộ XAPK chỉ có split ARM64; không suy ra ứng dụng trên Play chỉ hỗ trợ ARM64.

Thư viện native gồm libhermes.so, libreactnative.so, libexpo-modules-core.so, libreanimated.so, libworklets.so, libexpo-av.so và thư viện ML Kit barcode. Expo Updates có `ENABLED=false` trong manifest; không coi cấu hình CHECK_ON_LAUNCH=ALWAYS là bằng chứng OTA đang bật.

## Backend và chức năng

Đã đọc bảng chuỗi Hermes theo offset/độ dài thay vì ghép các đoạn ASCII. Tách được 43.136 chuỗi; kiểm tra độ dài file, giới hạn bảng chuỗi và SHA-1 footer của bundle thành công. Đây là kiểm tra cấu trúc/hash bundle, không xác minh chữ ký ứng dụng. Tham khảo định dạng của dự án Hermes: https://github.com/facebook/hermes/blob/v0.13.0/include/hermes/BCGen/HBC/BytecodeFileFormat.h

Các chuỗi nguyên vẹn quan sát được:

- `https://api.vutcaulong.com`
- `https://api.vutcaulong.com/auth-service`
- `https://api.vutcaulong.com/spc-service`
- `/api/v1/login`, `/api/v1/signUp`, `/api/v1/refresh`
- `/api/v1/sendOTP`, `/api/v1/verifyOtp`, `/api/v1/forgotPassword`, `/api/v1/change-password`
- `/api/v1/badmintonCourts`, `/api/v1/badmintonCourts?city=`
- `/api/v1/badminton-sessions`, `/api/v1/badminton-sessions/filters`
- `/api/v1/joinRequests`, `/api/v1/joinRequests/updateStatus/`
- `/api/v1/matchHistories`, `/api/v1/notificationSettings`, `/api/v1/userDevices`
- `/socket.io`, `/socket.io/`

Những chuỗi này gợi ý đăng nhập/OTP, quản lý buổi cầu lông, tìm sân, yêu cầu tham gia, lịch sử trận và thông báo. Chưa khôi phục luồng gọi nên không khẳng định phương thức HTTP, cách ghép base URL, quyền truy cập hoặc endpoint nào thực sự được gọi. Không kiểm thử các endpoint trên máy chủ.

Tích hợp quan sát: Firebase app/messaging, Expo Notifications, Google Sign-In, ML Kit barcode, WebView, vị trí, camera/chọn ảnh, clipboard, chia sẻ, audio/video, AsyncStorage và SecureStore. Sự hiện diện thư viện không chứng minh dữ liệu cụ thể được lưu hoặc gửi qua thư viện đó.

Danh sách URL/path có string ID: [hermes-endpoints.json](hermes-endpoints.json). Toàn bộ bảng chuỗi: [hermes-strings.json](hermes-strings.json).

## Quyền và điểm cần kiểm chứng

Manifest khai báo 35 uses-permission, bao gồm nhiều quyền badge của launcher. Nhóm đáng chú ý: vị trí gần đúng/chính xác, camera, microphone, vẽ đè màn hình (`SYSTEM_ALERT_WINDOW`), đọc/ghi bộ nhớ, sinh trắc học, nhận boot, thông báo, Internet và wake lock. Quyền khai báo không có nghĩa người dùng đã cấp hoặc app đang sử dụng.

### 1. Provider clipboard được export: cần kiểm chứng mức lộ dữ liệu

Manifest khai báo `expo.modules.clipboard.ClipboardFileProvider` với `exported=true`, authority `truong.vut.ClipboardFileProvider`, không thấy permission bảo vệ trên provider. XML chỉ ánh xạ `cache/.clipboard/`.

JADX đọc được phương thức `openFile`: chỉ chấp nhận mode `r`, không thấy kiểm tra người gọi ở phương thức này. Phần giải quyết đường dẫn dùng canonical path và kiểm tra nằm trong root được cấu hình. Vì vậy có bề mặt đọc tệp clipboard qua content provider nếu biết URI và tệp tồn tại; chưa chứng minh đọc tùy ý file ngoài root. Cần kiểm tra tên tệp, vòng đời/xóa cache và truy cập từ ứng dụng khác trên thiết bị kiểm thử để đánh giá tác động thực tế.

Bằng chứng: [ClipboardFileProvider.java](ClipboardFileProvider.java), [XML đường dẫn](decoded/resources/res/xml/clipboard_provider_paths.xml).

### 2. Sao lưu được bật nhưng đã loại trừ SecureStore

`allowBackup=true`. Cả quy tắc full backup, cloud backup và device transfer đều include shared preferences và exclude `SecureStore`. Không nên kết luận toàn bộ token bị backup. Cần kiểm tra dữ liệu nào thực sự nằm trong shared preferences ngoài SecureStore. Sự hiện diện AsyncStorage không tự chứng minh dữ liệu của nó nằm trong phạm vi backup này.

Bằng chứng: `decoded/resources/res/xml/secure_store_backup_rules.xml` và `secure_store_data_extraction_rules.xml`.

### 3. Quyền vẽ đè màn hình

Có `SYSTEM_ALERT_WINDOW`. Cần xác định chức năng sản phẩm nào yêu cầu và có luồng xin quyền hay không. Chưa có bằng chứng quyền được cấp hoặc có hành vi lạm dụng.

### 4. Deep link và activity được export

MainActivity nhận scheme `vut`, `exp+vut`, và HTTPS App Link host `api.vutcaulong.com`; không thấy hạn chế path trong intent filter HTTPS. Cần kiểm tra xử lý đầu vào/điều hướng, xác thực callback và kiểm tra quyền ở backend. Manifest còn export CropImageActivity và Compose PreviewActivity; sự hiện diện của chúng không tự chứng minh khai thác được hoặc build là debug. Không thấy `debuggable=true` trong application.

### 5. Tính năng bảo vệ và giới hạn quan sát

SecureStore được tích hợp, quy tắc backup loại trừ kho này. Nhiều file provider khác có `exported=false`; receiver Firebase có permission bảo vệ. Tuy nhiên chưa kiểm tra cách lưu token thực tế, TLS/pinning, kiểm tra quyền API hoặc luồng đăng nhập nên không đánh giá được hiệu quả bảo vệ toàn hệ thống.

## Công cụ và giới hạn

REA 6.5.0 đã lập inventory base APK và ARM64 split: [rea-artifact.json](rea-artifact.json), [rea-arm64.json](rea-arm64.json). Lệnh REA analyze trực tiếp APK không có provider phù hợp trong môi trường hiện tại; lỗi được giữ ở [rea-analyze.json](rea-analyze.json). Android provider đã biết thiếu REA_JADX_MCP_JAR, nên dùng JADX 1.5.6 có sẵn để giải mã resource và đọc một lớp clipboard, bổ trợ bằng đọc bảng chuỗi Hermes và APK signing block.

Chưa giải mã đầy đủ bytecode Hermes thành JavaScript hoặc dựng call graph, chưa chạy app, chưa xác minh chữ ký mật mã, chưa thử truy cập provider trên thiết bị và chưa kiểm tra backend. Các điểm trên là kết quả phân tích tĩnh, không phải danh sách lỗ hổng đã khai thác thành công.

## Mở báo cáo trên Windows

Trong File Explorer, dùng `\\wsl.localhost\<tên-distro>\home\pota\analysis\vut\vut-report.md`. Thay `<tên-distro>` bằng tên trả về của `wsl -l -q`. Nếu distro là Ubuntu: `\\wsl.localhost\Ubuntu\home\pota\analysis\vut\vut-report.md`.
