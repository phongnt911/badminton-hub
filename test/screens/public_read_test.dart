import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:badminton_hub/core/auth_guard.dart';
import 'package:badminton_hub/data/auth_repository.dart';
import 'package:badminton_hub/providers/auth_provider.dart';
import 'package:badminton_hub/screens/account_screen.dart';

class MockAuthRepository extends Mock implements AuthRepository {}
class MockUser extends Mock implements User {}

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

  group('Public Read & Auth Guard Tests', () {
    testWidgets(
        'Người dùng chưa đăng nhập mở AccountScreen thấy giao diện khách và nút Đăng Nhập',
        (tester) async {
      await tester.pumpWidget(buildTestableWidget(const AccountScreen()));

      expect(find.text('Bạn đang xem dưới dạng khách'), findsOneWidget);
      expect(find.text('Đăng Nhập / Đăng Ký'), findsOneWidget);
      expect(find.byKey(const Key('account_login_button')), findsOneWidget);
    });

    testWidgets(
        'Người dùng đã đăng nhập mở AccountScreen thấy thông tin tài khoản và nút Đăng Xuất',
        (tester) async {
      final mockUser = MockUser();
      when(() => mockUser.email).thenReturn('host@badminton.vn');
      when(() => mockUser.userMetadata).thenReturn({'display_name': 'Host Khánh Hòa'});
      when(() => mockRepository.currentUser).thenReturn(mockUser);

      // Tạo provider mới với user đã đăng nhập
      final loggedInProvider = AuthProvider(repository: mockRepository);

      await tester.pumpWidget(
        ChangeNotifierProvider<AuthProvider>.value(
          value: loggedInProvider,
          child: const MaterialApp(home: AccountScreen()),
        ),
      );

      expect(find.text('Host Khánh Hòa'), findsOneWidget);
      expect(find.text('host@badminton.vn'), findsOneWidget);
      expect(find.text('Đổi mật khẩu'), findsOneWidget);
      expect(find.text('Đăng xuất'), findsOneWidget);

      loggedInProvider.dispose();
    });

    testWidgets(
        'AuthGuard chặn người chưa đăng nhập và hiển thị thông báo yêu cầu đăng nhập',
        (tester) async {
      await tester.pumpWidget(buildTestableWidget(
        const AuthGuard(
          child: Text('Nội dung bảo vệ chỉ cho Host'),
        ),
      ));

      expect(find.text('Tính năng yêu cầu đăng nhập'), findsOneWidget);
      expect(find.text('Nội dung bảo vệ chỉ cho Host'), findsNothing);
    });

    testWidgets(
        'AuthGuard cho phép truy cập nội dung khi đã đăng nhập',
        (tester) async {
      final mockUser = MockUser();
      when(() => mockRepository.currentUser).thenReturn(mockUser);
      final loggedInProvider = AuthProvider(repository: mockRepository);

      await tester.pumpWidget(
        ChangeNotifierProvider<AuthProvider>.value(
          value: loggedInProvider,
          child: const MaterialApp(
            home: AuthGuard(
              child: Text('Nội dung bảo vệ chỉ cho Host'),
            ),
          ),
        ),
      );

      expect(find.text('Nội dung bảo vệ chỉ cho Host'), findsOneWidget);
      expect(find.text('Tính năng yêu cầu đăng nhập'), findsNothing);

      loggedInProvider.dispose();
    });
  });
}
