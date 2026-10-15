import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';

import '../core/domain_error.dart';
import '../data/session_repository.dart';
import '../models/session.dart';
import 'auth_provider.dart';

/// Dữ liệu form tạo/sửa buổi chơi (thời gian đã ở UTC).
class SessionFormData {
  final String venueId;
  final String title;
  final DateTime startsAt;
  final DateTime endsAt;
  final int capacity;
  final int courtCount;
  final String? clubId;
  final String? description;
  final String? levelRequirement;
  final String visibility;
  final String approvalMode;
  final String feeMode;
  final int? memberFeeVnd;
  final int? guestFeeVnd;
  final DateTime? registrationDeadline;
  final DateTime? cancellationDeadline;

  const SessionFormData({
    required this.venueId,
    required this.title,
    required this.startsAt,
    required this.endsAt,
    required this.capacity,
    required this.courtCount,
    this.clubId,
    this.description,
    this.levelRequirement,
    this.visibility = 'unlisted',
    this.approvalMode = 'host_approval',
    this.feeMode = 'split_actual',
    this.memberFeeVnd,
    this.guestFeeVnd,
    this.registrationDeadline,
    this.cancellationDeadline,
  });

  /// Payload ổn định để tính khoá idempotency khi retry.
  List<Object?> get requestPayload => [
    venueId,
    title,
    startsAt.toUtc().toIso8601String(),
    endsAt.toUtc().toIso8601String(),
    capacity,
    courtCount,
    clubId,
    description,
    levelRequirement,
    visibility,
    approvalMode,
    feeMode,
    memberFeeVnd,
    guestFeeVnd,
    registrationDeadline?.toUtc().toIso8601String(),
    cancellationDeadline?.toUtc().toIso8601String(),
  ];
}

/// Quản lý trạng thái buổi chơi: khám phá công khai, danh sách quản lý và chi tiết.
///
/// Gắn với vòng đời auth: đổi người dùng/đăng xuất sẽ dọn state riêng tư và tăng
/// generation để bỏ qua phản hồi của phiên cũ.
class SessionProvider extends ChangeNotifier {
  final SessionRepository _repository;

  final AuthProvider? auth;
  String? _authUserId;
  int _generation = 0;
  int _publicSerial = 0;
  int _mineSerial = 0;
  int _detailSerial = 0;
  bool _disposed = false;
  final _pendingRequests = <String, ({String payload, String id})>{};

  SessionProvider({SessionRepository? repository, this.auth})
    : _repository = repository ?? SessionRepository() {
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
    _publicSessions = [];
    _publicErrorMessage = null;
    _mySessions = [];
    _myErrorMessage = null;
    _currentSessionId = null;
    _currentSession = null;
    _currentPlayers = [];
    _myInvitation = null;
    _isLoadingInvitation = false;
    _invitationErrorMessage = null;
    _playersErrorMessage = null;
    _isLoadingPlayers = false;
    _detailErrorMessage = null;
    _isLoadingPublic = false;
    _isLoadingMine = false;
    _isLoadingDetail = false;
    _isSubmitting = false;
    _submitErrorMessage = null;
    notifyListeners();
  }

  // --- Khám phá công khai ------------------------------------------------ //
  List<Session> _publicSessions = [];
  bool _isLoadingPublic = false;
  String? _publicErrorMessage;
  SessionFilter _filter = const SessionFilter();

  List<Session> get publicSessions => _publicSessions;
  bool get isLoadingPublic => _isLoadingPublic;
  String? get publicErrorMessage => _publicErrorMessage;
  SessionFilter get filter => _filter;

  /// Tải danh sách buổi công khai theo bộ lọc (PD-02).
  Future<void> fetchPublicSessions({SessionFilter? filter}) async {
    if (filter != null) _filter = filter;
    final generation = _generation;
    final serial = ++_publicSerial;
    _isLoadingPublic = true;
    _publicErrorMessage = null;
    notifyListeners();

    try {
      final sessions = await _repository.listPublicSessions(
        area: _filter.area,
        from: _filter.from,
        to: _filter.to,
        feeMode: _filter.feeMode,
        onlyAvailable: _filter.onlyAvailable,
      );
      if (_generation != generation || serial != _publicSerial) return;
      _publicSessions = sessions;
    } catch (e) {
      if (_generation == generation && serial == _publicSerial) {
        _publicErrorMessage = domainErrorMessage(e);
      }
    } finally {
      if (_generation == generation && serial == _publicSerial) {
        _isLoadingPublic = false;
        notifyListeners();
      }
    }
  }

