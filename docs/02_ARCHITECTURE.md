# KIẾN TRÚC KỸ THUẬT & QUY ĐỊNH MÃ NGUỒN
## 1. Công Nghệ
- **Frontend:** Flutter 3.47+ (Dart 3.13+)
- **Backend & Database:** Supabase (PostgreSQL Singapore region)
  - URL: `https://vqelcjxljddxoyplgcvm.supabase.co`
- **Dịch vụ thanh toán:** VietQR Open API (`https://img.vietqr.io/image/...`)
- **Thư viện chính:** `supabase_flutter`, `provider`, `intl`, `url_launcher`
## 2. Cấu Trúc Thư Mục Thực Tế (`lib/`)

  

lib/
├── core/
│   ├── app_constants.dart    # Chứa khóa Supabase, màu sắc, danh sách link Affiliate
│   └── vietqr_helper.dart    # Hàm sinh URL ảnh VietQR chuẩn NAPAS
├── data/
│   └── supabase_service.dart # (Repository) Gọi API Supabase: CRUD Venues, Sessions, Clubs, Transactions
├── providers/                # Tầng quản lý State (MVVM)
│   ├── club_provider.dart    # State cho Quản lý CLB & Sổ Quỹ
│   └── session_provider.dart # State cho Kèo vãng lai & Điểm danh
├── screens/
│   ├── home_screen.dart      # Tab 1: Kèo Hôm Nay, Đăng Kèo, Banner Affiliate Shopee
│   ├── venues_screen.dart    # Tab 2: Danh bạ 5 sân Nha Trang, gọi hotline
│   ├── clubs_screen.dart     # Tab 3: Quản lý CLB, Tạo nhóm, xem Sổ Quỹ
│   ├── tools_screen.dart     # Tab 4: Bảng điểm BWF, Sổ Kèo Nợ Nước Ngọt, Máy chia tiền VietQR
│   └── session_detail_screen.dart # Chi tiết kèo, điểm danh & thu tiền
└── main.dart                 # Khởi tạo Supabase, MultiProvider và thanh điều hướng 4 Tab

## 3. Quy Tắc VietQR
Sử dụng cú pháp URL chuẩn:
`https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png?amount={amount}&addInfo={content}&accountName={owner}`
Không dùng SDK thanh toán rườm rà.