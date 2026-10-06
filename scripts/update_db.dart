import 'dart:convert';
import 'dart:io';

void main() async {
  final url = Uri.parse('https://vqelcjxljddxoyplgcvm.supabase.co/rest/v1/venues');
  final key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZxZWxjanhsamRkeG95cGxnY3ZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTEyODc0NjIsImV4cCI6MjEwNjg2MzQ2Mn0.u_lf-7_EYW9SGuVL5iiOw5hXiuiR-Sq4HE7xw-kdgpg';
  
  final rawData = [
    {
      "name": "Sân Cầu Lông LITA",
      "address": "442 Lê Hồng Phong, Phường Nha Trang, TP. Nha Trang, Khánh Hòa",
      "district": "Phường Nha Trang",
      "maps_link": "https://maps.google.com/?cid=2174209630026573077",
      "phone": "0708660670",
      "number_of_courts": 8,
      "price_per_hour": "60.000 - 80.000",
      "opening_time": "05:00",
      "closing_time": "22:00",
      "amenities": ["Gửi xe", "Wifi miễn phí", "Bán nước giải khát", "Phòng thay đồ/WC", "Cho thuê vợt"],
      "image_url": "",
      "notes": "Sân thảm tiêu chuẩn, quy mô lớn, trần cao thoáng mát (khu vực Phước Hòa cũ)"
    },
    {
      "name": "Sân Cầu Lông Huy Forza",
      "address": "75/A - 87 Nguyễn Thị Minh Khai, Phường Nha Trang, TP. Nha Trang, Khánh Hòa",
      "district": "Phường Nha Trang",
      "maps_link": "https://maps.google.com/?cid=1412232966704266094",
      "phone": "0905416838",
      "number_of_courts": 6,
      "price_per_hour": "60.000 - 80.000",
      "opening_time": "06:00",
      "closing_time": "22:00",
      "amenities": ["Gửi xe", "Wifi", "Quầy nước", "Cho thuê phụ kiện"],
      "image_url": "",
      "notes": "Nằm ngay trung tâm thành phố, hệ thống chiếu sáng LED chống chói (khu vực Tân Lập cũ)"
    },
    {
      "name": "Sân Cầu Lông Liên Đoàn Cầu Lông Khánh Hòa",
      "address": "12 Yersin, Phường Tây Nha Trang, TP. Nha Trang, Khánh Hòa",
      "district": "Phường Tây Nha Trang",
      "maps_link": "https://maps.google.com/?cid=11185502763904619090",
      "phone": "02583824540",
      "number_of_courts": 3,
      "price_per_hour": "50.000 - 70.000",
      "opening_time": "05:00",
      "closing_time": "22:00",
      "amenities": ["Gửi xe", "Nhà vệ sinh", "Bán nước"],
      "image_url": "",
      "notes": "Sân đạt chuẩn liên đoàn tỉnh (khu vực Phương Sài cũ)"
    },
    {
      "name": "Sân Cầu Lông Hưng Phú 5",
      "address": "63 Khúc Thừa Dụ, Phường Nam Nha Trang, TP. Nha Trang, Khánh Hòa",
      "district": "Phường Nam Nha Trang",
      "maps_link": "https://maps.google.com/?cid=3097649374214055446",
      "phone": "0948082021",
      "number_of_courts": 5,
      "price_per_hour": "80.000 - 120.000",
      "opening_time": "06:00",
      "closing_time": "22:00",
      "amenities": ["Gửi xe ô tô & xe máy", "Wifi", "Khu giải khát", "Phòng thay đồ/WC sạch sẽ"],
      "image_url": "",
      "notes": "Khu đô thị Phước Long mới, cơ sở vật chất hiện đại"
    },
    {
      "name": "Sân Cầu Lông Hưng Phú Phong Châu (Chi nhánh 7)",
      "address": "163 Phong Châu, Phường Nam Nha Trang, TP. Nha Trang, Khánh Hòa",
      "district": "Phường Nam Nha Trang",
      "maps_link": "https://maps.google.com/?cid=1760342682870403157",
      "phone": "0948082021",
      "number_of_courts": 5,
      "price_per_hour": "80.000 - 110.000",
      "opening_time": "06:00",
      "closing_time": "22:00",
      "amenities": ["Bãi đỗ xe", "Wifi", "Tủ nước", "Khu nghỉ ngơi"],
      "image_url": "",
      "notes": "Cụm sân thể thao Hưng Phú khu vực trục đường Phong Châu"
    },
    {
      "name": "Sân Cầu Lông Vĩnh Thạnh",
      "address": "44 Cầu Bè, Phường Tây Nha Trang, TP. Nha Trang, Khánh Hòa",
      "district": "Phường Tây Nha Trang",
      "maps_link": "https://maps.google.com/?cid=13037138462244119316",
      "phone": "0826779781",
      "number_of_courts": 6,
      "price_per_hour": "50.000 - 60.000",
      "opening_time": "05:00",
      "closing_time": "20:00",
      "amenities": ["Bãi giữ xe", "Bán nước", "Nhà vệ sinh"],
      "image_url": "",
      "notes": "Khu vực xã Vĩnh Thạnh cũ nhập vào phường Tây Nha Trang"
    },
    {
      "name": "Sân Cầu Lông Ngọc Hội",
      "address": "319 Đ. 23 Tháng 10, Phường Tây Nha Trang, TP. Nha Trang, Khánh Hòa",
      "district": "Phường Tây Nha Trang",
      "maps_link": "https://maps.google.com/?cid=11595289792109662465",
      "phone": "0986786780",
      "number_of_courts": 3,
      "price_per_hour": "80.000 - 100.000",
      "opening_time": "05:00",
      "closing_time": "22:00",
      "amenities": ["Gửi xe", "Wifi", "Quầy nước", "WC"],
      "image_url": "",
      "notes": "Khu vực Ngọc Hiệp cũ, mặt tiền trục đường 23 Tháng 10"
    },
    {
      "name": "Sân Cầu Lông Speedy Sports",
      "address": "Hương lộ Ngọc Hiệp, Lư Cấm, Phường Tây Nha Trang, TP. Nha Trang, Khánh Hòa",
      "district": "Phường Tây Nha Trang",
      "maps_link": "https://maps.google.com/?cid=5003341570418452882",
      "phone": "0844360399",
      "number_of_courts": 4,
      "price_per_hour": "70.000 - 100.000",
      "opening_time": "05:00",
      "closing_time": "22:00",
      "amenities": ["Gửi xe", "Wifi", "Quầy nước", "Kết hợp sân Pickleball"],
      "image_url": "",
      "notes": "Tổ hợp thể thao cầu lông & pickleball tại Lư Cấm (khu vực Ngọc Hiệp cũ)"
    }
  ];

  final dbData = rawData.map((e) => {
    "name": e["name"],
    "address": e["address"],
    "area": e["district"],
    "map_url": e["maps_link"],
    "phone_number": e["phone"],
    "court_count": e["number_of_courts"],
    "price_range": e["price_per_hour"],
    "image_url": (e["image_url"] as String).isEmpty ? null : e["image_url"],
  }).toList();

  final httpClient = HttpClient();
  try {
    final request = await httpClient.postUrl(url);
    request.headers.set('apikey', key);
    request.headers.set('Authorization', 'Bearer ' + key);
    request.headers.set('Content-Type', 'application/json');
    
    request.add(utf8.encode(jsonEncode(dbData)));
    final response = await request.close();
    final responseBody = await response.transform(utf8.decoder).join();
    print('Status: ' + response.statusCode.toString());
    print('Body: ' + responseBody);
  } catch (e) {
    print('Error: ' + e.toString());
  } finally {
    httpClient.close();
  }
}
