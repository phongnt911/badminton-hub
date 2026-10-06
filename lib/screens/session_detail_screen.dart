import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:intl/intl.dart';

import '../core/app_constants.dart';

class SessionDetailScreen extends StatefulWidget {
  final String sessionId;

  const SessionDetailScreen({super.key, required this.sessionId});

  @override
  State<SessionDetailScreen> createState() => _SessionDetailScreenState();
}

class _SessionDetailScreenState extends State<SessionDetailScreen> {
  final _client = Supabase.instance.client;
  bool _isLoading = true;
  Map<String, dynamic>? _session;
  List<Map<String, dynamic>> _players = [];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    
    // Lấy thông tin session
    final sessionData = await _client
        .from('sessions')
        .select()
        .eq('id', widget.sessionId)
        .single();
        
    // Lấy danh sách người chơi
    final playersData = await _client
        .from('session_players')
        .select()
        .eq('session_id', widget.sessionId)
        .order('created_at', ascending: true);

    setState(() {
      _session = sessionData;
      _players = List<Map<String, dynamic>>.from(playersData);
      _isLoading = false;
    });
  }

  Future<void> _toggleArrival(String playerId, bool currentValue) async {
    await _client
        .from('session_players')
        .update({'has_arrived': !currentValue})
        .eq('id', playerId);
    _loadData();
  }

  Future<void> _togglePayment(String playerId, bool currentValue) async {
    await _client
        .from('session_players')
        .update({'has_paid': !currentValue})
        .eq('id', playerId);
    _loadData();
  }

  void _showVietQrDialog() {
    // Tạm thời hiển thị ảnh QR hoặc popup VietQR
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Mã VietQR Buổi Chơi', textAlign: TextAlign.center),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.qr_code_2, size: 200, color: AppConstants.primaryColor),
            const SizedBox(height: 16),
            Text(
              'Quét mã để thanh toán ${NumberFormat('#,###').format(_session?['estimated_cost'] ?? 0)} VNĐ',
              textAlign: TextAlign.center,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('ĐÓNG'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_session == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Lỗi')),
        body: const Center(child: Text('Không tìm thấy buổi chơi.')),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Chi Tiết Buổi Chơi', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Card(
              elevation: 4,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _session!['venue_name'],
                      style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text('⏰ Giờ chơi: ${_session!['start_time']} - ${_session!['end_time']}'),
                    Text('💰 Phí dự kiến: ${NumberFormat('#,###').format(_session!['estimated_cost'] ?? 0)} VNĐ/người', style: const TextStyle(color: Colors.orange, fontWeight: FontWeight.bold)),
                    Text('📞 Liên hệ: ${_session!['contact_phone']}'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Center(
              child: ElevatedButton.icon(
                icon: const Icon(Icons.qr_code),
                label: const Text('MÃ VIETQR BUỔI NÀY'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                ),
                onPressed: _showVietQrDialog,
              ),
            ),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Danh sách đăng ký',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                Text('${_players.length}/${_session!['max_slots']} người'),
              ],
            ),
            const SizedBox(height: 8),
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _players.length,
              itemBuilder: (ctx, index) {
                final player = _players[index];
                final hasArrived = player['has_arrived'] == true;
                final hasPaid = player['has_paid'] == true;
                
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: AppConstants.primaryColor,
                      child: Text('${index + 1}', style: const TextStyle(color: Colors.white)),
                    ),
                    title: Text(player['player_name'] ?? 'Khách', style: const TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Text(player['phone_number'] ?? ''),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Text('Có mặt', style: TextStyle(fontSize: 10)),
                            Switch(
                              value: hasArrived,
                              onChanged: (val) => _toggleArrival(player['id'], hasArrived),
                            ),
                          ],
                        ),
                        Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Text('Đã thu', style: TextStyle(fontSize: 10)),
                            Switch(
                              value: hasPaid,
                              activeTrackColor: Colors.green.shade200,
                              activeThumbColor: Colors.green,
                              onChanged: (val) => _togglePayment(player['id'], hasPaid),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
