import 'package:flutter/material.dart';
import '../data/supabase_service.dart';

class SessionProvider extends ChangeNotifier {
  final SupabaseService _service = SupabaseService();

  bool isLoading = false;
  List<Map<String, dynamic>> sessions = [];

  // Dữ liệu cho màn hình chi tiết
  bool isDetailLoading = false;
  Map<String, dynamic>? currentSession;
  List<Map<String, dynamic>> currentPlayers = [];

  Future<void> fetchSessions() async {
    isLoading = true;
    notifyListeners();
    try {
      sessions = await _service.getSessions();
    } catch (e) {
      debugPrint('Error fetching sessions: $e');
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchSessionDetails(String sessionId) async {
    isDetailLoading = true;
    notifyListeners();
    try {
      currentSession = await _service.getSessionById(sessionId);
      currentPlayers = await _service.getSessionPlayers(sessionId);
    } catch (e) {
      debugPrint('Error fetching session detail: $e');
    } finally {
      isDetailLoading = false;
      notifyListeners();
    }
  }

  Future<void> createSession(String venue, String time, int slots, int cost, String phone) async {
    await _service.createSession(
      venueName: venue,
      playDate: DateTime.now().toIso8601String().substring(0, 10),
      startTime: time.split('-')[0].trim(),
      endTime: time.split('-').length > 1 ? time.split('-')[1].trim() : '',
      maxSlots: slots,
      estimatedCost: cost,
      contactPhone: phone,
      levelRequirement: 'Giao lưu vui vẻ',
    );
    await fetchSessions();
  }

  Future<void> joinSession(String sessionId, String name, String phone, int currentJoined, int maxSlots) async {
    await _service.joinSession(
      sessionId: sessionId,
      playerName: name,
      phone: phone,
      currentJoined: currentJoined,
      maxSlots: maxSlots,
    );
    await fetchSessions();
  }

  Future<void> togglePlayerStatus(String playerId, String field, bool value) async {
    await _service.togglePlayerStatus(playerId, field, value);
    if (currentSession != null) {
      await fetchSessionDetails(currentSession!['id']);
    }
  }
}
