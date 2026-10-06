import 'package:supabase_flutter/supabase_flutter.dart';

class SupabaseService {
  final SupabaseClient _client = Supabase.instance.client;

  // 1. Lấy danh sách Sân Cầu Lông tại Nha Trang
  Future<List<Map<String, dynamic>>> getVenues() async {
    final response = await _client
        .from('venues')
        .select()
        .order('created_at', ascending: true);
    return List<Map<String, dynamic>>.from(response);
  }

  // 2. Lấy danh sách Kèo tìm vãng lai hôm nay
  Future<List<Map<String, dynamic>>> getSessions() async {
    final response = await _client
        .from('sessions')
        .select()
        .order('play_date', ascending: true);
    return List<Map<String, dynamic>>.from(response);
  }

  // 3. Đăng kèo mới tìm vãng lai
  Future<void> createSession({
    required String venueName,
    required String playDate,
    required String startTime,
    required String endTime,
    required int maxSlots,
    required int estimatedCost,
    required String contactPhone,
    required String levelRequirement,
  }) async {
    await _client.from('sessions').insert({
      'venue_name': venueName,
      'play_date': playDate,
      'start_time': startTime,
      'end_time': endTime,
      'max_slots': maxSlots,
      'joined_count': 1,
      'estimated_cost': estimatedCost,
      'contact_phone': contactPhone,
      'level_requirement': levelRequirement,
      'status': 'open',
    });
  }

  // 4. Người chơi đăng ký tham gia slot
  Future<void> joinSession({
    required String sessionId,
    required String playerName,
    required String phone,
    required int currentJoined,
    required int maxSlots,
  }) async {
    // Thêm người chơi vào bảng session_players
    await _client.from('session_players').insert({
      'session_id': sessionId,
      'player_name': playerName,
      'phone_number': phone,
    });

    // Cập nhật số người đã đăng ký trong buổi chơi
    final newCount = currentJoined + 1;
    final newStatus = newCount >= maxSlots ? 'full' : 'open';
    await _client
        .from('sessions')
        .update({'joined_count': newCount, 'status': newStatus})
        .eq('id', sessionId);
  }
}
