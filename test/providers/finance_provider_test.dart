import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide Session;

import 'package:badminton_hub/data/finance_repository.dart';
import 'package:badminton_hub/models/finance.dart';
import 'package:badminton_hub/models/session.dart';
import 'package:badminton_hub/providers/auth_provider.dart';
import 'package:badminton_hub/providers/finance_provider.dart';

class MockFinanceRepository extends Mock implements FinanceRepository {}

class FakeAuth extends Mock implements AuthProvider {
  final callbacks = <VoidCallback>[];
  User? user;

  @override
  User? get currentUser => user;

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
  late MockFinanceRepository repo;
  late FakeAuth auth;

  const sessionFinance = SessionFinance(
    sessionId: 's1',
    clubId: 'c1',
    lifecycle: 'in_progress',
    billingState: 'current',
    billingInputVersion: 4,
    activeRevision: FinanceRevision(
      revisionId: 'r1',
      revisionNo: 1,
      sourceVersion: 4,
      allocationTotalVnd: 450000,
    ),
    expensesTotalVnd: 450000,
    outstandingTotalVnd: 450000,
  );

  const sessionSummary = SessionSummary(
    sessionId: 's1',
    title: 'Buổi tối',
    clubId: 'c1',
    lifecycle: 'completed',
    sessionVersion: 7,
    canManage: true,
    canViewFinance: true,
    presentCount: 6,
    noShowCount: 1,
    confirmedCount: 7,
    billingState: 'current',
    activeRevisionId: 'r1',
    revisionNo: 2,
    sourceVersion: 7,
    expensesTotalVnd: 0,
    amountDueTotalVnd: 420000,
    totalPaidVnd: 400000,
    outstandingTotalVnd: 20000,
  );

  const ledger = ClubLedger(
    clubId: 'c1',
    balanceVnd: 1550000,
    limit: 20,
    entries: [
      ClubLedgerEntry(
        transactionId: 't1',
        direction: 'income',
        amountVnd: 200000,
      ),
    ],
  );

  const instructions = PaymentInstructions(
    sessionId: 's1',
    playerId: 'p1',
    amountDueVnd: 65000,
    outstandingVnd: 65000,
    reference: 'BH-ABC123',
    receiverSnapshot: {
      'bank_code': '970422',
      'account_number': '123456789',
      'account_name': 'NGUYEN VAN A',
    },
    hasReceiver: true,
    canPay: true,
  );

  setUp(() {
    repo = MockFinanceRepository();
    auth = FakeAuth();
  });

  FinanceProvider buildProvider() {
    return FinanceProvider(repository: repo, auth: auth);
  }

  void stubFinance(SessionFinance result) {
    when(
      () => repo.getSessionFinance(
        any(),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) async => result);
  }

  void stubSummary(String sessionId, SessionSummary result) {
    when(() => repo.getSessionSummary(sessionId))
        .thenAnswer((_) async => result);
  }

  void stubLedger(String clubId, ClubLedger result) {
    when(
      () => repo.getClubLedger(
        clubId,
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) async => result);
  }

  test('khởi tạo rỗng và không loading', () {
    final provider = buildProvider();
    expect(provider.finance, isNull);
    expect(provider.ledger, isNull);
    expect(provider.paymentInstructions, isNull);
    expect(provider.isLoadingFinance, isFalse);
    expect(provider.isSubmitting, isFalse);
    provider.dispose();
  });

