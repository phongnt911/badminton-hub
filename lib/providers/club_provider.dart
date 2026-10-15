import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';

import '../data/club_repository.dart';
import '../models/club.dart';
import 'auth_provider.dart';

class ClubProvider extends ChangeNotifier {
  final ClubRepository _repository;

  final AuthProvider? auth;
  String? _authUserId;
  int _generation = 0;
  int _listSerial = 0;
  bool _disposed = false;
  final _pendingRequests = <String, ({String payload, String id})>{};

  ClubProvider({ClubRepository? repository, this.auth})
    : _repository = repository ?? ClubRepository() {
    _authUserId = auth?.currentUser?.id;
    auth?.addListener(_onAuthChanged);
  }

  void _onAuthChanged() {
    final userId = auth?.currentUser?.id;
    if (userId != _authUserId) {
      _authUserId = userId;
      clearAll();
    }
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

  // State danh sách CLB
  List<Club> _clubs = [];
  bool _isLoadingClubs = false;
  String? _clubsErrorMessage;

  List<Club> get clubs => _clubs;
  bool get isLoadingClubs => _isLoadingClubs;
  String? get clubsErrorMessage => _clubsErrorMessage;
  bool get hasClubs => _clubs.isNotEmpty;

  // State chi tiết CLB đang chọn
  String? _currentClubId;
  Club? _currentClub;
  bool _isLoadingDetail = false;
  String? _detailErrorMessage;

  String? get currentClubId => _currentClubId;
  Club? get currentClub => _currentClub;
  bool get isLoadingDetail => _isLoadingDetail;
  String? get detailErrorMessage => _detailErrorMessage;

  // State thành viên của CLB đang chọn
  List<ClubMember> _currentMembers = [];
  bool _isLoadingMembers = false;
  String? _membersErrorMessage;

  List<ClubMember> get currentMembers => _currentMembers;
  bool get isLoadingMembers => _isLoadingMembers;
  String? get membersErrorMessage => _membersErrorMessage;

  // State tài khoản ngân hàng của CLB
  BankAccount? _currentBankAccount;
  bool _isLoadingBank = false;
  String? _bankErrorMessage;

  BankAccount? get currentBankAccount => _currentBankAccount;
  bool get isLoadingBank => _isLoadingBank;
  String? get bankErrorMessage => _bankErrorMessage;

  // Trạng thái thao tác mutating (chống nhấn lặp)
  bool _isSubmitting = false;
  String? _submitErrorMessage;

  bool get isSubmitting => _isSubmitting;
  String? get submitErrorMessage => _submitErrorMessage;

  /// Tải danh sách CLB của người dùng
  Future<void> fetchClubs() async {
    final generation = _generation;
    final serial = ++_listSerial;
    _isLoadingClubs = true;
    _clubsErrorMessage = null;
    notifyListeners();

    try {
      final clubs = await _repository.listMyClubs();
      if (_generation != generation || serial != _listSerial) return;
      _clubs = clubs;
    } catch (e) {
      if (_generation == generation && serial == _listSerial) {
        _clubsErrorMessage = 'Không thể tải danh sách CLB: $e';
      }
    } finally {
      if (_generation == generation && serial == _listSerial) {
        _isLoadingClubs = false;
        notifyListeners();
      }
    }
  }

  /// Tải chi tiết CLB, thành viên và thông tin ngân hàng
  Future<void> fetchClubDetails(String clubId) async {
    final generation = _generation;
    // Nếu chuyển sang CLB khác, dọn dẹp state cũ ngay lập tức để tránh data leakage
    if (_currentClubId != clubId) {
      _currentClubId = clubId;
      _currentClub = null;
      _currentMembers = [];
      _currentBankAccount = null;
    }

    _isLoadingDetail = true;
    _detailErrorMessage = null;
    notifyListeners();

    try {
      final club = await _repository.getClubDetail(clubId);
      // Đảm bảo kết quả này vẫn khớp với clubId hiện tại (tránh race condition khi chuyển nhanh giữa các CLB)
      if (_generation == generation && _currentClubId == clubId) {
        _currentClub = club;
        _isLoadingDetail = false;
        notifyListeners();

        // Tải danh sách thành viên song song
        await fetchMembers(clubId);

        // Nếu user có quyền xem ngân hàng (owner hoặc treasurer), tải thêm bank
        if (club.canViewBalance || club.canConfigureBank) {
          await fetchClubBankAccount(clubId);
        }
      }
    } catch (e) {
      if (_generation == generation && _currentClubId == clubId) {
        _detailErrorMessage = 'Không thể tải chi tiết CLB: $e';
        _isLoadingDetail = false;
        notifyListeners();
      }
    }
  }

  /// Tải danh sách thành viên của CLB
  Future<void> fetchMembers(String clubId) async {
    final generation = _generation;
    if (_currentClubId != clubId) return;

    _isLoadingMembers = true;
    _membersErrorMessage = null;
    notifyListeners();

    try {
      final members = await _repository.listClubMembers(clubId);
      if (_generation == generation && _currentClubId == clubId) {
        _currentMembers = members;
      }
    } catch (e) {
      if (_generation == generation && _currentClubId == clubId) {
        _membersErrorMessage = 'Không thể tải danh sách thành viên: $e';
      }
    } finally {
      if (_generation == generation && _currentClubId == clubId) {
        _isLoadingMembers = false;
        notifyListeners();
      }
    }
  }

  /// Tải tài khoản ngân hàng của CLB
  Future<void> fetchClubBankAccount(String clubId) async {
    final generation = _generation;
    if (_currentClubId != clubId) return;

    _isLoadingBank = true;
    _bankErrorMessage = null;
    notifyListeners();

    try {
      final bank = await _repository.getClubBankAccount(clubId);
      if (_generation == generation && _currentClubId == clubId) {
        _currentBankAccount = bank;
      }
    } catch (e) {
      if (_generation == generation && _currentClubId == clubId) {
        _bankErrorMessage = 'Không thể tải thông tin ngân hàng: $e';
      }
    } finally {
      if (_generation == generation && _currentClubId == clubId) {
        _isLoadingBank = false;
        notifyListeners();
      }
    }
  }

  /// Tạo CLB mới (chỉ cần tên, mô tả, quyền riêng tư)
  Future<Club?> createClub({
    required String name,
    String? description,
    String visibility = 'private',
    String? requestId,
  }) async {
    if (_isSubmitting) return null;
    final generation = _generation;
    final key = _requestKey('createClub', [
      name,
      description,
      visibility,
    ], requestId);
    var succeeded = false;
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      final newClub = await _repository.createClub(
        name: name,
        description: description,
        visibility: visibility,
        requestId: key,
      );
      if (_generation != generation) return null;
      succeeded = true;
      await fetchClubs();
      return _generation == generation ? newClub : null;
    } catch (e) {
      if (_generation == generation) {
        _submitErrorMessage = 'Tạo CLB thất bại: $e';
      }
      return null;
    } finally {
      if (succeeded && _pendingRequests['createClub']?.id == key) {
        _pendingRequests.remove('createClub');
      }
      if (_generation == generation) {
        _isSubmitting = false;
        notifyListeners();
      }
    }
  }

