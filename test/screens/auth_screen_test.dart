import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:badminton_hub/data/auth_repository.dart';
import 'package:badminton_hub/providers/auth_provider.dart';
import 'package:badminton_hub/screens/auth_screen.dart';

class MockAuthRepository extends Mock implements AuthRepository {}
class MockUser extends Mock implements User {}
class MockAuthResponse extends Mock implements AuthResponse {}

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

  Widget buildTestableWidget(Widget child) {
    return ChangeNotifierProvider<AuthProvider>.value(
      value: authProvider,
      child: MaterialApp(
        home: child,
      ),
    );
  }

  group('AuthScreen Widget Tests', () {
    testWidgets('Hiển thị tab Đăng Nhập mặc định với các trường nhập liệu',
        (tester) async {
      await tester.pumpWidget(buildTestableWidget(const AuthScreen()));

      expect(find.text('Đăng Nhập'), findsWidgets);
      expect(find.text('Đăng Ký'), findsOneWidget);
      expect(find.text('Khôi Phục'), findsOneWidget);

      expect(find.byKey(const Key('login_email_field')), findsOneWidget);
      expect(find.byKey(const Key('login_password_field')), findsOneWidget);
      expect(find.byKey(const Key('login_submit_button')), findsOneWidget);
    });

    testWidgets('Chuyển tab sang Đăng Ký hiển thị các trường đăng ký',
        (tester) async {
      await tester.pumpWidget(buildTestableWidget(const AuthScreen()));

      // Nhấp vào tab Đăng Ký
      await tester.tap(find.text('Đăng Ký'));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('register_name_field')), findsOneWidget);
      expect(find.byKey(const Key('register_email_field')), findsOneWidget);
      expect(find.byKey(const Key('register_password_field')), findsOneWidget);
      expect(find.byKey(const Key('register_confirm_password_field')), findsOneWidget);
      expect(find.byKey(const Key('register_submit_button')), findsOneWidget);
    });

    testWidgets('Báo lỗi SnackBar khi nhấn Đăng Nhập mà để trống trường dữ liệu',
        (tester) async {
      await tester.pumpWidget(buildTestableWidget(const AuthScreen()));

      // Bấm nút đăng nhập ngay khi chưa điền thông tin
      await tester.tap(find.byKey(const Key('login_submit_button')));
      await tester.pump();

      expect(find.text('Vui lòng nhập đầy đủ email và mật khẩu.'), findsOneWidget);
    });

    testWidgets('Đăng nhập thành công kích hoạt callback onSuccess / route return',
        (tester) async {
      bool callbackInvoked = false;
      final mockUser = MockUser();
      final mockResponse = MockAuthResponse();
      when(() => mockResponse.user).thenReturn(mockUser);
      when(() => mockRepository.signInWithEmail(
            email: 'player@example.com',
            password: 'secretPassword',
          )).thenAnswer((_) async => mockResponse);

      await tester.pumpWidget(buildTestableWidget(
        AuthScreen(
          onSuccess: () {
            callbackInvoked = true;
          },
        ),
      ));

      // Điền thông tin đăng nhập
      await tester.enterText(
        find.byKey(const Key('login_email_field')),
        'player@example.com',
      );
      await tester.enterText(
        find.byKey(const Key('login_password_field')),
        'secretPassword',
      );

      // Bấm nút đăng nhập
      await tester.tap(find.byKey(const Key('login_submit_button')));
      await tester.pumpAndSettle();

      expect(callbackInvoked, isTrue);
      expect(find.text('Đăng nhập thành công!'), findsOneWidget);
    });
  });
}
