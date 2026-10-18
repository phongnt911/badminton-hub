import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';

import '../core/domain_error.dart';
import '../data/finance_repository.dart';
import '../models/finance.dart';
import '../models/session.dart';
import 'auth_provider.dart';

/// Quản lý trạng thái tài chính BH-06B: hướng dẫn thanh toán/QR, tài chính
/// buổi, sổ quỹ CLB và các mutation (chi phí/chốt phí/thanh toán/quỹ).
///
/// Nguyên tắc theo [docs/24_BH06_IMPLEMENTATION_HANDOFF.md] §3.B:
/// - giữ `request_id` qua lỗi/timeout, xoay key sau commit thành công **trước**
///   khi làm mới; payload đổi tạo ý định mới;
/// - làm mới lỗi không biến mutation thành thất bại;
/// - dọn state riêng tư khi logout/đổi actor/đổi session/club và bỏ phản hồi trễ;
/// - lỗi đọc (kể cả thiếu quyền) KHÔNG biến dữ liệu thành rỗng/số dư 0.
class FinanceProvider extends ChangeNotifier {
  final FinanceRepository _repository;

  final AuthProvider? auth;
  String? _authUserId;
  int _generation = 0;
  bool _disposed = false;
  final _pendingRequests = <String, ({String payload, String id})>{};

  FinanceProvider({FinanceRepository? repository, this.auth})
      : _repository = repository ?? FinanceRepository() {
    _authUserId = auth?.currentUser?.id;
    auth?.addListener(_onAuthChanged);
  }

  // Một ý định giữ cùng UUID qua lỗi/timeout; payload đổi tạo ý định mới.
  String _requestKey(
    String operation,
    List<Object?> payload,
    String? supplied,
  ) {
    if (supplied != null) return supplied;
    final encoded = jsonEncode(payload);
    final pending = _pendingRequests[operation];
    if (pending?.payload == encoded) return pending!.id;
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    final id =
        '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
    _pendingRequests[operation] = (payload: encoded, id: id);
    return id;
  }

  void _onAuthChanged() {
    final userId = auth?.currentUser?.id;
    if (userId != _authUserId) {
      _authUserId = userId;
      clearAll();
    }
  }

  @override
  void notifyListeners() {
    if (!_disposed) super.notifyListeners();
  }

  @override
  void dispose() {
    auth?.removeListener(_onAuthChanged);
    _generation++;
    _disposed = true;
    super.dispose();
  }

  /// Dọn toàn bộ state riêng tư (đổi user/đăng xuất).
  void clearAll() {
    _generation++;
    _pendingRequests.clear();
    _resetInstructions();
    _resetFinance();
    _resetLedger();
    _isSubmitting = false;
    _submitErrorMessage = null;
    notifyListeners();
  }

  void clearSubmitError() {
    if (_submitErrorMessage == null) return;
    _submitErrorMessage = null;
    notifyListeners();
  }

  // --- Hướng dẫn thanh toán / QR ------------------------------------------ //

  String? _instructionsSessionId;
  String? _instructionsPlayerId;
  PaymentInstructions? _instructions;
  bool _isLoadingInstructions = false;
  String? _instructionsErrorMessage;
  int _instructionsSerial = 0;

  PaymentInstructions? get paymentInstructions => _instructions;
  bool get isLoadingInstructions => _isLoadingInstructions;
  String? get instructionsErrorMessage => _instructionsErrorMessage;
  String? get instructionsSessionId => _instructionsSessionId;
  String? get instructionsPlayerId => _instructionsPlayerId;

  void _resetInstructions() {
    _instructionsSerial++;
    _instructionsSessionId = null;
    _instructionsPlayerId = null;
    _instructions = null;
    _isLoadingInstructions = false;
    _instructionsErrorMessage = null;
  }

