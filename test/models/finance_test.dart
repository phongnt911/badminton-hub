import 'package:flutter_test/flutter_test.dart';

import 'package:badminton_hub/models/finance.dart';

void main() {
  group('PaymentInstructions.fromJson', () {
    test('đọc đủ số tiền, mã tham chiếu và snapshot ngân hàng', () {
      final instructions = PaymentInstructions.fromJson({
        'session_id': 's1',
        'player_id': 'p1',
        'display_name': 'An',
        'billing_state': 'current',
        'active_revision_id': 'r1',
        'source_version': 3,
        'amount_due_vnd': 65000,
        'total_paid_vnd': 20000,
        'outstanding_vnd': 45000,
        'reference': 'BH-ABC123',
        'receiver_snapshot': {
          'bank_code': '970422',
          'account_number': '123456789',
          'account_name': 'NGUYEN VAN A',
        },
        'has_receiver': true,
        'can_pay': true,
      });

      expect(instructions.sessionId, 's1');
      expect(instructions.playerId, 'p1');
      expect(instructions.displayName, 'An');
      expect(instructions.isCurrent, isTrue);
      expect(instructions.sourceVersion, 3);
      expect(instructions.amountDueVnd, 65000);
      expect(instructions.totalPaidVnd, 20000);
      expect(instructions.outstandingVnd, 45000);
      expect(instructions.reference, 'BH-ABC123');
      expect(instructions.bankCode, '970422');
      expect(instructions.accountNumber, '123456789');
      expect(instructions.accountName, 'NGUYEN VAN A');
      expect(instructions.hasReceiver, isTrue);
      expect(instructions.canPay, isTrue);
    });

    test('thiếu snapshot/người nhận vẫn đọc an toàn, không tự suy đã trả', () {
      final instructions = PaymentInstructions.fromJson({
        'session_id': 's1',
        'player_id': 'p1',
        'billing_state': 'current',
        'outstanding_vnd': 0,
        'receiver_snapshot': null,
        'has_receiver': false,
        'can_pay': false,
      });

      expect(instructions.hasReceiver, isFalse);
      expect(instructions.bankCode, isNull);
      expect(instructions.accountNumber, isNull);
      expect(instructions.accountName, isNull);
      expect(instructions.canPay, isFalse);
      expect(instructions.outstandingVnd, 0);
    });
  });

  group('SessionFinance.fromJson', () {
    test('đọc revision active, tổng hợp và các trang chi phí/charges/payments',
        () {
      final finance = SessionFinance.fromJson({
        'session_id': 's1',
        'title': 'Buổi tối',
        'club_id': 'c1',
        'lifecycle': 'in_progress',
        'fee_mode': 'split_actual',
        'billing_input_version': 4,
        'session_version': 6,
        'billing_state': 'current',
        'active_revision': {
          'revision_id': 'r1',
          'revision_no': 2,
          'source_version': 4,
          'allocation_total_vnd': 450000,
          'fee_mode': 'split_actual',
          'reason': 'chia lại',
          'finalized_at': '2026-10-16T10:00:00Z',
        },
        'expenses_total_vnd': 450000,
        'outstanding_total_vnd': 300000,
        'expenses': [
          {
            'expense_id': 'e1',
            'category': 'court',
            'title': 'Tiền sân',
            'amount_vnd': 450000,
            'status': 'posted',
            'reversal_reason': null,
            'posted_at': '2026-10-16T09:00:00Z',
          },
        ],
        'charges': [
          {'player_id': 'p1', 'display_name': 'An', 'amount_due_vnd': 65000},
        ],
        'payments': [
          {
            'payment_id': 'pay1',
            'player_id': 'p1',
            'amount_vnd': 60000,
            'method': 'cash',
            'status': 'confirmed',
            'reference': 'CASH-1',
            'confirmed_at': '2026-10-16T09:30:00Z',
            'created_at': '2026-10-16T09:30:00Z',
          },
          {
            'payment_id': 'pay2',
            'player_id': 'p1',
            'amount_vnd': 5000,
            'method': 'bank_transfer',
            'status': 'submitted',
            'reference': 'PAY-1',
            'confirmed_at': null,
            'created_at': '2026-10-16T09:40:00Z',
          },
        ],
        'limit': 50,
        'offset': 0,
      });

      expect(finance.sessionId, 's1');
      expect(finance.clubId, 'c1');
      expect(finance.billingInputVersion, 4);
      expect(finance.sessionVersion, 6);
      expect(finance.isCurrent, isTrue);
      expect(finance.canCollect, isTrue);
      expect(finance.activeRevision?.revisionId, 'r1');
      expect(finance.activeRevision?.revisionNo, 2);
      expect(finance.activeRevision?.allocationTotalVnd, 450000);
      expect(finance.expensesTotalVnd, 450000);
      expect(finance.outstandingTotalVnd, 300000);
      expect(finance.expenses.single.isPosted, isTrue);
      expect(finance.expenses.single.category, 'court');
      expect(finance.charges.single.amountDueVnd, 65000);
      expect(finance.payments, hasLength(2));
      expect(finance.payments.first.isConfirmed, isTrue);
      expect(finance.submittedPayments.single.paymentId, 'pay2');
    });

    test('billing_state stale/not_finalized chặn thu và không có revision', () {
      final stale = SessionFinance.fromJson({
        'session_id': 's1',
        'billing_state': 'stale',
        'active_revision': null,
        'outstanding_total_vnd': 450000,
      });
      expect(stale.isStale, isTrue);
      expect(stale.canCollect, isFalse);
      expect(stale.hasActiveRevision, isFalse);
      expect(stale.outstandingTotalVnd, 450000);

      final notFinalized = SessionFinance.fromJson({
        'session_id': 's1',
        'billing_state': 'not_finalized',
      });
      expect(notFinalized.isNotFinalized, isTrue);
      expect(notFinalized.canCollect, isFalse);
    });
  });

  group('ClubLedger.fromJson', () {
    test('đọc số dư và bút toán với nguồn/đảo nullable', () {
      final ledger = ClubLedger.fromJson({
        'club_id': 'c1',
        'balance_vnd': 1550000,
        'limit': 20,
        'offset': 0,
        'entries': [
          {
            'transaction_id': 't2',
            'direction': 'expense',
            'amount_vnd': 150000,
            'title': 'Tiền sân',
            'source_type': 'session_expense',
            'source_payment_id': null,
            'source_expense_id': 'e1',
            'reversal_of': null,
            'created_at': '2026-10-16T09:00:00Z',
          },
          {
            'transaction_id': 't1',
            'direction': 'income',
            'amount_vnd': 200000,
            'title': 'Thu thủ công',
            'source_type': 'manual',
            'source_payment_id': null,
            'source_expense_id': null,
            'reversal_of': 't0',
            'created_at': '2026-10-16T08:00:00Z',
          },
        ],
      });

      expect(ledger.balanceVnd, 1550000);
      expect(ledger.entries, hasLength(2));
      expect(ledger.entries.first.isExpense, isTrue);
      expect(ledger.entries.first.sourceExpenseId, 'e1');
      expect(ledger.entries.first.isReversal, isFalse);
      expect(ledger.entries.last.isManual, isTrue);
      expect(ledger.entries.last.isReversal, isTrue);
    });

    test('thiếu entries trả danh sách rỗng nhưng vẫn giữ số dư server', () {
      final ledger = ClubLedger.fromJson({'club_id': 'c1', 'balance_vnd': 0});
      expect(ledger.entries, isEmpty);
      expect(ledger.isEmpty, isTrue);
      expect(ledger.balanceVnd, 0);
    });
  });

  group('kết quả mutation', () {
    test('ExpenseResult đọc cờ ledger và billing_state', () {
      final expense = ExpenseResult.fromJson({
        'expense_id': 'e1',
        'session_id': 's1',
        'category': 'court',
        'amount_vnd': 450000,
        'status': 'posted',
        'club_ledger_entry': true,
        'billing_state': 'stale',
      });

      expect(expense.expenseId, 'e1');
      expect(expense.sessionId, 's1');
      expect(expense.clubLedgerEntry, isTrue);
      expect(expense.billingState, 'stale');
    });

    test('RevisionResult và PaymentResult (kể cả đã xác nhận trước đó)', () {
      final revision = RevisionResult.fromJson({
        'revision_id': 'r1',
        'session_id': 's1',
        'revision_no': 1,
        'source_version': 4,
        'allocation_total_vnd': 450000,
        'fee_mode': 'split_actual',
        'present_count': 7,
        'charge_count': 7,
        'billing_state': 'current',
      });
      expect(revision.revisionNo, 1);
      expect(revision.presentCount, 7);
      expect(revision.chargeCount, 7);
      expect(revision.billingState, 'current');

      final confirmed = PaymentResult.fromJson({
        'payment_id': 'pay1',
        'player_id': 'p1',
        'session_id': 's1',
        'amount_vnd': 45000,
        'method': 'bank_transfer',
        'status': 'confirmed',
        'already_confirmed': true,
        'total_paid_vnd': 45000,
        'billing_state': 'current',
      });
      expect(confirmed.isConfirmed, isTrue);
      expect(confirmed.alreadyConfirmed, isTrue);
      expect(confirmed.totalPaidVnd, 45000);
    });

    test('ClubTransactionResult đọc ghi thủ công và bút toán đảo', () {
      final tx = ClubTransactionResult.fromJson({
        'transaction_id': 't1',
        'club_id': 'c1',
        'direction': 'income',
        'amount_vnd': 200000,
        'balance_vnd': 1750000,
        'source_type': 'manual',
      });
      expect(tx.transactionId, 't1');
      expect(tx.balanceVnd, 1750000);
      expect(tx.sourceType, 'manual');

      final reversal = ClubTransactionResult.fromJson({
        'transaction_id': 't1',
        'reversal_id': 't9',
        'club_id': 'c1',
        'balance_vnd': 1550000,
      });
      expect(reversal.reversalId, 't9');
      expect(reversal.direction, isNull);
    });
  });

  group('SessionSummary.fromJson', () {
    test('finance: đọc aggregate, version, billing và giữ 0 thật', () {
      final summary = SessionSummary.fromJson({
        'session_id': 's1',
        'title': 'Buổi tối',
        'club_id': 'c1',
        'club_name': 'CLB A',
        'venue_name': 'Sân A',
        'starts_at': '2026-10-20T10:00:00Z',
        'ends_at': '2026-10-20T12:00:00Z',
        'lifecycle': 'completed',
        'fee_mode': 'split_actual',
        'session_version': 7,
        'can_manage': true,
        'can_view_finance': true,
        'present_count': 6,
        'no_show_count': 1,
        'confirmed_count': 7,
        'billing_state': 'current',
        'active_revision_id': 'r1',
        'revision_no': 2,
        'source_version': 7,
        'expenses_total_vnd': 0,
        'amount_due_total_vnd': 420000,
        'total_paid_vnd': 400000,
        'outstanding_total_vnd': 20000,
      });

      expect(summary.sessionId, 's1');
      expect(summary.clubName, 'CLB A');
      expect(summary.venueName, 'Sân A');
      expect(summary.sessionVersion, 7);
      expect(summary.canManage, isTrue);
      expect(summary.canViewFinance, isTrue);
      expect(summary.presentCount, 6);
      expect(summary.noShowCount, 1);
      expect(summary.confirmedCount, 7);
      expect(summary.isBillingCurrent, isTrue);
      expect(summary.hasActiveRevision, isTrue);
      expect(summary.revisionNo, 2);
      expect(summary.sourceVersion, 7);
      expect(
        summary.expensesTotalVnd,
        0,
        reason: '0 thật phải giữ là 0, không bị nhầm với thiếu quyền',
      );
      expect(summary.amountDueTotalVnd, 420000);
      expect(summary.totalPaidVnd, 400000);
      expect(summary.outstandingTotalVnd, 20000);
    });

    test('management-only: tiền/billing NULL, không tự đổi thành 0', () {
      final summary = SessionSummary.fromJson({
        'session_id': 's1',
        'lifecycle': 'completed',
        'can_manage': true,
        'can_view_finance': false,
        'present_count': 3,
        'no_show_count': 0,
        'confirmed_count': 3,
        'billing_state': null,
        'active_revision_id': null,
        'revision_no': null,
        'source_version': null,
        'expenses_total_vnd': null,
        'amount_due_total_vnd': null,
        'total_paid_vnd': null,
        'outstanding_total_vnd': null,
      });

      expect(summary.hasFinanceView, isFalse);
      expect(summary.isBillingCurrent, isFalse);
      expect(summary.hasActiveRevision, isFalse);
      expect(summary.billingState, isNull);
      expect(summary.expensesTotalVnd, isNull);
      expect(summary.amountDueTotalVnd, isNull);
      expect(summary.totalPaidVnd, isNull);
      expect(summary.outstandingTotalVnd, isNull);
      expect(summary.presentCount, 3);
    });

    test('stale giữ nhãn và số tiền server, không tự suy current', () {
      final summary = SessionSummary.fromJson({
        'session_id': 's1',
        'lifecycle': 'completed',
        'can_view_finance': true,
        'billing_state': 'stale',
        'amount_due_total_vnd': 100000,
        'total_paid_vnd': 50000,
        'outstanding_total_vnd': 50000,
      });

      expect(summary.isBillingStale, isTrue);
      expect(summary.isBillingCurrent, isFalse);
      expect(summary.outstandingTotalVnd, 50000);
    });
  });
}
