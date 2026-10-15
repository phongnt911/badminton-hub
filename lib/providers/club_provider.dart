import 'package:flutter/material.dart';
import '../data/club_repository.dart';
import '../models/club.dart';

class ClubProvider extends ChangeNotifier {
  final ClubRepository _repository;

  ClubProvider({ClubRepository? repository})
      : _repository = repository ?? ClubRepository();

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
    _isLoadingClubs = true;
    _clubsErrorMessage = null;
    notifyListeners();

    try {
      _clubs = await _repository.listMyClubs();
    } catch (e) {
      _clubsErrorMessage = 'Không thể tải danh sách CLB: $e';
    } finally {
      _isLoadingClubs = false;
      notifyListeners();
    }
  }

  /// Tải chi tiết CLB, thành viên và thông tin ngân hàng
  Future<void> fetchClubDetails(String clubId) async {
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
      if (_currentClubId == clubId) {
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
      if (_currentClubId == clubId) {
        _detailErrorMessage = 'Không thể tải chi tiết CLB: $e';
        _isLoadingDetail = false;
        notifyListeners();
      }
    }
  }

  /// Tải danh sách thành viên của CLB
  Future<void> fetchMembers(String clubId) async {
    if (_currentClubId != clubId) return;

    _isLoadingMembers = true;
    _membersErrorMessage = null;
    notifyListeners();

    try {
      final members = await _repository.listClubMembers(clubId);
      if (_currentClubId == clubId) {
        _currentMembers = members;
      }
    } catch (e) {
      if (_currentClubId == clubId) {
        _membersErrorMessage = 'Không thể tải danh sách thành viên: $e';
      }
    } finally {
      if (_currentClubId == clubId) {
        _isLoadingMembers = false;
        notifyListeners();
      }
    }
  }

  /// Tải tài khoản ngân hàng của CLB
  Future<void> fetchClubBankAccount(String clubId) async {
    if (_currentClubId != clubId) return;

    _isLoadingBank = true;
    _bankErrorMessage = null;
    notifyListeners();

    try {
      final bank = await _repository.getClubBankAccount(clubId);
      if (_currentClubId == clubId) {
        _currentBankAccount = bank;
      }
    } catch (e) {
      if (_currentClubId == clubId) {
        _bankErrorMessage = 'Không thể tải thông tin ngân hàng: $e';
      }
    } finally {
      if (_currentClubId == clubId) {
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
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      final newClub = await _repository.createClub(
        name: name,
        description: description,
        visibility: visibility,
        requestId: requestId,
      );
      await fetchClubs();
      return newClub;
    } catch (e) {
      _submitErrorMessage = 'Tạo CLB thất bại: $e';
      return null;
    } finally {
      _isSubmitting = false;
      notifyListeners();
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
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      final updated = await _repository.updateClub(
        clubId: clubId,
        name: name,
        description: description,
        visibility: visibility,
        requestId: requestId,
      );
      if (_currentClubId == clubId) {
        _currentClub = updated;
      }
      await fetchClubs();
      return true;
    } catch (e) {
      _submitErrorMessage = 'Cập nhật CLB thất bại: $e';
      return false;
    } finally {
      _isSubmitting = false;
      notifyListeners();
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
        requestId: requestId,
      );
      await fetchMembers(clubId);
      return true;
    } catch (e) {
      _submitErrorMessage = 'Thêm thành viên thất bại: $e';
      return false;
    } finally {
      _isSubmitting = false;
      notifyListeners();
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
        requestId: requestId,
      );
      await fetchMembers(clubId);
      return true;
    } catch (e) {
      _submitErrorMessage = 'Cập nhật liên hệ thất bại: $e';
      return false;
    } finally {
      _isSubmitting = false;
      notifyListeners();
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
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      await _repository.setClubMemberRole(
        clubId: clubId,
        memberId: memberId,
        role: role,
        requestId: requestId,
      );
      await fetchMembers(clubId);
      return true;
    } catch (e) {
      _submitErrorMessage = 'Phân quyền thất bại: $e';
      return false;
    } finally {
      _isSubmitting = false;
      notifyListeners();
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
    _isSubmitting = true;
    _submitErrorMessage = null;
    notifyListeners();

    try {
      final bank = await _repository.setClubBankAccount(
        clubId: clubId,
        bankCode: bankCode,
        accountNumber: accountNumber,
        accountName: accountName,
        requestId: requestId,
      );
      if (_currentClubId == clubId) {
        _currentBankAccount = bank;
      }
      return true;
    } catch (e) {
      _submitErrorMessage = 'Cấu hình ngân hàng thất bại: $e';
      return false;
    } finally {
      _isSubmitting = false;
      notifyListeners();
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
    _clubs = [];
    _isLoadingClubs = false;
    _clubsErrorMessage = null;
    _isSubmitting = false;
    _submitErrorMessage = null;
    clearCurrentClub();
  }
}