  // --- Buổi tôi quản lý -------------------------------------------------- //
  List<Session> _mySessions = [];
  bool _isLoadingMine = false;
  String? _myErrorMessage;

  List<Session> get mySessions => _mySessions;
  bool get isLoadingMine => _isLoadingMine;
  String? get myErrorMessage => _myErrorMessage;

  Future<void> fetchMySessions() async {
    final generation = _generation;
    final serial = ++_mineSerial;
    _isLoadingMine = true;
    _myErrorMessage = null;
    notifyListeners();

    try {
      final sessions = await _repository.listMySessions();
      if (_generation != generation || serial != _mineSerial) return;
      _mySessions = sessions;
    } catch (e) {
      if (_generation == generation && serial == _mineSerial) {
        _myErrorMessage = domainErrorMessage(e);
      }
    } finally {
      if (_generation == generation && serial == _mineSerial) {
        _isLoadingMine = false;
        notifyListeners();
      }
    }
  }

  // --- Chi tiết buổi chơi ------------------------------------------------ //
  String? _currentSessionId;
  Session? _currentSession;
  List<SessionPlayer> _currentPlayers = [];
  WaitlistInvitation? _myInvitation;
  bool _isLoadingDetail = false;
  String? _detailErrorMessage;

  // Trạng thái riêng của lời mời danh sách chờ (B1): phân biệt "không có lời mời"
  // với "tải lời mời lỗi", tương tự playersErrorMessage.
  bool _isLoadingInvitation = false;
  String? _invitationErrorMessage;
  int _invitationSerial = 0;

  String? get currentSessionId => _currentSessionId;
  Session? get currentSession => _currentSession;
  List<SessionPlayer> get currentPlayers => _currentPlayers;
  WaitlistInvitation? get myInvitation => _myInvitation;
  bool get isLoadingInvitation => _isLoadingInvitation;
  String? get invitationErrorMessage => _invitationErrorMessage;
  bool get isLoadingDetail => _isLoadingDetail;
  String? get detailErrorMessage => _detailErrorMessage;

  /// Chỉ host/quản lý buổi mới xem được danh sách đăng ký (F7).
  bool _isLoadingPlayers = false;
  String? _playersErrorMessage;
  bool get isLoadingPlayers => _isLoadingPlayers;
  String? get playersErrorMessage => _playersErrorMessage;

  bool get canManagePlayers => _currentSession?.canManage == true;

  Future<void> fetchSessionDetail(String sessionId) async {
    final generation = _generation;
    final serial = ++_detailSerial;
    if (_currentSessionId != sessionId) {
      _currentSessionId = sessionId;
      _currentSession = null;
      _currentPlayers = [];
      _resetInvitation();
      _playersErrorMessage = null;
      _isLoadingPlayers = false;
    }
    _isLoadingDetail = true;
    _detailErrorMessage = null;
    notifyListeners();

    try {
      final session = await _repository.getSessionDetail(sessionId);
      if (_generation != generation ||
          serial != _detailSerial ||
          _currentSessionId != sessionId) {
        return;
      }
      _currentSession = session;
      _isLoadingDetail = false;
      notifyListeners();
      if (session.canManage) {
        await fetchSessionPlayers(sessionId);
      } else if (session.myRegistration?.registrationStatus == 'waitlisted') {
        await fetchMyInvitation(sessionId);
      } else {
        // B2: detail mới không còn điều kiện hiển thị lời mời → xoá state cũ và
        // vô hiệu hoá phản hồi lời mời đang bay để không khôi phục lại.
        _resetInvitation();
        notifyListeners();
      }
    } catch (e) {
      if (_generation == generation &&
          serial == _detailSerial &&
          _currentSessionId == sessionId) {
        _detailErrorMessage = domainErrorMessage(e);
        _isLoadingDetail = false;
        notifyListeners();
      }
    }
  }

