/// Buổi chơi (session) — model typed cho cả projection công khai và danh sách quản lý.
///
/// Thời gian được lưu UTC (`starts_at`/`ends_at` là timestamptz) và chỉ đổi sang
/// giờ Việt Nam khi hiển thị (xem `core/time_utils.dart`).
class Session {
  final String id;
  final String? clubId;
  final String? clubName;
  final String title;
  final String? description;
  final DateTime? startsAt;
  final DateTime? endsAt;
  final int capacity;
  final int courtCount;
  final String? levelRequirement;
  final String visibility;
  final String lifecycle;
  final String approvalMode;
  final String feeMode;
  final int? memberFeeVnd;
  final int? guestFeeVnd;
  final DateTime? registrationDeadline;
  final DateTime? cancellationDeadline;
  final String? venueId;
  final String? venueName;
  final String? venueAddress;
  final String? venueArea;
  final String? hostDisplayName;
  final int? version;
  final bool isHost;
  final bool canManage;
  final bool canViewFinance;
  final int confirmedCount;
  final SessionRegistration? myRegistration;

  const Session({
    required this.id,
    this.clubId,
    this.clubName,
    required this.title,
    this.description,
    this.startsAt,
    this.endsAt,
    this.capacity = 0,
    this.courtCount = 0,
    this.levelRequirement,
    this.visibility = 'unlisted',
    this.lifecycle = 'draft',
    this.approvalMode = 'host_approval',
    this.feeMode = 'split_actual',
    this.memberFeeVnd,
    this.guestFeeVnd,
    this.registrationDeadline,
    this.cancellationDeadline,
    this.venueId,
    this.venueName,
    this.venueAddress,
    this.venueArea,
    this.hostDisplayName,
    this.version,
    this.isHost = false,
    this.canManage = false,
    this.canViewFinance = false,
    this.confirmedCount = 0,
    this.myRegistration,
  });

  bool get isDraft => lifecycle == 'draft';
  bool get isPublished => lifecycle == 'published';
  bool get isInProgress => lifecycle == 'in_progress';
  bool get isCompleted => lifecycle == 'completed';
  bool get isCancelled => lifecycle == 'cancelled';

  /// Buổi đã công bố/đang diễn ra nên có thể chia sẻ link.
  bool get isShareable => isPublished || isInProgress;

  bool get isActionable => !isCancelled && !isCompleted;

  int get seatsLeft => confirmedCount >= capacity ? 0 : capacity - confirmedCount;
  bool get isFull => capacity > 0 && confirmedCount >= capacity;

  /// Phí hiển thị đúng nhãn; không quy đổi `split_actual` thành giá cuối (PD-02).
  String get feeLabel {
    if (feeMode == 'fixed') {
      final member = memberFeeVnd ?? 0;
      final guest = guestFeeVnd ?? 0;
      if (member == guest) return 'Phí cố định';
      return 'Phí cố định';
    }
    return 'Chia theo chi phí thực tế';
  }

  String get lifecycleLabel {
    switch (lifecycle) {
      case 'draft':
        return 'Bản nháp';
      case 'published':
        return 'Đã công bố';
      case 'in_progress':
        return 'Đang diễn ra';
      case 'completed':
        return 'Đã kết thúc';
      case 'cancelled':
        return 'Đã huỷ';
      default:
        return lifecycle;
    }
  }

  String get visibilityLabel {
    switch (visibility) {
      case 'public':
        return 'Công khai';
      case 'unlisted':
        return 'Có link';
      case 'private':
        return 'Riêng tư';
      default:
        return visibility;
    }
  }

  static int? _asInt(dynamic value) =>
      value == null ? null : (value as num).toInt();

  static DateTime? _asDate(dynamic value) =>
      value == null ? null : DateTime.tryParse(value.toString());

  factory Session.fromJson(Map<String, dynamic> json) {
    return Session(
      id: json['id']?.toString() ?? '',
      clubId: json['club_id']?.toString(),
      clubName: json['club_name']?.toString(),
      title: json['title']?.toString() ?? '',
      description: json['description']?.toString(),
      startsAt: _asDate(json['starts_at']),
      endsAt: _asDate(json['ends_at']),
      capacity: _asInt(json['capacity']) ?? 0,
      courtCount: _asInt(json['court_count']) ?? 0,
      levelRequirement: json['level_requirement']?.toString(),
      visibility: json['visibility']?.toString() ?? 'unlisted',
      lifecycle: json['lifecycle']?.toString() ?? 'draft',
      approvalMode: json['approval_mode']?.toString() ?? 'host_approval',
      feeMode: json['fee_mode']?.toString() ?? 'split_actual',
      memberFeeVnd: _asInt(json['member_fee_vnd']),
      guestFeeVnd: _asInt(json['guest_fee_vnd']),
      registrationDeadline: _asDate(json['registration_deadline']),
      cancellationDeadline: _asDate(json['cancellation_deadline']),
      venueId: json['venue_id']?.toString(),
      venueName: json['venue_name']?.toString(),
      venueAddress: json['venue_address']?.toString(),
      venueArea: json['venue_area']?.toString(),
      hostDisplayName: json['host_display_name']?.toString(),
      version: _asInt(json['version']),
      isHost: json['is_host'] == true,
      canManage: json['can_manage'] == true,
      canViewFinance: json['can_view_finance'] == true,
      confirmedCount: _asInt(json['confirmed_count']) ?? 0,
      myRegistration: json['my_registration'] is Map
          ? SessionRegistration.fromJson(
              Map<String, dynamic>.from(json['my_registration'] as Map))
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'club_id': clubId,
        'club_name': clubName,
        'title': title,
        'description': description,
        'starts_at': startsAt?.toIso8601String(),
        'ends_at': endsAt?.toIso8601String(),
        'capacity': capacity,
        'court_count': courtCount,
        'level_requirement': levelRequirement,
        'visibility': visibility,
        'lifecycle': lifecycle,
        'approval_mode': approvalMode,
        'fee_mode': feeMode,
        'member_fee_vnd': memberFeeVnd,
        'guest_fee_vnd': guestFeeVnd,
        'registration_deadline': registrationDeadline?.toIso8601String(),
        'cancellation_deadline': cancellationDeadline?.toIso8601String(),
        'venue_id': venueId,
        'venue_name': venueName,
        'venue_address': venueAddress,
        'venue_area': venueArea,
        'host_display_name': hostDisplayName,
        'version': version,
        'is_host': isHost,
        'can_manage': canManage,
        'can_view_finance': canViewFinance,
        'confirmed_count': confirmedCount,
        'my_registration': myRegistration?.toJson(),
      };
}

/// Đăng ký của chính người dùng trong buổi (nếu có).
class SessionRegistration {
  final String playerId;
  final String registrationStatus;
  final String attendanceStatus;
  final String participantType;
  final int? agreedFeeVnd;

