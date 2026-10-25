import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide Session;

import 'package:badminton_hub/data/finance_repository.dart';
import 'package:badminton_hub/data/session_repository.dart';
import 'package:badminton_hub/data/club_repository.dart';
import 'package:badminton_hub/models/finance.dart';
import 'package:badminton_hub/models/session.dart';
import 'package:badminton_hub/models/club.dart';
import 'package:badminton_hub/providers/auth_provider.dart';
import 'package:badminton_hub/providers/finance_provider.dart';
import 'package:badminton_hub/providers/session_provider.dart';
import 'package:badminton_hub/providers/club_provider.dart';

class MockFinanceRepository extends Mock implements FinanceRepository {}
class MockSessionRepository extends Mock implements SessionRepository {}
class MockClubRepository extends Mock implements ClubRepository {}

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

/// Ép buộc Dart VM thực hiện generational GC (Scavenge + Mark-Sweep)
/// thông qua memory allocation pressure và microtask flushing.
Future<void> triggerGc() async {
  await Future<void>.delayed(Duration.zero);
  for (int i = 0; i < 6; i++) {
    // Allocation of transient objects forces generational GC
    final pressure = List<List<int>>.generate(200, (_) => List<int>.filled(5000, 1));
    if (pressure.isEmpty) return;
    await Future<void>.delayed(const Duration(milliseconds: 15));
  }
  await Future<void>.delayed(const Duration(milliseconds: 50));
}

// Fixtures tạo động trên Heap (KHÔNG const, tương đương payload parse từ HTTP)
PaymentInstructions createDynamicOwnerInstructions() => PaymentInstructions.fromJson(<String, dynamic>{
      'session_id': 's1',
      'player_id': 'p_owner',
      'display_name': 'Owner Player',
      'billing_state': 'current',
      'active_revision_id': 'rev_owner_1',
      'source_version': 4,
      'amount_due_vnd': 75000,
      'total_paid_vnd': 0,
      'outstanding_vnd': 75000,
      'reference': 'BH-OWNER-QR7788',
      'receiver_snapshot': <String, dynamic>{
        'bank_code': '970422',
        'account_number': '0123456789',
        'account_name': 'CHU SAN CAU LONG',
      },
      'has_receiver': true,
      'can_pay': true,
    });

SessionFinance createDynamicOwnerFinance() => SessionFinance.fromJson(<String, dynamic>{
      'session_id': 's1',
      'club_id': 'c1',
      'lifecycle': 'in_progress',
      'billing_state': 'current',
      'billing_input_version': 4,
      'active_revision': <String, dynamic>{
        'revision_id': 'rev_owner_1',
        'revision_no': 1,
        'source_version': 4,
        'allocation_total_vnd': 500000,
      },
      'expenses_total_vnd': 500000,
      'outstanding_total_vnd': 500000,
    });

SessionSummary createDynamicOwnerSummary() => SessionSummary.fromJson(<String, dynamic>{
      'session_id': 's1',
      'title': 'Buổi thi đấu CLB',
      'club_id': 'c1',
      'lifecycle': 'completed',
      'session_version': 7,
      'can_manage': true,
      'can_view_finance': true,
      'present_count': 8,
      'no_show_count': 0,
      'confirmed_count': 8,
      'billing_state': 'current',
      'active_revision_id': 'rev_owner_1',
      'revision_no': 2,
      'source_version': 7,
      'expenses_total_vnd': 500000,
      'amount_due_total_vnd': 500000,
      'total_paid_vnd': 425000,
      'outstanding_total_vnd': 75000,
    });

ClubLedger createDynamicOwnerLedger() => ClubLedger.fromJson(<String, dynamic>{
      'club_id': 'c1',
      'balance_vnd': 2500000,
      'limit': 20,
      'entries': <Map<String, dynamic>>[
        <String, dynamic>{
          'transaction_id': 'tx_owner_1',
          'direction': 'income',
          'amount_vnd': 500000,
          'title': 'Nạp quỹ nội bộ Owner',
        },
      ],
    });

