/// Model tài chính BH-06B — phí/chốt phí, chi phí, thanh toán và sổ quỹ.
///
/// Ánh xạ 1:1 DTO đã review ở BH-06A: `get_payment_instructions`,
/// `get_session_finance`, `get_club_ledger` và kết quả các RPC mutation
/// (`post/reverse_session_expense`, `finalize_session_charges`,
/// `complete_session`, `submit/confirm/reject/reverse_payment`,
/// `record_cash_payment`, `post/reverse_manual_club_transaction`).
///
/// Thời gian từ DB là UTC (ISO-8601); chỉ đổi sang giờ Việt Nam khi hiển thị
/// (xem `core/time_utils.dart`). Số tiền là VNĐ nguyên (BIGINT).
library;

int? _asInt(dynamic value) => value == null ? null : (value as num).toInt();

DateTime? _asDate(dynamic value) =>
    value == null ? null : DateTime.tryParse(value.toString());

Map<String, dynamic>? _asMap(dynamic value) =>
    value is Map ? Map<String, dynamic>.from(value) : null;

List<Map<String, dynamic>> _asMapList(dynamic value) {
  if (value is! List) return const [];
  return value
      .whereType<Map>()
      .map((item) => Map<String, dynamic>.from(item))
      .toList();
}

/// Hướng dẫn thanh toán cho một người trong buổi
/// (`get_payment_instructions`) — dùng để dựng QR/nội dung chuyển khoản.
///
/// Chỉ có giá trị khi phí đang `current`; `stale`/`not_finalized` bị RPC chặn
/// nên provider giữ `billingState` để UI phản ánh trạng thái.
class PaymentInstructions {
  final String sessionId;
  final String playerId;
  final String? displayName;
  final String billingState;
  final String? activeRevisionId;
  final int? sourceVersion;
  final int amountDueVnd;
  final int totalPaidVnd;
  final int outstandingVnd;
  final String? reference;
  final Map<String, dynamic>? receiverSnapshot;
  final bool hasReceiver;
  final bool canPay;

  const PaymentInstructions({
    required this.sessionId,
    required this.playerId,
    this.displayName,
    this.billingState = 'current',
    this.activeRevisionId,
    this.sourceVersion,
    this.amountDueVnd = 0,
    this.totalPaidVnd = 0,
    this.outstandingVnd = 0,
    this.reference,
    this.receiverSnapshot,
    this.hasReceiver = false,
    this.canPay = false,
  });

  bool get isCurrent => billingState == 'current';
  bool get isStale => billingState == 'stale';
  bool get isNotFinalized => billingState == 'not_finalized';

  String? get bankCode => receiverSnapshot?['bank_code']?.toString();
  String? get accountNumber => receiverSnapshot?['account_number']?.toString();
  String? get accountName => receiverSnapshot?['account_name']?.toString();

  factory PaymentInstructions.fromJson(Map<String, dynamic> json) {
    final snapshot = _asMap(json['receiver_snapshot']);
    return PaymentInstructions(
      sessionId: json['session_id']?.toString() ?? '',
      playerId: json['player_id']?.toString() ?? '',
      displayName: json['display_name']?.toString(),
      billingState: json['billing_state']?.toString() ?? 'current',
      activeRevisionId: json['active_revision_id']?.toString(),
      sourceVersion: _asInt(json['source_version']),
      amountDueVnd: _asInt(json['amount_due_vnd']) ?? 0,
      totalPaidVnd: _asInt(json['total_paid_vnd']) ?? 0,
      outstandingVnd: _asInt(json['outstanding_vnd']) ?? 0,
      reference: json['reference']?.toString(),
      receiverSnapshot: snapshot,
      hasReceiver: json['has_receiver'] == true || snapshot != null,
      canPay: json['can_pay'] == true,
    );
  }
}

/// Tổng kết buổi (`get_session_summary`) — aggregate an toàn cho tab Tổng kết.
///
/// Các trường tiền là **nullable** và phải giữ nguyên `null` khi actor không có
/// quyền tài chính. Không đổi `null` thành 0 và không suy `outstanding` từ
/// `due - paid` hoặc từ một trang payment bị cắt.
class SessionSummary {
  final String sessionId;
  final String? title;
  final String? clubId;
  final String? clubName;
  final String? venueName;
  final DateTime? startsAt;
  final DateTime? endsAt;
  final String lifecycle;
  final String feeMode;

  /// `sessions.version` server-side; null nếu DTO cũ/không có.
  final int? sessionVersion;
  final bool canManage;
  final bool canViewFinance;
  final int presentCount;
  final int noShowCount;
  final int confirmedCount;