  /// Tải hướng dẫn thanh toán cho chính actor (`playerId` NULL) hoặc một người
  /// trong buổi (finance). Lỗi quyền/chưa chốt/stale giữ nguyên lỗi, không thành
  /// "chưa cần trả".
  Future<void> fetchPaymentInstructions(
    String sessionId, {
    String? playerId,
  }) async {
    if (_authUserId == null) {
      _resetInstructions();
      notifyListeners();
      return;
    }
    final generation = _generation;
    final serial = ++_instructionsSerial;
    if (_instructionsSessionId != sessionId ||
        _instructionsPlayerId != playerId) {
      _instructionsSessionId = sessionId;
      _instructionsPlayerId = playerId;
      _instructions = null;
    }
    _isLoadingInstructions = true;
    _instructionsErrorMessage = null;
    notifyListeners();

    try {
      final instructions = await _repository.getPaymentInstructions(
        sessionId,
        playerId: playerId,
      );
      if (_generation == generation &&
          serial == _instructionsSerial &&
          _instructionsSessionId == sessionId &&
          _instructionsPlayerId == playerId) {
        _instructions = instructions;
      }
    } catch (e) {
      if (_generation == generation &&
          serial == _instructionsSerial &&
          _instructionsSessionId == sessionId &&
          _instructionsPlayerId == playerId) {
        // Server vừa từ chối (stale/chưa chốt/mất quyền): không giữ chỉ dẫn
        // thanh toán có thể trả của revision cũ, chỉ giữ thông điệp lỗi (B1).
        _instructions = null;
        _instructionsErrorMessage = domainErrorMessage(e);
      }
    } finally {
      if (_generation == generation &&
          serial == _instructionsSerial &&
          _instructionsSessionId == sessionId &&
          _instructionsPlayerId == playerId) {
        _isLoadingInstructions = false;
        notifyListeners();
      }
    }
  }

  // --- Tài chính buổi ------------------------------------------------------ //

  String? _financeSessionId;
  SessionFinance? _finance;
  bool _isLoadingFinance = false;
  String? _financeErrorMessage;
  int _financeSerial = 0;

  SessionFinance? get finance => _finance;
  String? get financeSessionId => _financeSessionId;
  bool get isLoadingFinance => _isLoadingFinance;
  String? get financeErrorMessage => _financeErrorMessage;

  void _resetFinance() {
    _financeSerial++;
    _financeSessionId = null;
    _finance = null;
    _isLoadingFinance = false;
    _financeErrorMessage = null;
  }

  /// Tải tài chính buổi (chỉ finance). Đổi buổi sẽ xoá dữ liệu buổi trước và vô
  /// hiệu hoá phản hồi đang bay. Lỗi đọc giữ nguyên dữ liệu cũ, không thành rỗng.
  Future<void> fetchSessionFinance(
    String sessionId, {
    int limit = 50,
    int offset = 0,
  }) async {
    final generation = _generation;
    final serial = ++_financeSerial;
    if (_financeSessionId != sessionId) {
      _financeSessionId = sessionId;
      _finance = null;
    }
    _isLoadingFinance = true;
    _financeErrorMessage = null;
    notifyListeners();

    try {
      final finance = await _repository.getSessionFinance(
        sessionId,
        limit: limit,
        offset: offset,
      );
      if (_generation == generation &&
          serial == _financeSerial &&
          _financeSessionId == sessionId) {
        _finance = finance;
      }
    } catch (e) {
      if (_generation == generation &&
          serial == _financeSerial &&
          _financeSessionId == sessionId) {
        _financeErrorMessage = domainErrorMessage(e);
      }
    } finally {
      if (_generation == generation &&
          serial == _financeSerial &&
          _financeSessionId == sessionId) {
        _isLoadingFinance = false;
        notifyListeners();
      }
    }
  }

  // --- Sổ quỹ CLB ---------------------------------------------------------- //

  String? _ledgerClubId;
  ClubLedger? _ledger;
  bool _isLoadingLedger = false;
  bool _isLoadingMoreLedger = false;
  bool _ledgerHasMore = false;
  String? _ledgerErrorMessage;
  int _ledgerSerial = 0;

