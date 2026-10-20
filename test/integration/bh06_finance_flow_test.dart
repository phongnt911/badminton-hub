import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart' show AuthState, User;

import 'package:badminton_hub/data/auth_repository.dart';
import 'package:badminton_hub/data/finance_repository.dart';
import 'package:badminton_hub/models/finance.dart';
import 'package:badminton_hub/models/session.dart';
import 'package:badminton_hub/providers/auth_provider.dart';
import 'package:badminton_hub/providers/finance_provider.dart';
import 'package:badminton_hub/screens/session_finance_screen.dart';

class MockFinanceRepository extends Mock implements FinanceRepository {}

class MockAuthRepository extends Mock implements AuthRepository {}

/// Test tich hop man hinh <-> FinanceProvider that <-> FinanceRepository
/// (mock dung ranh gioi client/RPC). Bo sung cho runner DB: kiem tra UI truyen
/// dung session/version/amount/player xuong provider va provider goi repository
/// voi dung tham so, roi refresh lai sau khi mutation thanh cong.
void main() {
  late MockFinanceRepository repo;
  late MockAuthRepository authRepository;
  late StreamController<AuthState> authStateController;
  late AuthProvider authProvider;
  late int financeCalls;

  const managerSession = Session(
    id: 's1',
    title: 'Buổi A',
    canViewFinance: true,
    canManage: true,
    version: 3,
  );
  const playerSession = Session(id: 's1', title: 'Buổi A');

  User user() => User(
        id: 'u1',
        appMetadata: {},
        userMetadata: {},
        aud: 'authenticated',
        createdAt: '2026-10-15',
      );

  setUp(() {
    repo = MockFinanceRepository();
    financeCalls = 0;
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

  SessionFinance notFinalized() => SessionFinance.fromJson({
        'session_id': 's1',
        'title': 'Buổi A',
        'lifecycle': 'in_progress',
        'fee_mode': 'split_actual',
        'billing_input_version': 2,
        'billing_state': 'not_finalized',
        'active_revision': null,
        'expenses_total_vnd': 450000,
        'outstanding_total_vnd': 0,
        'expenses': [
          {
            'expense_id': 'e1',
            'category': 'court',
            'title': 'Tiền sân',
            'amount_vnd': 400000,
            'status': 'posted',
            'reversal_reason': null,
            'posted_at': '2026-10-20T01:00:00Z',
          },
          {
            'expense_id': 'e2',
            'category': 'other',
            'title': 'Nước',
            'amount_vnd': 50000,
            'status': 'posted',
            'reversal_reason': null,
            'posted_at': '2026-10-20T01:01:00Z',
          },
        ],
        'charges': <Map<String, dynamic>>[],
        'payments': <Map<String, dynamic>>[],
        'limit': 50,
        'offset': 0,
      });

  SessionFinance current({bool withSubmitted = false}) =>
      SessionFinance.fromJson({
        'session_id': 's1',
        'title': 'Buổi A',
        'lifecycle': 'in_progress',
        'fee_mode': 'split_actual',
        'billing_input_version': 2,
        'billing_state': 'current',
        'active_revision': {
          'revision_id': 'r1',
          'revision_no': 1,
          'source_version': 2,
          'allocation_total_vnd': 450000,
          'fee_mode': 'split_actual',
          'reason': null,
          'finalized_at': '2026-10-20T02:00:00Z',
        },
        'expenses_total_vnd': 450000,
        'outstanding_total_vnd': 225000,
        'expenses': [
          {
            'expense_id': 'e1',
            'category': 'court',
            'title': 'Tiền sân',
            'amount_vnd': 400000,
            'status': 'posted',
            'reversal_reason': null,
            'posted_at': '2026-10-20T01:00:00Z',
          },
        ],
        'charges': [
          {'player_id': 'p1', 'display_name': 'An', 'amount_due_vnd': 225000},
        ],
        'payments': [
          if (withSubmitted)
            {
              'payment_id': 'pay1',
              'player_id': 'p1',
              'amount_vnd': 100000,
              'method': 'bank_transfer',
              'status': 'submitted',
              'reference': 'PAY-1',
              'confirmed_at': null,
              'created_at': '2026-10-20T02:10:00Z',
            },
        ],
        'limit': 50,
        'offset': 0,
      });

  PaymentInstructions instructions() => PaymentInstructions.fromJson({
        'session_id': 's1',
        'player_id': 'p1',
        'display_name': 'An',
        'billing_state': 'current',
        'active_revision_id': 'r1',
        'source_version': 2,
        'amount_due_vnd': 225000,
        'total_paid_vnd': 0,
        'outstanding_vnd': 225000,
        'reference': 'BH-TEST0001',
        'receiver_snapshot': {
          'bank_code': 'TCB',
          'account_number': '9999888877',
          'account_name': 'CLB INTEGRATION',
        },
        'has_receiver': true,
        'can_pay': true,
      });

  PaymentResult paymentResult(String id, String status, int amount) =>
      PaymentResult.fromJson({
        'payment_id': id,
        'player_id': 'p1',
        'session_id': 's1',
        'amount_vnd': amount,
        'method': 'cash',
        'status': status,
        'reference': 'CASH-1',
        'billing_state': 'current',
      });

  Widget build(Session session, FinanceProvider provider) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
        ChangeNotifierProvider<FinanceProvider>.value(value: provider),
      ],
      child: MaterialApp(home: SessionFinanceScreen(session: session)),
    );
  }

  FinanceProvider provider() {
    final instance = FinanceProvider(repository: repo, auth: authProvider);
    addTearDown(instance.dispose);
    return instance;
  }

  Future<void> pumpScreen(
    WidgetTester tester,
    Session session,
    FinanceProvider provider,
  ) async {
    tester.view.physicalSize = const Size(1200, 3200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(build(session, provider));
  }

  testWidgets('manager: chot phi -> thu tien mat -> confirm qua provider that',
      (tester) async {
    when(() => repo.getSessionFinance('s1')).thenAnswer((_) async {
      financeCalls += 1;
      return financeCalls == 1 ? notFinalized() : current(withSubmitted: true);
    });
    when(() => repo.finalizeSessionCharges(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
          expectedVersion: 3,
          expectedBillingInputVersion: 2,
          reason: 'chot lan 1',
        )).thenAnswer((_) async => RevisionResult.fromJson({
          'revision_id': 'r1',
          'session_id': 's1',
          'revision_no': 1,
          'source_version': 2,
          'allocation_total_vnd': 450000,
          'fee_mode': 'split_actual',
          'present_count': 1,
          'charge_count': 1,
          'billing_state': 'current',
        }));

    final financeProvider = provider();
    await pumpScreen(tester, managerSession, financeProvider);
    await tester.pumpAndSettle();

    expect(find.text('Chưa chốt phí'), findsOneWidget);

    await tester.tap(find.byKey(const Key('bh06c-finalize')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'chot lan 1');
    await tester.tap(find.text('Xác nhận'));
    await tester.pumpAndSettle();

    verify(() => repo.finalizeSessionCharges(
          requestId: any(named: 'requestId'),
          sessionId: 's1',
          expectedVersion: 3,
          expectedBillingInputVersion: 2,
          reason: 'chot lan 1',
        )).called(1);
    expect(find.text('Đang hiệu lực'), findsOneWidget);
    expect(find.text('Revision #1 (nguồn v2)'), findsOneWidget);
    // Cho snackbar "Đã chốt phí." hết hạn để snackbar thu tiền mặt không bị xếp hàng.
    await tester.pump(const Duration(seconds: 5));
    await tester.pumpAndSettle();

    when(() => repo.getPaymentInstructions('s1', playerId: 'p1'))
        .thenAnswer((_) async => instructions());
    when(() => repo.recordCashPayment(
          requestId: any(named: 'requestId'),
          playerId: 'p1',
          amountVnd: 225000,
        )).thenAnswer((_) async => paymentResult('pay-cash', 'confirmed', 225000));

    await tester.tap(find.byKey(const Key('bh06c-cash-p1')));
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsOneWidget);
    await tester.tap(find.descendant(
      of: find.byType(AlertDialog),
      matching: find.text('Xác nhận'),
    ));
    await tester.pumpAndSettle();

    verify(() => repo.recordCashPayment(
          requestId: any(named: 'requestId'),
          playerId: 'p1',
          amountVnd: 225000,
        )).called(1);
    expect(find.text('Đã ghi thu tiền mặt.'), findsOneWidget);
    await tester.pump(const Duration(seconds: 5));
    await tester.pumpAndSettle();

    when(() => repo.confirmPayment(
          requestId: any(named: 'requestId'),
          paymentId: 'pay1',
        )).thenAnswer((_) async => paymentResult('pay1', 'confirmed', 100000));

    await tester.tap(find.byKey(const Key('bh06c-confirm-pay1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Đồng ý'));
    await tester.pumpAndSettle();

    verify(() => repo.confirmPayment(
          requestId: any(named: 'requestId'),
          paymentId: 'pay1',
        )).called(1);
    expect(find.text('Đã xác nhận thanh toán.'), findsOneWidget);
    expect(financeCalls, greaterThanOrEqualTo(3));
  });

  testWidgets('player: huong dan/QR + gui chuyen khoan qua provider that',
      (tester) async {
    when(() => repo.getPaymentInstructions('s1'))
        .thenAnswer((_) async => instructions());
    when(() => repo.submitPayment(
          requestId: any(named: 'requestId'),
          playerId: 'p1',
          amountVnd: 225000,
          method: 'bank_transfer',
          reference: null,
        )).thenAnswer((_) async => PaymentResult.fromJson({
          'payment_id': 'pay-submit',
          'player_id': 'p1',
          'session_id': 's1',
          'amount_vnd': 225000,
          'method': 'bank_transfer',
          'status': 'submitted',
          'reference': 'PAY-SUBMIT',
          'billing_state': 'current',
        }));

    final financeProvider = provider();
    await pumpScreen(tester, playerSession, financeProvider);
    await tester.pumpAndSettle();

    expect(find.text('Chuyển khoản để thanh toán'), findsOneWidget);
    expect(find.byKey(const Key('bh06c-qr')), findsOneWidget);
    expect(find.text('BH-TEST0001'), findsOneWidget);

    await tester.tap(find.byKey(const Key('bh06c-submit-payment')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Đồng ý'));
    await tester.pumpAndSettle();

    verify(() => repo.submitPayment(
          requestId: any(named: 'requestId'),
          playerId: 'p1',
          amountVnd: 225000,
          method: 'bank_transfer',
          reference: null,
        )).called(1);
    expect(find.text('Đã ghi nhận, chờ ban quản lý xác nhận.'), findsOneWidget);
  });
}