  // --- Chỉ có khi canViewFinance = true -------------------------------- //
  final String? billingState;
  final String? activeRevisionId;
  final int? revisionNo;
  final int? sourceVersion;
  final int? expensesTotalVnd;
  final int? amountDueTotalVnd;
  final int? totalPaidVnd;
  final int? outstandingTotalVnd;

  const SessionSummary({
    required this.sessionId,
    this.title,
    this.clubId,
    this.clubName,
    this.venueName,
    this.startsAt,
    this.endsAt,
    this.lifecycle = '',
    this.feeMode = 'split_actual',
    this.sessionVersion,
    this.canManage = false,
    this.canViewFinance = false,
    this.presentCount = 0,
    this.noShowCount = 0,
    this.confirmedCount = 0,
    this.billingState,
    this.activeRevisionId,
    this.revisionNo,
    this.sourceVersion,
    this.expensesTotalVnd,
    this.amountDueTotalVnd,
    this.totalPaidVnd,
    this.outstandingTotalVnd,
  });

  bool get hasFinanceView => canViewFinance;
  bool get hasActiveRevision => activeRevisionId != null;
  bool get isBillingCurrent => billingState == 'current';
  bool get isBillingStale => billingState == 'stale';
  bool get isBillingNotFinalized => billingState == 'not_finalized';

  factory SessionSummary.fromJson(Map<String, dynamic> json) {
    return SessionSummary(
      sessionId: json['session_id']?.toString() ?? '',
      title: json['title']?.toString(),
      clubId: json['club_id']?.toString(),
      clubName: json['club_name']?.toString(),
      venueName: json['venue_name']?.toString(),
      startsAt: _asDate(json['starts_at']),
      endsAt: _asDate(json['ends_at']),
      lifecycle: json['lifecycle']?.toString() ?? '',
      feeMode: json['fee_mode']?.toString() ?? 'split_actual',
      sessionVersion: _asInt(json['session_version']),
      canManage: json['can_manage'] == true,
      canViewFinance: json['can_view_finance'] == true,
      presentCount: _asInt(json['present_count']) ?? 0,
      noShowCount: _asInt(json['no_show_count']) ?? 0,
      confirmedCount: _asInt(json['confirmed_count']) ?? 0,
      billingState: json['billing_state']?.toString(),
      activeRevisionId: json['active_revision_id']?.toString(),
      revisionNo: _asInt(json['revision_no']),
      sourceVersion: _asInt(json['source_version']),
      expensesTotalVnd: _asInt(json['expenses_total_vnd']),
      amountDueTotalVnd: _asInt(json['amount_due_total_vnd']),
      totalPaidVnd: _asInt(json['total_paid_vnd']),
      outstandingTotalVnd: _asInt(json['outstanding_total_vnd']),
    );
  }
}

/// Revision phí đang hiệu lực trong `get_session_finance`.
class FinanceRevision {
  final String revisionId;
  final int revisionNo;
  final int? sourceVersion;
  final int allocationTotalVnd;
  final String? feeMode;
  final String? reason;
  final DateTime? finalizedAt;

  const FinanceRevision({
    required this.revisionId,
    this.revisionNo = 0,
    this.sourceVersion,
    this.allocationTotalVnd = 0,
    this.feeMode,
    this.reason,
    this.finalizedAt,
  });

  factory FinanceRevision.fromJson(Map<String, dynamic> json) {
    return FinanceRevision(
      revisionId: json['revision_id']?.toString() ?? '',
      revisionNo: _asInt(json['revision_no']) ?? 0,
      sourceVersion: _asInt(json['source_version']),
      allocationTotalVnd: _asInt(json['allocation_total_vnd']) ?? 0,
      feeMode: json['fee_mode']?.toString(),
      reason: json['reason']?.toString(),
      finalizedAt: _asDate(json['finalized_at']),
    );
  }
}

/// Một khoản chi phí của buổi (`session_expenses`).
class FinanceExpense {
  final String expenseId;
  final String category;
  final String? title;
  final int amountVnd;
  final String status;
  final String? reversalReason;
  final DateTime? postedAt;

  const FinanceExpense({
    required this.expenseId,
    this.category = 'other',
    this.title,
    this.amountVnd = 0,
    this.status = 'posted',
    this.reversalReason,
    this.postedAt,
  });

  bool get isPosted => status == 'posted';
  bool get isReversed => status == 'reversed';