  ClubLedger? get ledger => _ledger;
  String? get ledgerClubId => _ledgerClubId;
  bool get isLoadingLedger => _isLoadingLedger;
  bool get isLoadingMoreLedger => _isLoadingMoreLedger;
  String? get ledgerErrorMessage => _ledgerErrorMessage;

  /// Còn trang để nối hay không, suy từ **trang vừa nhận** (trang đầy ⇒ còn).
  bool get hasMoreLedger => _ledger != null && _ledgerHasMore;

  void _resetLedger() {
    _ledgerSerial++;
    _ledgerClubId = null;
    _ledger = null;
    _isLoadingLedger = false;
    _isLoadingMoreLedger = false;
    _ledgerHasMore = false;
    _ledgerErrorMessage = null;
  }

  /// Tải sổ quỹ CLB. `loadMore` nối trang kế theo `offset` đã có; đổi CLB sẽ
  /// tải lại từ đầu. Lỗi giữ nguyên số dư cũ và **không** đánh dấu hết trang.
  Future<void> fetchClubLedger(
    String clubId, {
    int limit = 20,
    bool loadMore = false,
  }) async {
    final generation = _generation;
    final serial = ++_ledgerSerial;
    final previous = _ledger;
    final switching = _ledgerClubId != clubId;
    final appending = loadMore && !switching && previous != null;
    // Đã biết hết trang (trang cuối ngắn hơn limit) thì không phát RPC nối thêm.
    if (appending && !_ledgerHasMore) return;
    if (switching) {
      _ledgerClubId = clubId;
      _ledger = null;
      _ledgerHasMore = false;
    }
    final offset = appending ? previous.entries.length : 0;
    if (appending) {
      _isLoadingMoreLedger = true;
    } else {
      _isLoadingLedger = true;
    }
    _ledgerErrorMessage = null;
    notifyListeners();

    try {
      final page = await _repository.getClubLedger(
        clubId,
        limit: limit,
        offset: offset,
      );
      if (_generation == generation &&
          serial == _ledgerSerial &&
          _ledgerClubId == clubId) {
        // Chỉ trang vừa nhận quyết định còn trang: đầy ⇒ còn, ngắn ⇒ hết (B2).
        _ledgerHasMore = page.entries.length >= page.limit;
        _ledger = appending
            ? ClubLedger(
                clubId: page.clubId,
                balanceVnd: page.balanceVnd,
                limit: page.limit,
                offset: page.offset,
                entries: [...previous.entries, ...page.entries],
              )
            : page;
      }
    } catch (e) {
      if (_generation == generation &&
          serial == _ledgerSerial &&
          _ledgerClubId == clubId) {
        // Giữ nguyên _ledgerHasMore khi lỗi: không kết thúc phân trang do lỗi.
        _ledgerErrorMessage = domainErrorMessage(e);
      }
    } finally {
      if (_generation == generation &&
          serial == _ledgerSerial &&
          _ledgerClubId == clubId) {
        _isLoadingLedger = false;
        _isLoadingMoreLedger = false;
        notifyListeners();
      }
    }
  }

  /// Nối thêm một trang sổ quỹ của CLB đang mở, chỉ khi còn trang.
  Future<void> loadMoreLedger() async {
    final clubId = _ledgerClubId;
    final current = _ledger;
    if (clubId == null || current == null) return;
    if (_isLoadingLedger || _isLoadingMoreLedger) return;
    if (!_ledgerHasMore) return;
    await fetchClubLedger(clubId, limit: current.limit, loadMore: true);
  }

  // --- Thao tác (mutation) ------------------------------------------------- //

  bool _isSubmitting = false;
  String? _submitErrorMessage;

  bool get isSubmitting => _isSubmitting;
  String? get submitErrorMessage => _submitErrorMessage;