  test('lỗi đọc tài chính giữ số cũ, KHÔNG hạ công nợ về 0', () async {
    stubFinance(sessionFinance);
    final provider = buildProvider();
    await provider.fetchSessionFinance('s1');
    expect(provider.finance?.outstandingTotalVnd, 450000);

    when(
      () => repo.getSessionFinance(
        's1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenThrow(Exception('PostgrestException(FORBIDDEN: raw pg detail)'));

    await provider.fetchSessionFinance('s1');

    expect(provider.finance, isNotNull);
    expect(
      provider.finance?.outstandingTotalVnd,
      450000,
      reason: 'lỗi đọc không được biến công nợ thành 0',
    );
    expect(
      provider.financeErrorMessage,
      'Bạn không có quyền thực hiện thao tác này.',
    );
    provider.dispose();
  });

  test('lỗi đọc sổ quỹ giữ số dư cũ, không hạ về 0', () async {
    stubLedger('c1', ledger);
    final provider = buildProvider();
    await provider.fetchClubLedger('c1');
    expect(provider.ledger?.balanceVnd, 1550000);

    when(
      () => repo.getClubLedger(
        'c1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenThrow(Exception('PostgrestException(FORBIDDEN: raw)'));

    await provider.fetchClubLedger('c1');

    expect(provider.ledger?.balanceVnd, 1550000);
    expect(provider.ledgerErrorMessage, isNotNull);
    provider.dispose();
  });

  test('loadMoreLedger nối trang đầy bằng offset đã có, không nhân đôi', () async {
    final offsets = <int>[];
    when(
      () => repo.getClubLedger(
        'c1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((invocation) async {
      final offset = invocation.namedArguments[#offset] as int;
      final limit = invocation.namedArguments[#limit] as int;
      offsets.add(offset);
      return ClubLedger(
        clubId: 'c1',
        balanceVnd: offset == 0 ? 1550000 : 1400000,
        limit: limit,
        offset: offset,
        entries: offset == 0
            ? const [
                ClubLedgerEntry(
                  transactionId: 't1',
                  direction: 'income',
                  amountVnd: 200000,
                ),
                ClubLedgerEntry(
                  transactionId: 't2',
                  direction: 'income',
                  amountVnd: 300000,
                ),
              ]
            : const [
                ClubLedgerEntry(
                  transactionId: 't3',
                  direction: 'expense',
                  amountVnd: 150000,
                ),
              ],
      );
    });

    final provider = buildProvider();
    await provider.fetchClubLedger('c1', limit: 2);
    expect(provider.ledger?.entries, hasLength(2));
    expect(provider.hasMoreLedger, isTrue);

    await provider.loadMoreLedger();

    expect(offsets, [0, 2]);
    expect(provider.ledger?.entries, hasLength(3));
    expect(provider.ledger?.entries.last.transactionId, 't3');
    expect(provider.isLoadingMoreLedger, isFalse);
    provider.dispose();
  });

  test('đổi CLB xoá dữ liệu CLB cũ và tải lại từ đầu', () async {
    stubLedger('c1', ledger);
    stubLedger(
      'c2',
      const ClubLedger(clubId: 'c2', balanceVnd: 500, entries: []),
    );

    final provider = buildProvider();
    await provider.fetchClubLedger('c1');
    expect(provider.ledger?.balanceVnd, 1550000);

    await provider.fetchClubLedger('c2');
    expect(provider.ledgerClubId, 'c2');
    expect(provider.ledger?.balanceVnd, 500);
    provider.dispose();
  });

  test('đổi user/đăng xuất dọn state riêng tư', () async {
    stubFinance(sessionFinance);
    stubLedger('c1', ledger);
    when(
      () => repo.getPaymentInstructions(
        any(),
        playerId: any(named: 'playerId'),
      ),
    ).thenAnswer((_) async => instructions);

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionFinance('s1');
    await provider.fetchClubLedger('c1');
    await provider.fetchPaymentInstructions('s1');
    expect(provider.finance, isNotNull);
    expect(provider.ledger, isNotNull);
    expect(provider.paymentInstructions, isNotNull);

    auth.changeUser(null);

    expect(provider.finance, isNull);
    expect(provider.ledger, isNull);
    expect(provider.paymentInstructions, isNull);
    expect(provider.submitErrorMessage, isNull);
    provider.dispose();
  });

  test('đổi buổi loại bỏ phản hồi trễ của buổi cũ', () async {
    final slow = Completer<SessionFinance>();
    when(
      () => repo.getSessionFinance(
        's1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) => slow.future);
    when(
      () => repo.getSessionFinance(
        's2',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer(
      (_) async => const SessionFinance(sessionId: 's2', outstandingTotalVnd: 9),
    );

    final provider = buildProvider();
    final pending = provider.fetchSessionFinance('s1');
    await provider.fetchSessionFinance('s2');

    slow.complete(sessionFinance);
    await pending;

    expect(provider.finance?.sessionId, 's2');
    expect(
      provider.finance?.outstandingTotalVnd,
      9,
      reason: 'phản hồi trễ của buổi cũ không được ghi đè',
    );
    provider.dispose();
  });

  test('postExpense giữ request_id khi lỗi, xoay key sau thành công', () async {
    stubFinance(sessionFinance);
    final keys = <String>[];
    var attempts = 0;
    when(
      () => repo.postSessionExpense(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        category: any(named: 'category'),
        title: any(named: 'title'),
        amountVnd: any(named: 'amountVnd'),
      ),
    ).thenAnswer((invocation) async {
      keys.add(invocation.namedArguments[#requestId] as String);
      attempts++;
      if (attempts == 1) throw Exception('timeout');
      return const ExpenseResult(
        expenseId: 'e1',
        sessionId: 's1',
        amountVnd: 450000,
      );
    });

    final provider = buildProvider();
    await provider.fetchSessionFinance('s1');

    final first = await provider.postExpense(
      sessionId: 's1',
      category: 'court',
      title: 'Tiền sân',
      amountVnd: 450000,
    );
    expect(first, isNull);
    expect(provider.submitErrorMessage, isNotNull);

    final second = await provider.postExpense(
      sessionId: 's1',
      category: 'court',
      title: 'Tiền sân',
      amountVnd: 450000,
    );
    expect(second, isNotNull);
    expect(keys.first, keys[1], reason: 'retry cùng payload dùng lại UUID');

    await provider.postExpense(
      sessionId: 's1',
      category: 'court',
      title: 'Tiền sân',
      amountVnd: 450000,
    );
    expect(
      keys[2],
      isNot(keys[1]),
      reason: 'sau commit thành công phải xoay UUID',
    );
    verify(
      () => repo.getSessionFinance(
        's1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).called(greaterThan(1));
    provider.dispose();
  });

  test('finalizeCharges gửi đúng version + billing_input_version', () async {
    when(
      () => repo.finalizeSessionCharges(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        expectedVersion: any(named: 'expectedVersion'),
        expectedBillingInputVersion: any(named: 'expectedBillingInputVersion'),
        reason: any(named: 'reason'),
      ),
    ).thenAnswer(
      (_) async => const RevisionResult(
        revisionId: 'r1',
        sessionId: 's1',
        revisionNo: 1,
        allocationTotalVnd: 450000,
        billingState: 'current',
      ),
    );

    final provider = buildProvider();
    final result = await provider.finalizeCharges(
      sessionId: 's1',
      expectedVersion: 3,
      expectedBillingInputVersion: 4,
      reason: 'chia lại',
    );

    expect(result?.revisionId, 'r1');
    verify(
      () => repo.finalizeSessionCharges(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        expectedVersion: 3,
        expectedBillingInputVersion: 4,
        reason: 'chia lại',
      ),
    ).called(1);
    provider.dispose();
  });

  test('submitPayment stale giữ nguyên lỗi domain, không coi đã thu', () async {
    when(
      () => repo.submitPayment(
        requestId: any(named: 'requestId'),
        playerId: any(named: 'playerId'),
        amountVnd: any(named: 'amountVnd'),
        method: any(named: 'method'),
        reference: any(named: 'reference'),
      ),
    ).thenThrow(Exception('PostgrestException(BILLING_STALE: raw)'));

    final provider = buildProvider();
    final result = await provider.submitPayment(playerId: 'p1', amountVnd: 65000);

    expect(result, isNull);
    expect(
      provider.submitErrorMessage,
      'Phí đã lỗi thời so với thay đổi mới nhất.',
    );
    provider.dispose();
  });

  test('trùng khoá idempotency hiển thị tiếng Việt', () async {
    when(
      () => repo.submitPayment(
        requestId: any(named: 'requestId'),
        playerId: any(named: 'playerId'),
        amountVnd: any(named: 'amountVnd'),
        method: any(named: 'method'),
        reference: any(named: 'reference'),
      ),
    ).thenThrow(Exception('PostgrestException(IDEMPOTENCY_CONFLICT: raw)'));

    final provider = buildProvider();
    await provider.submitPayment(playerId: 'p1', amountVnd: 65000);

    expect(
      provider.submitErrorMessage,
      'Yêu cầu bị trùng khoá với dữ liệu khác.',
    );
    provider.dispose();
  });

  test('chặn double-submit khi đang gửi', () async {
    final completer = Completer<PaymentResult>();
    when(
      () => repo.recordCashPayment(
        requestId: any(named: 'requestId'),
        playerId: any(named: 'playerId'),
        amountVnd: any(named: 'amountVnd'),
        reference: any(named: 'reference'),
      ),
    ).thenAnswer((_) => completer.future);

    final provider = buildProvider();
    final first = provider.recordCashPayment(playerId: 'p1', amountVnd: 65000);
    expect(provider.isSubmitting, isTrue);

    final second = await provider.recordCashPayment(
      playerId: 'p1',
      amountVnd: 65000,
    );
    expect(second, isNull, reason: 'lần nhấn thứ hai bị chặn');

    completer.complete(
      const PaymentResult(
        paymentId: 'pay1',
        playerId: 'p1',
        sessionId: 's1',
        status: 'confirmed',
      ),
    );
    final result = await first;

    expect(result?.isConfirmed, isTrue);
    expect(provider.isSubmitting, isFalse);
    verify(
      () => repo.recordCashPayment(
        requestId: any(named: 'requestId'),
        playerId: any(named: 'playerId'),
        amountVnd: any(named: 'amountVnd'),
        reference: any(named: 'reference'),
      ),
    ).called(1);
    provider.dispose();
  });

  test('mutation thành công khi làm mới lỗi (không báo thất bại theo refresh)',
      () async {
    // Tài chính buổi đang mở nhưng lần đọc kế tiếp bị chặn quyền.
    stubFinance(sessionFinance);
    when(
      () => repo.recordCashPayment(
        requestId: any(named: 'requestId'),
        playerId: any(named: 'playerId'),
        amountVnd: any(named: 'amountVnd'),
        reference: any(named: 'reference'),
      ),
    ).thenAnswer(
      (_) async => const PaymentResult(
        paymentId: 'pay1',
        playerId: 'p1',
        sessionId: 's1',
        status: 'confirmed',
      ),
    );

    final provider = buildProvider();
    await provider.fetchSessionFinance('s1');

    when(
      () => repo.getSessionFinance(
        's1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenThrow(Exception('PostgrestException(FORBIDDEN: raw)'));

    final result = await provider.recordCashPayment(
      playerId: 'p1',
      amountVnd: 65000,
    );

    expect(result?.isConfirmed, isTrue);
    expect(
      provider.submitErrorMessage,
      isNull,
      reason: 'lỗi làm mới không được đánh dấu mutation thất bại',
    );
    expect(provider.financeErrorMessage, isNotNull);
    provider.dispose();
  });

  test('reject/reverse gửi đúng lý do', () async {
    when(
      () => repo.rejectPayment(
        requestId: any(named: 'requestId'),
        paymentId: any(named: 'paymentId'),
        reason: any(named: 'reason'),
      ),
    ).thenAnswer(
      (_) async => const PaymentResult(
        paymentId: 'pay1',
        playerId: 'p1',
        sessionId: 's1',
        status: 'rejected',
      ),
    );
    when(
      () => repo.reversePayment(
        requestId: any(named: 'requestId'),
        paymentId: any(named: 'paymentId'),
        reason: any(named: 'reason'),
      ),
    ).thenAnswer(
      (_) async => const PaymentResult(
        paymentId: 'pay1',
        playerId: 'p1',
        sessionId: 's1',
        status: 'reversed',
      ),
    );

    final provider = buildProvider();
    final rejected = await provider.rejectPayment(
      paymentId: 'pay1',
      reason: 'Sai số tiền',
    );
    expect(rejected?.isRejected, isTrue);
    verify(
      () => repo.rejectPayment(
        requestId: any(named: 'requestId'),
        paymentId: 'pay1',
        reason: 'Sai số tiền',
      ),
    ).called(1);

    final reversed = await provider.reversePayment(
      paymentId: 'pay1',
      reason: 'Hoàn do huỷ buổi',
    );
    expect(reversed?.isReversed, isTrue);
    verify(
      () => repo.reversePayment(
        requestId: any(named: 'requestId'),
        paymentId: 'pay1',
        reason: 'Hoàn do huỷ buổi',
      ),
    ).called(1);
    provider.dispose();
  });

  test('postManualClubTransaction làm mới sổ quỹ đang mở', () async {
    stubLedger('c1', ledger);
    when(
      () => repo.postManualClubTransaction(
        requestId: any(named: 'requestId'),
        clubId: any(named: 'clubId'),
        direction: any(named: 'direction'),
        amountVnd: any(named: 'amountVnd'),
        title: any(named: 'title'),
      ),
    ).thenAnswer(
      (_) async => const ClubTransactionResult(
        transactionId: 't9',
        clubId: 'c1',
        direction: 'income',
        amountVnd: 200000,
        balanceVnd: 1750000,
        sourceType: 'manual',
      ),
    );

    final provider = buildProvider();
    await provider.fetchClubLedger('c1');

    final result = await provider.postManualClubTransaction(
      clubId: 'c1',
      direction: 'income',
      amountVnd: 200000,
      title: 'Thu quỹ tháng 10',
    );

    expect(result?.transactionId, 't9');
    verify(
      () => repo.getClubLedger(
        'c1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).called(2);
    provider.dispose();
  });

  test('completeSession trả buổi đã kết thúc', () async {
    when(
      () => repo.completeSession(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        expectedVersion: any(named: 'expectedVersion'),
      ),
    ).thenAnswer(
      (_) async => const Session(
        id: 's2',
        title: 'Buổi test',
        capacity: 8,
        lifecycle: 'completed',
        version: 2,
      ),
    );

    final provider = buildProvider();
    final result = await provider.completeSession(
      sessionId: 's2',
      expectedVersion: 1,
    );

    expect(result?.lifecycle, 'completed');
    verify(
      () => repo.completeSession(
        requestId: any(named: 'requestId'),
        sessionId: 's2',
        expectedVersion: 1,
      ),
    ).called(1);
    provider.dispose();
  });

  test('fetchPaymentInstructions giữ lỗi chưa chốt phí, không thành đã trả',
      () async {
    when(
      () => repo.getPaymentInstructions(
        any(),
        playerId: any(named: 'playerId'),
      ),
    ).thenThrow(Exception('PostgrestException(BILLING_NOT_FINALIZED: raw)'));

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchPaymentInstructions('s1');

    expect(provider.paymentInstructions, isNull);
    expect(
      provider.instructionsErrorMessage,
      'Buổi chơi chưa chốt phí.',
    );
    provider.dispose();
  });

  // --- Sửa theo review vòng 1 (B1/B2) ------------------------------------- //

  test('B1: BILLING_STALE vô hiệu cache hướng dẫn thanh toán đang current',
      () async {
    var attempts = 0;
    when(
      () => repo.getPaymentInstructions(
        's1',
        playerId: any(named: 'playerId'),
      ),
    ).thenAnswer((_) async {
      attempts++;
      if (attempts > 1) {
        throw Exception('PostgrestException(BILLING_STALE: raw)');
      }
      return instructions;
    });

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchPaymentInstructions('s1');
    expect(provider.paymentInstructions?.canPay, isTrue);

    await provider.fetchPaymentInstructions('s1');

    expect(provider.instructionsErrorMessage, isNotNull);
    expect(provider.isLoadingInstructions, isFalse);
    expect(
      provider.paymentInstructions,
      isNull,
      reason: 'server từ chối revision current thì không giữ chỉ dẫn có thể trả',
    );
    provider.dispose();
  });

  test('B2: trang cuối ngắn phải kết thúc phân trang ledger', () async {
    when(
      () => repo.getClubLedger(
        'c1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((invocation) async {
      final offset = invocation.namedArguments[#offset] as int;
      final limit = invocation.namedArguments[#limit] as int;
      return ClubLedger(
        clubId: 'c1',
        limit: limit,
        offset: offset,
        entries: offset == 0
            ? const [
                ClubLedgerEntry(transactionId: 't1'),
                ClubLedgerEntry(transactionId: 't2'),
              ]
            : const [ClubLedgerEntry(transactionId: 't3')],
      );
    });

    final provider = buildProvider();
    await provider.fetchClubLedger('c1', limit: 2);
    expect(provider.hasMoreLedger, isTrue);

    await provider.loadMoreLedger();

    expect(provider.ledger?.entries, hasLength(3));
    expect(
      provider.hasMoreLedger,
      isFalse,
      reason: 'trang vừa nhận chỉ 1 < limit 2 nên đã hết trang',
    );
    provider.dispose();
  });

  test('B2: sổ quỹ đã hết thì loadMore không phát RPC', () async {
    var calls = 0;
    when(
      () => repo.getClubLedger(
        'c1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((invocation) async {
      calls++;
      return ClubLedger(
        clubId: 'c1',
        limit: invocation.namedArguments[#limit] as int,
        offset: invocation.namedArguments[#offset] as int,
        entries: calls == 1
            ? const [ClubLedgerEntry(transactionId: 't1')]
            : const [],
      );
    });

    final provider = buildProvider();
    await provider.fetchClubLedger('c1', limit: 2);
    expect(provider.hasMoreLedger, isFalse);

    await provider.loadMoreLedger();

    expect(calls, 1, reason: 'hết dữ liệu thì loadMore không gọi thêm RPC');
    provider.dispose();
  });

  test('B2-R1: loadMore bị bỏ qua không được huỷ refresh đang bay', () async {
    var calls = 0;
    final refreshing = Completer<ClubLedger>();
    when(
      () => repo.getClubLedger(
        'c1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) async {
      calls++;
      if (calls > 1) return refreshing.future;
      return const ClubLedger(
        clubId: 'c1',
        limit: 2,
        balanceVnd: 100,
        entries: [ClubLedgerEntry(transactionId: 't1')],
      );
    });

    final provider = buildProvider();
    await provider.fetchClubLedger('c1', limit: 2);
    expect(provider.hasMoreLedger, isFalse);

    // Refresh cùng CLB đang bay (response bị trì hoãn).
    final pending = provider.fetchClubLedger('c1', limit: 2);
    expect(provider.isLoadingLedger, isTrue);

    // Gọi load-more trực tiếp khi đã hết trang: phải bị bỏ qua, không RPC.
    await provider.fetchClubLedger('c1', limit: 2, loadMore: true);
    expect(calls, 2, reason: 'bỏ qua phân trang đã hết thì không phát RPC');

    refreshing.complete(
      const ClubLedger(
        clubId: 'c1',
        limit: 2,
        balanceVnd: 200,
        entries: [
          ClubLedgerEntry(transactionId: 't1'),
          ClubLedgerEntry(transactionId: 't2'),
        ],
      ),
    );
    await pending;

    expect(
      provider.isLoadingLedger,
      isFalse,
      reason: 'yêu cầu bị bỏ qua không được tăng serial bỏ rơi finally refresh',
    );
    expect(
      provider.ledger?.balanceVnd,
      200,
      reason: 'refresh hợp lệ vẫn phải cập nhật số dư mới',
    );
    provider.dispose();
  });

  // --- BH-07B: tổng kết + complete --------------------------------------- //

  test('summary: load, lỗi giữ aggregate cũ, retry phục hồi', () async {
    stubSummary('s1', sessionSummary);
    final provider = buildProvider();
    auth.changeUser('user-a');

    await provider.fetchSessionSummary('s1');
    expect(provider.sessionSummary?.outstandingTotalVnd, 20000);
    expect(provider.sessionSummary?.sessionVersion, 7);
    expect(provider.isLoadingSummary, isFalse);
    expect(provider.summaryErrorMessage, isNull);

    when(() => repo.getSessionSummary('s1'))
        .thenThrow(Exception('PostgrestException(FORBIDDEN: raw)'));
    await provider.fetchSessionSummary('s1');
    expect(
      provider.sessionSummary?.outstandingTotalVnd,
      20000,
      reason: 'lỗi đọc cùng buổi không được hạ tiền về 0/xoá aggregate',
    );
    expect(
      provider.summaryErrorMessage,
      'Bạn không có quyền thực hiện thao tác này.',
    );

    stubSummary('s1', sessionSummary);
    await provider.fetchSessionSummary('s1');
    expect(provider.summaryErrorMessage, isNull);
    expect(provider.hasSummary, isTrue);
    provider.dispose();
  });

  test('summary: management-only giữ tiền NULL, không biến thành 0', () async {
    stubSummary(
      's1',
      const SessionSummary(
        sessionId: 's1',
        lifecycle: 'completed',
        canManage: true,
        presentCount: 3,
        confirmedCount: 3,
      ),
    );
    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionSummary('s1');

    expect(provider.sessionSummary?.hasFinanceView, isFalse);
    expect(provider.sessionSummary?.billingState, isNull);
    expect(provider.sessionSummary?.expensesTotalVnd, isNull);
    expect(provider.sessionSummary?.amountDueTotalVnd, isNull);
    expect(provider.sessionSummary?.totalPaidVnd, isNull);
    expect(provider.sessionSummary?.outstandingTotalVnd, isNull);
    provider.dispose();
  });

  test('summary: đổi buổi xoá dữ liệu cũ và bỏ phản hồi đến trễ', () async {
    final slow = Completer<SessionSummary>();
    when(() => repo.getSessionSummary('s1')).thenAnswer((_) => slow.future);
    when(() => repo.getSessionSummary('s2')).thenAnswer(
      (_) async => const SessionSummary(
        sessionId: 's2',
        lifecycle: 'completed',
        outstandingTotalVnd: 9,
      ),
    );

    final provider = buildProvider();
    auth.changeUser('user-a');
    final pending = provider.fetchSessionSummary('s1');
    await provider.fetchSessionSummary('s2');

    slow.complete(sessionSummary);
    await pending;

    expect(provider.summarySessionId, 's2');
    expect(provider.sessionSummary?.sessionId, 's2');
    expect(provider.sessionSummary?.outstandingTotalVnd, 9);
    expect(provider.isLoadingSummary, isFalse);
    provider.dispose();
  });

  test(
    'summary: logout/đổi actor dọn state, phản hồi cũ không khôi phục',
    () async {
      final slow = Completer<SessionSummary>();
      when(() => repo.getSessionSummary('s1')).thenAnswer((_) => slow.future);

      final provider = buildProvider();
      auth.changeUser('user-a');
      final pending = provider.fetchSessionSummary('s1');
      auth.changeUser(null);

      expect(provider.sessionSummary, isNull);
      expect(provider.summarySessionId, isNull);
      expect(provider.isLoadingSummary, isFalse);

      slow.complete(sessionSummary);
      await pending;
      expect(provider.sessionSummary, isNull);
      provider.dispose();
    },
  );

  test(
    'summary: đổi actor A→B xoá state của actor cũ',
    () async {
      stubSummary('s1', sessionSummary);
      final provider = buildProvider();
      auth.changeUser('user-a');
      await provider.fetchSessionSummary('s1');
      expect(provider.hasSummary, isTrue);

      auth.changeUser('user-b');
      expect(provider.sessionSummary, isNull);
      expect(provider.summarySessionId, isNull);
      expect(provider.summaryErrorMessage, isNull);
      provider.dispose();
    },
  );

  test(
    'summary: mutation tiền làm mới summary đang mở, không gọi ngoài scope',
    () async {
      stubSummary('s1', sessionSummary);
      when(
        () => repo.recordCashPayment(
          requestId: any(named: 'requestId'),
          playerId: any(named: 'playerId'),
          amountVnd: any(named: 'amountVnd'),
          reference: any(named: 'reference'),
        ),
      ).thenAnswer(
        (_) async => const PaymentResult(
          paymentId: 'pay1',
          playerId: 'p1',
          sessionId: 's1',
          status: 'confirmed',
        ),
      );

      final provider = buildProvider();
      auth.changeUser('user-a');
      await provider.recordCashPayment(playerId: 'p1', amountVnd: 10000);
      verifyNever(() => repo.getSessionSummary(any()));

      await provider.fetchSessionSummary('s1');
      await provider.recordCashPayment(playerId: 'p1', amountVnd: 10000);
      verify(() => repo.getSessionSummary('s1')).called(2);
      provider.dispose();
    },
  );

  test(
    'complete: stale trả null/error, retry giữ request_id rồi xoay key',
    () async {
      final keys = <String>[];
      var attempts = 0;
      when(
        () => repo.completeSession(
          requestId: any(named: 'requestId'),
          sessionId: any(named: 'sessionId'),
          expectedVersion: any(named: 'expectedVersion'),
        ),
      ).thenAnswer((invocation) async {
        keys.add(invocation.namedArguments[#requestId] as String);
        attempts++;
        if (attempts == 1) {
          throw Exception('PostgrestException(VERSION_CONFLICT: raw)');
        }
        return const Session(
          id: 's2',
          title: 'Buổi xong',
          lifecycle: 'completed',
          version: 2,
        );
      });

      final provider = buildProvider();
      final failed = await provider.completeSession(
        sessionId: 's2',
        expectedVersion: 1,
      );
      expect(
        failed,
        isNull,
        reason: 'VERSION_CONFLICT không được báo thành công',
      );
      expect(
        provider.submitErrorMessage,
        'Buổi chơi đã được thay đổi ở nơi khác. Vui lòng tải lại.',
      );

      final retried = await provider.completeSession(
        sessionId: 's2',
        expectedVersion: 1,
      );
      expect(retried?.isCompleted, isTrue);
      expect(keys.first, keys[1], reason: 'retry cùng intent dùng lại UUID');

      await provider.completeSession(sessionId: 's2', expectedVersion: 1);
      expect(keys[2], isNot(keys[1]), reason: 'thành công xong mới xoay UUID');
      provider.dispose();
    },
  );
}