  factory FinanceExpense.fromJson(Map<String, dynamic> json) {
    return FinanceExpense(
      expenseId: json['expense_id']?.toString() ?? '',
      category: json['category']?.toString() ?? 'other',
      title: json['title']?.toString(),
      amountVnd: _asInt(json['amount_vnd']) ?? 0,
      status: json['status']?.toString() ?? 'posted',
      reversalReason: json['reversal_reason']?.toString(),
      postedAt: _asDate(json['posted_at']),
    );
  }
}

/// Khoản phải thu của một người theo revision active.
class FinanceCharge {
  final String playerId;
  final String? displayName;
  final int amountDueVnd;

  const FinanceCharge({
    required this.playerId,
    this.displayName,
    this.amountDueVnd = 0,
  });

  factory FinanceCharge.fromJson(Map<String, dynamic> json) {
    return FinanceCharge(
      playerId: json['player_id']?.toString() ?? '',
      displayName: json['display_name']?.toString(),
      amountDueVnd: _asInt(json['amount_due_vnd']) ?? 0,
    );
  }
}

/// Một bản ghi thanh toán (`payments`).
class FinancePayment {
  final String paymentId;
  final String playerId;
  final int amountVnd;
  final String method;
  final String status;
  final String? reference;
  final DateTime? confirmedAt;
  final DateTime? createdAt;

  const FinancePayment({
    required this.paymentId,
    required this.playerId,
    this.amountVnd = 0,
    this.method = 'bank_transfer',
    this.status = 'submitted',
    this.reference,
    this.confirmedAt,
    this.createdAt,
  });

  bool get isSubmitted => status == 'submitted';
  bool get isConfirmed => status == 'confirmed';
  bool get isRejected => status == 'rejected';
  bool get isReversed => status == 'reversed';

  factory FinancePayment.fromJson(Map<String, dynamic> json) {
    return FinancePayment(
      paymentId: json['payment_id']?.toString() ?? '',
      playerId: json['player_id']?.toString() ?? '',
      amountVnd: _asInt(json['amount_vnd']) ?? 0,
      method: json['method']?.toString() ?? 'bank_transfer',
      status: json['status']?.toString() ?? 'submitted',
      reference: json['reference']?.toString(),
      confirmedAt: _asDate(json['confirmed_at']),
      createdAt: _asDate(json['created_at']),
    );
  }
}

/// Projection tài chính một buổi (`get_session_finance`), đã phân trang
/// `expenses`/`payments` theo `limit`/`offset`.
class SessionFinance {
  final String sessionId;
  final String? title;
  final String? clubId;
  final String lifecycle;
  final String feeMode;
  final int billingInputVersion;

  /// `sessions.version` hiện hành tại thời điểm đọc DTO — dùng làm
  /// `expectedVersion` cho `finalize_session_charges` để refresh sau
  /// VERSION_CONFLICT lấy được version mới. Nullable khi server cũ/không có.
  final int? sessionVersion;
  final String billingState;
  final FinanceRevision? activeRevision;
  final int expensesTotalVnd;
  final int outstandingTotalVnd;
  final List<FinanceExpense> expenses;
  final List<FinanceCharge> charges;
  final List<FinancePayment> payments;
  final int limit;
  final int offset;

  const SessionFinance({
    required this.sessionId,
    this.title,
    this.clubId,
    this.lifecycle = 'draft',
    this.feeMode = 'split_actual',
    this.billingInputVersion = 1,
    this.sessionVersion,
    this.billingState = 'not_finalized',
    this.activeRevision,
    this.expensesTotalVnd = 0,
    this.outstandingTotalVnd = 0,
    this.expenses = const [],
    this.charges = const [],
    this.payments = const [],
    this.limit = 50,
    this.offset = 0,
  });

  bool get isCurrent => billingState == 'current';
  bool get isStale => billingState == 'stale';
  bool get isNotFinalized => billingState == 'not_finalized';
  bool get hasActiveRevision => activeRevision != null;

  /// Có được phép thu mới/hoàn tất hay không (chỉ khi phí `current`).
  bool get canCollect => isCurrent && hasActiveRevision;

  List<FinancePayment> get submittedPayments =>
      payments.where((p) => p.isSubmitted).toList();

