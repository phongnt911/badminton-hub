import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:badminton_hub/data/auth_repository.dart';

class MockSupabaseClient extends Mock implements SupabaseClient {}
class MockGoTrueClient extends Mock implements GoTrueClient {}
class MockUser extends Mock implements User {}
class MockSession extends Mock implements Session {}
class MockAuthResponse extends Mock implements AuthResponse {}
class MockUserResponse extends Mock implements UserResponse {}

void main() {
  late MockSupabaseClient mockSupabaseClient;
  late MockGoTrueClient mockAuth;
  late AuthRepository repository;

  setUpAll(() {
    registerFallbackValue(UserAttributes());
  });

  setUp(() {
    mockSupabaseClient = MockSupabaseClient();
    mockAuth = MockGoTrueClient();
    when(() => mockSupabaseClient.auth).thenReturn(mockAuth);

    repository = AuthRepository(client: mockSupabaseClient);
  });

  group('AuthRepository Tests', () {
    test('currentUser và isAuthenticated phản ánh đúng trạng thái', () {
      final mockUser = MockUser();
      when(() => mockAuth.currentUser).thenReturn(mockUser);

      expect(repository.currentUser, equals(mockUser));
      expect(repository.isAuthenticated, isTrue);

      when(() => mockAuth.currentUser).thenReturn(null);
      expect(repository.currentUser, isNull);
      expect(repository.isAuthenticated, isFalse);
    });

    test('currentSession phản ánh đúng phiên', () {
      final mockSession = MockSession();
      when(() => mockAuth.currentSession).thenReturn(mockSession);
      expect(repository.currentSession, equals(mockSession));
    });

    test('signInWithEmail thành công trả về AuthResponse', () async {
      final mockResponse = MockAuthResponse();
      when(() => mockAuth.signInWithPassword(
            email: 'test@example.com',
            password: 'password123',
          )).thenAnswer((_) async => mockResponse);

      final res = await repository.signInWithEmail(
        email: 'test@example.com',
        password: 'password123',
      );

      expect(res, equals(mockResponse));
      verify(() => mockAuth.signInWithPassword(
            email: 'test@example.com',
            password: 'password123',
          )).called(1);
    });

    test('signInWithEmail thất bại dịch lỗi thân thiện tiếng Việt', () async {
      when(() => mockAuth.signInWithPassword(
            email: 'test@example.com',
            password: 'wrongpassword',
          )).thenThrow(const AuthException('Invalid login credentials'));

      expect(
        () => repository.signInWithEmail(
          email: 'test@example.com',
          password: 'wrongpassword',
        ),
        throwsA(equals('Email hoặc mật khẩu không chính xác.')),
      );
    });

    test('signUpWithEmail thành công gọi signUp với dữ liệu metadata', () async {
      final mockResponse = MockAuthResponse();
      when(() => mockAuth.signUp(
            email: 'newuser@example.com',
            password: 'password123',
            data: any(named: 'data'),
            emailRedirectTo: any(named: 'emailRedirectTo'),
          )).thenAnswer((_) async => mockResponse);

      final res = await repository.signUpWithEmail(
        email: 'newuser@example.com',
        password: 'password123',
        displayName: 'Nguyễn Văn A',
      );

      expect(res, equals(mockResponse));
      verify(() => mockAuth.signUp(
            email: 'newuser@example.com',
            password: 'password123',
            data: {'display_name': 'Nguyễn Văn A'},
            emailRedirectTo: any(named: 'emailRedirectTo'),
          )).called(1);
    });

    test('signUpWithEmail báo lỗi khi email đã tồn tại', () async {
      when(() => mockAuth.signUp(
            email: 'existing@example.com',
            password: 'password123',
            data: any(named: 'data'),
            emailRedirectTo: any(named: 'emailRedirectTo'),
          )).thenThrow(const AuthException('User already registered'));

      expect(
        () => repository.signUpWithEmail(
          email: 'existing@example.com',
          password: 'password123',
        ),
        throwsA(equals('Email này đã được đăng ký tài khoản. Vui lòng chọn Đăng nhập.')),
      );
    });

    test('sendPasswordResetEmail gọi resetPasswordForEmail', () async {
      when(() => mockAuth.resetPasswordForEmail(
            'reset@example.com',
            redirectTo: any(named: 'redirectTo'),
          )).thenAnswer((_) async {});

      await repository.sendPasswordResetEmail(email: 'reset@example.com');

      verify(() => mockAuth.resetPasswordForEmail(
            'reset@example.com',
            redirectTo: any(named: 'redirectTo'),
          )).called(1);
    });

    test('updatePassword gọi updateUser với mật khẩu mới', () async {
      final mockResponse = MockUserResponse();
      when(() => mockAuth.updateUser(any())).thenAnswer((_) async => mockResponse);

      final res = await repository.updatePassword(newPassword: 'newpass123');

      expect(res, equals(mockResponse));
      verify(() => mockAuth.updateUser(any())).called(1);
    });

    test('signOut gọi auth.signOut', () async {
      when(() => mockAuth.signOut()).thenAnswer((_) async {});

      await repository.signOut();

      verify(() => mockAuth.signOut()).called(1);
    });

    test('authStateChanges stream hoạt động chuẩn', () async {
      final controller = StreamController<AuthState>();
      when(() => mockAuth.onAuthStateChange).thenAnswer((_) => controller.stream);

      expect(repository.authStateChanges, emitsInOrder([]));
      await controller.close();
    });
  });
}