SessionSummary createDynamicCohostSummary() => SessionSummary.fromJson(<String, dynamic>{
      'session_id': 's1',
      'title': 'Buổi thi đấu CLB',
      'lifecycle': 'completed',
      'can_manage': true,
      'can_view_finance': false,
      'present_count': 8,
      'confirmed_count': 8,
      'expenses_total_vnd': null,
      'amount_due_total_vnd': null,
      'total_paid_vnd': null,
      'outstanding_total_vnd': null,
    });

PaymentInstructions createDynamicMemberInstructions() => PaymentInstructions.fromJson(<String, dynamic>{
      'session_id': 's1',
      'player_id': 'p_member',
      'display_name': 'Regular Member',
      'billing_state': 'current',
      'amount_due_vnd': 60000,
      'outstanding_vnd': 60000,
      'reference': 'BH-MEMBER-QR1122',
      'has_receiver': true,
      'can_pay': true,
    });

// Helper functions: chạy trong stack frame riêng để khi pop ra khỏi stack,
// không để lại strong reference nào trong stack của hàm test chính.
Future<({
  WeakReference<PaymentInstructions> instructions,
  WeakReference<SessionFinance> finance,
  WeakReference<SessionSummary> summary,
  WeakReference<ClubLedger> ledger,
})> loadOwnerEpoch(FinanceProvider provider, MockFinanceRepository repo) async {
  when(() => repo.getPaymentInstructions('s1', playerId: any(named: 'playerId')))
      .thenAnswer((_) async => createDynamicOwnerInstructions());
  when(() => repo.getSessionFinance('s1', limit: any(named: 'limit'), offset: any(named: 'offset')))
      .thenAnswer((_) async => createDynamicOwnerFinance());
  when(() => repo.getSessionSummary('s1'))
      .thenAnswer((_) async => createDynamicOwnerSummary());
  when(() => repo.getClubLedger('c1', limit: any(named: 'limit'), offset: any(named: 'offset')))
      .thenAnswer((_) async => createDynamicOwnerLedger());

  await provider.fetchPaymentInstructions('s1');
  await provider.fetchSessionFinance('s1');
  await provider.fetchSessionSummary('s1');
  await provider.fetchClubLedger('c1');

  return (
    instructions: WeakReference(provider.paymentInstructions!),
    finance: WeakReference(provider.finance!),
    summary: WeakReference(provider.sessionSummary!),
    ledger: WeakReference(provider.ledger!),
  );
}

Future<WeakReference<SessionSummary>> loadCohostEpoch(
  FinanceProvider provider,
  MockFinanceRepository repo,
) async {
  when(() => repo.getSessionSummary('s1')).thenAnswer((_) async => createDynamicCohostSummary());
  await provider.fetchSessionSummary('s1');
  return WeakReference(provider.sessionSummary!);
}

Future<WeakReference<PaymentInstructions>> loadMemberEpoch(
  FinanceProvider provider,
  MockFinanceRepository repo,
) async {
  when(() => repo.getPaymentInstructions('s1', playerId: any(named: 'playerId')))
      .thenAnswer((_) async => createDynamicMemberInstructions());
  await provider.fetchPaymentInstructions('s1', playerId: 'p_member');
  return WeakReference(provider.paymentInstructions!);
}

Future<WeakReference<SessionSummary>> simulateLateResponseAfterLogout(
  FinanceProvider provider,
  MockFinanceRepository repo,
  FakeAuth auth,
) async {
  auth.changeUser('owner-id-1234');
  Completer<SessionSummary>? slowCompleter = Completer<SessionSummary>();
  when(() => repo.getSessionSummary('s1')).thenAnswer((_) => slowCompleter!.future);

  Future<void>? pendingFuture = provider.fetchSessionSummary('s1');

  // Owner logs out while request is in-flight
  auth.changeUser(null);
  reset(repo);

  final payload = createDynamicOwnerSummary();
  final weakLatePayload = WeakReference(payload);

  slowCompleter.complete(payload);
  await pendingFuture;

  slowCompleter = null;
  pendingFuture = null;

  return weakLatePayload;
}