  Future<void> _safeRefresh(Future<void> Function() refresh) async {
    try {
      await refresh();
    } catch (_) {
      // Lỗi làm mới không được biến mutation đã commit thành thất bại.
      return;
    }
  }

  Future<T?> _runMutation<T>({
    required String operation,
    required List<Object?> payload,
    required String? requestId,
    required Future<T> Function(String key) call,
    Future<void> Function(T result)? refresh,
  }) async {
    if (_isSubmitting) return null;
    final generation = _generation;
    final key = _requestKey(operation, payload, requestId);
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      final result = await call(key);
      if (_generation != generation) return null;
      // Xoá key ngay sau khi server xác nhận, TRƯỚC khi làm mới (R3).
      if (_pendingRequests[operation]?.id == key) {
        _pendingRequests.remove(operation);
      }
      if (refresh != null) {
        await _safeRefresh(() => refresh(result));
      }
      return _generation == generation ? result : null;
    } catch (e) {
      if (_generation == generation) {
        _submitErrorMessage = domainErrorMessage(e);
      }
      return null;
    } finally {
      if (_generation == generation) {
        _isSubmitting = false;
        notifyListeners();
      }
    }
  }

  /// Làm mới các đường đọc đang mở của một buổi (chỉ khi đã được tải, để không
  /// gọi `get_session_finance` ngoài quyền của người chơi).
  Future<void> _refreshSessionReads(String sessionId) async {
    if (_financeSessionId == sessionId) {
      await fetchSessionFinance(sessionId);
    }
    if (_instructionsSessionId == sessionId) {
      await fetchPaymentInstructions(
        sessionId,
        playerId: _instructionsPlayerId,
      );
    }
    final clubId = _ledgerClubId;
    if (clubId != null) {
      await fetchClubLedger(clubId);
    }
  }

  Future<void> _refreshClubReads(String clubId) async {
    if (_ledgerClubId == clubId) {
      await fetchClubLedger(clubId);
    }
  }

  Future<ExpenseResult?> postExpense({
    required String sessionId,
    required String category,
    required String title,
    required int amountVnd,
    String? requestId,
  }) {
    return _runMutation<ExpenseResult>(
      operation: 'post_session_expense',
      payload: [sessionId, category, title, amountVnd],
      requestId: requestId,
      call: (key) => _repository.postSessionExpense(
        requestId: key,
        sessionId: sessionId,
        category: category,
        title: title,
        amountVnd: amountVnd,
      ),
      refresh: (result) => _refreshSessionReads(result.sessionId),
    );
  }

  Future<ExpenseResult?> reverseExpense({
    required String sessionId,
    required String expenseId,
    required String reason,
    String? requestId,
  }) {
    return _runMutation<ExpenseResult>(
      operation: 'reverse_session_expense',
      payload: [sessionId, expenseId, reason],
      requestId: requestId,
      call: (key) => _repository.reverseSessionExpense(
        requestId: key,
        sessionId: sessionId,
        expenseId: expenseId,
        reason: reason,
      ),
      refresh: (result) => _refreshSessionReads(result.sessionId),
    );
  }

  Future<RevisionResult?> finalizeCharges({
    required String sessionId,
    required int expectedVersion,
    required int expectedBillingInputVersion,
    String? reason,
    String? requestId,
  }) {
    return _runMutation<RevisionResult>(
      operation: 'finalize_session_charges',
      payload: [
        sessionId,
        expectedVersion,
        expectedBillingInputVersion,
        reason,
      ],
      requestId: requestId,
      call: (key) => _repository.finalizeSessionCharges(
        requestId: key,
        sessionId: sessionId,
        expectedVersion: expectedVersion,
        expectedBillingInputVersion: expectedBillingInputVersion,
        reason: reason,
      ),
      refresh: (result) => _refreshSessionReads(result.sessionId),
    );
  }

  Future<Session?> completeSession({
    required String sessionId,
    required int expectedVersion,
    String? requestId,
  }) {
    return _runMutation<Session>(
      operation: 'complete_session',
      payload: [sessionId, expectedVersion],
      requestId: requestId,
      call: (key) => _repository.completeSession(
        requestId: key,
        sessionId: sessionId,
        expectedVersion: expectedVersion,
      ),
      refresh: (session) => _refreshSessionReads(session.id),
    );
  }

  Future<PaymentResult?> submitPayment({
    required String playerId,
    required int amountVnd,
    String method = 'bank_transfer',
    String? reference,
    String? requestId,
  }) {
    return _runMutation<PaymentResult>(
      operation: 'submit_payment',
      payload: [playerId, amountVnd, method, reference],
      requestId: requestId,
      call: (key) => _repository.submitPayment(
        requestId: key,
        playerId: playerId,
        amountVnd: amountVnd,
        method: method,
        reference: reference,
      ),
      refresh: (result) => _refreshSessionReads(result.sessionId),
    );
  }

  Future<PaymentResult?> confirmPayment({
    required String paymentId,
    String? requestId,
  }) {
    return _runMutation<PaymentResult>(
      operation: 'confirm_payment',
      payload: [paymentId],
      requestId: requestId,
      call: (key) => _repository.confirmPayment(
        requestId: key,
        paymentId: paymentId,
      ),
      refresh: (result) => _refreshSessionReads(result.sessionId),
    );
  }

  Future<PaymentResult?> rejectPayment({
    required String paymentId,
    required String reason,
    String? requestId,
  }) {
    return _runMutation<PaymentResult>(
      operation: 'reject_payment',
      payload: [paymentId, reason],
      requestId: requestId,
      call: (key) => _repository.rejectPayment(
        requestId: key,
        paymentId: paymentId,
        reason: reason,
      ),
      refresh: (result) => _refreshSessionReads(result.sessionId),
    );
  }

  Future<PaymentResult?> reversePayment({
    required String paymentId,
    required String reason,
    String? requestId,
  }) {
    return _runMutation<PaymentResult>(
      operation: 'reverse_payment',
      payload: [paymentId, reason],
      requestId: requestId,
      call: (key) => _repository.reversePayment(
        requestId: key,
        paymentId: paymentId,
        reason: reason,
      ),
      refresh: (result) => _refreshSessionReads(result.sessionId),
    );
  }

  Future<PaymentResult?> recordCashPayment({
    required String playerId,
    required int amountVnd,
    String? reference,
    String? requestId,
  }) {
    return _runMutation<PaymentResult>(
      operation: 'record_cash_payment',
      payload: [playerId, amountVnd, reference],
      requestId: requestId,
      call: (key) => _repository.recordCashPayment(
        requestId: key,
        playerId: playerId,
        amountVnd: amountVnd,
        reference: reference,
      ),
      refresh: (result) => _refreshSessionReads(result.sessionId),
    );
  }

  Future<ClubTransactionResult?> postManualClubTransaction({
    required String clubId,
    required String direction,
    required int amountVnd,
    required String title,
    String? requestId,
  }) {
    return _runMutation<ClubTransactionResult>(
      operation: 'post_manual_club_transaction',
      payload: [clubId, direction, amountVnd, title],
      requestId: requestId,
      call: (key) => _repository.postManualClubTransaction(
        requestId: key,
        clubId: clubId,
        direction: direction,
        amountVnd: amountVnd,
        title: title,
      ),
      refresh: (result) => _refreshClubReads(result.clubId),
    );
  }

  Future<ClubTransactionResult?> reverseClubTransaction({
    required String transactionId,
    required String reason,
    String? requestId,
  }) {
    return _runMutation<ClubTransactionResult>(
      operation: 'reverse_club_transaction',
      payload: [transactionId, reason],
      requestId: requestId,
      call: (key) => _repository.reverseClubTransaction(
        requestId: key,
        transactionId: transactionId,
        reason: reason,
      ),
      refresh: (result) => _refreshClubReads(result.clubId),
    );
  }
}
