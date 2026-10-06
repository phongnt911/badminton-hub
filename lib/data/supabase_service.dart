import 'package:supabase_flutter/supabase_flutter.dart';

class SupabaseService {
  final SupabaseClient _client = Supabase.instance.client;

  // ================= VENUES =================
  Future<List<Map<String, dynamic>>> getVenues() async {
    final response = await _client.from('venues').select().order('created_at', ascending: true);
    return List<Map<String, dynamic>>.from(response);
  }

  // ================= SESSIONS =================
  Future<List<Map<String, dynamic>>> getSessions() async {
    final response = await _client.from('sessions').select().order('play_date', ascending: true);
    return List<Map<String, dynamic>>.from(response);
  }
  
  Future<Map<String, dynamic>> getSessionById(String sessionId) async {
    return await _client.from('sessions').select().eq('id', sessionId).single();
  }

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

  // ================= SESSION PLAYERS =================
  Future<List<Map<String, dynamic>>> getSessionPlayers(String sessionId) async {
    final response = await _client
        .from('session_players')
        .select()
        .eq('session_id', sessionId)
        .order('created_at', ascending: true);
    return List<Map<String, dynamic>>.from(response);
  }

  Future<void> joinSession({
    required String sessionId,
    required String playerName,
    required String phone,
    required int currentJoined,
    required int maxSlots,
  }) async {
    await _client.from('session_players').insert({
      'session_id': sessionId,
      'player_name': playerName,
      'phone_number': phone,
    });

    final newCount = currentJoined + 1;
    final newStatus = newCount >= maxSlots ? 'full' : 'open';
    await _client.from('sessions').update({'joined_count': newCount, 'status': newStatus}).eq('id', sessionId);
  }

  Future<void> togglePlayerStatus(String playerId, String field, bool value) async {
    await _client.from('session_players').update({field: value}).eq('id', playerId);
  }

  // ================= CLUBS & TRANSACTIONS =================
  Future<List<Map<String, dynamic>>> getClubs() async {
    final response = await _client.from('clubs').select().order('created_at', ascending: true);
    return List<Map<String, dynamic>>.from(response);
  }
  
  Future<Map<String, dynamic>> getClubById(String clubId) async {
    return await _client.from('clubs').select().eq('id', clubId).single();
  }

  Future<void> createClub({
    required String name,
    required String ownerPhone,
    required String bankAccount,
  }) async {
    await _client.from('clubs').insert({
      'name': name,
      'owner_phone': ownerPhone,
      'bank_account': bankAccount,
      'balance': 0,
    });
  }

  Future<List<Map<String, dynamic>>> getClubTransactions(String clubId) async {
    final response = await _client
        .from('club_transactions')
        .select()
        .eq('club_id', clubId)
        .order('created_at', ascending: false);
    return List<Map<String, dynamic>>.from(response);
  }

  Future<void> addClubTransaction({
    required String clubId,
    required String type, // 'thu' or 'chi'
    required String title,
    required int amount,
    required int currentBalance,
  }) async {
    // Thêm giao dịch
    await _client.from('club_transactions').insert({
      'club_id': clubId,
      'type': type,
      'title': title,
      'amount': amount,
    });

    // Cập nhật số dư CLB
    final newBalance = type == 'thu' ? currentBalance + amount : currentBalance - amount;
    await _client.from('clubs').update({'balance': newBalance}).eq('id', clubId);
  }
}
