import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/club.dart';

class ClubRepository {
  final SupabaseClient _client;

  ClubRepository({SupabaseClient? client})
    : _client = client ?? Supabase.instance.client;

  /// Lấy danh sách các CLB của người dùng hiện tại (làm chủ hoặc tham gia)
  Future<List<Club>> listMyClubs() async {
    final response = await _client.rpc('list_my_clubs');
    if (response is List) {
      return response
          .map((item) => Club.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    }
    return [];
  }

  /// Lấy thông tin chi tiết CLB theo quyền (số dư quỹ chỉ hiển thị cho owner/treasurer)
  Future<Club> getClubDetail(String clubId) async {
    final response = await _client.rpc(
      'get_club_detail',
      params: {'p_club_id': clubId},
    );
    return Club.fromJson(Map<String, dynamic>.from(response as Map));
  }

  /// Tạo CLB mới và tự động gán người tạo làm chủ nhiệm (atomic create_club)
  Future<Club> createClub({
    required String name,
    String? description,
    String visibility = 'private',
    required String requestId,
  }) async {
    final params = <String, dynamic>{
      'p_name': name,
      'p_description': description,
      'p_visibility': visibility,
    };
    params['p_request_id'] = requestId;

    final response = await _client.rpc('create_club', params: params);
    return Club.fromJson(Map<String, dynamic>.from(response as Map));
  }

  /// Cập nhật thông tin CLB (chỉ dành cho Chủ nhiệm)
  Future<Club> updateClub({
    required String clubId,
    String? name,
    String? description,
    String? visibility,
    required String requestId,
  }) async {
    final params = <String, dynamic>{
      'p_club_id': clubId,
      'p_name': name,
      'p_description': description,
      'p_visibility': visibility,
    };
    params['p_request_id'] = requestId;

    final response = await _client.rpc('update_club', params: params);
    return Club.fromJson(Map<String, dynamic>.from(response as Map));
  }

  /// Lấy danh sách thành viên CLB theo quyền (SĐT chỉ hiện cho Owner/Host hoặc chính chủ)
  Future<List<ClubMember>> listClubMembers(
    String clubId, {
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _client.rpc(
      'list_club_members',
      params: {'p_club_id': clubId, 'p_limit': limit, 'p_offset': offset},
    );
    if (response is List) {
      return response
          .map(
            (item) =>
                ClubMember.fromJson(Map<String, dynamic>.from(item as Map)),
          )
          .toList();
    }
    return [];
  }

  /// Thêm thành viên mới vào CLB (hỗ trợ thành viên offline chưa có tài khoản)
  Future<ClubMember> addClubMember({
    required String clubId,
    required String displayName,
    String? phoneNumber,
    String? contactNote,
    String? userId,
    required String requestId,
  }) async {
    final params = <String, dynamic>{
      'p_club_id': clubId,
      'p_display_name': displayName,
      'p_phone_number': phoneNumber,
      'p_contact_note': contactNote,
      'p_user_id': userId,
    };
    params['p_request_id'] = requestId;

    final response = await _client.rpc('add_club_member', params: params);
    return ClubMember.fromJson(Map<String, dynamic>.from(response as Map));
  }

  /// Cập nhật thông tin liên hệ của thành viên (Chủ nhiệm hoặc Host)
  Future<ClubMember> updateClubMemberContact({
    required String clubId,
    required String memberId,
    String? displayName,
    String? phoneNumber,
    String? contactNote,
    required String requestId,
  }) async {
    final params = <String, dynamic>{
      'p_club_id': clubId,
      'p_member_id': memberId,
      'p_display_name': displayName,
      'p_phone_number': phoneNumber,
      'p_contact_note': contactNote,
    };
    params['p_request_id'] = requestId;

    final response = await _client.rpc(
      'update_club_member_contact',
      params: params,
    );
    return ClubMember.fromJson(Map<String, dynamic>.from(response as Map));
  }

  /// Phân quyền thành viên CLB (chỉ dành cho Chủ nhiệm, không cấp quyền cho người chưa có tài khoản)
  Future<ClubMember> setClubMemberRole({
    required String clubId,
    required String memberId,
    required String role,
    required String requestId,
  }) async {
    final params = <String, dynamic>{
      'p_club_id': clubId,
      'p_member_id': memberId,
      'p_role': role,
    };
    params['p_request_id'] = requestId;

    final response = await _client.rpc('set_club_member_role', params: params);
    return ClubMember.fromJson(Map<String, dynamic>.from(response as Map));
  }

  /// Lấy tài khoản ngân hàng nhận tiền của CLB (chỉ Owner và Treasurer)
  Future<BankAccount?> getClubBankAccount(String clubId) async {
    final response = await _client.rpc(
      'get_club_bank_account',
      params: {'p_club_id': clubId},
    );
    if (response == null) return null;
    return BankAccount.fromJson(Map<String, dynamic>.from(response as Map));
  }

  /// Cấu hình tài khoản ngân hàng CLB (chỉ Chủ nhiệm)
  Future<BankAccount> setClubBankAccount({
    required String clubId,
    required String bankCode,
    required String accountNumber,
    required String accountName,
    required String requestId,
  }) async {
    final params = <String, dynamic>{
      'p_club_id': clubId,
      'p_bank_code': bankCode,
      'p_account_number': accountNumber,
      'p_account_name': accountName,
    };
    params['p_request_id'] = requestId;

    final response = await _client.rpc('set_club_bank_account', params: params);
    return BankAccount.fromJson(Map<String, dynamic>.from(response as Map));
  }

  /// Lấy tài khoản ngân hàng cá nhân của host
  Future<BankAccount?> getHostBankAccount() async {
    final response = await _client.rpc('get_host_bank_account');
    if (response == null) return null;
    return BankAccount.fromJson(Map<String, dynamic>.from(response as Map));
  }

  /// Cấu hình tài khoản ngân hàng cá nhân của host
  Future<BankAccount> setHostBankAccount({
    required String bankCode,
    required String accountNumber,
    required String accountName,
    required String requestId,
  }) async {
    final params = <String, dynamic>{
      'p_bank_code': bankCode,
      'p_account_number': accountNumber,
      'p_account_name': accountName,
    };
    params['p_request_id'] = requestId;

    final response = await _client.rpc('set_host_bank_account', params: params);
    return BankAccount.fromJson(Map<String, dynamic>.from(response as Map));
  }
}
