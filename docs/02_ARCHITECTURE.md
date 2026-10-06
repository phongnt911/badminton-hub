# KIẾN TRÚC KỸ THUẬT & QUY ĐỊNH MÃ NGUỒN
## 1. Công Nghệ
- **Frontend:** Flutter SDK (Dart) - Hỗ trợ Android, iOS, Web.
- **Backend & Database:** Supabase (PostgreSQL + Realtime + Auth).
- **Thanh toán:** VietQR API mở (`https://img.vietqr.io/image/...`).
- **Quản lý trạng thái (State Management):** `Provider` (đơn giản, dễ hiểu, tránh phức tạp hóa cho người mới).
## 2. Cấu Trúc Thư Mục Tiêu Chuẩn (lib/)

lib/
├── core/
│   ├── constants/       # Màu sắc, chuỗi chữ cố định, API URL
│   ├── theme/           # Giao diện Sáng/Tối
│   └── utils/           # Hàm tiện ích (Hàm tạo VietQR, định dạng tiền VNĐ)
├── data/
│   ├── models/          # Các class dữ liệu: Venue, Session, Club, Player
│   └── services/        # Kết nối Supabase: supabase_service.dart
├── providers/           # Quản lý dữ liệu app (SessionProvider, VenueProvider)
├── screens/
│   ├── home/            # Màn hình Kèo Hôm Nay & Tìm vãng lai
│   ├── venues/          # Màn hình Danh bạ sân Nha Trang
│   └── tools/           # Bảng điểm, Máy tính chia tiền VietQR
└── widgets/             # Các thành phần tái sử dụng (Thẻ kèo, Nút bấm, Banner)

## 3. Quy Tắc VietQR
Sử dụng cú pháp URL chuẩn:
`https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png?amount={amount}&addInfo={content}&accountName={owner}`
Không dùng SDK thanh toán rườm rà.