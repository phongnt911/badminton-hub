class Club {
  final String id;
  final String ownerUserId;
  final String name;
  final String? description;
  final String visibility;
  final String status;
  final String? myRole;
  final int? balanceVnd;
  final int? memberCount;
  final DateTime? createdAt;

  const Club({
    required this.id,
    required this.ownerUserId,
    required this.name,
    this.description,
    this.visibility = 'private',
    this.status = 'active',
    this.myRole,
    this.balanceVnd,
    this.memberCount,
    this.createdAt,
  });

  bool get isOwner => myRole == 'owner';
  bool get isHost => myRole == 'host';
  bool get isTreasurer => myRole == 'treasurer';
  bool get canManageMembers => isOwner || isHost;
  bool get canViewBalance => isOwner || isTreasurer;
  bool get canConfigureBank => isOwner;

  factory Club.fromJson(Map<String, dynamic> json) {
    return Club(
      id: json['id']?.toString() ?? '',
      ownerUserId: json['owner_user_id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      description: json['description']?.toString(),
      visibility: json['visibility']?.toString() ?? 'private',
      status: json['status']?.toString() ?? 'active',
      myRole: json['my_role']?.toString(),
      balanceVnd: json['balance_vnd'] != null ? (json['balance_vnd'] as num).toInt() : null,
      memberCount: json['member_count'] != null ? (json['member_count'] as num).toInt() : null,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'owner_user_id': ownerUserId,
      'name': name,
      'description': description,
      'visibility': visibility,
      'status': status,
      'my_role': myRole,
      'balance_vnd': balanceVnd,
      'member_count': memberCount,
      'created_at': createdAt?.toIso8601String(),
    };
  }
}

class ClubMember {
  final String id;
  final String clubId;
  final String? userId;
  final String displayName;
  final String role;
  final String status;
  final DateTime? joinedAt;
  final String? phoneNumber;
  final String? contactNote;

  const ClubMember({
    required this.id,
    required this.clubId,
    this.userId,
    required this.displayName,
    this.role = 'member',
    this.status = 'active',
    this.joinedAt,
    this.phoneNumber,
    this.contactNote,
  });

  bool get isOffline => userId == null;
  bool get isOwner => role == 'owner';
  bool get isHost => role == 'host';
  bool get isTreasurer => role == 'treasurer';
  bool get isMember => role == 'member';

  factory ClubMember.fromJson(Map<String, dynamic> json) {
    return ClubMember(
      id: json['id']?.toString() ?? '',
      clubId: json['club_id']?.toString() ?? '',
      userId: json['user_id']?.toString(),
      displayName: json['display_name']?.toString() ?? '',
      role: json['role']?.toString() ?? 'member',
      status: json['status']?.toString() ?? 'active',
      joinedAt: json['joined_at'] != null ? DateTime.tryParse(json['joined_at'].toString()) : null,
      phoneNumber: json['phone_number']?.toString(),
      contactNote: json['contact_note']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'club_id': clubId,
      'user_id': userId,
      'display_name': displayName,
      'role': role,
      'status': status,
      'joined_at': joinedAt?.toIso8601String(),
      'phone_number': phoneNumber,
      'contact_note': contactNote,
    };
  }
}

class BankAccount {
  final String id;
  final String? clubId;
  final String? userId;
  final String bankCode;
  final String accountNumber;
  final String accountName;
  final String status;

  const BankAccount({
    required this.id,
    this.clubId,
    this.userId,
    required this.bankCode,
    required this.accountNumber,
    required this.accountName,
    this.status = 'active',
  });

  factory BankAccount.fromJson(Map<String, dynamic> json) {
    return BankAccount(
      id: json['id']?.toString() ?? '',
      clubId: json['club_id']?.toString(),
      userId: json['user_id']?.toString(),
      bankCode: json['bank_code']?.toString() ?? '',
      accountNumber: json['account_number']?.toString() ?? '',
      accountName: json['account_name']?.toString() ?? '',
      status: json['status']?.toString() ?? 'active',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'club_id': clubId,
      'user_id': userId,
      'bank_code': bankCode,
      'account_number': accountNumber,
      'account_name': accountName,
      'status': status,
    };
  }
}
