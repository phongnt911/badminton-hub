import 'package:flutter/foundation.dart';

/// Các môi trường thực thi của ứng dụng
enum AppEnvironment { dev, staging, prod, test }

/// Quản lý cấu hình toàn cục và kết nối Supabase
///
/// Hỗ trợ đọc từ biến môi trường (--dart-define) để không gán cứng
/// thông tin sản xuất khi chạy kiểm thử hoặc phát triển.
class AppConfig {
  static const String _defaultSupabaseUrl =
      'https://vqelcjxljddxoyplgcvm.supabase.co';
  static const String _defaultAnonKey =
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZxZWxjanhsamRkeG95cGxnY3ZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTEyODc0NjIsImV4cCI6MjEwNjg2MzQ2Mn0.u_lf-7_EYW9SGuVL5iiOw5hXiuiR-Sq4HE7xw-kdgpg';

  /// Môi trường hiện tại, mặc định là dev nếu không truyền
  static const AppEnvironment environment = AppEnvironment.dev;

  /// URL kết nối Supabase, có thể ghi đè qua --dart-define=SUPABASE_URL=...
  static String get supabaseUrl => const String.fromEnvironment(
    'SUPABASE_URL',
    defaultValue: _defaultSupabaseUrl,
  );

  /// Khóa công khai Anon Key, có thể ghi đè qua --dart-define=SUPABASE_ANON_KEY=...
  static String get supabaseAnonKey => const String.fromEnvironment(
    'SUPABASE_ANON_KEY',
    defaultValue: _defaultAnonKey,
  );

  /// URL điều hướng sau khi xác nhận email hoặc đặt lại mật khẩu.
  /// Trên Web: dùng origin hiện tại (ví dụ: http://localhost:3000 hoặc domain web).
  /// Trên Mobile: dùng Deep Link Scheme đã cấu hình cho ứng dụng.
  static String? get authCallbackUrl {
    if (kIsWeb) {
      return null; // Supabase Flutter Web tự động nhận diện window.location.origin
    }
    return 'io.supabase.badmintonhub://login-callback';
  }

  /// Kiểm tra xem có đang chạy trong môi trường test hay không
  static bool get isTest => environment == AppEnvironment.test;
}
