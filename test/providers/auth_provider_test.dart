import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:badminton_hub/data/auth_repository.dart';
import 'package:badminton_hub/providers/auth_provider.dart';

class MockAuthRepository extends Mock implements AuthRepository {}

class MockUser extends Mock implements User {}

class MockSession extends Mock implements Session {}

class MockAuthResponse extends Mock implements AuthResponse {}

class MockUserResponse extends Mock implements UserResponse {}

void main() {
  late MockAuthRepository mockRepository;
  late StreamController<AuthState> authStateController;
  late AuthProvider authProvider;

  setUp(() {
    mockRepository = MockAuthRepository();
    authStateController = StreamController<AuthState>.broadcast();
    when(() => mockRepository.authStateChanges)
        .thenAnswer((_) => authStateController.stream);
    when(() => mockRepository.currentUser).thenReturn(null);

    authProvider = AuthProvider(repository: mockRepository);
  });

  tearDown(() {
    authStateController.close();
    authProvider.dispose();
  });

  group('AuthProvider Tests', () {
    test('Trạng thái khởi tạo chính xác', () {
      expect(authProvider.currentUser, isNull);
      expect(authProvider.isAuthenticated, isFalse);
      expect(authProvider.isLoading, isFalse);
      expect(authProvider.isSubmitting, isFalse);
      expect(authProvider.errorMessage, isNull);
      expect(authProvider.successMessage, isNull);
    });

    test('login thành công cập nhật user và successMessage', () async {
      final mockUser = MockUser();
      final mockResponse = MockAuthResponse();
      when(() => mockResponse.user).thenReturn(mockUser);
      when(
        () => mockRepository.signInWithEmail(
          email: 'user@example.com',
          password: 'secretPassword',
        ),
      ).thenAnswer((_) async => mockResponse);

      final result = await authProvider.login(
        'user@example.com',
        'secretPassword',
      );

      expect(result, isTrue);
      expect(authProvider.currentUser, equals(mockUser));
      expect(authProvider.isAuthenticated, isTrue);
      expect(authProvider.isSubmitting, isFalse);
      expect(authProvider.errorMessage, isNull);
      expect(authProvider.successMessage, isNotNull);
    });

    test('login thất bại lưu errorMessage và trả về false', () async {
      when(
        () => mockRepository.signInWithEmail(
          email: 'user@example.com',
          password: 'wrongPassword',
        ),
      ).thenThrow('Email hoặc mật khẩu không chính xác.');

      final result = await authProvider.login(
        'user@example.com',
        'wrongPassword',
      );

      expect(result, isFalse);
      expect(authProvider.currentUser, isNull);
      expect(authProvider.isAuthenticated, isFalse);
      expect(authProvider.isSubmitting, isFalse);
      expect(authProvider.errorMessage, contains('không chính xác'));
    });

    test('chống bấm trùng nút login khi đang submitting', () async {
      final completer = Completer<AuthResponse>();
      when(
        () => mockRepository.signInWithEmail(
          email: 'user@example.com',
          password: 'password',
        ),
      ).thenAnswer((_) => completer.future);

      final firstCall = authProvider.login('user@example.com', 'password');
      expect(authProvider.isSubmitting, isTrue);

      // Lần gọi thứ hai khi lần một chưa xong
      final secondCall = await authProvider.login(
        'user@example.com',
        'password',
      );
      expect(secondCall, isFalse); // Bị chặn vì đang submitting

      completer.complete(MockAuthResponse());
      await firstCall;
      expect(authProvider.isSubmitting, isFalse);
    });

    test('signUp chưa confirm không tạo phiên đăng nhập', () async {
      final mockUser = MockUser();
      final mockResponse = MockAuthResponse();
      when(() => mockResponse.user).thenReturn(mockUser);
      when(
        () => mockRepository.signUpWithEmail(
          email: 'new@example.com',
          password: 'password123',
          displayName: 'Nguyễn Văn B',
        ),
      ).thenAnswer((_) async => mockResponse);

      final result = await authProvider.signUp(
        'new@example.com',
        'password123',
        displayName: 'Nguyễn Văn B',
      );

      expect(result, isTrue);
      expect(authProvider.currentUser, isNull);
      expect(authProvider.isAuthenticated, isFalse);
      expect(authProvider.successMessage, contains('Đăng ký thành công'));
    });

    test('signup with session authenticates', () async {
      final user = MockUser();
      final session = MockSession();
      when(() => session.user).thenReturn(user);
      when(() => mockRepository.signUpWithEmail(email: 'a@b.com', password: 'password', displayName: null))
          .thenAnswer((_) async => AuthResponse(user: user, session: session));
      expect(await authProvider.signUp('a@b.com', 'password'), isTrue);
      expect(authProvider.currentUser, user);
      expect(authProvider.isAuthenticated, isTrue);
    });

    test('resetPassword thành công cập nhật successMessage', () async {
      when(
        () => mockRepository.sendPasswordResetEmail(email: 'reset@example.com'),
      ).thenAnswer((_) async {});

      final result = await authProvider.resetPassword('reset@example.com');

      expect(result, isTrue);
      expect(
        authProvider.successMessage,
        contains('Đã gửi liên kết khôi phục'),
      );
    });

    test('updatePassword thành công cập nhật successMessage', () async {
      when(() => mockRepository.updatePassword(newPassword: 'newpass'))
          .thenAnswer((_) async => MockUserResponse());

      final result = await authProvider.updatePassword('newpass');

      expect(result, isTrue);
      expect(authProvider.successMessage, contains('Đã cập nhật mật khẩu mới'));
    });

    test('logout đặt lại currentUser về null', () async {
      when(() => mockRepository.signOut()).thenAnswer((_) async {});

      await authProvider.logout();

      expect(authProvider.currentUser, isNull);
      expect(authProvider.isAuthenticated, isFalse);
      expect(authProvider.isLoading, isFalse);
    });

    test('authStateChanges tự động cập nhật session user', () async {
      final mockUser = MockUser();
      final mockSession = MockSession();
      when(() => mockSession.user).thenReturn(mockUser);

      authStateController.add(AuthState(AuthChangeEvent.signedIn, mockSession));
      await pumpEventQueue();

      expect(authProvider.currentUser, equals(mockUser));
      expect(authProvider.isAuthenticated, isTrue);
    });
  });
}
