import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart' show AuthState, User;

import 'package:badminton_hub/data/auth_repository.dart';
import 'package:badminton_hub/data/club_repository.dart';
import 'package:badminton_hub/data/session_repository.dart';
import 'package:badminton_hub/models/club.dart';
import 'package:badminton_hub/models/session.dart';
import 'package:badminton_hub/providers/auth_provider.dart';
import 'package:badminton_hub/providers/club_provider.dart';
import 'package:badminton_hub/providers/session_provider.dart';
import 'package:badminton_hub/screens/session_history_screen.dart';

class MockAuthRepository extends Mock implements AuthRepository {}

class MockClubRepository extends Mock implements ClubRepository {}

class MockSessionRepository extends Mock implements SessionRepository {}

void main() {
  late MockAuthRepository authRepository;
  late MockClubRepository clubRepository;
  late MockSessionRepository sessionRepository;
  late StreamController<AuthState> authStateController;
  late AuthProvider authProvider;
  late ClubProvider clubProvider;
  late SessionProvider sessionProvider;

  const club = Club(id: 'c1', ownerUserId: 'u1', name: 'CLB A');

  const completed = Session(
    id: 'h1',
    title: 'Buổi đã xong',
    lifecycle: 'completed',
    capacity: 8,
    confirmedCount: 6,
    venueName: 'Sân B',
    clubName: 'CLB A',
  );

  const cancelled = Session(
    id: 'h2',
    title: 'Buổi đã huỷ',
    lifecycle: 'cancelled',
    capacity: 8,
  );

  User user() => User(
    id: 'u1',
    appMetadata: {},
    userMetadata: {},
    aud: 'authenticated',
    createdAt: '2026-10-15',
  );

  setUpAll(() {
    registerFallbackValue(const SessionHistoryFilter());
  });

  setUp(() {
    authRepository = MockAuthRepository();
    clubRepository = MockClubRepository();
    sessionRepository = MockSessionRepository();
    authStateController = StreamController<AuthState>.broadcast();
    when(() => authRepository.authStateChanges)
        .thenAnswer((_) => authStateController.stream);
    when(() => authRepository.currentUser).thenReturn(user());
    authProvider = AuthProvider(repository: authRepository);
    clubProvider = ClubProvider(repository: clubRepository, auth: authProvider);
    sessionProvider = SessionProvider(
      repository: sessionRepository,
      auth: authProvider,
    );
  });

  tearDown(() {
    sessionProvider.dispose();
    clubProvider.dispose();
    authProvider.dispose();
    authStateController.close();
  });

  void stubClubs() {
    when(() => clubRepository.listMyClubs()).thenAnswer((_) async => [club]);
  }

  Widget build() {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
        ChangeNotifierProvider<ClubProvider>.value(value: clubProvider),
        ChangeNotifierProvider<SessionProvider>.value(value: sessionProvider),
      ],
      child: const MaterialApp(home: SessionHistoryScreen()),
    );
  }

  Future<void> pumpScreen(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 3200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(build());
  }

  testWidgets('hiện lịch sử, giữ lifecycle và nối trang kế', (tester) async {
    stubClubs();
    final offsets = <int>[];
    when(
      () => sessionRepository.listMySessionHistory(
        filter: any(named: 'filter'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((invocation) async {
      final offset = invocation.namedArguments[#offset] as int;
      offsets.add(offset);
      return offset == 0
          ? const SessionHistoryPage(
              sessions: [completed, cancelled],
              limit: 20,
              offset: 0,
              hasMoreOverride: true,
            )
          : const SessionHistoryPage(
              sessions: [Session(id: 'h3', title: 'Buổi cũ hơn')],
              limit: 20,
              offset: 2,
            );
    });

    await pumpScreen(tester);
    await tester.pumpAndSettle();

    expect(find.text('Buổi đã xong'), findsOneWidget);
    expect(find.text('Buổi đã huỷ'), findsOneWidget);
    expect(find.text('Đã kết thúc'), findsOneWidget);
    expect(find.text('Đã huỷ'), findsOneWidget);
    expect(find.byKey(const Key('bh07c-history-load-more')), findsOneWidget);

    await tester.tap(find.byKey(const Key('bh07c-history-load-more')));
    await tester.pumpAndSettle();

    expect(find.text('Buổi cũ hơn'), findsOneWidget);
    expect(offsets, [0, 2]);
    expect(find.byKey(const Key('bh07c-history-load-more')), findsNothing);
  });

  testWidgets('lỗi lịch sử có thông báo và retry', (tester) async {
    stubClubs();
    when(
      () => sessionRepository.listMySessionHistory(
        filter: any(named: 'filter'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenThrow(Exception('offline'));

    await pumpScreen(tester);
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('bh07c-history-error')), findsOneWidget);
    expect(find.text('Không tải được lịch sử'), findsOneWidget);

    when(
      () => sessionRepository.listMySessionHistory(
        filter: any(named: 'filter'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer(
      (_) async =>
          const SessionHistoryPage(sessions: [completed], limit: 20, offset: 0),
    );
    await tester.tap(find.text('Thử lại'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('bh07c-history-error')), findsNothing);
    expect(find.text('Buổi đã xong'), findsOneWidget);
  });

  testWidgets('lọc theo CLB gửi đúng filter và empty có xoá lọc', (
    tester,
  ) async {
    stubClubs();
    when(
      () => sessionRepository.listMySessionHistory(
        filter: any(named: 'filter'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) async => const SessionHistoryPage(limit: 20, offset: 0));

    await pumpScreen(tester);
    await tester.pumpAndSettle();
    expect(find.text('Chưa có buổi nào'), findsOneWidget);

    await tester.tap(find.byKey(const Key('bh07c-history-club-filter')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('CLB A').last);
    await tester.pumpAndSettle();

    verify(
      () => sessionRepository.listMySessionHistory(
        filter: const SessionHistoryFilter(clubId: 'c1'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).called(1);
    expect(find.text('Xoá bộ lọc'), findsOneWidget);
  });
}
