# 🏸 Badminton Nha Trang Hub

Ứng dụng di động đa nền tảng (Android, iOS, Web, Windows) dành cho cộng đồng người chơi cầu lông và chủ nhóm tại TP. Nha Trang.

---

## 🚀 HƯỚNG DẪN CHẠY DỰ ÁN TRÊN MÁY TÍNH MỚI (Windows / macOS)

Khi chuyển sang máy tính mới (ở nhà, công ty, hoặc MacBook), bạn chỉ cần làm đúng các bước sau:

### 1. Chuẩn bị công cụ trên máy mới:
- Đã cài **Git** và **GitHub Desktop**.
- Đã cài **VS Code** (kèm Extension **Flutter**).
- Đã cài **Flutter SDK** và thêm vào biến môi trường Path.

### 2. Kéo code về máy mới bằng GitHub Desktop:
1. Mở **GitHub Desktop** -> `File` -> `Clone repository...`
2. Chọn repo: `phongnt911/badminton-hub` -> Bấm **Clone**.
3. Bấm nút: **Open in Visual Studio Code**.

### 3. Cài thư viện và chạy App:
Mở Terminal trong VS Code và gõ 2 lệnh:
```bash
flutter pub get
flutter run -d windows   # Trên máy Windows
# HOẶC
flutter run -d chrome    # Chạy trên trình duyệt Chrome
# HOẶC (trên MacBook)
flutter run -d macos     # hoặc cắm iPhone/máy ảo iOS