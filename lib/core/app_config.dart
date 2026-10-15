import 'package:flutter/foundation.dart';

/// Các môi trường thực thi của ứng dụng
enum AppEnvironment { dev, staging, prod, test }

/// Quản lý cấu hình toàn cục và kết nối Supabase
///
/// Hỗ trợ đọc từ biến môi trường (--dart-define) để không gán cứng
/// thông tin sản xuất khi chạy kiểm thử hoặc phát triển.
class AppConfig {
  static const String environmentName = String.fromEnvironment('APP_ENV');
  static AppEnvironment get environment => AppEnvironment.values.firstWhere(
    (value) => value.name == environmentName,
    orElse: () => throw StateError('Cần APP_ENV=dev|staging|prod|test'),
  );

  static String get supabaseUrl => const String.fromEnvironment('SUPABASE_URL');
  static String get supabaseAnonKey =>
      const String.fromEnvironment('SUPABASE_ANON_KEY');

  static void validate() {
    final env = environment;
    final uri = Uri.tryParse(supabaseUrl);
    if (uri == null ||
        !uri.hasAuthority ||
        !['http', 'https'].contains(uri.scheme) ||
        supabaseAnonKey.isEmpty) {
      throw StateError('Cần SUPABASE_URL và SUPABASE_ANON_KEY hợp lệ');
    }
    if (env == AppEnvironment.test &&
        !['localhost', '127.0.0.1', '::1'].contains(uri.host)) {
      throw StateError('Môi trường test chỉ được kết nối local');
    }
    if (uri.host == 'vqelcjxljddxoyplgcvm.supabase.co' &&
        env != AppEnvironment.prod) {
      throw StateError('Project production yêu cầu APP_ENV=prod');
    }
  }

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
