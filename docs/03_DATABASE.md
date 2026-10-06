# CƠ SỞ DỮ LIỆU SUPABASE (POSTGRESQL)

## 1. Bảng `venues` (Sân Cầu Lông Nha Trang)
- `id` (UUID, Primary Key)
- `name` (TEXT) - Tên sân (VD: Sân Đa Năng Khánh Hòa)
- `address` (TEXT) - Địa chỉ
- `area` (TEXT) - Khu vực ('Bắc Nha Trang', 'Trung tâm', 'Nam Nha Trang')
- `phone_number` (TEXT) - Hotline đặt sân
- `court_count` (INT) - Số lượng sân
- `price_range` (TEXT) - Giá tham khảo (VD: '70k - 90k/h')

## 2. Bảng `sessions` (Kèo Đấu / Buổi Chơi)
- `id` (UUID, Primary Key)
- `venue_name` (TEXT) - Tên sân diễn ra
- `play_date` (DATE) - Ngày chơi
- `start_time` (TIME) - Giờ bắt đầu
- `end_time` (TIME) - Giờ kết thúc
- `max_slots` (INT) - Tổng số người tối đa
- `joined_count` (INT) - Số người đã đăng ký
- `estimated_cost` (INT) - Tiền dự kiến mỗi người (VNĐ)
- `contact_phone` (TEXT) - SĐT/Zalo chủ kèo
- `status` (TEXT) - 'open' (còn chỗ), 'full' (hết chỗ), 'completed' (đã xong)

## 3. Bảng `session_players` (Người Tham Gia Buổi Chơi)
- `id` (UUID, Primary Key)
- `session_id` (UUID, Foreign Key -> sessions.id)
- `player_name` (TEXT) - Tên người chơi
- `phone_number` (TEXT) - Số điện thoại
- `has_arrived` (BOOLEAN) - Đã có mặt trên sân chưa
- `has_paid` (BOOLEAN) - Đã chuyển khoản tiền sân chưa