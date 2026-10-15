import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide Session;

import 'package:badminton_hub/data/auth_repository.dart';
import 'package:badminton_hub/data/session_repository.dart';
import 'package:badminton_hub/models/session.dart';
import 'package:badminton_hub/providers/auth_provider.dart';
import 'package:badminton_hub/providers/session_provider.dart';
import 'package:badminton_hub/screens/auth_screen.dart';
import 'package:badminton_hub/main.dart';
import 'package:badminton_hub/screens/session_detail_screen.dart';

class MockAuthRepository extends Mock implements AuthRepository {}

class MockSessionRepository extends Mock implements SessionRepository {}

void main() {
  late MockAuthRepository authRepository;
  late MockSessionRepository sessionRepository;
  late StreamController<AuthState> authStateController;
  late AuthProvider authProvider;
  late SessionProvider sessionProvider;

  const publicSession = Session(
    id: 's1',
    title: 'Buổi công khai',
    capacity: 8,
    lifecycle: 'published',
    visibility: 'public',
    canManage: false,
    confirmedCount: 2,
  );

  const draftSession = Session(
    id: 's2',
    title: 'Buổi nháp của tôi',
    capacity: 8,
    lifecycle: 'draft',
    canManage: true,
    version: 1,
  );

  setUpAll(() {
    registerFallbackValue(DateTime(2020));
  });

  setUp(() {
    authRepository = MockAuthRepository();
    sessionRepository = MockSessionRepository();
    authStateController = StreamController<AuthState>.broadcast();
    when(() => authRepository.authStateChanges)
        .thenAnswer((_) => authStateController.stream);
    when(() => authRepository.currentUser).thenReturn(null);
    authProvider = AuthProvider(repository: authRepository);
    sessionProvider = SessionProvider(
      repository: sessionRepository,
      auth: authProvider,
    );
  });

  tearDown(() {
    sessionProvider.dispose();
    authProvider.dispose();
    authStateController.close();
  });

  Widget build(Widget child) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
        ChangeNotifierProvider<SessionProvider>.value(value: sessionProvider),
      ],
      child: MaterialApp(home: child),
    );
  }

  testWidgets('application opens initial session URL and returns after login', (
    tester,
  ) async {
    const id = '11111111-2222-3333-4444-555555555555';
    tester.platformDispatcher.defaultRouteNameTestValue = '/sessions/$id';
    addTearDown(tester.platformDispatcher.clearDefaultRouteNameTestValue);
    when(() => sessionRepository.getSessionDetail(id))
        .thenAnswer((_) async => publicSession);
    final user = User(
      id: 'u1',
      appMetadata: {},
      userMetadata: {},
      aud: 'authenticated',
      createdAt: '2026-10-15',
    );
    when(
      () => authRepository.signInWithEmail(
        email: 'a@b.com',
        password: 'password',
      ),
    ).thenAnswer((_) async => AuthResponse(user: user));
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
          ChangeNotifierProvider<SessionProvider>.value(value: sessionProvider),
        ],
        child: const BadmintonHubApp(),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byType(SessionDetailScreen), findsOneWidget);
    expect(
      tester
          .widget<SessionDetailScreen>(find.byType(SessionDetailScreen))
          .sessionId,
      id,
    );
    await tester.tap(find.text('Đăng nhập để đăng ký'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('login_email_field')),
      'a@b.com',
    );
    await tester.enterText(
      find.byKey(const Key('login_password_field')),
      'password',
    );
    await tester.tap(find.byKey(const Key('login_submit_button')));
    await tester.pumpAndSettle();
    expect(find.byType(AuthScreen), findsNothing);
    expect(
      tester
          .widget<SessionDetailScreen>(find.byType(SessionDetailScreen))
          .sessionId,
      id,
    );
    expect(find.text('Buổi công khai'), findsWidgets);
  });

  testWidgets('roster error is not empty state and retry recovers', (
    tester,
  ) async {
    when(() => sessionRepository.getSessionDetail('s2'))
        .thenAnswer((_) async => draftSession);
    when(
      () => sessionRepository.listSessionPlayers(
        's2',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenThrow(Exception('offline'));
    await tester.pumpWidget(build(const SessionDetailScreen(sessionId: 's2')));
    await tester.pumpAndSettle();
    expect(find.text('Không thể tải danh sách đăng ký.'), findsOneWidget);
    expect(find.text('Chưa có ai đăng ký.'), findsNothing);
    when(
      () => sessionRepository.listSessionPlayers(
        's2',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) async => []);
    await tester.ensureVisible(find.text('Thử lại danh sách'));
    await tester.tap(find.text('Thử lại danh sách'));
    await tester.pumpAndSettle();
    expect(find.text('Không thể tải danh sách đăng ký.'), findsNothing);
    expect(find.text('Chưa có ai đăng ký.'), findsOneWidget);
  });

  testWidgets(
    'guest mở link công khai, được mời đăng nhập và giữ đúng route quay lại',
    (tester) async {
      when(() => sessionRepository.getSessionDetail('s1'))
          .thenAnswer((_) async => publicSession);

      await tester.pumpWidget(
        build(const SessionDetailScreen(sessionId: 's1')),
      );
      await tester.pumpAndSettle();

      expect(find.text('Buổi công khai'), findsOneWidget);
      expect(find.text('Đăng nhập để đăng ký'), findsOneWidget);

      await tester.tap(find.text('Đăng nhập để đăng ký'));
      await tester.pumpAndSettle();

      final authScreen = tester.widget<AuthScreen>(find.byType(AuthScreen));
      expect(authScreen.returnRoute, '/sessions/s1');
    },
  );

  testWidgets('host thấy nút Công bố cho bản nháp và gọi publish', (
    tester,
  ) async {
    when(() => sessionRepository.getSessionDetail('s2'))
        .thenAnswer((_) async => draftSession);
    when(
      () => sessionRepository.listSessionPlayers(
        's2',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) async => const []);
    when(
      () => sessionRepository.listMySessions(
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) async => [draftSession]);
    when(
      () => sessionRepository.setSessionLifecycle(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        action: any(named: 'action'),
      ),
    ).thenAnswer((_) async => draftSession);

    await tester.pumpWidget(build(const SessionDetailScreen(sessionId: 's2')));
    await tester.pumpAndSettle();

    expect(find.text('Công bố'), findsOneWidget);

    await tester.tap(find.text('Công bố'));
    await tester.pumpAndSettle();

    verify(
      () => sessionRepository.setSessionLifecycle(
        requestId: any(named: 'requestId'),
        sessionId: 's2',
        action: 'publish',
      ),
    ).called(1);
  });

  testWidgets('lỗi cần đăng nhập hiển thị nút Đăng nhập và Thử lại', (
    tester,
  ) async {
    when(() => sessionRepository.getSessionDetail('s1'))
        .thenThrow(Exception('PostgrestException(UNAUTHENTICATED: raw)'));

    await tester.pumpWidget(build(const SessionDetailScreen(sessionId: 's1')));
    await tester.pumpAndSettle();

    expect(
      find.text('Bạn cần đăng nhập để thực hiện thao tác này.'),
      findsOneWidget,
    );
    expect(find.text('Đăng nhập'), findsOneWidget);
    expect(find.text('Thử lại'), findsOneWidget);
  });

  testWidgets('lỗi khác chỉ hiển thị Thử lại', (tester) async {
    when(() => sessionRepository.getSessionDetail('s1'))
        .thenThrow(Exception('NOT_FOUND: raw'));

    await tester.pumpWidget(build(const SessionDetailScreen(sessionId: 's1')));
    await tester.pumpAndSettle();

    expect(find.text('Không tìm thấy dữ liệu yêu cầu.'), findsOneWidget);
    expect(find.text('Thử lại'), findsOneWidget);
    expect(find.text('Đăng nhập'), findsNothing);
  });

  // --- BH-05 -------------------------------------------------------------- //

  Widget buildAuthed(
    Widget child,
    AuthProvider auth,
    SessionProvider session,
  ) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthProvider>.value(value: auth),
        ChangeNotifierProvider<SessionProvider>.value(value: session),
      ],
      child: MaterialApp(home: child),
    );
  }

  ({AuthProvider auth, SessionProvider session}) authedProviders() {
    final user = User(
      id: 'u1',
      appMetadata: {},
      userMetadata: {},
      aud: 'authenticated',
      createdAt: '2026-10-15',
    );
    when(() => authRepository.currentUser).thenReturn(user);
    final auth = AuthProvider(repository: authRepository);
    final session = SessionProvider(repository: sessionRepository, auth: auth);
    addTearDown(session.dispose);
    addTearDown(auth.dispose);
    return (auth: auth, session: session);
  }

  testWidgets('player chưa đăng ký bấm Đăng ký tham gia gọi requestJoinSession', (
    tester,
  ) async {
    final p = authedProviders();
    when(() => sessionRepository.getSessionDetail('s1'))
        .thenAnswer((_) async => publicSession);
    when(
      () => sessionRepository.requestJoinSession(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        contact: any(named: 'contact'),
      ),
    ).thenAnswer(
      (_) async => const RegistrationResult(
        playerId: 'p1',
        sessionId: 's1',
        registrationStatus: 'pending',
        confirmedCount: 2,
        capacity: 8,
        seatsLeft: 6,
      ),
    );

    await tester.pumpWidget(
      buildAuthed(const SessionDetailScreen(sessionId: 's1'), p.auth, p.session),
    );
    await tester.pumpAndSettle();

    expect(find.text('Đăng ký tham gia'), findsOneWidget);
    await tester.tap(find.text('Đăng ký tham gia'));
    await tester.pumpAndSettle();

    verify(
      () => sessionRepository.requestJoinSession(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        contact: any(named: 'contact'),
      ),
    ).called(1);
    expect(find.text('Đã gửi yêu cầu tham gia buổi chơi.'), findsOneWidget);
  });

  testWidgets('player trong danh sách chờ có lời mời thấy nút Chấp nhận lời mời', (
    tester,
  ) async {
    final p = authedProviders();
    const waitlisted = Session(
      id: 's1',
      title: 'Buổi chờ',
      capacity: 8,
      lifecycle: 'published',
      confirmedCount: 8,
      myRegistration: SessionRegistration(
        playerId: 'p1',
        registrationStatus: 'waitlisted',
      ),
    );
    when(() => sessionRepository.getSessionDetail('s1'))
        .thenAnswer((_) async => waitlisted);
    when(() => sessionRepository.getMyWaitlistInvitation('s1')).thenAnswer(
      (_) async => const WaitlistInvitation(
        invitationId: 'i1',
        playerId: 'p1',
        sessionId: 's1',
      ),
    );
    when(
      () => sessionRepository.acceptWaitlistInvitation(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        invitationId: any(named: 'invitationId'),
        consentNote: any(named: 'consentNote'),
      ),
    ).thenAnswer(
      (_) async => const RegistrationResult(
        playerId: 'p1',
        sessionId: 's1',
        registrationStatus: 'confirmed',
      ),
    );

    await tester.pumpWidget(
      buildAuthed(const SessionDetailScreen(sessionId: 's1'), p.auth, p.session),
    );
    await tester.pumpAndSettle();

    expect(find.text('Chấp nhận lời mời'), findsOneWidget);
    await tester.tap(find.text('Chấp nhận lời mời'));
    await tester.pumpAndSettle();

    verify(
      () => sessionRepository.acceptWaitlistInvitation(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        invitationId: 'i1',
        consentNote: any(named: 'consentNote'),
      ),
    ).called(1);
  });

  testWidgets('player confirmed tự huỷ đăng ký sau khi xác nhận', (tester) async {
    final p = authedProviders();
    const confirmed = Session(
      id: 's1',
      title: 'Buổi',
      capacity: 8,
      lifecycle: 'published',
      confirmedCount: 1,
      myRegistration: SessionRegistration(
        playerId: 'p1',
        registrationStatus: 'confirmed',
      ),
    );
    when(() => sessionRepository.getSessionDetail('s1'))
        .thenAnswer((_) async => confirmed);
    when(
      () => sessionRepository.cancelRegistration(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        playerId: any(named: 'playerId'),
        reason: any(named: 'reason'),
      ),
    ).thenAnswer(
      (_) async => const RegistrationResult(
        playerId: 'p1',
        sessionId: 's1',
        registrationStatus: 'cancelled',
      ),
    );

    await tester.pumpWidget(
      buildAuthed(const SessionDetailScreen(sessionId: 's1'), p.auth, p.session),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('Đã xác nhận'), findsWidgets);
    await tester.tap(find.text('Huỷ đăng ký'));
    await tester.pumpAndSettle();
    expect(
      find.text('Bạn chắc chắn muốn huỷ đăng ký buổi này?'),
      findsOneWidget,
    );
    await tester.tap(find.text('Đồng ý'));
    await tester.pumpAndSettle();

    verify(
      () => sessionRepository.cancelRegistration(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        playerId: 'p1',
        reason: any(named: 'reason'),
      ),
    ).called(1);
  });

  testWidgets('host duyệt pending gọi decide_registration', (tester) async {
    const publishedManaged = Session(
      id: 's2',
      title: 'Buổi của tôi',
      capacity: 8,
      lifecycle: 'published',
      canManage: true,
      version: 1,
    );
    when(() => sessionRepository.getSessionDetail('s2'))
        .thenAnswer((_) async => publishedManaged);
    when(
      () => sessionRepository.listSessionPlayers(
        's2',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer(
      (_) async => const [
        SessionPlayer(id: 'p1', displayName: 'An', registrationStatus: 'pending'),
      ],
    );
    when(
      () => sessionRepository.decideRegistration(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        playerId: any(named: 'playerId'),
        decision: any(named: 'decision'),
        reason: any(named: 'reason'),
      ),
    ).thenAnswer(
      (_) async => const RegistrationResult(
        playerId: 'p1',
        sessionId: 's2',
        registrationStatus: 'confirmed',
      ),
    );

    await tester.pumpWidget(build(const SessionDetailScreen(sessionId: 's2')));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('Duyệt'),
      300.0,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('Duyệt'));
    await tester.pumpAndSettle();

    verify(
      () => sessionRepository.decideRegistration(
        requestId: any(named: 'requestId'),
        sessionId: 's2',
        playerId: 'p1',
        decision: 'confirmed',
        reason: any(named: 'reason'),
      ),
    ).called(1);
  });

  testWidgets('lỗi mutation đăng ký hiển thị thông điệp và cho phép thử lại', (
    tester,
  ) async {
    final p = authedProviders();
    when(() => sessionRepository.getSessionDetail('s1'))
        .thenAnswer((_) async => publicSession);
    var attempts = 0;
    when(
      () => sessionRepository.requestJoinSession(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        contact: any(named: 'contact'),
      ),
    ).thenAnswer((invocation) async {
      attempts++;
      if (attempts == 1) throw Exception('CAPACITY_FULL: dữ liệu thô');
      return const RegistrationResult(
        playerId: 'p1',
        sessionId: 's1',
        registrationStatus: 'confirmed',
      );
    });

    await tester.pumpWidget(
      buildAuthed(const SessionDetailScreen(sessionId: 's1'), p.auth, p.session),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Đăng ký tham gia'));
    await tester.pumpAndSettle();
    expect(find.text('Buổi chơi đã đủ chỗ.'), findsOneWidget);

    // Để snackbar lỗi tự ẩn (xếp hàng) rồi thử lại.
    await tester.pump(const Duration(seconds: 5));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Đăng ký tham gia'), warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(
      find.text('Đã gửi yêu cầu tham gia buổi chơi.'),
      findsOneWidget,
    );
  });
}