  Future<void> fetchSessionPlayers(String sessionId) async {
    final generation = _generation;
    final serial = _detailSerial;
    if (_currentSessionId != sessionId) return;
    _isLoadingPlayers = true;
    _playersErrorMessage = null;
    notifyListeners();
    try {
      final players = await _repository.listSessionPlayers(sessionId);
      if (_generation == generation &&
          serial == _detailSerial &&
          _currentSessionId == sessionId) {
        _currentPlayers = players;
        notifyListeners();
      }
    } catch (e) {
      if (_generation == generation &&
          serial == _detailSerial &&
          _currentSessionId == sessionId) {
        _playersErrorMessage = domainErrorMessage(e);
      }
    } finally {
      if (_generation == generation &&
          serial == _detailSerial &&
          _currentSessionId == sessionId) {
        _isLoadingPlayers = false;
        notifyListeners();
      }
    }
  }

  // --- Thao tác (mutation) ----------------------------------------------- //
  bool _isSubmitting = false;
  String? _submitErrorMessage;

  bool get isSubmitting => _isSubmitting;
  String? get submitErrorMessage => _submitErrorMessage;

  Future<Session?> _runMutation({
    required String operation,
    required List<Object?> payload,
    required String? requestId,
    required Future<Session> Function(String key) call,
    bool refreshMine = true,
  }) async {
    if (_isSubmitting) return null;
    final generation = _generation;
    final key = _requestKey(operation, payload, requestId);
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      final session = await call(key);
      if (_generation != generation) return null;
      _pendingRequests.remove(operation);
      if (refreshMine) await fetchMySessions();
      return _generation == generation ? session : null;
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

  Future<Session?> createSession(SessionFormData form, {String? requestId}) {
    return _runMutation(
      operation: 'create_session',
      payload: form.requestPayload,
      requestId: requestId,
      call: (key) => _repository.createSession(
        requestId: key,
        venueId: form.venueId,
        title: form.title,
        startsAt: form.startsAt,
        endsAt: form.endsAt,
        capacity: form.capacity,
        courtCount: form.courtCount,
        clubId: form.clubId,
        description: form.description,
        levelRequirement: form.levelRequirement,
        visibility: form.visibility,
        approvalMode: form.approvalMode,
        feeMode: form.feeMode,
        memberFeeVnd: form.memberFeeVnd,
        guestFeeVnd: form.guestFeeVnd,
        registrationDeadline: form.registrationDeadline,
        cancellationDeadline: form.cancellationDeadline,
      ),
    );
  }

  Future<Session?> updateSession(
    SessionFormData form, {
    required String sessionId,
    required int version,
    String? requestId,
  }) {
    return _runMutation(
      operation: 'update_session',
      payload: [sessionId, version, ...form.requestPayload],
      requestId: requestId,
      call: (key) => _repository.updateSession(
        requestId: key,
        sessionId: sessionId,
        version: version,
        venueId: form.venueId,
        title: form.title,
        startsAt: form.startsAt,
        endsAt: form.endsAt,
        capacity: form.capacity,
        courtCount: form.courtCount,
        description: form.description,
        levelRequirement: form.levelRequirement,
        visibility: form.visibility,
        approvalMode: form.approvalMode,
        feeMode: form.feeMode,
        memberFeeVnd: form.memberFeeVnd,
        guestFeeVnd: form.guestFeeVnd,
        registrationDeadline: form.registrationDeadline,
        cancellationDeadline: form.cancellationDeadline,
      ),
    );
  }

  Future<Session?> publishSession(String sessionId, {String? requestId}) {
    return _runMutation(
      operation: 'set_session_lifecycle_publish',
      payload: [sessionId],
      requestId: requestId,
      call: (key) => _repository.setSessionLifecycle(
        requestId: key,
        sessionId: sessionId,
        action: 'publish',
      ),
    );
  }

  Future<Session?> cancelSession(String sessionId, {String? requestId}) {
    return _runMutation(
      operation: 'set_session_lifecycle_cancel',
      payload: [sessionId],
      requestId: requestId,
      call: (key) => _repository.setSessionLifecycle(
        requestId: key,
        sessionId: sessionId,
        action: 'cancel',
      ),
    );
  }

  Future<Session?> duplicateSession(
    String sessionId, {
    required DateTime startsAt,
    required DateTime endsAt,
    String? requestId,
  }) {
    return _runMutation(
      operation: 'duplicate_session',
      payload: [
        sessionId,
        startsAt.toUtc().toIso8601String(),
        endsAt.toUtc().toIso8601String(),
      ],
      requestId: requestId,
      call: (key) => _repository.duplicateSession(
        requestId: key,
        sessionId: sessionId,
        startsAt: startsAt,
        endsAt: endsAt,
      ),
    );
  }

  // --- BH-05: đăng ký, duyệt, huỷ, điểm danh và lời mời ------------------- //

  /// Xoá state lời mời và vô hiệu hoá mọi phản hồi lời mời đang bay (B2).
  void _resetInvitation() {
    _invitationSerial++;
    _myInvitation = null;
    _invitationErrorMessage = null;
    _isLoadingInvitation = false;
  }

  /// Tải lời mời đang chờ của chính người dùng (chỉ khi đang ở danh sách chờ).
  ///
  /// B1: tách loading/error riêng và chỉ coi response thành công `null` là rỗng;
  /// lỗi tải không bị nuốt thành "không có lời mời". B2: dùng `_invitationSerial`
  /// để phản hồi đến trễ không ghi đè state đã bị xoá.
  Future<void> fetchMyInvitation(String sessionId) async {
    final generation = _generation;
    final serial = ++_invitationSerial;
    if (_currentSessionId != sessionId) return;

    if (_authUserId == null) {
      _resetInvitation();
      notifyListeners();
      return;
    }

    _isLoadingInvitation = true;
    _invitationErrorMessage = null;
    notifyListeners();

    try {
      final invitation = await _repository.getMyWaitlistInvitation(sessionId);
      if (_generation == generation &&
          serial == _invitationSerial &&
          _currentSessionId == sessionId) {
        _myInvitation = invitation;
      }
    } catch (e) {
      if (_generation == generation &&
          serial == _invitationSerial &&
          _currentSessionId == sessionId) {
        _invitationErrorMessage = domainErrorMessage(e);
      }
    } finally {
      if (_generation == generation &&
          serial == _invitationSerial &&
          _currentSessionId == sessionId) {
        _isLoadingInvitation = false;
        notifyListeners();
      }
    }
  }

  /// Chạy mutation đăng ký: chống nhấn lặp, giữ request key khi lỗi, làm mới
  /// chi tiết (và danh sách người/lời mời) sau khi thành công.
  Future<bool> _runPlayerMutation({
    required String operation,
    required List<Object?> payload,
    required String? requestId,
    required Future<void> Function(String key) call,
  }) async {
    if (_isSubmitting) return false;
    final generation = _generation;
    final key = _requestKey(operation, payload, requestId);
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      await call(key);
      if (_generation != generation) return false;
      // Xoá key ngay sau khi server xác nhận, trước khi làm mới danh sách (R3).
      if (_pendingRequests[operation]?.id == key) {
        _pendingRequests.remove(operation);
      }
      final sessionId = _currentSessionId;
      if (sessionId != null) {
        await fetchSessionDetail(sessionId);
      }
      return _generation == generation;
    } catch (e) {
      if (_generation == generation) {
        _submitErrorMessage = domainErrorMessage(e);
      }
      return false;
    } finally {
      if (_generation == generation) {
        _isSubmitting = false;
        notifyListeners();
      }
    }
  }

