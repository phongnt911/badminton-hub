import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../data/auth_repository.dart';

/// Provider quản lý trạng thái xác thực trong ứng dụng
class AuthProvider extends ChangeNotifier {
  final AuthRepository _repository;
  StreamSubscription<AuthState>? _authSubscription;

  User? _currentUser;
  bool _isLoading = false;
  bool _isSubmitting = false;
  String? _errorMessage;
  String? _successMessage;

  AuthProvider({AuthRepository? repository})
    : _repository = repository ?? AuthRepository() {
    _currentUser = _repository.currentUser;
    _listenToAuthChanges();
  }

  User? get currentUser => _currentUser;
  bool get isAuthenticated => _currentUser != null;
  bool get isLoading => _isLoading;
  bool get isSubmitting => _isSubmitting;
  String? get errorMessage => _errorMessage;
  String? get successMessage => _successMessage;

  void _listenToAuthChanges() {
    _authSubscription = _repository.authStateChanges.listen((data) {
      _currentUser = data.session?.user ?? _repository.currentUser;
      notifyListeners();
    });
  }

  void clearMessages() {
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();
  }

  /// Đăng nhập bằng email và mật khẩu
  Future<bool> login(String email, String password) async {
    if (_isSubmitting) return false; // Chống bấm trùng nút

    _isSubmitting = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      final res = await _repository.signInWithEmail(
        email: email,
        password: password,
      );
      _currentUser = res.user;
      _successMessage = 'Đăng nhập thành công!';
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      return false;
    } finally {
      _isSubmitting = false;
      notifyListeners();
    }
  }

  /// Đăng ký tài khoản mới
  Future<bool> signUp(
    String email,
    String password, {
    String? displayName,
  }) async {
    if (_isSubmitting) return false;

    _isSubmitting = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      final res = await _repository.signUpWithEmail(
        email: email,
        password: password,
        displayName: displayName,
      );
      _currentUser = res.session?.user;
      _successMessage = 'Đăng ký thành công! Vui lòng kiểm tra email để xác nhận tài khoản (nếu có yêu cầu).';
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      return false;
    } finally {
      _isSubmitting = false;
      notifyListeners();
    }
  }

  /// Gửi yêu cầu đặt lại mật khẩu
  Future<bool> resetPassword(String email) async {
    if (_isSubmitting) return false;

    _isSubmitting = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      await _repository.sendPasswordResetEmail(email: email);
      _successMessage = 'Đã gửi liên kết khôi phục mật khẩu vào hộp thư của bạn. Vui lòng kiểm tra email.';
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      return false;
    } finally {
      _isSubmitting = false;
      notifyListeners();
    }
  }

  /// Cập nhật mật khẩu mới
  Future<bool> updatePassword(String newPassword) async {
    if (_isSubmitting) return false;

    _isSubmitting = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      await _repository.updatePassword(newPassword: newPassword);
      _successMessage = 'Đã cập nhật mật khẩu mới thành công!';
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      return false;
    } finally {
      _isSubmitting = false;
      notifyListeners();
    }
  }

  /// Đăng xuất khỏi hệ thống
  Future<void> logout() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      await _repository.signOut();
      _currentUser = null;
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _authSubscription?.cancel();
    super.dispose();
  }
}