  factory SessionFinance.fromJson(Map<String, dynamic> json) {
    final revision = _asMap(json['active_revision']);
    return SessionFinance(
      sessionId: json['session_id']?.toString() ?? '',
      title: json['title']?.toString(),
      clubId: json['club_id']?.toString(),
      lifecycle: json['lifecycle']?.toString() ?? 'draft',
      feeMode: json['fee_mode']?.toString() ?? 'split_actual',
      billingInputVersion: _asInt(json['billing_input_version']) ?? 1,
      sessionVersion: _asInt(json['session_version']),
      billingState: json['billing_state']?.toString() ?? 'not_finalized',
      activeRevision:
          revision == null ? null : FinanceRevision.fromJson(revision),
      expensesTotalVnd: _asInt(json['expenses_total_vnd']) ?? 0,
      outstandingTotalVnd: _asInt(json['outstanding_total_vnd']) ?? 0,
      expenses: _asMapList(json['expenses'])
          .map(FinanceExpense.fromJson)
          .toList(),
      charges:
          _asMapList(json['charges']).map(FinanceCharge.fromJson).toList(),
      payments:
          _asMapList(json['payments']).map(FinancePayment.fromJson).toList(),
      limit: _asInt(json['limit']) ?? 50,
      offset: _asInt(json['offset']) ?? 0,
    );
  }
}

/// Một bút toán sổ quỹ CLB (`club_transactions`).
class ClubLedgerEntry {
  final String transactionId;
  final String direction;
  final int amountVnd;
  final String? title;
  final String? sourceType;
  final String? sourcePaymentId;
  final String? sourceExpenseId;
  final String? reversalOf;
  final DateTime? createdAt;

  const ClubLedgerEntry({
    required this.transactionId,
    this.direction = 'income',
    this.amountVnd = 0,
    this.title,
    this.sourceType,
    this.sourcePaymentId,
    this.sourceExpenseId,
    this.reversalOf,
    this.createdAt,
  });

  bool get isIncome => direction == 'income';
  bool get isExpense => direction == 'expense';
  bool get isManual => sourceType == 'manual';
  bool get isReversal => reversalOf != null;

  factory ClubLedgerEntry.fromJson(Map<String, dynamic> json) {
    return ClubLedgerEntry(
      transactionId: json['transaction_id']?.toString() ?? '',
      direction: json['direction']?.toString() ?? 'income',
      amountVnd: _asInt(json['amount_vnd']) ?? 0,
      title: json['title']?.toString(),
      sourceType: json['source_type']?.toString(),
      sourcePaymentId: json['source_payment_id']?.toString(),
      sourceExpenseId: json['source_expense_id']?.toString(),
      reversalOf: json['reversal_of']?.toString(),
      createdAt: _asDate(json['created_at']),
    );
  }
}

/// Sổ quỹ CLB (`get_club_ledger`) — `balanceVnd` là số dư server-side, phân
/// trang theo `limit`/`offset`.
class ClubLedger {
  final String clubId;
  final int balanceVnd;
  final int limit;
  final int offset;
  final List<ClubLedgerEntry> entries;

  const ClubLedger({
    required this.clubId,
    this.balanceVnd = 0,
    this.limit = 20,
    this.offset = 0,
    this.entries = const [],
  });

  bool get isEmpty => entries.isEmpty;

  factory ClubLedger.fromJson(Map<String, dynamic> json) {
    return ClubLedger(
      clubId: json['club_id']?.toString() ?? '',
      balanceVnd: _asInt(json['balance_vnd']) ?? 0,
      limit: _asInt(json['limit']) ?? 20,
      offset: _asInt(json['offset']) ?? 0,
      entries:
          _asMapList(json['entries']).map(ClubLedgerEntry.fromJson).toList(),
    );
  }
}

/// Kết quả `post_session_expense` / `reverse_session_expense`.
class ExpenseResult {
  final String expenseId;
  final String sessionId;
  final String status;
  final String? category;
  final int? amountVnd;
  final bool clubLedgerEntry;
  final String? reversalLedgerId;
  final String? billingState;

  const ExpenseResult({
    required this.expenseId,
    required this.sessionId,
    this.status = 'posted',
    this.category,
    this.amountVnd,
    this.clubLedgerEntry = false,
    this.reversalLedgerId,
    this.billingState,
  });

  factory ExpenseResult.fromJson(Map<String, dynamic> json) {
    return ExpenseResult(
      expenseId: json['expense_id']?.toString() ?? '',
      sessionId: json['session_id']?.toString() ?? '',
      status: json['status']?.toString() ?? 'posted',
      category: json['category']?.toString(),
      amountVnd: _asInt(json['amount_vnd']),
      clubLedgerEntry: json['club_ledger_entry'] == true,
      reversalLedgerId: json['reversal_ledger_id']?.toString(),
      billingState: json['billing_state']?.toString(),
    );
  }
}

