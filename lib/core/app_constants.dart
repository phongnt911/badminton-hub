import 'package:flutter/material.dart';

class AppConstants {
  // 1. Khóa kết nối Supabase của bạn
  static const String supabaseUrl = 'https://vqelcjxljddxoyplgcvm.supabase.co';
  static const String supabaseAnonKey =
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZxZWxjanhsamRkeG95cGxnY3ZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTEyODc0NjIsImV4cCI6MjEwNjg2MzQ2Mn0.u_lf-7_EYW9SGuVL5iiOw5hXiuiR-Sq4HE7xw-kdgpg';

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
