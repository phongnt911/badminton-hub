import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart'
    show AuthChangeEvent, AuthState, User;

import 'package:badminton_hub/data/auth_repository.dart';
import 'package:badminton_hub/data/club_repository.dart';
import 'package:badminton_hub/data/finance_repository.dart';
import 'package:badminton_hub/data/session_repository.dart';
import 'package:badminton_hub/models/club.dart';
import 'package:badminton_hub/models/finance.dart';
import 'package:badminton_hub/models/session.dart';
import 'package:badminton_hub/providers/auth_provider.dart';
import 'package:badminton_hub/providers/club_provider.dart';
import 'package:badminton_hub/providers/finance_provider.dart';
import 'package:badminton_hub/providers/session_provider.dart';
import 'package:badminton_hub/screens/session_detail_screen.dart';
import 'package:badminton_hub/screens/session_finance_screen.dart';
import 'package:badminton_hub/screens/session_history_screen.dart';
import 'package:badminton_hub/screens/session_summary_screen.dart';

class MockSessionRepository extends Mock implements SessionRepository {}

class MockFinanceRepository extends Mock implements FinanceRepository {}

class MockClubRepository extends Mock implements ClubRepository {}

class MockAuthRepository extends Mock implements AuthRepository {}

/// BH-07D: tich hop man hinh that <-> provider that <-> repository mock tai
/// ranh gioi client/RPC. Khong thay the man hinh/nghiep vu; khong chung minh
/// duoc HTTP/PostgREST/JWT/Auth that (ghi NOT RUN trong ban giao).
void main() {
  late MockSessionRepository sessionRepository;
  late MockFinanceRepository financeRepository;
  late MockClubRepository clubRepository;
  late MockAuthRepository authRepository;
  late StreamController<AuthState> authStateController;
  late AuthProvider authProvider;

  final startsAt = DateTime.utc(2026, 10, 20, 10);
  final endsAt = DateTime.utc(2026, 10, 20, 12);

  User user([String id = 'u1']) => User(
    id: id,
    appMetadata: const {},
    userMetadata: const {},
    aud: 'authenticated',
    createdAt: '2026-10-15',
  );

  Session session({
    String lifecycle = 'published',
    int version = 3,
    bool canManage = true,
    bool canViewFinance = true,
    String id = 's1',
    String title = 'Buổi tích hợp',
  }) => Session(
    id: id,
    clubId: 'c1',
    clubName: 'CLB A',
    title: title,
    startsAt: startsAt,
    endsAt: endsAt,
    capacity: 8,
    courtCount: 2,
    lifecycle: lifecycle,
    version: version,
    canManage: canManage,
    canViewFinance: canViewFinance,
    confirmedCount: 1,
    venueName: 'Sân A',
  );

  SessionPlayer player({String attendance = 'not_checked_in'}) => SessionPlayer(
    id: 'p1',
    displayName: 'An',
    participantType: 'member',
    registrationStatus: 'confirmed',
    attendanceStatus: attendance,
    phoneNumber: '0900000001',
  );

  SessionFinance finance({
    String lifecycle = 'in_progress',
    String state = 'not_finalized',
    int? sessionVersion = 5,
    int billingInputVersion = 2,
    int expensesTotal = 450000,
    int outstandingTotal = 0,
    List<FinanceExpense> expenses = const [],
    List<FinanceCharge> charges = const [],
    List<FinancePayment> payments = const [],
  }) => SessionFinance(
    sessionId: 's1',
    title: 'Buổi tích hợp',
    clubId: 'c1',
    lifecycle: lifecycle,
    billingInputVersion: billingInputVersion,
    sessionVersion: sessionVersion,
    billingState: state,
    activeRevision: state == 'not_finalized'
        ? null
        : const FinanceRevision(
            revisionId: 'r1',
            revisionNo: 1,
            sourceVersion: 2,
            allocationTotalVnd: 450000,
            feeMode: 'split_actual',
          ),
    expensesTotalVnd: expensesTotal,
    outstandingTotalVnd: outstandingTotal,
    expenses: expenses,
    charges: charges,
    payments: payments,
  );

  const courtExpense = FinanceExpense(
    expenseId: 'e1',
    category: 'court',
    title: 'Tiền sân',
    amountVnd: 450000,
    status: 'posted',
  );

  const submittedPayment = FinancePayment(
    paymentId: 'pay1',
    playerId: 'p1',
    amountVnd: 100000,
    method: 'bank_transfer',
    status: 'submitted',
  );

  const confirmedPayment = FinancePayment(
    paymentId: 'pay2',
    playerId: 'p1',
    amountVnd: 50000,
    method: 'cash',
    status: 'confirmed',
  );

  const rejectedPayment = FinancePayment(
    paymentId: 'pay3',
    playerId: 'p1',
    amountVnd: 30000,
    method: 'bank_transfer',
    status: 'submitted',
  );

  setUpAll(() {
    registerFallbackValue(const SessionHistoryFilter());
  });

  setUp(() {
    sessionRepository = MockSessionRepository();
    financeRepository = MockFinanceRepository();
    clubRepository = MockClubRepository();
    authRepository = MockAuthRepository();
    authStateController = StreamController<AuthState>.broadcast();
    when(() => authRepository.authStateChanges)
        .thenAnswer((_) => authStateController.stream);
    when(() => authRepository.currentUser).thenReturn(user());
    authProvider = AuthProvider(repository: authRepository);
  });

  tearDown(() {
    authProvider.dispose();
    authStateController.close();
  });

  SessionProvider sessionProvider() {
    final provider = SessionProvider(
      repository: sessionRepository,
      auth: authProvider,
    );
    addTearDown(provider.dispose);
    return provider;
  }

  FinanceProvider financeProvider() {
    final provider = FinanceProvider(
      repository: financeRepository,
      auth: authProvider,
    );
    addTearDown(provider.dispose);
    return provider;
  }

  ClubProvider clubProvider() {
    final provider = ClubProvider(
      repository: clubRepository,
      auth: authProvider,
    );
    addTearDown(provider.dispose);
    return provider;
  }

  Future<void> pumpApp(
    WidgetTester tester,
    Widget home, {
    required SessionProvider sessions,
    required FinanceProvider finances,
    ClubProvider? clubs,
  }) async {
    tester.view.physicalSize = const Size(1200, 3600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
          ChangeNotifierProvider<SessionProvider>.value(value: sessions),
          ChangeNotifierProvider<FinanceProvider>.value(value: finances),
          if (clubs != null)
            ChangeNotifierProvider<ClubProvider>.value(value: clubs),
        ],
        child: MaterialApp(home: home),
      ),
    );
  }

  Future<void> pumpFinanceRoute(
    WidgetTester tester,
    Session value,
    FinanceProvider provider, {
    required void Function(bool?) onResult,
  }) async {
    tester.view.physicalSize = const Size(1200, 3600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
          ChangeNotifierProvider<FinanceProvider>.value(value: provider),
        ],
        child: MaterialApp(
          home: Builder(
            builder: (context) => Scaffold(
              body: TextButton(
                key: const Key('open-finance'),
                onPressed: () async {
                  final result = await Navigator.of(context).push<bool>(
                    MaterialPageRoute(
                      builder: (_) => SessionFinanceScreen(session: value),
                    ),
                  );
                  onResult(result);
                },
                child: const Text('Mở tài chính'),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.byKey(const Key('open-finance')));
    await tester.pumpAndSettle();
  }

  testWidgets(
    'host: start -> điểm danh -> chốt phí -> complete -> history refresh, giữ công nợ',
    (tester) async {
      var detailCalls = 0;
      var financeCalls = 0;
      var historyCalls = 0;
      var attendanceRecorded = false;
      String? startRequestId;
      String? attendanceRequestId;
      String? finalizeRequestId;
      String? completeRequestId;

      final published = session();
      final inProgressV4 = session(lifecycle: 'in_progress', version: 4);
      final inProgressV5 = session(lifecycle: 'in_progress', version: 5);
      final completedV7 = session(lifecycle: 'completed', version: 7);

      when(() => sessionRepository.getSessionDetail('s1'))
          .thenAnswer((_) async {
            detailCalls += 1;
            return switch (detailCalls) {
              1 => published,
              2 => inProgressV4,
              3 => inProgressV5,
              _ => completedV7,
            };
          });
      when(() => sessionRepository.listMySessions())
          .thenAnswer((_) async => []);
      when(() => sessionRepository.listSessionPlayers('s1')).thenAnswer(
        (_) async => [
          player(attendance: attendanceRecorded ? 'present' : 'not_checked_in'),
        ],
      );
      when(
        () => sessionRepository.startSession(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
        ),
      ).thenAnswer((invocation) async {
        startRequestId = invocation.namedArguments[#requestId] as String;
        return inProgressV4;
      });
      when(
        () => sessionRepository.recordAttendance(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
          playerId: 'p1',
          attendance: 'present',
        ),
      ).thenAnswer((invocation) async {
        attendanceRequestId = invocation.namedArguments[#requestId] as String;
        attendanceRecorded = true;
        return const RegistrationResult(
          playerId: 'p1',
          sessionId: 's1',
          registrationStatus: 'confirmed',
          attendanceStatus: 'present',
          sessionVersion: 6,
        );
      });

      when(
        () => sessionRepository.listMySessionHistory(
          filter: any(named: 'filter'),
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ),
      ).thenAnswer((_) async {
        historyCalls += 1;
        return SessionHistoryPage(
          sessions: historyCalls == 1
              ? [session(id: 'old', title: 'Buổi cũ', lifecycle: 'completed')]
              : [
                  session(id: 'old', title: 'Buổi cũ', lifecycle: 'completed'),
                  completedV7,
                ],
          limit: 20,
          offset: 0,
          hasMoreOverride: false,
        );
      });

      when(
        () => financeRepository.getSessionFinance(
          's1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ),
      ).thenAnswer((_) async {
        financeCalls += 1;
        if (financeCalls == 1) {
          return finance(expenses: const [courtExpense], sessionVersion: 5);
        }
        if (financeCalls == 2) {
          return finance(
            state: 'current',
            sessionVersion: 6,
            expenses: const [courtExpense],
            outstandingTotal: 200000,
            charges: const [
              FinanceCharge(
                playerId: 'p1',
                displayName: 'An',
                amountDueVnd: 225000,
              ),
            ],
          );
        }
        return finance(
          lifecycle: 'completed',
          state: 'current',
          sessionVersion: 7,
          expenses: const [courtExpense],
          outstandingTotal: 200000,
          charges: const [
            FinanceCharge(
              playerId: 'p1',
              displayName: 'An',
              amountDueVnd: 225000,
            ),
          ],
        );
      });
      when(
        () => financeRepository.finalizeSessionCharges(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
          expectedVersion: 5,
          expectedBillingInputVersion: 2,
          reason: any(named: 'reason'),
        ),
      ).thenAnswer((invocation) async {
        finalizeRequestId = invocation.namedArguments[#requestId] as String;
        return const RevisionResult(
          revisionId: 'r1',
          sessionId: 's1',
          revisionNo: 1,
          sourceVersion: 2,
          allocationTotalVnd: 450000,
          feeMode: 'split_actual',
          presentCount: 1,
          chargeCount: 1,
          billingState: 'current',
        );
      });
      when(
        () => financeRepository.completeSession(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
          expectedVersion: 6,
        ),
      ).thenAnswer((invocation) async {
        completeRequestId = invocation.namedArguments[#requestId] as String;
        return completedV7;
      });

      final sessions = sessionProvider();
      final finances = financeProvider();
      await sessions.fetchSessionHistory();
      expect(historyCalls, 1);

      await pumpApp(
        tester,
        const SessionDetailScreen(sessionId: 's1'),
        sessions: sessions,
        finances: finances,
      );
      await tester.pumpAndSettle();

      expect(find.text('Đã công bố'), findsOneWidget);
      await tester.tap(find.text('Bắt đầu buổi chơi'));
      await tester.pumpAndSettle();
      expect(startRequestId, isNotEmpty);
      expect(find.text('Đang diễn ra'), findsOneWidget);

      await tester.tap(find.text('Có mặt'));
      await tester.pumpAndSettle();
      expect(attendanceRequestId, isNotEmpty);
      expect(sessions.currentPlayers.single.attendanceStatus, 'present');

      await tester.tap(find.text('Tài chính & thu tiền'));
      await tester.pumpAndSettle();
      expect(find.text('Chưa chốt phí'), findsOneWidget);

      await tester.tap(find.byKey(const Key('bh06c-finalize')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'chốt lần 1');
      await tester.tap(find.text('Xác nhận'));
      await tester.pumpAndSettle();
      expect(finalizeRequestId, isNotEmpty);
      expect(find.text('Đang hiệu lực'), findsOneWidget);
      expect(find.text('200,000 VNĐ'), findsOneWidget);

      await tester.tap(find.byKey(const Key('bh07c-complete-session')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Đồng ý'));
      await tester.pumpAndSettle();

      expect(completeRequestId, isNotEmpty);
      expect(find.byType(SessionFinanceScreen), findsNothing);
      expect(find.text('Đã kết thúc'), findsWidgets);
      expect(find.byKey(const Key('bh07c-summary-entry')), findsOneWidget);
      expect(historyCalls, 2);
      expect(
        sessions.historyItems.map((item) => item.id),
        containsAll(<String>['old', 's1']),
      );
      expect(detailCalls, greaterThanOrEqualTo(4));
      expect(financeCalls, greaterThanOrEqualTo(3));
    },
  );

  testWidgets(
    'complete buổi miễn phí current 0 vẫn gọi đúng version/request_id',
    (tester) async {
      String? requestId;
      var result = false;
      when(
        () => financeRepository.getSessionFinance(
          's1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ),
      ).thenAnswer(
        (_) async => finance(
          state: 'current',
          sessionVersion: 4,
          expensesTotal: 0,
          outstandingTotal: 0,
          charges: const [
            FinanceCharge(playerId: 'p1', displayName: 'An', amountDueVnd: 0),
          ],
        ),
      );
      when(
        () => financeRepository.completeSession(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
          expectedVersion: 4,
        ),
      ).thenAnswer((invocation) async {
        requestId = invocation.namedArguments[#requestId] as String;
        return session(lifecycle: 'completed', version: 5);
      });

      final finances = financeProvider();
      await pumpFinanceRoute(
        tester,
        session(lifecycle: 'in_progress', version: 4),
        finances,
        onResult: (value) => result = value ?? false,
      );

      await tester.tap(find.byKey(const Key('bh07c-complete-session')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Đồng ý'));
      await tester.pumpAndSettle();

      expect(requestId, isNotEmpty);
      expect(result, isTrue);
      verify(
        () => financeRepository.completeSession(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
          expectedVersion: 4,
        ),
      ).called(1);
    },
  );

  testWidgets('complete bị khoá khi phí stale hoặc chưa chốt, không gọi RPC', (
    tester,
  ) async {
    for (final state in ['stale', 'not_finalized']) {
      final repo = MockFinanceRepository();
      when(
        () => repo.getSessionFinance(
          's1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ),
      ).thenAnswer((_) async => finance(state: state, sessionVersion: 6));
      final provider = FinanceProvider(repository: repo, auth: authProvider);
      addTearDown(provider.dispose);
      tester.view.physicalSize = const Size(1200, 3600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
            ChangeNotifierProvider<FinanceProvider>.value(value: provider),
          ],
          child: MaterialApp(
            home: SessionFinanceScreen(
              key: ValueKey('finance-$state'),
              session: session(lifecycle: 'in_progress', version: 6),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final button = tester.widget<FilledButton>(
        find.byKey(const Key('bh07c-complete-session')),
      );
      expect(button.onPressed, isNull, reason: state);
      verifyNever(
        () => repo.completeSession(
          requestId: any(named: 'requestId'),
          sessionId: any(named: 'sessionId'),
          expectedVersion: any(named: 'expectedVersion'),
        ),
      );
    }
  });

  testWidgets(
    'VERSION_CONFLICT: không báo thành công, tải lại lấy version mới rồi complete',
    (tester) async {
      var financeCalls = 0;
      var completeCalls = 0;
      bool? result;
      final versions = <int>[];
      final requestIds = <String>[];

      when(
        () => financeRepository.getSessionFinance(
          's1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ),
      ).thenAnswer((_) async {
        financeCalls += 1;
        return finance(
          state: 'current',
          sessionVersion: financeCalls == 1 ? 7 : 8,
          expenses: const [courtExpense],
          outstandingTotal: 200000,
          charges: const [
            FinanceCharge(
              playerId: 'p1',
              displayName: 'An',
              amountDueVnd: 225000,
            ),
          ],
        );
      });
      when(
        () => financeRepository.completeSession(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
          expectedVersion: any(named: 'expectedVersion'),
        ),
      ).thenAnswer((invocation) async {
        completeCalls += 1;
        versions.add(invocation.namedArguments[#expectedVersion] as int);
        requestIds.add(invocation.namedArguments[#requestId] as String);
        if (completeCalls == 1) {
          throw Exception('PostgrestException(VERSION_CONFLICT: raw)');
        }
        return session(lifecycle: 'completed', version: 9);
      });

      final finances = financeProvider();
      await pumpFinanceRoute(
        tester,
        session(lifecycle: 'in_progress', version: 7),
        finances,
        onResult: (value) => result = value,
      );

      await tester.tap(find.byKey(const Key('bh07c-complete-session')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Đồng ý'));
      await tester.pumpAndSettle();

      expect(completeCalls, 1);
      expect(result, isNull);
      expect(find.byType(SessionFinanceScreen), findsOneWidget);
      expect(
        find.text('Buổi chơi đã được thay đổi ở nơi khác. Vui lòng tải lại.'),
        findsOneWidget,
      );

      await tester
          .widget<RefreshIndicator>(find.byType(RefreshIndicator))
          .onRefresh();
      await tester.pumpAndSettle();
      expect(financeCalls, greaterThanOrEqualTo(2));

      await tester.tap(find.byKey(const Key('bh07c-complete-session')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Đồng ý'));
      await tester.pumpAndSettle();

      expect(versions, [7, 8]);
      expect(requestIds, hasLength(2));
      expect(requestIds.first, isNot(requestIds.last));
      expect(result, isTrue);
      expect(find.byType(SessionFinanceScreen), findsNothing);
    },
  );

  testWidgets(
    'retry cùng intent complete giữ request_id, không báo thành công giả',
    (tester) async {
      var completeCalls = 0;
      bool? result;
      final versions = <int>[];
      final requestIds = <String>[];
      final firstAttempt = Completer<Session>();

      when(
        () => financeRepository.getSessionFinance(
          's1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ),
      ).thenAnswer(
        (_) async => finance(
          state: 'current',
          sessionVersion: 7,
          expenses: const [courtExpense],
          outstandingTotal: 200000,
        ),
      );
      when(
        () => financeRepository.completeSession(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
          expectedVersion: any(named: 'expectedVersion'),
        ),
      ).thenAnswer((invocation) async {
        completeCalls += 1;
        versions.add(invocation.namedArguments[#expectedVersion] as int);
        requestIds.add(invocation.namedArguments[#requestId] as String);
        if (completeCalls == 1) {
          return firstAttempt.future;
        }
        return session(lifecycle: 'completed', version: 8);
      });

      final finances = financeProvider();
      await pumpFinanceRoute(
        tester,
        session(lifecycle: 'in_progress', version: 7),
        finances,
        onResult: (value) => result = value,
      );

      await tester.tap(find.byKey(const Key('bh07c-complete-session')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Đồng ý'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(completeCalls, 1);
      expect(result, isNull);
      expect(find.byType(SessionFinanceScreen), findsOneWidget);
      expect(
        tester
            .widget<FilledButton>(
              find.byKey(const Key('bh07c-complete-session')),
            )
            .onPressed,
        isNull,
      );

      firstAttempt.completeError(Exception('PostgrestException(timeout)'));
      await tester.pumpAndSettle();
      expect(result, isNull);

      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('bh07c-complete-session')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Đồng ý'));
      await tester.pumpAndSettle();

      expect(versions, [7, 7]);
      expect(requestIds, hasLength(2));
      expect(requestIds.first, requestIds.last);
      expect(result, isTrue);
      expect(find.byType(SessionFinanceScreen), findsNothing);
    },
  );

  testWidgets(
    'history: offset/dedupe, lọc CLB và ngày UTC+7, mở chi tiết rồi quay lại refresh',
    (tester) async {
      const clubA = Club(id: 'c1', ownerUserId: 'u1', name: 'CLB A');
      final h1 = session(id: 'h1', title: 'Buổi một', lifecycle: 'completed');
      final h2 = session(id: 'h2', title: 'Buổi hai', lifecycle: 'completed');
      final h3 = session(id: 'h3', title: 'Buổi ba', lifecycle: 'cancelled');
      final offsets = <int>[];
      final filters = <SessionHistoryFilter>[];

      when(() => clubRepository.listMyClubs()).thenAnswer((_) async => [clubA]);
      when(
        () => sessionRepository.listMySessionHistory(
          filter: any(named: 'filter'),
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ),
      ).thenAnswer((invocation) async {
        final offset = invocation.namedArguments[#offset] as int;
        final filter =
            invocation.namedArguments[#filter] as SessionHistoryFilter;
        offsets.add(offset);
        filters.add(filter);
        if (filter.clubId == 'c1') {
          return SessionHistoryPage(
            sessions: [h3],
            limit: 20,
            offset: offset,
            hasMoreOverride: false,
          );
        }
        if (offset == 0) {
          return const SessionHistoryPage(
            sessions: [],
            limit: 20,
            offset: 0,
            hasMoreOverride: true,
          ).copyWith(sessions: [h1, h2]);
        }
        return SessionHistoryPage(
          sessions: [h2, h3],
          limit: 20,
          offset: offset,
          hasMoreOverride: false,
        );
      });
      when(() => sessionRepository.getSessionDetail('h3')).thenAnswer(
        (_) async => session(
          id: 'h3',
          title: 'Buổi ba',
          lifecycle: 'cancelled',
          version: 2,
          canManage: false,
          canViewFinance: false,
        ),
      );

      final sessions = sessionProvider();
      final finances = financeProvider();
      final clubs = clubProvider();
      await pumpApp(
        tester,
        const SessionHistoryScreen(),
        sessions: sessions,
        finances: finances,
        clubs: clubs,
      );
      await tester.pumpAndSettle();

      expect(find.text('Buổi một'), findsOneWidget);
      expect(find.text('Buổi hai'), findsOneWidget);
      expect(find.byKey(const Key('bh07c-history-load-more')), findsOneWidget);

      await tester.tap(find.byKey(const Key('bh07c-history-load-more')));
      await tester.pumpAndSettle();
      expect(offsets.take(2).toList(), [0, 2]);
      expect(find.text('Buổi ba'), findsOneWidget);
      expect(find.text('Buổi hai'), findsOneWidget);
      expect(find.byKey(const Key('bh07c-history-load-more')), findsNothing);

      await tester.tap(find.byKey(const Key('bh07c-history-club-filter')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('CLB A').last);
      await tester.pumpAndSettle();
      expect(filters.last.clubId, 'c1');
      expect(offsets.last, 0);

      await tester.tap(find.byKey(const Key('bh07c-history-date-filter')));
      await tester.pumpAndSettle();
      await tester.tap(find.byIcon(Icons.edit_outlined));
      await tester.pumpAndSettle();
      final fields = find.byType(TextField);
      await tester.enterText(fields.at(0), '10/20/2026');
      await tester.enterText(fields.at(1), '10/20/2026');
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      expect(filters.last.from, DateTime.utc(2026, 10, 19, 17));
      expect(filters.last.to, DateTime.utc(2026, 10, 20, 16, 59, 59, 999, 999));

      final beforeOpen = filters.length;
      await tester.tap(find.text('Buổi ba'));
      await tester.pumpAndSettle();
      expect(find.text('Chi tiết buổi chơi'), findsOneWidget);
      await tester.pageBack();
      await tester.pumpAndSettle();
      expect(filters.length, greaterThan(beforeOpen));
      expect(filters.last, filters[beforeOpen - 1]);
    },
  );

  testWidgets(
    'tổng kết management-only không lộ tiền; finance giữ NULL là dấu gạch',
    (tester) async {
      const managementSummary = SessionSummary(
        sessionId: 's1',
        title: 'Buổi tổng kết',
        lifecycle: 'completed',
        canManage: true,
        canViewFinance: false,
        presentCount: 6,
        noShowCount: 1,
        confirmedCount: 7,
      );
      const financeSummary = SessionSummary(
        sessionId: 's2',
        title: 'Buổi tài chính',
        lifecycle: 'completed',
        canManage: true,
        canViewFinance: true,
        presentCount: 4,
        noShowCount: 0,
        confirmedCount: 4,
        billingState: 'current',
        expensesTotalVnd: 450000,
        amountDueTotalVnd: null,
        totalPaidVnd: null,
        outstandingTotalVnd: 300000,
      );

      when(() => sessionRepository.getSessionDetail('s1'))
          .thenAnswer((_) async => session(lifecycle: 'completed', version: 8));
      when(() => sessionRepository.listSessionPlayers('s1'))
          .thenAnswer((_) async => [player(attendance: 'present')]);
      when(() => financeRepository.getSessionSummary('s1'))
          .thenAnswer((_) async => managementSummary);
      when(() => financeRepository.getSessionSummary('s2'))
          .thenAnswer((_) async => financeSummary);

      String? copied;
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(SystemChannels.platform, (call) async {
            if (call.method == 'Clipboard.setData') {
              copied = (call.arguments as Map)['text'] as String?;
            }
            return null;
          });
      addTearDown(
        () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(SystemChannels.platform, null),
      );

      final sessions = sessionProvider();
      final finances = financeProvider();
      await pumpApp(
        tester,
        const SessionDetailScreen(sessionId: 's1'),
        sessions: sessions,
        finances: finances,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('bh07c-summary-entry')));
      await tester.pumpAndSettle();

      expect(find.text('Chỉ xem số lượng'), findsOneWidget);
      expect(find.byKey(const Key('bh07c-summary-finance')), findsNothing);
      expect(find.text('Tổng chi phí'), findsNothing);
      await tester.ensureVisible(find.byKey(const Key('bh07c-copy-summary')));
      await tester.tap(find.byKey(const Key('bh07c-copy-summary')));
      await tester.pumpAndSettle();
      expect(copied, contains('Có mặt: 6'));
      expect(copied, isNot(contains('VNĐ')));
      expect(copied, isNot(contains('Tổng chi phí')));
      expect(copied, isNot(contains('0900000001')));
      expect(copied, isNot(contains('ngân hàng')));

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
            ChangeNotifierProvider<FinanceProvider>.value(value: finances),
          ],
          child: const MaterialApp(home: SessionSummaryScreen(sessionId: 's2')),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('bh07c-summary-finance')), findsOneWidget);
      expect(find.text('—'), findsNWidgets(2));
      await tester.ensureVisible(find.byKey(const Key('bh07c-copy-summary')));
      await tester.tap(find.byKey(const Key('bh07c-copy-summary')));
      await tester.pumpAndSettle();
      expect(copied, contains('Đã thu: —'));
      expect(copied, contains('Còn phải thu: 300,000 VNĐ'));
      expect(copied, isNot(contains('Tổng phải thu: 0 VNĐ')));
      expect(copied, isNot(contains('ngân hàng')));
    },
  );

  testWidgets(
    'participant/guest không thấy lối tổng kết quản lý hay tài chính quản lý',
    (tester) async {
      when(() => sessionRepository.getSessionDetail('sp')).thenAnswer(
        (_) async => session(
          id: 'sp',
          title: 'Buổi participant',
          lifecycle: 'completed',
          version: 9,
          canManage: false,
          canViewFinance: false,
        ),
      );
      when(() => sessionRepository.getSessionDetail('sg')).thenAnswer(
        (_) async => session(
          id: 'sg',
          title: 'Buổi guest',
          lifecycle: 'completed',
          version: 9,
          canManage: false,
          canViewFinance: false,
        ),
      );

      final sessions = sessionProvider();
      final finances = financeProvider();
      await pumpApp(
        tester,
        const SessionDetailScreen(
          key: ValueKey('participant-detail'),
          sessionId: 'sp',
        ),
        sessions: sessions,
        finances: finances,
      );
      await tester.pumpAndSettle();

      expect(find.text('Phần phí của tôi'), findsOneWidget);
      expect(find.text('Tài chính & thu tiền'), findsNothing);
      expect(find.byKey(const Key('bh07c-summary-entry')), findsNothing);
      expect(find.text('Bắt đầu buổi chơi'), findsNothing);
      expect(find.text('Kết thúc buổi chơi'), findsNothing);

      when(() => authRepository.currentUser).thenReturn(null);
      authStateController.add(AuthState(AuthChangeEvent.signedOut, null));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      await pumpApp(
        tester,
        const SessionDetailScreen(
          key: ValueKey('guest-detail'),
          sessionId: 'sg',
        ),
        sessions: sessions,
        finances: finances,
      );
      await tester.pumpAndSettle();

      expect(find.text('Buổi guest'), findsOneWidget);
      expect(find.text('Phần phí của tôi'), findsNothing);
      expect(find.text('Tài chính & thu tiền'), findsNothing);
      expect(find.byKey(const Key('bh07c-summary-entry')), findsNothing);
      expect(find.text('Bắt đầu buổi chơi'), findsNothing);
    },
  );

  testWidgets(
    'sau complete: ẩn thêm chi phí, vẫn cho chốt lại/thu/xác nhận/từ chối/hoàn tác',
    (tester) async {
      var financeCalls = 0;
      String? finalizeRequestId;
      String? confirmRequestId;
      String? rejectRequestId;
      String? reverseRequestId;

      when(
        () => financeRepository.getSessionFinance(
          's1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ),
      ).thenAnswer((_) async {
        financeCalls += 1;
        return finance(
          lifecycle: 'completed',
          state: 'current',
          sessionVersion: 8,
          billingInputVersion: 5,
          expenses: const [courtExpense],
          outstandingTotal: 60000,
          charges: const [
            FinanceCharge(
              playerId: 'p1',
              displayName: 'An',
              amountDueVnd: 100000,
            ),
          ],
          payments: const [submittedPayment, confirmedPayment, rejectedPayment],
        );
      });
      when(
        () => financeRepository.finalizeSessionCharges(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
          expectedVersion: 8,
          expectedBillingInputVersion: 5,
          reason: any(named: 'reason'),
        ),
      ).thenAnswer((invocation) async {
        finalizeRequestId = invocation.namedArguments[#requestId] as String;
        return const RevisionResult(
          revisionId: 'r2',
          sessionId: 's1',
          revisionNo: 2,
          sourceVersion: 5,
          billingState: 'current',
        );
      });
      when(
        () => financeRepository.confirmPayment(
          requestId: any(named: 'requestId'),
          paymentId: 'pay1',
        ),
      ).thenAnswer((invocation) async {
        confirmRequestId = invocation.namedArguments[#requestId] as String;
        return const PaymentResult(
          paymentId: 'pay1',
          playerId: 'p1',
          sessionId: 's1',
          amountVnd: 100000,
          method: 'bank_transfer',
          status: 'confirmed',
          billingState: 'current',
        );
      });
      when(
        () => financeRepository.rejectPayment(
          requestId: any(named: 'requestId'),
          paymentId: 'pay3',
          reason: any(named: 'reason'),
        ),
      ).thenAnswer((invocation) async {
        rejectRequestId = invocation.namedArguments[#requestId] as String;
        return const PaymentResult(
          paymentId: 'pay3',
          playerId: 'p1',
          sessionId: 's1',
          amountVnd: 30000,
          method: 'bank_transfer',
          status: 'rejected',
          billingState: 'current',
        );
      });
      when(
        () => financeRepository.reversePayment(
          requestId: any(named: 'requestId'),
          paymentId: 'pay2',
          reason: any(named: 'reason'),
        ),
      ).thenAnswer((invocation) async {
        reverseRequestId = invocation.namedArguments[#requestId] as String;
        return const PaymentResult(
          paymentId: 'pay2',
          playerId: 'p1',
          sessionId: 's1',
          amountVnd: 50000,
          method: 'cash',
          status: 'reversed',
          billingState: 'current',
        );
      });
      when(
        () => financeRepository.reverseSessionExpense(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
          expenseId: 'e1',
          reason: any(named: 'reason'),
        ),
      ).thenAnswer(
        (_) async => const ExpenseResult(
          expenseId: 'e1',
          sessionId: 's1',
          status: 'reversed',
          billingState: 'stale',
        ),
      );

      final finances = financeProvider();
      await pumpFinanceRoute(
        tester,
        session(lifecycle: 'completed', version: 8),
        finances,
        onResult: (_) {},
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('bh06c-add-expense')), findsNothing);
      expect(find.byKey(const Key('bh06c-finalize')), findsOneWidget);
      expect(find.byKey(const Key('bh07c-complete-session')), findsNothing);
      expect(find.byKey(const Key('bh06c-confirm-pay1')), findsOneWidget);
      expect(find.byKey(const Key('bh06c-reject-pay1')), findsOneWidget);
      expect(find.byKey(const Key('bh06c-reject-pay3')), findsOneWidget);
      expect(find.byKey(const Key('bh06c-reverse-pay2')), findsOneWidget);
      expect(find.byKey(const Key('bh06c-cash-p1')), findsOneWidget);
      expect(find.byKey(const Key('bh06c-reverse-expense-e1')), findsOneWidget);
      expect(find.text('60,000 VNĐ'), findsOneWidget);

      await tester.tap(find.byKey(const Key('bh06c-finalize')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'chốt lại sau complete');
      await tester.tap(
        find.descendant(
          of: find.byType(AlertDialog),
          matching: find.text('Xác nhận'),
        ),
      );
      await tester.pumpAndSettle();
      expect(finalizeRequestId, isNotEmpty);
      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('bh06c-confirm-pay1')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Đồng ý'));
      await tester.pumpAndSettle();
      expect(confirmRequestId, isNotEmpty);
      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('bh06c-reject-pay3')));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byType(TextField),
        'chuyển khoản sai nội dung',
      );
      await tester.tap(
        find.descendant(
          of: find.byType(AlertDialog),
          matching: find.text('Xác nhận'),
        ),
      );
      await tester.pumpAndSettle();
      expect(rejectRequestId, isNotEmpty);
      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('bh06c-reverse-pay2')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'hoàn tác sau complete');
      await tester.tap(
        find.descendant(
          of: find.byType(AlertDialog),
          matching: find.text('Xác nhận'),
        ),
      );
      await tester.pumpAndSettle();
      expect(reverseRequestId, isNotEmpty);
      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('bh06c-reverse-expense-e1')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'điều chỉnh chi phí');
      await tester.tap(
        find.descendant(
          of: find.byType(AlertDialog),
          matching: find.text('Xác nhận'),
        ),
      );
      await tester.pumpAndSettle();
      verify(
        () => financeRepository.reverseSessionExpense(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
          expenseId: 'e1',
          reason: 'điều chỉnh chi phí',
        ),
      ).called(1);
      expect(financeCalls, greaterThanOrEqualTo(4));
    },
  );

  testWidgets(
    'logout/đổi actor xoá lịch sử cũ và không lộ dữ liệu actor trước',
    (tester) async {
      const clubA = Club(id: 'c1', ownerUserId: 'u1', name: 'CLB A');
      final userOneSession = session(
        id: 'h1',
        title: 'Buổi của user một',
        lifecycle: 'completed',
      );
      final userTwoSession = session(
        id: 'h2',
        title: 'Buổi của user hai',
        lifecycle: 'completed',
      );
      var historyCalls = 0;

      when(() => clubRepository.listMyClubs()).thenAnswer((_) async => [clubA]);
      when(
        () => sessionRepository.listMySessionHistory(
          filter: any(named: 'filter'),
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ),
      ).thenAnswer((_) async {
        historyCalls += 1;
        return SessionHistoryPage(
          sessions: historyCalls == 1 ? [userOneSession] : [userTwoSession],
          limit: 20,
          offset: 0,
          hasMoreOverride: false,
        );
      });

      final sessions = sessionProvider();
      final finances = financeProvider();
      final clubs = clubProvider();
      await pumpApp(
        tester,
        const SessionHistoryScreen(),
        sessions: sessions,
        finances: finances,
        clubs: clubs,
      );
      await tester.pumpAndSettle();
      expect(find.text('Buổi của user một'), findsOneWidget);

      when(() => authRepository.currentUser).thenReturn(null);
      authStateController.add(AuthState(AuthChangeEvent.signedOut, null));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      expect(
        find.byKey(const Key('bh07c-history-login-required')),
        findsOneWidget,
      );
      expect(find.text('Buổi của user một'), findsNothing);
      expect(sessions.history, isNull);

      when(() => authRepository.currentUser).thenReturn(user('u2'));
      authStateController.add(AuthState(AuthChangeEvent.signedIn, null));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      expect(find.text('Buổi của user một'), findsNothing);
      expect(sessions.history, isNull);

      await tester.tap(find.byTooltip('Tải lại lịch sử'));
      await tester.pumpAndSettle();
      expect(find.text('Buổi của user hai'), findsOneWidget);
      expect(find.text('Buổi của user một'), findsNothing);
      expect(historyCalls, 2);
    },
  );
}

extension on SessionHistoryPage {
  SessionHistoryPage copyWith({List<Session>? sessions}) => SessionHistoryPage(
    sessions: sessions ?? this.sessions,
    limit: limit,
    offset: offset,
    hasMoreOverride: hasMoreOverride,
  );
}