  const SessionRegistration({
    required this.playerId,
    this.registrationStatus = 'pending',
    this.attendanceStatus = 'not_checked_in',
    this.participantType = 'guest',
    this.agreedFeeVnd,
  });

  factory SessionRegistration.fromJson(Map<String, dynamic> json) {
    return SessionRegistration(
      playerId: json['player_id']?.toString() ?? '',
      registrationStatus: json['registration_status']?.toString() ?? 'pending',
      attendanceStatus: json['attendance_status']?.toString() ?? 'not_checked_in',
      participantType: json['participant_type']?.toString() ?? 'guest',
      agreedFeeVnd: json['agreed_fee_vnd'] == null
          ? null
          : (json['agreed_fee_vnd'] as num).toInt(),
    );
  }

  Map<String, dynamic> toJson() => {
        'player_id': playerId,
        'registration_status': registrationStatus,
        'attendance_status': attendanceStatus,
        'participant_type': participantType,
        'agreed_fee_vnd': agreedFeeVnd,
      };
}

/// Người đăng ký trong buổi — chỉ host/quản lý buổi đọc được (F7).
class SessionPlayer {
  final String id;
  final String? userId;
  final String displayName;
  final String participantType;
  final String registrationStatus;
  final String attendanceStatus;
  final bool feeExempt;
  final int? agreedFeeVnd;
  final DateTime? requestedAt;
  final DateTime? confirmedAt;
  final String? phoneNumber;

  const SessionPlayer({
    required this.id,
    this.userId,
    required this.displayName,
    this.participantType = 'guest',
    this.registrationStatus = 'pending',
    this.attendanceStatus = 'not_checked_in',
    this.feeExempt = false,
    this.agreedFeeVnd,
    this.requestedAt,
    this.confirmedAt,
    this.phoneNumber,
  });

  bool get isConfirmed => registrationStatus == 'confirmed';

  factory SessionPlayer.fromJson(Map<String, dynamic> json) {
    return SessionPlayer(
      id: json['id']?.toString() ?? '',
      userId: json['user_id']?.toString(),
      displayName: json['display_name']?.toString() ?? '',
      participantType: json['participant_type']?.toString() ?? 'guest',
      registrationStatus: json['registration_status']?.toString() ?? 'pending',
      attendanceStatus: json['attendance_status']?.toString() ?? 'not_checked_in',
      feeExempt: json['fee_exempt'] == true,
      agreedFeeVnd: json['agreed_fee_vnd'] == null
          ? null
          : (json['agreed_fee_vnd'] as num).toInt(),
      requestedAt: json['requested_at'] == null
          ? null
          : DateTime.tryParse(json['requested_at'].toString()),
      confirmedAt: json['confirmed_at'] == null
          ? null
          : DateTime.tryParse(json['confirmed_at'].toString()),
      phoneNumber: json['phone_number']?.toString(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'display_name': displayName,
        'participant_type': participantType,
        'registration_status': registrationStatus,
        'attendance_status': attendanceStatus,
        'fee_exempt': feeExempt,
        'agreed_fee_vnd': agreedFeeVnd,
        'requested_at': requestedAt?.toIso8601String(),
        'confirmed_at': confirmedAt?.toIso8601String(),
        'phone_number': phoneNumber,
      };
}

/// Bộ lọc khám phá buổi công khai (PD-02) — thủ công, không cần GPS.
class SessionFilter {
  final String? area;
  final DateTime? from;
  final DateTime? to;
  final String? feeMode;
  final bool onlyAvailable;

  const SessionFilter({
    this.area,
    this.from,
    this.to,
    this.feeMode,
    this.onlyAvailable = false,
  });

  bool get isEmpty =>
      area == null && from == null && to == null && feeMode == null && !onlyAvailable;

  SessionFilter copyWith({
    String? area,
    DateTime? from,
    DateTime? to,
    String? feeMode,
    bool? onlyAvailable,
    bool clearArea = false,
    bool clearFrom = false,
    bool clearTo = false,
    bool clearFeeMode = false,
  }) {
    return SessionFilter(
      area: clearArea ? null : (area ?? this.area),
      from: clearFrom ? null : (from ?? this.from),
      to: clearTo ? null : (to ?? this.to),
      feeMode: clearFeeMode ? null : (feeMode ?? this.feeMode),
      onlyAvailable: onlyAvailable ?? this.onlyAvailable,
    );
  }
}
