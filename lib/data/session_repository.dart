import 'package:supabase_flutter/supabase_flutter.dart' hide Session;

import '../models/session.dart';

/// Truy cập buổi chơi qua RPC (mọi mutation có `request_id`, không ghi cột trực tiếp).
class SessionRepository {
  final SupabaseClient _client;

  SessionRepository({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  static List<Session> _toSessions(dynamic response) {
    if (response is List) {
      return response
          .map((item) => Session.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    }
    return [];
  }

  Session _toSession(dynamic response) =>
      Session.fromJson(Map<String, dynamic>.from(response as Map));

  /// Chi tiết buổi chơi theo quyền (public/unlisted mở; draft/private cần quyền).
  Future<Session> getSessionDetail(String sessionId) async {
    final response = await _client.rpc(
      'get_session_public_detail',
      params: {'p_session_id': sessionId},
    );
    return _toSession(response);
  }

  /// Danh sách buổi tôi quản lý (host/cohost/chủ CLB/thủ quỹ).
  Future<List<Session>> listMySessions({int limit = 50, int offset = 0}) async {
    final response = await _client.rpc(
      'list_my_sessions',
      params: {'p_limit': limit, 'p_offset': offset},
    );
    return _toSessions(response);
  }

  /// Khám phá buổi công khai (whitelist, anon đọc được).
  Future<List<Session>> listPublicSessions({
    String? area,
    DateTime? from,
    DateTime? to,
    String? feeMode,
    bool onlyAvailable = false,
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _client.rpc('list_public_sessions', params: {
      'p_area': area,
      'p_from': from?.toUtc().toIso8601String(),
      'p_to': to?.toUtc().toIso8601String(),
      'p_fee_mode': feeMode,
      'p_only_available': onlyAvailable,
      'p_limit': limit,
      'p_offset': offset,
    });
    return _toSessions(response);
  }

  /// Danh sách người đăng ký của buổi (chỉ host/quản lý).
  Future<List<SessionPlayer>> listSessionPlayers(
    String sessionId, {
    int limit = 100,
    int offset = 0,
  }) async {
    final response = await _client.rpc('list_session_players', params: {
      'p_session_id': sessionId,
      'p_limit': limit,
      'p_offset': offset,
    });
    if (response is List) {
      return response
          .map((item) =>
              SessionPlayer.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    }
    return [];
  }

  Future<Session> createSession({
    required String requestId,
    required String venueId,
    required String title,
    required DateTime startsAt,
    required DateTime endsAt,
    required int capacity,
    required int courtCount,
    String? clubId,
    String? description,
    String? levelRequirement,
    String visibility = 'unlisted',
    String approvalMode = 'host_approval',
    String feeMode = 'split_actual',
    int? memberFeeVnd,
    int? guestFeeVnd,
    DateTime? registrationDeadline,
    DateTime? cancellationDeadline,
  }) async {
    final response = await _client.rpc('create_session', params: {
      'p_venue_id': venueId,
      'p_title': title,
      'p_starts_at': startsAt.toUtc().toIso8601String(),
      'p_ends_at': endsAt.toUtc().toIso8601String(),
      'p_capacity': capacity,
      'p_court_count': courtCount,
      'p_club_id': clubId,
      'p_description': description,
      'p_level_requirement': levelRequirement,
      'p_visibility': visibility,
      'p_approval_mode': approvalMode,
      'p_fee_mode': feeMode,
      'p_member_fee_vnd': memberFeeVnd,
      'p_guest_fee_vnd': guestFeeVnd,
      'p_registration_deadline': registrationDeadline?.toUtc().toIso8601String(),
      'p_cancellation_deadline': cancellationDeadline?.toUtc().toIso8601String(),
      'p_request_id': requestId,
    });
    return _toSession(response);
  }

  Future<Session> updateSession({
    required String requestId,
    required String sessionId,
    required int version,
    required String venueId,
    required String title,
    required DateTime startsAt,
    required DateTime endsAt,
    required int capacity,
    required int courtCount,
    String? description,
    String? levelRequirement,
    String visibility = 'unlisted',
    String approvalMode = 'host_approval',
    String feeMode = 'split_actual',
    int? memberFeeVnd,
    int? guestFeeVnd,
    DateTime? registrationDeadline,
    DateTime? cancellationDeadline,
  }) async {
    final response = await _client.rpc('update_session', params: {
      'p_session_id': sessionId,
      'p_version': version,
      'p_venue_id': venueId,
      'p_title': title,
      'p_starts_at': startsAt.toUtc().toIso8601String(),
      'p_ends_at': endsAt.toUtc().toIso8601String(),
      'p_capacity': capacity,
      'p_court_count': courtCount,
      'p_description': description,
      'p_level_requirement': levelRequirement,
      'p_visibility': visibility,
      'p_approval_mode': approvalMode,
      'p_fee_mode': feeMode,
      'p_member_fee_vnd': memberFeeVnd,
      'p_guest_fee_vnd': guestFeeVnd,
      'p_registration_deadline': registrationDeadline?.toUtc().toIso8601String(),
      'p_cancellation_deadline': cancellationDeadline?.toUtc().toIso8601String(),
      'p_request_id': requestId,
    });
    return _toSession(response);
  }

  /// Đổi vòng đời: 'publish' hoặc 'cancel'.
  Future<Session> setSessionLifecycle({
    required String requestId,
    required String sessionId,
    required String action,
  }) async {
    final response = await _client.rpc('set_session_lifecycle', params: {
      'p_session_id': sessionId,
      'p_action': action,
      'p_request_id': requestId,
    });
    return _toSession(response);
  }

  /// Bắt đầu buổi đã công bố để điểm danh (published → in_progress).
  Future<Session> startSession({
    required String requestId,
    required String sessionId,
  }) async {
    final response = await _client.rpc('start_session', params: {
      'p_session_id': sessionId,
      'p_request_id': requestId,
    });
    return _toSession(response);
  }

  /// Nhân bản cấu hình buổi chơi (không sao chép người/tiền).
  Future<Session> duplicateSession({
    required String requestId,
    required String sessionId,
    required DateTime startsAt,
    required DateTime endsAt,
  }) async {
    final response = await _client.rpc('duplicate_session', params: {
      'p_session_id': sessionId,
      'p_starts_at': startsAt.toUtc().toIso8601String(),
      'p_ends_at': endsAt.toUtc().toIso8601String(),
      'p_request_id': requestId,
    });
    return _toSession(response);
  }

  // --- BH-05: đăng ký, duyệt, huỷ, điểm danh và lời mời danh sách chờ ----- //

  RegistrationResult _toResult(dynamic response) => RegistrationResult.fromJson(
    Map<String, dynamic>.from(response as Map),
  );

  WaitlistInvitation _toInvitation(dynamic response) =>
      WaitlistInvitation.fromJson(Map<String, dynamic>.from(response as Map));

  /// Người chơi tự gửi yêu cầu tham gia buổi đã công bố.
  Future<RegistrationResult> requestJoinSession({
    required String requestId,
    required String sessionId,
    String? contact,
  }) async {
    final response = await _client.rpc('request_join_session', params: {
      'p_session_id': sessionId,
      'p_contact': contact,
      'p_request_id': requestId,
    });
    return _toResult(response);
  }

  /// Host/cohost thêm thành viên CLB hoặc khách chưa có tài khoản.
  Future<RegistrationResult> addSessionPlayer({
    required String requestId,
    required String sessionId,
    String? memberId,
    String? guestName,
    String? contact,
    bool feeExempt = false,
    bool allowWaitlist = false,
  }) async {
    final response = await _client.rpc('add_session_player', params: {
      'p_session_id': sessionId,
      'p_member_id': memberId,
      'p_guest_name': guestName,
      'p_contact': contact,
      'p_fee_exempt': feeExempt,
      'p_allow_waitlist': allowWaitlist,
      'p_request_id': requestId,
    });
    return _toResult(response);
  }

  /// Host/cohost duyệt/từ chối/đưa vào danh sách chờ một đăng ký.
  Future<RegistrationResult> decideRegistration({
    required String requestId,
    required String sessionId,
    required String playerId,
    required String decision,
    String? reason,
  }) async {
    final response = await _client.rpc('decide_registration', params: {
      'p_session_id': sessionId,
      'p_player_id': playerId,
      'p_decision': decision,
      'p_reason': reason,
      'p_request_id': requestId,
    });
    return _toResult(response);
  }

  /// Hủy đăng ký (người chơi tự hủy theo hạn, hoặc host/quản lý theo quyền).
  Future<RegistrationResult> cancelRegistration({
    required String requestId,
    required String sessionId,
    required String playerId,
    String? reason,
  }) async {
    final response = await _client.rpc('cancel_registration', params: {
      'p_session_id': sessionId,
      'p_player_id': playerId,
      'p_reason': reason,
      'p_request_id': requestId,
    });
    return _toResult(response);
  }

  /// Điểm danh người đã confirmed khi buổi đang diễn ra.
  Future<RegistrationResult> recordAttendance({
    required String requestId,
    required String sessionId,
    required String playerId,
    required String attendance,
  }) async {
    final response = await _client.rpc('record_attendance', params: {
      'p_session_id': sessionId,
      'p_player_id': playerId,
      'p_attendance': attendance,
      'p_request_id': requestId,
    });
    return _toResult(response);
  }

  /// Host phát hành lời mời nhận chỗ cho người trong danh sách chờ.
  Future<WaitlistInvitation> inviteWaitlistedPlayer({
    required String requestId,
    required String sessionId,
    required String playerId,
    DateTime? expiresAt,
  }) async {
    final response = await _client.rpc('invite_waitlisted_player', params: {
      'p_session_id': sessionId,
      'p_player_id': playerId,
      'p_expires_at': expiresAt?.toUtc().toIso8601String(),
      'p_request_id': requestId,
    });
    return _toInvitation(response);
  }

  /// Thu hồi lời mời đang chờ (chưa được chấp nhận).
  Future<WaitlistInvitation> revokeWaitlistInvitation({
    required String requestId,
    required String sessionId,
    required String invitationId,
    String? reason,
  }) async {
    final response = await _client.rpc('revoke_waitlist_invitation', params: {
      'p_session_id': sessionId,
      'p_invitation_id': invitationId,
      'p_reason': reason,
      'p_request_id': requestId,
    });
    return _toInvitation(response);
  }

  /// Chấp nhận lời mời: người nhận tự xác nhận hoặc host ghi nhận đồng ý cho khách.
  Future<RegistrationResult> acceptWaitlistInvitation({
    required String requestId,
    required String sessionId,
    required String invitationId,
    String? consentNote,
  }) async {
    final response = await _client.rpc('accept_waitlist_invitation', params: {
      'p_session_id': sessionId,
      'p_invitation_id': invitationId,
      'p_consent_note': consentNote,
      'p_request_id': requestId,
    });
    return _toResult(response);
  }

  /// Lời mời đang chờ của chính người dùng trong buổi (nếu có).
  Future<WaitlistInvitation?> getMyWaitlistInvitation(String sessionId) async {
    final response = await _client.rpc(
      'get_my_waitlist_invitation',
      params: {'p_session_id': sessionId},
    );
    if (response is Map) {
      return _toInvitation(response);
    }
    return null;
  }
}
