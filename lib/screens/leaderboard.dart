import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class LeaderboardScreen extends StatefulWidget {
  const LeaderboardScreen({super.key});

  @override
  State<LeaderboardScreen> createState() => _LeaderboardScreenState();
}

class _LeaderboardScreenState extends State<LeaderboardScreen> {
  final _client = Supabase.instance.client;
  bool _isLoading = true;
  List<Map<String, dynamic>> _stats = [];

  @override
  void initState() {
    super.initState();
    _loadStats();
  }

  Future<void> _loadStats() async {
    setState(() => _isLoading = true);
    final data = await _client
        .from('player_stats')
        .select()
        .order('matches_won', ascending: false);
    setState(() {
      _stats = List<Map<String, dynamic>>.from(data);
      _isLoading = false;
    });
  }

  String _getBadge(Map<String, dynamic> stat, int index) {
    if (index == 0) return '🏆 Thánh gánh team';
    final winStreak = stat['win_streak'] ?? 0;
    if (winStreak >= 5) return '🔥 Bất bại';
    final matchesPlayed = stat['matches_played'] ?? 0;
    final matchesWon = stat['matches_won'] ?? 0;
    if (matchesPlayed > 10 && matchesWon < 2) return '🥤 Cây ATM nước ngọt';
    return '';
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_stats.isEmpty) {
      return const Center(child: Text('Chưa có dữ liệu thống kê.'));
    }

    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: _stats.length,
      itemBuilder: (context, index) {
        final stat = _stats[index];
        final matchesPlayed = stat['matches_played'] ?? 0;
        final matchesWon = stat['matches_won'] ?? 0;
        final winRate = matchesPlayed == 0 ? 0 : (matchesWon / matchesPlayed * 100).round();
        final badge = _getBadge(stat, index);

        return Card(
          elevation: 2,
          margin: const EdgeInsets.only(bottom: 12),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: index == 0 ? Colors.amber : Colors.blueGrey,
              child: Text('#${index + 1}', style: const TextStyle(color: Colors.white)),
            ),
            title: Row(
              children: [
                Text(stat['name'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                if (badge.isNotEmpty) ...[
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.orange.shade100,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(badge, style: const TextStyle(fontSize: 10, color: Colors.orange)),
                  ),
                ]
              ],
            ),
            subtitle: Text('Thắng: $matchesWon/$matchesPlayed trận (Tỉ lệ: $winRate%)\nChuỗi thắng: ${stat['win_streak'] ?? 0}'),
            isThreeLine: true,
          ),
        );
      },
    );
  }
}