  String? _sessionIdForMutation() => _currentSessionId;

  Future<bool> requestJoinSession({String? contact, String? requestId}) {
    final sessionId = _sessionIdForMutation();
    if (sessionId == null) return Future.value(false);
    return _runPlayerMutation(
      operation: 'request_join_session',
      payload: [sessionId, contact],
      requestId: requestId,
      call: (key) async {
        await _repository.requestJoinSession(
          requestId: key,
          sessionId: sessionId,
          contact: contact,
        );
      },
    );
  }

  Future<bool> addSessionPlayer({
    String? memberId,
    String? guestName,
    String? contact,
    bool feeExempt = false,
    bool allowWaitlist = false,
    String? requestId,
  }) {
    final sessionId = _sessionIdForMutation();
    if (sessionId == null) return Future.value(false);
    return _runPlayerMutation(
      operation: 'add_session_player',
      payload: [
        sessionId,
        memberId,
        guestName,
        contact,
        feeExempt,
        allowWaitlist,
      ],
      requestId: requestId,
      call: (key) async {
        await _repository.addSessionPlayer(
          requestId: key,
          sessionId: sessionId,
          memberId: memberId,
          guestName: guestName,
          contact: contact,
          feeExempt: feeExempt,
          allowWaitlist: allowWaitlist,
        );
      },
    );
  }