/// Kết quả `finalize_session_charges`.
class RevisionResult {
  final String revisionId;
  final String sessionId;
  final int revisionNo;
  final int sourceVersion;
  final int allocationTotalVnd;
  final String? feeMode;
  final int presentCount;
  final int chargeCount;
  final String? billingState;

  const RevisionResult({
    required this.revisionId,
    required this.sessionId,
    this.revisionNo = 0,
    this.sourceVersion = 0,
    this.allocationTotalVnd = 0,
    this.feeMode,
    this.presentCount = 0,
    this.chargeCount = 0,
    this.billingState,
  });

  factory RevisionResult.fromJson(Map<String, dynamic> json) {
    return RevisionResult(
      revisionId: json['revision_id']?.toString() ?? '',
      sessionId: json['session_id']?.toString() ?? '',
      revisionNo: _asInt(json['revision_no']) ?? 0,
      sourceVersion: _asInt(json['source_version']) ?? 0,
      allocationTotalVnd: _asInt(json['allocation_total_vnd']) ?? 0,
      feeMode: json['fee_mode']?.toString(),
      presentCount: _asInt(json['present_count']) ?? 0,
      chargeCount: _asInt(json['charge_count']) ?? 0,
      billingState: json['billing_state']?.toString(),
    );
  }
}

/// Kết quả các RPC thanh toán
/// (`submit/confirm/reject/reverse_payment`, `record_cash_payment`).
class PaymentResult {
  final String paymentId;
  final String playerId;
  final String sessionId;
  final int amountVnd;
  final String method;
  final String status;
  final String? reference;
  final int? amountDueVnd;
  final int? totalPaidVnd;
  final int? outstandingVnd;
  final String? billingState;
  final bool alreadyConfirmed;
  final String? ledgerId;
  final String? reversalLedgerId;

  const PaymentResult({
    required this.paymentId,
    required this.playerId,
    required this.sessionId,
    this.amountVnd = 0,
    this.method = 'bank_transfer',
    this.status = 'submitted',
    this.reference,
    this.amountDueVnd,
    this.totalPaidVnd,
    this.outstandingVnd,
    this.billingState,
    this.alreadyConfirmed = false,
    this.ledgerId,
    this.reversalLedgerId,
  });

  bool get isConfirmed => status == 'confirmed';
  bool get isSubmitted => status == 'submitted';
  bool get isRejected => status == 'rejected';
  bool get isReversed => status == 'reversed';

  factory PaymentResult.fromJson(Map<String, dynamic> json) {
    return PaymentResult(
      paymentId: json['payment_id']?.toString() ?? '',
      playerId: json['player_id']?.toString() ?? '',
      sessionId: json['session_id']?.toString() ?? '',
      amountVnd: _asInt(json['amount_vnd']) ?? 0,
      method: json['method']?.toString() ?? 'bank_transfer',
      status: json['status']?.toString() ?? 'submitted',
      reference: json['reference']?.toString(),
      amountDueVnd: _asInt(json['amount_due_vnd']),
      totalPaidVnd: _asInt(json['total_paid_vnd']),
      outstandingVnd: _asInt(json['outstanding_vnd']),
      billingState: json['billing_state']?.toString(),
      alreadyConfirmed: json['already_confirmed'] == true,
      ledgerId: json['ledger_id']?.toString(),
      reversalLedgerId: json['reversal_ledger_id']?.toString(),
    );
  }
}

/// Kết quả `post_manual_club_transaction` / `reverse_club_transaction`.
class ClubTransactionResult {
  final String transactionId;
  final String clubId;
  final String? direction;
  final int amountVnd;
  final int balanceVnd;
  final String? sourceType;
  final String? reversalId;

  const ClubTransactionResult({
    required this.transactionId,
    required this.clubId,
    this.direction,
    this.amountVnd = 0,
    this.balanceVnd = 0,
    this.sourceType,
    this.reversalId,
  });

  factory ClubTransactionResult.fromJson(Map<String, dynamic> json) {
    return ClubTransactionResult(
      transactionId: json['transaction_id']?.toString() ?? '',
      clubId: json['club_id']?.toString() ?? '',
      direction: json['direction']?.toString(),
      amountVnd: _asInt(json['amount_vnd']) ?? 0,
      balanceVnd: _asInt(json['balance_vnd']) ?? 0,
      sourceType: json['source_type']?.toString(),
      reversalId: json['reversal_id']?.toString(),
    );
  }
}
