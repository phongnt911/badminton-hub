import 'package:flutter/material.dart';

import 'app_config.dart';

class AppConstants {
  // 1. Khóa kết nối Supabase (lấy từ cấu hình động AppConfig)
  static String get supabaseUrl => AppConfig.supabaseUrl;
  static String get supabaseAnonKey => AppConfig.supabaseAnonKey;

  // 2. Màu sắc chủ đạo (Xanh lá thể thao năng động)
  static const Color primaryColor = Color(0xFF00A86B); // Xanh Emerald
  static const Color accentColor = Color(0xFFFF9800); // Cam thể thao
  static const Color darkBg = Color(0xFF121820);

  // 3. Link Affiliate Shopee mẫu (Phụ kiện cầu lông Nha Trang giá tốt)
  static const List<Map<String, String>> affiliateItems = [
    {
      'title': 'Quấn cán vợt thấm mồ hôi Yonex (Combo 5)',
      'price': '45.000đ',
      'tag': 'Hot Sale',
      'url': 'https://shopee.vn',
    },
    {
      'title': 'Ống cầu lông Vina Star chính hãng (Tốc độ 77)',
      'price': '245.000đ',
      'tag': 'Bán chạy',
      'url': 'https://shopee.vn',
    },
    {
      'title': 'Bình xịt lạnh giảm đau chấn thương thể thao',
      'price': '85.000đ',
      'tag': 'Cần thiết',
      'url': 'https://shopee.vn',
    },
  ];
}