  Future<bool> decideRegistration({
    required String playerId,
    required String decision,
    String? reason,
    String? requestId,
  }) {
    final sessionId = _sessionIdForMutation();
    if (sessionId == null) return Future.value(false);
    return _runPlayerMutation(
      operation: 'decide_registration',
      payload: [sessionId, playerId, decision, reason],
      requestId: requestId,
      call: (key) async {
        await _repository.decideRegistration(
          requestId: key,
          sessionId: sessionId,
          playerId: playerId,
          decision: decision,
          reason: reason,
        );
      },
    );
  }

  Future<bool> cancelRegistration({
    required String playerId,
    String? reason,
    String? requestId,
  }) {
    final sessionId = _sessionIdForMutation();
    if (sessionId == null) return Future.value(false);
    return _runPlayerMutation(
      operation: 'cancel_registration',
      payload: [sessionId, playerId, reason],
      requestId: requestId,
      call: (key) async {
        await _repository.cancelRegistration(
          requestId: key,
          sessionId: sessionId,
          playerId: playerId,
          reason: reason,
        );
      },
    );
  }

  Future<bool> recordAttendance({
    required String playerId,
    required String attendance,
    String? requestId,
  }) {
    final sessionId = _sessionIdForMutation();
    if (sessionId == null) return Future.value(false);
    return _runPlayerMutation(
      operation: 'record_attendance',
      payload: [sessionId, playerId, attendance],
      requestId: requestId,
      call: (key) async {
        await _repository.recordAttendance(
          requestId: key,
          sessionId: sessionId,
          playerId: playerId,
          attendance: attendance,
        );
      },
    );
  }

  Future<bool> inviteWaitlistedPlayer({
    required String playerId,
    DateTime? expiresAt,
    String? requestId,
  }) {
    final sessionId = _sessionIdForMutation();
    if (sessionId == null) return Future.value(false);
    return _runPlayerMutation(
      operation: 'invite_waitlisted_player',
      payload: [
        sessionId,
        playerId,
        expiresAt?.toUtc().toIso8601String(),
      ],
      requestId: requestId,
      call: (key) async {
        await _repository.inviteWaitlistedPlayer(
          requestId: key,
          sessionId: sessionId,
          playerId: playerId,
          expiresAt: expiresAt,
        );
      },
    );
  }

  Future<bool> revokeWaitlistInvitation({
    required String invitationId,
    String? reason,
    String? requestId,
  }) {
    final sessionId = _sessionIdForMutation();
    if (sessionId == null) return Future.value(false);
    return _runPlayerMutation(
      operation: 'revoke_waitlist_invitation',
      payload: [sessionId, invitationId, reason],
      requestId: requestId,
      call: (key) async {
        await _repository.revokeWaitlistInvitation(
          requestId: key,
          sessionId: sessionId,
          invitationId: invitationId,
          reason: reason,
        );
      },
    );
  }

  Future<bool> acceptWaitlistInvitation({
    required String invitationId,
    String? consentNote,
    String? requestId,
  }) {
    final sessionId = _sessionIdForMutation();
    if (sessionId == null) return Future.value(false);
    return _runPlayerMutation(
      operation: 'accept_waitlist_invitation',
      payload: [sessionId, invitationId, consentNote],
      requestId: requestId,
      call: (key) async {
        await _repository.acceptWaitlistInvitation(
          requestId: key,
          sessionId: sessionId,
          invitationId: invitationId,
          consentNote: consentNote,
        );
      },
    );
  }
}
