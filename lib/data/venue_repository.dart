import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/venue.dart';

/// Truy cập danh sách sân — thay cho lớp demo `SupabaseService`.
class VenueRepository {
  final SupabaseClient _client;

  VenueRepository({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  /// Danh sách sân đang hoạt động, sắp theo khu vực rồi tên.
  Future<List<Venue>> listActiveVenues() async {
    final response = await _client
        .from('venues')
        .select()
        .eq('status', 'active')
        .order('area', ascending: true)
        .order('name', ascending: true);
    return (response as List)
        .map((item) => Venue.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }
}
