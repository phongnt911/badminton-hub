import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/supabase_service.dart';
import '../core/app_constants.dart';

class VenuesScreen extends StatefulWidget {
  const VenuesScreen({super.key});

  @override
  State<VenuesScreen> createState() => _VenuesScreenState();
}

class _VenuesScreenState extends State<VenuesScreen> {
  final SupabaseService _service = SupabaseService();
  late Future<List<Map<String, dynamic>>> _venuesFuture;

  @override
  void initState() {
    super.initState();
    _venuesFuture = _service.getVenues();
  }

  Future<void> _makeCall(String phoneNumber) async {
    final uri = Uri.parse('tel:$phoneNumber');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          '📍 Sân Cầu Lông Nha Trang',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
      ),
      body: FutureBuilder<List<Map<String, dynamic>>>(
        future: _venuesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('Lỗi tải dữ liệu: ${snapshot.error}'));
          }
          final venues = snapshot.data ?? [];
          if (venues.isEmpty) {
            return const Center(child: Text('Chưa có dữ liệu sân'));
          }

          return ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: venues.length,
            itemBuilder: (context, index) {
              final v = venues[index];
              return Card(
                elevation: 3,
                margin: const EdgeInsets.only(bottom: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              v['name'] ?? '',
                              style: const TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: AppConstants.primaryColor.withOpacity(
                                0.15,
                              ),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              v['area'] ?? '',
                              style: const TextStyle(
                                color: AppConstants.primaryColor,
                                fontWeight: FontWeight.bold,
                                fontSize: 12,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '🏠 ${v['address']}',
                        style: TextStyle(color: Colors.grey[700]),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Text(
                            '🏸 ${v['court_count']} sân',
                            style: const TextStyle(fontWeight: FontWeight.w500),
                          ),
                          const SizedBox(width: 16),
                          Text(
                            '💰 ${v['price_range']}',
                            style: const TextStyle(
                              color: Colors.orange,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const Divider(height: 20),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          ElevatedButton.icon(
                            onPressed: () => _makeCall(v['phone_number'] ?? ''),
                            icon: const Icon(Icons.phone, size: 18),
                            label: Text('Gọi: ${v['phone_number']}'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppConstants.primaryColor,
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