Future<WeakReference<SessionSummary>> simulateLateResponseAfterActorSwitch(
  FinanceProvider provider,
  MockFinanceRepository repo,
  FakeAuth auth,
) async {
  auth.changeUser('owner-id-1234');
  Completer<SessionSummary>? slowCompleter = Completer<SessionSummary>();
  when(() => repo.getSessionSummary('s1')).thenAnswer((_) => slowCompleter!.future);

  Future<void>? pendingFuture = provider.fetchSessionSummary('s1');

  // Actor switches to Member while request in-flight
  auth.changeUser('member-id-9999');
  reset(repo);

  final payload = createDynamicOwnerSummary();
  final weakLatePayload = WeakReference(payload);

  slowCompleter.complete(payload);
  await pendingFuture;

  slowCompleter = null;
  pendingFuture = null;

  return weakLatePayload;
}

void main() {
  late MockFinanceRepository financeRepo;
  late MockSessionRepository sessionRepo;
  late MockClubRepository clubRepo;
  late FakeAuth auth;

  late FinanceProvider financeProvider;
  late SessionProvider sessionProvider;
  late ClubProvider clubProvider;

  setUp(() {
    financeRepo = MockFinanceRepository();
    sessionRepo = MockSessionRepository();
    clubRepo = MockClubRepository();
    auth = FakeAuth();

    // Dựng toàn bộ providers trong CÙNG MỘT APPLICATION INSTANCE
    financeProvider = FinanceProvider(repository: financeRepo, auth: auth);
    sessionProvider = SessionProvider(repository: sessionRepo, auth: auth);
    clubProvider = ClubProvider(repository: clubRepo, auth: auth);
  });

  tearDown(() {
    financeProvider.dispose();
    sessionProvider.dispose();
    clubProvider.dispose();
  });

  group('V2b — Private Dart Heap / In-Memory Retention & Isolation Verification', () {
    test('Baseline Epoch: Initial providers state is empty, zero retained objects', () {
      expect(financeProvider.paymentInstructions, isNull);
      expect(financeProvider.finance, isNull);
      expect(financeProvider.sessionSummary, isNull);
      expect(financeProvider.ledger, isNull);
      expect(sessionProvider.currentSession, isNull);
      expect(clubProvider.currentClub, isNull);
    });

    test(
      'Full Cycle: Owner -> Logout -> Cohost -> Member retains NO sensitive Owner objects in Dart heap',
      () async {
        // =====================================================================
        // EPOCH 1: Owner Login & Finance Load (Positive Control P1)
        // =====================================================================
        auth.changeUser('owner-id-1234');

        final ownerRefs = await loadOwnerEpoch(financeProvider, financeRepo);

        // Positive Control P1: Verify instances exist and are strongly retained in Provider
        expect(ownerRefs.instructions.target, isNotNull, reason: 'P1: Owner instructions must be in heap');
        expect(ownerRefs.finance.target, isNotNull, reason: 'P1: Owner finance must be in heap');
        expect(ownerRefs.summary.target, isNotNull, reason: 'P1: Owner summary must be in heap');
        expect(ownerRefs.ledger.target, isNotNull, reason: 'P1: Owner ledger must be in heap');

        // =====================================================================
        // EPOCH 2: Owner Logout (Negative Control N1 - Memory Purge)
        // =====================================================================
        // Reset mock stubs so mock repo does not retain closures
        reset(financeRepo);

        auth.changeUser(null); // Trigger logout & _onAuthChanged()

        // Verify fields in provider are nullified immediately
        expect(financeProvider.paymentInstructions, isNull);
        expect(financeProvider.finance, isNull);
        expect(financeProvider.sessionSummary, isNull);
        expect(financeProvider.ledger, isNull);
        expect(financeProvider.instructionsSessionId, isNull);
        expect(financeProvider.financeSessionId, isNull);
        expect(financeProvider.summarySessionId, isNull);
        expect(financeProvider.ledgerClubId, isNull);

        // Force Garbage Collection on Dart VM
        await triggerGc();

        // Negative Control N1: All Owner sensitive objects must be collected by GC!
        expect(ownerRefs.instructions.target, isNull,
            reason: 'N1: Owner PaymentInstructions must be GC-collected after logout');
        expect(ownerRefs.finance.target, isNull,
            reason: 'N1: Owner SessionFinance must be GC-collected after logout');
        expect(ownerRefs.summary.target, isNull,
            reason: 'N1: Owner SessionSummary must be GC-collected after logout');
        expect(ownerRefs.ledger.target, isNull,
            reason: 'N1: Owner ClubLedger must be GC-collected after logout');

        // =====================================================================
        // EPOCH 3: Switch to Cohost in SAME Application Instance (N2)
        // =====================================================================
        auth.changeUser('cohost-id-5678');

        final cohostRef = await loadCohostEpoch(financeProvider, financeRepo);

        await triggerGc();

        // Negative Control N2: Owner references remain null, Cohost state is isolated
        expect(ownerRefs.instructions.target, isNull, reason: 'N2: Owner instructions must remain null');
        expect(ownerRefs.finance.target, isNull, reason: 'N2: Owner finance must remain null');
        expect(ownerRefs.summary.target, isNull, reason: 'N2: Owner summary must remain null');
        expect(ownerRefs.ledger.target, isNull, reason: 'N2: Owner ledger must remain null');

        expect(cohostRef.target, isNotNull);
        expect(financeProvider.sessionSummary?.hasFinanceView, isFalse);
        expect(financeProvider.sessionSummary?.amountDueTotalVnd, isNull);
        expect(financeProvider.paymentInstructions, isNull);
        expect(financeProvider.finance, isNull);
        expect(financeProvider.ledger, isNull);

        // =====================================================================
        // EPOCH 4: Switch to Member in SAME Application Instance (N3)
        // =====================================================================
        reset(financeRepo);
        auth.changeUser('member-id-9999');

        final memberRef = await loadMemberEpoch(financeProvider, financeRepo);

        await triggerGc();

        // Negative Control N3: Owner references remain dead, Member has distinct new object
        expect(ownerRefs.instructions.target, isNull, reason: 'N3: Owner instructions remain dead');
        expect(ownerRefs.finance.target, isNull, reason: 'N3: Owner finance remains dead');
        expect(ownerRefs.summary.target, isNull, reason: 'N3: Owner summary remains dead');
        expect(ownerRefs.ledger.target, isNull, reason: 'N3: Owner ledger remains dead');

        expect(memberRef.target, isNotNull);
        expect(financeProvider.paymentInstructions?.reference, 'BH-MEMBER-QR1122');
        expect(financeProvider.paymentInstructions?.amountDueVnd, 60000);
      },
    );

    test('Negative Control N4: Late-arriving response after logout is dropped & GC-collected', () async {
      final weakLatePayload = await simulateLateResponseAfterLogout(
        financeProvider,
        financeRepo,
        auth,
      );

      // Verify provider refused to adopt late response
      expect(financeProvider.sessionSummary, isNull);
      expect(financeProvider.isLoadingSummary, isFalse);

      // Trigger GC
      await triggerGc();

      // Negative Control N4: The late payload must not be retained
      expect(weakLatePayload.target, isNull,
          reason: 'N4: Late-arriving response must be dropped and collected by GC');
    });

    test('Negative Control N5: Late-arriving response after actor switch is dropped & GC-collected', () async {
      final weakLatePayload = await simulateLateResponseAfterActorSwitch(
        financeProvider,
        financeRepo,
        auth,
      );

      expect(financeProvider.sessionSummary, isNull);
      expect(financeProvider.isLoadingSummary, isFalse);

      await triggerGc();

      expect(weakLatePayload.target, isNull,
          reason: 'N5: Late response from previous actor must be dropped & collected');
    });

    test('Mutant Control M1: Static/global strong reference leak is reliably caught by Oracle', () async {
      final List<Object?> intentionalLeakySink = [];

      WeakReference<PaymentInstructions> loadAndLeak() {
        final obj = createDynamicOwnerInstructions();
        intentionalLeakySink.add(obj); // Simulate leak
        return WeakReference(obj);
      }

      final weakRef = loadAndLeak();

      await triggerGc();

      // The oracle MUST catch that this object is still retained in heap
      expect(weakRef.target, isNotNull,
          reason: 'M1 Oracle sensitivity: Retained object must be detected as alive');

      // Clean up leak
      intentionalLeakySink.clear();
      await triggerGc();
      expect(weakRef.target, isNull, reason: 'Cleaned leak should now be collected');
    });

    test('Mutant Control M2: Retained field on simulated failed clearAll is caught by Oracle', () async {
      Object? intentionalRetainedField;

      WeakReference<PaymentInstructions> simulateRetainedState() {
        final obj = createDynamicOwnerInstructions();
        intentionalRetainedField = obj; // Simulating field not cleared
        return WeakReference(obj);
      }

      final weakRef = simulateRetainedState();

      await triggerGc();

      // Oracle catches retention
      expect(intentionalRetainedField, isNotNull);
      expect(weakRef.target, isNotNull,
          reason: 'M2 Oracle sensitivity: Un-cleared field must be detected as alive');

      // Now clear field and trigger GC
      intentionalRetainedField = null;
      expect(intentionalRetainedField, isNull);
      await triggerGc();
      expect(weakRef.target, isNull, reason: 'Nullified field must be collected');
    });

    test('SessionProvider & ClubProvider: Private session and club details are purged from heap on logout', () async {
      auth.changeUser('owner-id-1234');

      Future<({WeakReference<Session> session, WeakReference<Club> club})> loadSessionAndClub() async {
        when(() => sessionRepo.getSessionDetail('s1')).thenAnswer((_) async => Session.fromJson(<String, dynamic>{
              'id': 's1',
              'title': 'Buổi nội bộ bí mật',
              'can_manage': true,
              'can_view_finance': true,
              'member_fee_vnd': 75000,
            }));
        when(() => clubRepo.getClubDetail('c1')).thenAnswer((_) async => Club.fromJson(<String, dynamic>{
              'id': 'c1',
              'owner_user_id': 'owner-id-1234',
              'name': 'CLB Độc Quyền',
              'balance_vnd': 9000000,
              'my_role': 'owner',
            }));
        when(() => clubRepo.listClubMembers(any())).thenAnswer((_) async => []);
        when(() => clubRepo.getClubBankAccount(any())).thenAnswer((_) async => null);

        await sessionProvider.fetchSessionDetail('s1');
        await clubProvider.fetchClubDetails('c1');

        return (
          session: WeakReference(sessionProvider.currentSession!),
          club: WeakReference(clubProvider.currentClub!),
        );
      }

      final refs = await loadSessionAndClub();

      expect(refs.session.target, isNotNull);
      expect(refs.club.target, isNotNull);

      // Logout
      reset(sessionRepo);
      reset(clubRepo);
      auth.changeUser(null);

      expect(sessionProvider.currentSession, isNull);
      expect(clubProvider.currentClub, isNull);

      await triggerGc();

      expect(refs.session.target, isNull, reason: 'Session object must be GC-collected after logout');
      expect(refs.club.target, isNull, reason: 'Club object must be GC-collected after logout');
    });
  });
}