  /// Cập nhật thông tin CLB
  Future<bool> updateClub({
    required String clubId,
    String? name,
    String? description,
    String? visibility,
    String? requestId,
  }) async {
    if (_isSubmitting) return false;
    final generation = _generation;
    final key = _requestKey('updateClub', [
      clubId,
      name,
      description,
      visibility,
    ], requestId);
    var succeeded = false;
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      final updated = await _repository.updateClub(
        clubId: clubId,
        name: name,
        description: description,
        visibility: visibility,
        requestId: key,
      );
      if (_generation != generation) return false;
      succeeded = true;
      if (_generation == generation && _currentClubId == clubId) {
        _currentClub = updated;
      }
      await fetchClubs();
      return _generation == generation;
    } catch (e) {
      if (_generation == generation) {
        _submitErrorMessage = 'Cập nhật CLB thất bại: $e';
      }
      return false;
    } finally {
      if (succeeded && _pendingRequests['updateClub']?.id == key) {
        _pendingRequests.remove('updateClub');
      }
      if (_generation == generation) {
        _isSubmitting = false;
        notifyListeners();
      }
    }
  }

  /// Thêm thành viên mới (hỗ trợ thành viên offline)
  Future<bool> addMember({
    required String clubId,
    required String displayName,
    String? phoneNumber,
    String? contactNote,
    String? userId,
    String? requestId,
  }) async {
    if (_isSubmitting) return false;
    final generation = _generation;
    final key = _requestKey('addMember', [
      clubId,
      displayName,
      phoneNumber,
      contactNote,
      userId,
    ], requestId);
    var succeeded = false;
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      await _repository.addClubMember(
        clubId: clubId,
        displayName: displayName,
        phoneNumber: phoneNumber,
        contactNote: contactNote,
        userId: userId,
        requestId: key,
      );
      if (_generation != generation) return false;
      succeeded = true;
      await fetchMembers(clubId);
      return _generation == generation;
    } catch (e) {
      if (_generation == generation) {
        _submitErrorMessage = 'Thêm thành viên thất bại: $e';
      }
      return false;
    } finally {
      if (succeeded && _pendingRequests['addMember']?.id == key) {
        _pendingRequests.remove('addMember');
      }
      if (_generation == generation) {
        _isSubmitting = false;
        notifyListeners();
      }
    }
  }

  /// Cập nhật thông tin liên hệ thành viên
  Future<bool> updateMemberContact({
    required String clubId,
    required String memberId,
    String? displayName,
    String? phoneNumber,
    String? contactNote,
    String? requestId,
  }) async {
    if (_isSubmitting) return false;
    final generation = _generation;
    final key = _requestKey('updateMemberContact', [
      clubId,
      memberId,
      displayName,
      phoneNumber,
      contactNote,
    ], requestId);
    var succeeded = false;
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      await _repository.updateClubMemberContact(
        clubId: clubId,
        memberId: memberId,
        displayName: displayName,
        phoneNumber: phoneNumber,
        contactNote: contactNote,
        requestId: key,
      );
      if (_generation != generation) return false;
      succeeded = true;
      await fetchMembers(clubId);
      return _generation == generation;
    } catch (e) {
      if (_generation == generation) {
        _submitErrorMessage = 'Cập nhật liên hệ thất bại: $e';
      }
      return false;
    } finally {
      if (succeeded && _pendingRequests['updateMemberContact']?.id == key) {
        _pendingRequests.remove('updateMemberContact');
      }
      if (_generation == generation) {
        _isSubmitting = false;
        notifyListeners();
      }
    }
  }

  /// Phân quyền thành viên (host/treasurer/member)
  Future<bool> setMemberRole({
    required String clubId,
    required String memberId,
    required String role,
    String? requestId,
  }) async {
    if (_isSubmitting) return false;
    final generation = _generation;
    final key = _requestKey('setMemberRole', [
      clubId,
      memberId,
      role,
    ], requestId);
    var succeeded = false;
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      await _repository.setClubMemberRole(
        clubId: clubId,
        memberId: memberId,
        role: role,
        requestId: key,
      );
      if (_generation != generation) return false;
      succeeded = true;
      await fetchMembers(clubId);
      return _generation == generation;
    } catch (e) {
      if (_generation == generation) {
        _submitErrorMessage = 'Phân quyền thất bại: $e';
      }
      return false;
    } finally {
      if (succeeded && _pendingRequests['setMemberRole']?.id == key) {
        _pendingRequests.remove('setMemberRole');
      }
      if (_generation == generation) {
        _isSubmitting = false;
        notifyListeners();
      }
    }
  }

  /// Cấu hình tài khoản ngân hàng nhận tiền của CLB
  Future<bool> setClubBankAccount({
    required String clubId,
    required String bankCode,
    required String accountNumber,
    required String accountName,
    String? requestId,
  }) async {
    if (_isSubmitting) return false;
    final generation = _generation;
    final key = _requestKey('setClubBankAccount', [
      clubId,
      bankCode,
      accountNumber,
      accountName,
    ], requestId);
    var succeeded = false;
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      final bank = await _repository.setClubBankAccount(
        clubId: clubId,
        bankCode: bankCode,
        accountNumber: accountNumber,
        accountName: accountName,
        requestId: key,
      );
      if (_generation != generation) return false;
      succeeded = true;
      if (_generation == generation && _currentClubId == clubId) {
        _currentBankAccount = bank;
      }
      return _generation == generation;
    } catch (e) {
      if (_generation == generation) {
        _submitErrorMessage = 'Cấu hình ngân hàng thất bại: $e';
      }
      return false;
    } finally {
      if (succeeded && _pendingRequests['setClubBankAccount']?.id == key) {
        _pendingRequests.remove('setClubBankAccount');
      }
      if (_generation == generation) {
        _isSubmitting = false;
        notifyListeners();
      }
    }
  }

  /// Dọn dẹp state CLB đang chọn (dùng khi rời màn hình chi tiết hoặc chuyển CLB)
  void clearCurrentClub() {
    _currentClubId = null;
    _currentClub = null;
    _currentMembers = [];
    _currentBankAccount = null;
    _isLoadingDetail = false;
    _isLoadingMembers = false;
    _isLoadingBank = false;
    _detailErrorMessage = null;
    _membersErrorMessage = null;
    _bankErrorMessage = null;
    notifyListeners();
  }

  /// Xóa toàn bộ dữ liệu (khi người dùng đăng xuất)
  void clearAll() {
    _generation++;
    _listSerial++;
    _pendingRequests.clear();
    _clubs = [];
    _isLoadingClubs = false;
    _clubsErrorMessage = null;
    _isSubmitting = false;
    _submitErrorMessage = null;
    clearCurrentClub();
  }
}
