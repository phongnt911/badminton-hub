import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide Session;

import 'package:badminton_hub/data/session_repository.dart';
import 'package:badminton_hub/models/session.dart';
import 'package:badminton_hub/providers/auth_provider.dart';
import 'package:badminton_hub/providers/session_provider.dart';
import 'package:badminton_hub/screens/home_screen.dart';

class MockSessionRepository extends Mock implements SessionRepository {}

class FakeAuth extends Mock implements AuthProvider {
  final callbacks = <VoidCallback>[];
  User? user;

  @override
  User? get currentUser => user;

  @override
  bool get isAuthenticated => user != null;

  @override
  void addListener(VoidCallback listener) => callbacks.add(listener);

  @override
  void removeListener(VoidCallback listener) => callbacks.remove(listener);

  void changeUser(String? id) {
    user = id == null
        ? null
        : User(
            id: id,
            appMetadata: {},
            userMetadata: {},
            aud: 'authenticated',
            createdAt: '2026-10-15',
          );
    for (final listener in List<VoidCallback>.of(callbacks)) {
      listener();
    }
  }
}

void main() {
  late MockSessionRepository sessionRepository;
  late FakeAuth auth;
  late SessionProvider sessionProvider;

  const managedSession = Session(
    id: 's2',
    title: 'Buổi của tôi',
    capacity: 8,
    lifecycle: 'published',
    canManage: true,
  );

  setUp(() {
    sessionRepository = MockSessionRepository();
    auth = FakeAuth();
    sessionProvider = SessionProvider(
      repository: sessionRepository,
      auth: auth,
    );
  });

  tearDown(() {
    sessionProvider.dispose();
  });

  Widget build() {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthProvider>.value(value: auth),
        ChangeNotifierProvider<SessionProvider>.value(value: sessionProvider),
      ],
      child: const MaterialApp(home: HomeScreen()),
    );
  }

  testWidgets('guest thấy ghi chú khách, không có nút tạo buổi',
      (tester) async {
    await tester.pumpWidget(build());
    await tester.pumpAndSettle();

    expect(find.text('Bạn đang xem dưới dạng khách'), findsOneWidget);
    expect(find.text('Khám phá buổi công khai'), findsOneWidget);
    expect(find.byKey(const Key('bh07c-history-entry')), findsNothing);
    expect(find.text('TẠO BUỔI'), findsNothing);
  });

  testWidgets('host thấy danh sách buổi quản lý và nút tạo buổi',
      (tester) async {
    when(() => sessionRepository.listMySessions(
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        )).thenAnswer((_) async => [managedSession]);

    auth.changeUser('u1');

    await tester.pumpWidget(build());
    await tester.pumpAndSettle();

    expect(find.text('TẠO BUỔI'), findsOneWidget);
    expect(find.text('Buổi của tôi'), findsWidgets);
    expect(find.byKey(const Key('bh07c-history-entry')), findsOneWidget);
    expect(find.text('Lịch sử buổi'), findsOneWidget);
  });
}
