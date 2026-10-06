# ĐẶC TẢ YÊU CẦU DỰ ÁN (PRD - PRODUCT REQUIREMENTS DOCUMENT)

## 1. Tên Dự Án: Badminton Nha Trang Hub
Ứng dụng di động đa nền tảng (Android & iOS) phục vụ cộng đồng người chơi cầu lông tại TP. Nha Trang.

## 2. Mục Tiêu & Triết Lý Sản Phẩm
- **Miễn phí 100%:** Dành cho cộng đồng, không thu phí thành viên hay chủ nhóm.
- **Tối giản (Zero Friction):** Người chơi không cần đăng nhập vẫn xem được sân và kèo. Đăng ký slot 1 chạm.
- **Nguồn thu duy trì app:** Tiếp thị liên kết (Affiliate Shopee/TikTok phụ kiện cầu lông) + Banner tài trợ từ các sân/shop căng vợt tại Nha Trang + Quảng cáo AdMob kín đáo (không pop-up).

## 3. Các Tính Năng Theo Giai Đoạn

### Giai đoạn 1 (MVP - Cốt lõi):
1. **Danh bạ Sân Cầu Lông Nha Trang:** Danh sách các cụm sân, địa chỉ, hotline đặt sân, số lượng sân, mức giá tham khảo, chỉ đường Google Maps.
2. **Kèo Đấu & Tuyển Vãng Lai:** 
   - Chủ nhóm đăng kèo nhanh trong 15s (Sân, khung giờ, thiếu mấy slot, phí tạm tính).
   - Vãng lai bấm đăng ký giữ chỗ.
3. **Chia Tiền Buổi & VietQR 1 Chạm:**
   - Công thức: (Tiền sân + Tiền cầu) / Số người có mặt.
   - Sinh mã ảnh VietQR chuẩn NAPAS tự động điền STK chủ sân + số tiền chính xác + nội dung chuyển khoản.
4. **Góc Phụ Kiện Giá Tốt (Affiliate):** Thẻ gợi ý mua quấn cán, ống cầu lông, cước, bình xịt lạnh.

### Giai đoạn 2 (Trải nghiệm trên sân):
1. Bảng điểm trực tiếp (Scoreboard): Chạm cộng điểm 21/11, tự đổi sân, báo giao cầu.
2. Xoay tua sân công bằng: Thuật toán nhắc ai ngồi chờ lâu nhất vào sân.
3. Kèo độ nước ngọt vui vẻ: Sổ nợ chai Revive/cà phê sau mỗi set đấu.

### Giai đoạn 3 (Nâng cao):
1. Hệ thống xếp hạng phong trào (Elo / Rank).
2. Thống kê cặp đôi ăn ý (Duos Winrate).


---

#### 📄 File 2: Cập nhật `docs/01_PRD_SPEC.md`
*(Mở file `docs/01_PRD_SPEC.md` và dán nội dung cập nhật tiến độ)*

```markdown
# ĐẶC TẢ YÊU CẦU DỰ ÁN (PRD - PRODUCT REQUIREMENTS DOCUMENT)

## 1. Thông Tin Chung
- **Tên dự án:** Badminton Nha Trang Hub
- **Thị trường mục tiêu ban đầu:** TP. Nha Trang, Tỉnh Khánh Hòa.
- **Mô hình:** Miễn phí 100% cho người chơi & chủ nhóm; Nguồn thu từ Tiếp thị liên kết (Affiliate Shopee phụ kiện) & Tài trợ sân địa phương.

---

## 2. Tiến Độ & Bản Đồ Tính Năng (Roadmap Status)

### ✅ Giai đoạn 1 (ĐÃ HOÀN THÀNH 100%):
- [x] **CSDL Supabase:** Đã tạo bảng `venues`, `sessions`, `session_players`, thiết lập chính sách RLS mở.
- [x] **Danh bạ Sân Nha Trang:** Đã nạp 5 cụm sân quen thuộc (Đa Năng Khánh Hòa, Vĩnh Hải, Phước Long, 19-8, Đồng Nai), hỗ trợ gọi hotline 1 chạm.
- [x] **Đăng Kèo & Đặt Chỗ Vãng Lai:** Màn hình Kèo Hôm Nay, đăng kèo mới, giữ chỗ slot.
- [x] **Banner Affiliate Shopee:** Thẻ gợi ý mua quấn cán vợt, ống cầu Vina Star, xịt lạnh thể thao.
- [x] **Bảng Điểm Trực Tiếp Chuẩn BWF:** Set 21đ/11đ, đổi sân điểm 11, tính ô giao cầu chẵn/lẻ, hỗ trợ Undo (-1).
- [x] **Sổ Kèo Độ Nước Ngọt / Cúng Cầu:** Chọn kèo trước trận, tự động lưu kết quả nợ vào Sổ Nợ Hôm Nay, đánh dấu đã thanh toán.
- [x] **Chia Tiền Buổi & VietQR 1 Chạm:** Công thức (Sân + Cầu)/Số người, sinh mã ảnh VietQR chuẩn NAPAS tự động điền STK và số tiền.

---

### ⏳ Giai đoạn 2 (DỰ KIẾN LÀM TIẾP THEO):
- [ ] **Nâng cấp Đăng ký Slot Vãng lai:** Nhập tên và SĐT thật khi giữ chỗ, chủ kèo duyệt danh sách, nút Check-in có mặt và Đã thanh toán.
- [ ] **Tạo Nhóm / CLB Cố Định:** Cho phép tạo CLB riêng (VD: CLB Biển Xanh), quản lý quỹ tháng cố định.
- [ ] **Xếp sân xoay tua công bằng (Fair Rotation):** Thuật toán gợi ý người ngồi ngoài lâu nhất vào sân tiếp theo.
- [ ] **Bảng xếp hạng vui vẻ:** Thống kê Winrate %, Chuỗi thắng (Win streak) của thành viên trong nhóm.