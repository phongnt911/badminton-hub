-- Script chèn dữ liệu các sân cầu lông tại Nha Trang (Cập nhật T10/2026)
-- Chạy đoạn mã này trong SQL Editor của Supabase

INSERT INTO venues (name, address, area, map_url, phone_number, court_count, price_range, image_url)
VALUES 
(
  'Sân Cầu Lông LITA', 
  '442 Lê Hồng Phong, Phường Nha Trang, TP. Nha Trang, Khánh Hòa', 
  'Phường Nha Trang', 
  'https://maps.google.com/?cid=2174209630026573077', 
  '0708660670', 
  8, 
  '60.000 - 80.000', 
  NULL
),
(
  'Sân Cầu Lông Huy Forza', 
  '75/A - 87 Nguyễn Thị Minh Khai, Phường Nha Trang, TP. Nha Trang, Khánh Hòa', 
  'Phường Nha Trang', 
  'https://maps.google.com/?cid=1412232966704266094', 
  '0905416838', 
  6, 
  '60.000 - 80.000', 
  NULL
),
(
  'Sân Cầu Lông Liên Đoàn Cầu Lông Khánh Hòa', 
  '12 Yersin, Phường Tây Nha Trang, TP. Nha Trang, Khánh Hòa', 
  'Phường Tây Nha Trang', 
  'https://maps.google.com/?cid=11185502763904619090', 
  '02583824540', 
  3, 
  '50.000 - 70.000', 
  NULL
),
(
  'Sân Cầu Lông Hưng Phú 5', 
  '63 Khúc Thừa Dụ, Phường Nam Nha Trang, TP. Nha Trang, Khánh Hòa', 
  'Phường Nam Nha Trang', 
  'https://maps.google.com/?cid=3097649374214055446', 
  '0948082021', 
  5, 
  '80.000 - 120.000', 
  NULL
),
(
  'Sân Cầu Lông Hưng Phú Phong Châu (Chi nhánh 7)', 
  '163 Phong Châu, Phường Nam Nha Trang, TP. Nha Trang, Khánh Hòa', 
  'Phường Nam Nha Trang', 
  'https://maps.google.com/?cid=1760342682870403157', 
  '0948082021', 
  5, 
  '80.000 - 110.000', 
  NULL
),
(
  'Sân Cầu Lông Vĩnh Thạnh', 
  '44 Cầu Bè, Phường Tây Nha Trang, TP. Nha Trang, Khánh Hòa', 
  'Phường Tây Nha Trang', 
  'https://maps.google.com/?cid=13037138462244119316', 
  '0826779781', 
  6, 
  '50.000 - 60.000', 
  NULL
),
(
  'Sân Cầu Lông Ngọc Hội', 
  '319 Đ. 23 Tháng 10, Phường Tây Nha Trang, TP. Nha Trang, Khánh Hòa', 
  'Phường Tây Nha Trang', 
  'https://maps.google.com/?cid=11595289792109662465', 
  '0986786780', 
  3, 
  '80.000 - 100.000', 
  NULL
),
(
  'Sân Cầu Lông Speedy Sports', 
  'Hương lộ Ngọc Hiệp, Lư Cấm, Phường Tây Nha Trang, TP. Nha Trang, Khánh Hòa', 
  'Phường Tây Nha Trang', 
  'https://maps.google.com/?cid=5003341570418452882', 
  '0844360399', 
  4, 
  '70.000 - 100.000', 
  NULL
);
