import 'package:flutter/material.dart';
import '../data/supabase_service.dart';

class ClubProvider extends ChangeNotifier {
  final SupabaseService _service = SupabaseService();

  bool isLoading = false;
  List<Map<String, dynamic>> clubs = [];

  // Lịch sử giao dịch và chi tiết CLB đang chọn
  Map<String, dynamic>? currentClub;
  List<Map<String, dynamic>> currentTransactions = [];
  bool isDetailLoading = false;

  Future<void> fetchClubs() async {
    isLoading = true;
    notifyListeners();
    try {
      clubs = await _service.getClubs();
    } catch (e) {
      debugPrint('Error fetching clubs: $e');
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<void> createClub(String name, String phone, String bankAccount) async {
    await _service.createClub(name: name, ownerPhone: phone, bankAccount: bankAccount);
    await fetchClubs();
  }

  Future<void> fetchClubDetails(String clubId) async {
    isDetailLoading = true;
    notifyListeners();
    try {
      currentClub = await _service.getClubById(clubId);
      currentTransactions = await _service.getClubTransactions(clubId);
    } catch (e) {
      debugPrint('Error fetching club details: $e');
    } finally {
      isDetailLoading = false;
      notifyListeners();
    }
  }

  Future<void> addTransaction(String type, String title, int amount) async {
    if (currentClub == null) return;
    final clubId = currentClub!['id'];
    final currentBalance = currentClub!['balance'] ?? 0;
    
    await _service.addClubTransaction(
      clubId: clubId, 
      type: type, 
      title: title, 
      amount: amount, 
      currentBalance: currentBalance
    );
    
    // Cập nhật lại chi tiết
    await fetchClubDetails(clubId);
    // Cũng cập nhật lại danh sách CLB để sync số dư
    await fetchClubs();
  }
}
