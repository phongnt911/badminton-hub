import 'package:flutter/material.dart';

class FairMatchmaker extends StatefulWidget {
  const FairMatchmaker({super.key});

  @override
  State<FairMatchmaker> createState() => _FairMatchmakerState();
}

class Player {
  final String name;
  int gamesPlayed = 0;
  int gamesWaiting = 0;

  Player(this.name);
}

class _FairMatchmakerState extends State<FairMatchmaker> {
  final _nameCtrl = TextEditingController();
  final List<Player> _players = [];
  List<Player> _currentMatch = [];
  List<Player> _currentWaiting = [];

  void _addPlayer() {
    if (_nameCtrl.text.isNotEmpty) {
      setState(() {
        _players.add(Player(_nameCtrl.text.trim()));
        _nameCtrl.clear();
      });
    }
  }

  void _removePlayer(int index) {
    setState(() {
      _players.removeAt(index);
    });
  }

  void _generateMatch() {
    if (_players.length < 4) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Cần ít nhất 4 người để tạo trận!')),
      );
      return;
    }

    // Sắp xếp: Ai đợi nhiều (gamesWaiting cao) và chơi ít (gamesPlayed thấp) thì ưu tiên
    final sortedPlayers = List<Player>.from(_players)
      ..sort((a, b) {
        if (a.gamesWaiting != b.gamesWaiting) {
          return b.gamesWaiting.compareTo(a.gamesWaiting);
        }
        return a.gamesPlayed.compareTo(b.gamesPlayed);
      });

    setState(() {
      _currentMatch = sortedPlayers.take(4).toList();
      _currentWaiting = sortedPlayers.skip(4).toList();

      for (var p in _currentMatch) {
        p.gamesPlayed++;
        p.gamesWaiting = 0; // Reset số trận chờ
      }
      for (var p in _currentWaiting) {
        p.gamesWaiting++;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '🏸 Nhập Danh Sách Người Chơi (6-8 người)',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _nameCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Tên người chơi',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12),
                  ),
                  onSubmitted: (_) => _addPlayer(),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: _addPlayer,
                child: const Text('THÊM'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _players.asMap().entries.map((e) {
              final idx = e.key;
              final p = e.value;
              return Chip(
                label: Text('${p.name} (Chơi: ${p.gamesPlayed} - Nghỉ: ${p.gamesWaiting})'),
                onDeleted: () => _removePlayer(idx),
                deleteIconColor: Colors.red,
              );
            }).toList(),
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: ElevatedButton(
              onPressed: _generateMatch,
              style: ElevatedButton.styleFrom(backgroundColor: Colors.blue, foregroundColor: Colors.white),
              child: const Text('XẾP TRẬN (TỰ ĐỘNG XOAY TUA)', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ),
          if (_currentMatch.isNotEmpty) ...[
            const SizedBox(height: 24),
            const Text('🔥 ĐỘI HÌNH VÀO SÂN:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: Colors.green)),
            Card(
              color: Colors.green.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        Text(_currentMatch[0].name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                        const Text(' & '),
                        Text(_currentMatch[1].name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      ],
                    ),
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 8.0),
                      child: Text('VS', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
                    ),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        Text(_currentMatch[2].name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                        const Text(' & '),
                        Text(_currentMatch[3].name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
          if (_currentWaiting.isNotEmpty) ...[
            const SizedBox(height: 16),
            const Text('☕ DANH SÁCH NGỒI NGOÀI NGHỈ:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.orange)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: _currentWaiting.map((p) => Chip(label: Text(p.name))).toList(),
            ),
          ],
        ],
      ),
    );
  }
}
