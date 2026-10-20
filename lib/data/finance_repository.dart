import 'package:supabase_flutter/supabase_flutter.dart' hide Session;

import '../models/finance.dart';
import '../models/session.dart';

/// Truy cập tài chính buổi/CLB qua RPC BH-06A.
///
/// Mọi mutation gửi `p_request_id` (idempotency server-side), không ghi cột
/// trực tiếp và không dựng số tiền/số dư ở client. Tên tham số khớp đúng
/// signature đã review trong `docs/08_DOMAIN_CONTRACTS.md` §13.
class FinanceRepository {
  final SupabaseClient _client;

  FinanceRepository({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  /// `p_limit` hợp lệ 1..100 theo contract; kẹp tại client để không gửi sai.
  static int _limit(int value) => value < 1 ? 1 : (value > 100 ? 100 : value);

  static int _offset(int value) => value < 0 ? 0 : value;

  static Map<String, dynamic> _toMap(dynamic response) =>
      Map<String, dynamic>.from(response as Map);

  // --- Đọc ----------------------------------------------------------------- //

  /// Hướng dẫn thanh toán/QR của một người (`p_player_id` NULL = chính actor).
  Future<PaymentInstructions> getPaymentInstructions(
    String sessionId, {
    String? playerId,
  }) async {
    final response = await _client.rpc('get_payment_instructions', params: {
      'p_session_id': sessionId,
      'p_player_id': playerId,
    });
    return PaymentInstructions.fromJson(_toMap(response));
  }

  /// Projection tài chính buổi cho finance (revision active + tổng hợp + trang).
  Future<SessionFinance> getSessionFinance(
    String sessionId, {
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _client.rpc('get_session_finance', params: {
      'p_session_id': sessionId,
      'p_limit': _limit(limit),
      'p_offset': _offset(offset),
    });
    return SessionFinance.fromJson(_toMap(response));
  }

  /// Tổng kết aggregate server-side; tiền nullable khi actor chỉ có quyền quản lý.
  Future<SessionSummary> getSessionSummary(String sessionId) async {
    final response = await _client.rpc(
      'get_session_summary',
      params: {'p_session_id': sessionId},
    );
    return SessionSummary.fromJson(_toMap(response));
  }

  /// Sổ quỹ CLB cho owner/treasurer (phân trang, số dư từ SUM server).
  Future<ClubLedger> getClubLedger(
    String clubId, {
    int limit = 20,
    int offset = 0,
  }) async {
    final response = await _client.rpc('get_club_ledger', params: {
      'p_club_id': clubId,
      'p_limit': _limit(limit),
      'p_offset': _offset(offset),
    });
    return ClubLedger.fromJson(_toMap(response));
  }

  // --- Chi phí / chốt phí -------------------------------------------------- //

  /// Ghi chi phí buổi (`court`/`shuttle`/`other`), sinh ledger CLB cùng transaction.
  Future<ExpenseResult> postSessionExpense({
    required String requestId,
    required String sessionId,
    required String category,
    required String title,
    required int amountVnd,
  }) async {
    final response = await _client.rpc('post_session_expense', params: {
      'p_session_id': sessionId,
      'p_category': category,
      'p_title': title,
      'p_amount_vnd': amountVnd,
      'p_request_id': requestId,
    });
    return ExpenseResult.fromJson(_toMap(response));
  }

  /// Đảo một chi phí đã ghi (giữ nguồn, entry đảo duy nhất) — cần lý do.
  Future<ExpenseResult> reverseSessionExpense({
    required String requestId,
    required String sessionId,
    required String expenseId,
    required String reason,
  }) async {
    final response = await _client.rpc('reverse_session_expense', params: {
      'p_session_id': sessionId,
      'p_expense_id': expenseId,
      'p_reason': reason,
      'p_request_id': requestId,
    });
    return ExpenseResult.fromJson(_toMap(response));
  }

  /// Chốt/chốt lại phí server-side; khoá version + billing_input_version.
  Future<RevisionResult> finalizeSessionCharges({
    required String requestId,
    required String sessionId,
    required int expectedVersion,
    required int expectedBillingInputVersion,
    String? reason,
  }) async {
    final response = await _client.rpc('finalize_session_charges', params: {
      'p_session_id': sessionId,
      'p_expected_version': expectedVersion,
      'p_expected_billing_input_version': expectedBillingInputVersion,
      'p_reason': reason,
      'p_request_id': requestId,
    });
    return RevisionResult.fromJson(_toMap(response));
  }

  /// Kết thúc buổi đang diễn ra (chỉ khi phí `current`); trả chi tiết buổi.
  Future<Session> completeSession({
    required String requestId,
    required String sessionId,
    required int expectedVersion,
  }) async {
    final response = await _client.rpc('complete_session', params: {
      'p_session_id': sessionId,
      'p_expected_version': expectedVersion,
      'p_request_id': requestId,
    });
    return Session.fromJson(_toMap(response));
  }

  // --- Thanh toán ---------------------------------------------------------- //

  /// Người chơi tự gửi ý định chuyển khoản (chưa tính là đã thu).
  Future<PaymentResult> submitPayment({
    required String requestId,
    required String playerId,
    required int amountVnd,
    String method = 'bank_transfer',
    String? reference,
  }) async {
    final response = await _client.rpc('submit_payment', params: {
      'p_player_id': playerId,
      'p_amount_vnd': amountVnd,
      'p_method': method,
      'p_reference': reference,
      'p_request_id': requestId,
    });
    return PaymentResult.fromJson(_toMap(response));
  }

  /// Finance xác nhận thủ công một khoản `submitted`.
  Future<PaymentResult> confirmPayment({
    required String requestId,
    required String paymentId,
  }) async {
    final response = await _client.rpc('confirm_payment', params: {
      'p_payment_id': paymentId,
      'p_request_id': requestId,
    });
    return PaymentResult.fromJson(_toMap(response));
  }

  /// Finance từ chối một khoản `submitted` — cần lý do.
  Future<PaymentResult> rejectPayment({
    required String requestId,
    required String paymentId,
    required String reason,
  }) async {
    final response = await _client.rpc('reject_payment', params: {
      'p_payment_id': paymentId,
      'p_reason': reason,
      'p_request_id': requestId,
    });
    return PaymentResult.fromJson(_toMap(response));
  }

  /// Finance đảo một khoản đã `confirmed` (giữ lịch sử) — cần lý do.
  Future<PaymentResult> reversePayment({
    required String requestId,
    required String paymentId,
    required String reason,
  }) async {
    final response = await _client.rpc('reverse_payment', params: {
      'p_payment_id': paymentId,
      'p_reason': reason,
      'p_request_id': requestId,
    });
    return PaymentResult.fromJson(_toMap(response));
  }

  /// Finance ghi tiền mặt đã thu nguyên tử (tạo + xác nhận cùng transaction).
  Future<PaymentResult> recordCashPayment({
    required String requestId,
    required String playerId,
    required int amountVnd,
    String? reference,
  }) async {
    final response = await _client.rpc('record_cash_payment', params: {
      'p_player_id': playerId,
      'p_amount_vnd': amountVnd,
      'p_reference': reference,
      'p_request_id': requestId,
    });
    return PaymentResult.fromJson(_toMap(response));
  }

  // --- Sổ quỹ CLB ---------------------------------------------------------- //

  /// Owner/treasurer ghi bút toán thủ công (`income`/`expense`), không gửi source.
  Future<ClubTransactionResult> postManualClubTransaction({
    required String requestId,
    required String clubId,
    required String direction,
    required int amountVnd,
    required String title,
  }) async {
    final response =
        await _client.rpc('post_manual_club_transaction', params: {
      'p_club_id': clubId,
      'p_direction': direction,
      'p_amount_vnd': amountVnd,
      'p_title': title,
      'p_request_id': requestId,
    });
    return ClubTransactionResult.fromJson(_toMap(response));
  }

  /// Owner/treasurer đảo một bút toán thủ công — chỉ entry `manual`, cần lý do.
  Future<ClubTransactionResult> reverseClubTransaction({
    required String requestId,
    required String transactionId,
    required String reason,
  }) async {
    final response = await _client.rpc('reverse_club_transaction', params: {
      'p_transaction_id': transactionId,
      'p_reason': reason,
      'p_request_id': requestId,
    });
    return ClubTransactionResult.fromJson(_toMap(response));
  }
}
