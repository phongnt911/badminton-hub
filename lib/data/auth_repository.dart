import 'package:supabase_flutter/supabase_flutter.dart';
import '../core/app_config.dart';

/// Repository xử lý xác thực tài khoản qua Supabase Auth.
///
/// Hỗ trợ dependency injection để kiểm thử độc lập (không gọi production).
class AuthRepository {
  final SupabaseClient _client;

  AuthRepository({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  /// Người dùng hiện tại (null nếu chưa đăng nhập)
  User? get currentUser => _client.auth.currentUser;

  /// Phiên hiện tại
  Session? get currentSession => _client.auth.currentSession;

  /// Đã đăng nhập hay chưa
  bool get isAuthenticated => currentUser != null;

  /// Stream lắng nghe thay đổi trạng thái xác thực
  Stream<AuthState> get authStateChanges => _client.auth.onAuthStateChange;

  /// Đăng ký tài khoản mới bằng Email và Mật khẩu
  Future<AuthResponse> signUpWithEmail({
    required String email,
    required String password,
    String? displayName,
  }) async {
    try {
      final res = await _client.auth.signUp(
        email: email.trim(),
        password: password,
        data: displayName != null && displayName.trim().isNotEmpty
            ? {'display_name': displayName.trim()}
            : null,
        emailRedirectTo: AppConfig.authCallbackUrl,
      );
      return res;
    } on AuthException catch (e) {
      throw _mapAuthException(e);
    } catch (e) {
      throw 'Đã xảy ra lỗi khi đăng ký: $e';
    }
  }

  /// Đăng nhập bằng Email và Mật khẩu
  Future<AuthResponse> signInWithEmail({
    required String email,
    required String password,
  }) async {
    try {
      final res = await _client.auth.signInWithPassword(
        email: email.trim(),
        password: password,
      );
      return res;
    } on AuthException catch (e) {
      throw _mapAuthException(e);
    } catch (e) {
      throw 'Đã xảy ra lỗi khi đăng nhập: $e';
    }
  }

  /// Gửi email đặt lại mật khẩu (khôi phục mật khẩu)
  Future<void> sendPasswordResetEmail({required String email}) async {
    try {
      await _client.auth.resetPasswordForEmail(
        email.trim(),
        redirectTo: AppConfig.authCallbackUrl,
      );
    } on AuthException catch (e) {
      throw _mapAuthException(e);
    } catch (e) {
      throw 'Đã xảy ra lỗi khi gửi yêu cầu đặt lại mật khẩu: $e';
    }
  }

  /// Cập nhật mật khẩu mới cho người dùng đang đăng nhập
  Future<UserResponse> updatePassword({required String newPassword}) async {
    try {
      return await _client.auth.updateUser(
        UserAttributes(password: newPassword),
      );
    } on AuthException catch (e) {
      throw _mapAuthException(e);
    } catch (e) {
      throw 'Đã xảy ra lỗi khi đổi mật khẩu: $e';
    }
  }

  /// Đăng xuất khỏi phiên hiện tại
  Future<void> signOut() async {
    try {
      await _client.auth.signOut();
    } on AuthException catch (e) {
      throw _mapAuthException(e);
    } catch (e) {
      throw 'Đã xảy ra lỗi khi đăng xuất: $e';
    }
  }

  /// Chuyển đổi mã lỗi Supabase thành thông điệp tiếng Việt thân thiện
  String _mapAuthException(AuthException e) {
    final msg = e.message.toLowerCase();
    if (msg.contains('invalid login credentials') ||
        msg.contains('invalid grant')) {
      return 'Email hoặc mật khẩu không chính xác.';
    }
    if (msg.contains('email not confirmed')) {
      return 'Email chưa được xác nhận. Vui lòng kiểm tra hộp thư đến của bạn.';
    }
    if (msg.contains('user already registered') ||
        msg.contains('already exists')) {
      return 'Email này đã được đăng ký tài khoản. Vui lòng chọn Đăng nhập.';
    }
    if (msg.contains('password should be at least')) {
      return 'Mật khẩu phải chứa ít nhất 6 ký tự.';
    }
    if (msg.contains('rate limit') || msg.contains('too many requests')) {
      return 'Bạn thao tác quá nhanh. Vui lòng đợi trong giây lát rồi thử lại.';
    }
    return e.message;
  }
}
