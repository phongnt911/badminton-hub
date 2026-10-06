import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../core/app_constants.dart';
import '../core/vietqr_helper.dart';
import 'fair_matchmaker.dart';
import 'leaderboard.dart';

// Model lưu vết kèo độ sau trận
class MatchDebt {
  final String id;
  final String teamA;
  final String teamB;
  final int scoreA;
  final int scoreB;
  final String betType;
  final String winner;
  final String loser;
  bool isPaid;
  final String time;

  MatchDebt({
    required this.id,
    required this.teamA,
    required this.teamB,
    required this.scoreA,
    required this.scoreB,
    required this.betType,
    required this.winner,
    required this.loser,
    this.isPaid = false,
    required this.time,
  });
}

class ToolsScreen extends StatefulWidget {
  const ToolsScreen({super.key});

  @override
  State<ToolsScreen> createState() => _ToolsScreenState();
}

class _ToolsScreenState extends State<ToolsScreen> {
  // ================= CẤU HÌNH TRẬN ĐẤU =================
  int maxPoints = 21; // 21 hoặc 11
  int scoreA = 0;
  int scoreB = 0;
  bool isServerA = true; // Ai đang giữ lượt giao cầu
  bool hasAlertedInterval = false; // Đã nhắc đổi sân ở điểm 11 chưa
  bool isGameOver = false;

  // Lịch sử điểm để hoàn tác (Undo)
  final List<Map<String, dynamic>> _scoreHistory = [];

  // Tên hai đội & Kèo độ
  String teamAName = 'Đội A';
  String teamBName = 'Đội B';
  String selectedBet = '2 chai Revive / Nước ngọt';

  final List<String> betOptions = [
    '2 chai Revive / Nước ngọt',
    '1 ly Cà phê muối / Trà đá',
    '1 quả Cầu cúng',
    '20.000đ Phạt Quỹ Nhậu',
    'Giao lưu vui vẻ (Không độ)',
  ];

  // Sổ ghi nợ kèo trong ngày
  final List<MatchDebt> _debtLedger = [];

  // ================= MÁY CHIA TIỀN VIETQR =================
  final courtCostCtrl = TextEditingController(text: '140000');
  final shuttleCostCtrl = TextEditingController(text: '60000');
  final peopleCtrl = TextEditingController(text: '5');
  final bankCtrl = TextEditingController(text: 'MB');
  final accCtrl = TextEditingController(text: '0905123456');
  final nameCtrl = TextEditingController(text: 'NGUYEN VAN A');
  int costPerPerson = 40000;
  String? qrUrl;

  // --- HÀM TÍNH ĐIỂM BẢNG ĐIỂM ---
  void _addPoint(bool toTeamA) {
    if (isGameOver) return;

    // Lưu lại lịch sử trước khi cộng để có thể Undo
    _scoreHistory.add({
      'scoreA': scoreA,
      'scoreB': scoreB,
      'isServerA': isServerA,
      'hasAlertedInterval': hasAlertedInterval,
    });

    setState(() {
      if (toTeamA) {
        scoreA++;
        isServerA = true;
      } else {
        scoreB++;
        isServerA = false;
      }

      // 1. Nhắc đổi sân ở điểm 11 (trong set 21 điểm)
      if (maxPoints == 21 &&
          !hasAlertedInterval &&
          (scoreA == 11 || scoreB == 11)) {
        hasAlertedInterval = true;
        _showIntervalDialog();
      }

      // 2. Kiểm tra chiến thắng (Luật Deuce)
      _checkWinner();
    });
  }

  void _undoPoint() {
    if (_scoreHistory.isEmpty) return;
    final last = _scoreHistory.removeLast();
    setState(() {
      scoreA = last['scoreA'];
      scoreB = last['scoreB'];
      isServerA = last['isServerA'];
      hasAlertedInterval = last['hasAlertedInterval'];
      isGameOver = false;
    });
  }

  void _checkWinner() {
    bool teamAWon = false;
    bool teamBWon = false;

    if (maxPoints == 21) {
      // Luật 21: Thắng khi đạt 21 và cách 2 điểm, hoặc chạm mốc 30 trước
      if (scoreA >= 21 && (scoreA - scoreB >= 2 || scoreA == 30))
        teamAWon = true;
      if (scoreB >= 21 && (scoreB - scoreA >= 2 || scoreB == 30))
        teamBWon = true;
    } else {
      // Set 11 điểm
      if (scoreA >= 11 && (scoreA - scoreB >= 2 || scoreA == 15))
        teamAWon = true;
      if (scoreB >= 11 && (scoreB - scoreA >= 2 || scoreB == 15))
        teamBWon = true;
    }

    if (teamAWon || teamBWon) {
      isGameOver = true;
      final winner = teamAWon ? teamAName : teamBName;
      final loser = teamAWon ? teamBName : teamAName;

      // Lưu vào Sổ nợ
      _debtLedger.insert(
        0,
        MatchDebt(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          teamA: teamAName,
          teamB: teamBName,
          scoreA: scoreA,
          scoreB: scoreB,
          betType: selectedBet,
          winner: winner,
          loser: loser,
          time: DateFormat('HH:mm').format(DateTime.now()),
        ),
      );

      _showVictoryDialog(winner, loser);
    }
  }

  void _resetMatch() {
    setState(() {
      scoreA = 0;
      scoreB = 0;
      isServerA = true;
      hasAlertedInterval = false;
      isGameOver = false;
      _scoreHistory.clear();
    });
  }

  void _showIntervalDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.swap_horiz, color: Colors.blue, size: 28),
            SizedBox(width: 8),
            Text('ĐIỂM 11 - ĐỔI SÂN!'),
          ],
        ),
        content: const Text(
          'Hai bên đổi sân và nghỉ ngơi 60 giây theo luật cầu lông BWF!',
          style: TextStyle(fontSize: 16),
        ),
        actions: [
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppConstants.primaryColor,
              foregroundColor: Colors.white,
            ),
            child: const Text('Tiếp tục đấu'),
          ),
        ],
      ),
    );
  }

  void _showVictoryDialog(String winner, String loser) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: const Center(
          child: Text(
            '🏆 TRẬN ĐẤU KẾT THÚC! 🏆',
            style: TextStyle(fontWeight: FontWeight.bold, color: Colors.amber),
          ),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Tỷ số chung cuộc: $scoreA - $scoreB',
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.green.shade50,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                '🎉 CHÚC MỪNG $winner CHIẾN THẮNG!',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.green,
                  fontSize: 16,
                ),
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 12),
            if (selectedBet != 'Giao lưu vui vẻ (Không độ)') ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  children: [
                    const Text(
                      '📜 ĐÃ GHI VÀO SỔ NỢ KÈO:',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                        color: Colors.orange,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '$loser nợ $winner:\n👉 $selectedBet',
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Xem lại bảng điểm'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              _resetMatch();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppConstants.primaryColor,
              foregroundColor: Colors.white,
            ),
            child: const Text('Trận tiếp theo'),
          ),
        ],
      ),
    );
  }

  // Hộp thoại cài đặt tên đội & Kèo
  void _showSetupDialog() {
    final aCtrl = TextEditingController(text: teamAName);
    final bCtrl = TextEditingController(text: teamBName);
    String tempBet = selectedBet;
    int tempPoints = maxPoints;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setModalState) => AlertDialog(
          title: const Text('⚙️ Cài Đặt Trận Đấu & Kèo'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: aCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Tên Đội A (VD: Tuấn + Hưng)',
                  ),
                ),
                TextField(
                  controller: bCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Tên Đội B (VD: Nam + Phong)',
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'Loại set thi đấu:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                Row(
                  children: [
                    ChoiceChip(
                      label: const Text('21 Điểm (Chuẩn)'),
                      selected: tempPoints == 21,
                      onSelected: (val) => setModalState(() => tempPoints = 21),
                    ),
                    const SizedBox(width: 8),
                    ChoiceChip(
                      label: const Text('11 Điểm (Nhanh)'),
                      selected: tempPoints == 11,
                      onSelected: (val) => setModalState(() => tempPoints = 11),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const Text(
                  'Kèo độ vui vẻ:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                DropdownButton<String>(
                  isExpanded: true,
                  value: tempBet,
                  items: betOptions
                      .map(
                        (b) => DropdownMenuItem(
                          value: b,
                          child: Text(b, style: const TextStyle(fontSize: 14)),
                        ),
                      )
                      .toList(),
                  onChanged: (val) {
                    if (val != null) setModalState(() => tempBet = val);
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Hủy'),
            ),
            ElevatedButton(
              onPressed: () {
                setState(() {
                  teamAName = aCtrl.text.trim().isEmpty
                      ? 'Đội A'
                      : aCtrl.text.trim();
                  teamBName = bCtrl.text.trim().isEmpty
                      ? 'Đội B'
                      : bCtrl.text.trim();
                  selectedBet = tempBet;
                  maxPoints = tempPoints;
                  _resetMatch();
                });
                Navigator.pop(ctx);
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppConstants.primaryColor,
                foregroundColor: Colors.white,
              ),
              child: const Text('Lưu & Bắt đầu'),
            ),
          ],
        ),
      ),
    );
  }

  // --- TÍNH TIỀN CHIA VIETQR ---
  void _calculateBill() {
    final court = int.tryParse(courtCostCtrl.text) ?? 0;
    final shuttle = int.tryParse(shuttleCostCtrl.text) ?? 0;
    final people = int.tryParse(peopleCtrl.text) ?? 1;

    final total = court + shuttle;
    final perPerson = (total / (people > 0 ? people : 1)).round();

    setState(() {
      costPerPerson = perPerson;
      qrUrl = VietQRHelper.generateQrUrl(
        bankCode: bankCtrl.text.trim(),
        accountNumber: accCtrl.text.trim(),
        amount: perPerson,
        description:
            'Tien cau long ${DateFormat('dd/MM').format(DateTime.now())}',
        accountName: nameCtrl.text.trim(),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    // Xác định ô giao cầu chuẩn luật BWF:
    // Điểm chẵn (0, 2, 4...) -> Giao ô bên Phải
    // Điểm lẻ (1, 3, 5...)   -> Giao ô bên Trái
    final serverScore = isServerA ? scoreA : scoreB;
    final serverCourtSide = (serverScore % 2 == 0) ? 'Ô Phải ➡️' : 'Ô Trái ⬅️';

    return DefaultTabController(
      length: 5,
      child: Scaffold(
        appBar: AppBar(
          title: const Text(
            '🛠️ Tiện Ích Sân Cầu',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          backgroundColor: AppConstants.primaryColor,
          foregroundColor: Colors.white,
          actions: [
            IconButton(
              icon: const Icon(Icons.settings),
              tooltip: 'Cài đặt kèo & đội',
              onPressed: _showSetupDialog,
            ),
          ],
          bottom: const TabBar(
            isScrollable: true,
            tabAlignment: TabAlignment.start,
            indicatorColor: Colors.white,
            labelColor: Colors.white,
            unselectedLabelColor: Colors.white70,
            tabs: [
              Tab(icon: Icon(Icons.scoreboard), text: 'Bảng Điểm'),
              Tab(icon: Icon(Icons.menu_book), text: 'Sổ Nợ'),
              Tab(icon: Icon(Icons.qr_code), text: 'Chia Tiền'),
              Tab(icon: Icon(Icons.group), text: 'Xoay Tua Sân'),
              Tab(icon: Icon(Icons.emoji_events), text: 'Xếp Hạng'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            // ================= TAB 1: BẢNG ĐIỂM SÂN CẦU =================
            Column(
              children: [
                // Thanh thông tin kèo & Lượt phát cầu
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 8,
                  ),
                  color: Colors.grey.shade100,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '🎯 Kèo: $selectedBet',
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 13,
                              color: Colors.deepOrange,
                            ),
                          ),
                          Text(
                            '🏸 Giao cầu: ${isServerA ? teamAName : teamBName} ($serverCourtSide)',
                            style: const TextStyle(
                              fontSize: 12,
                              color: Colors.blueGrey,
                            ),
                          ),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.blue.shade100,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'Set $maxPoints đ',
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Colors.blue,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                // KHU VỰC CHẠM BẤM ĐIỂM FULL MÀN HÌNH
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        // ĐỘI A
                        Expanded(
                          child: InkWell(
                            onTap: () => _addPoint(true),
                            borderRadius: BorderRadius.circular(16),
                            child: Container(
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  colors: [
                                    Colors.blue.shade50,
                                    Colors.blue.shade100,
                                  ],
                                  begin: Alignment.topCenter,
                                  end: Alignment.bottomCenter,
                                ),
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(
                                  color: isServerA
                                      ? Colors.blue.shade800
                                      : Colors.blue.shade300,
                                  width: isServerA ? 3 : 1,
                                ),
                              ),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  if (isServerA)
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 10,
                                        vertical: 4,
                                      ),
                                      decoration: BoxDecoration(
                                        color: Colors.blue,
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: const Text(
                                        '🏸 GIAO CẦU',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 11,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ),
                                  const SizedBox(height: 8),
                                  Text(
                                    teamAName,
                                    textAlign: TextAlign.center,
                                    maxLines: 2,
                                    style: const TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.blue,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    '$scoreA',
                                    style: const TextStyle(
                                      fontSize: 90,
                                      fontWeight: FontWeight.w900,
                                      color: Colors.blue,
                                    ),
                                  ),
                                  const Text(
                                    'Chạm để +1 điểm',
                                    style: TextStyle(
                                      color: Colors.grey,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        // ĐỘI B
                        Expanded(
                          child: InkWell(
                            onTap: () => _addPoint(false),
                            borderRadius: BorderRadius.circular(16),
                            child: Container(
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  colors: [
                                    Colors.orange.shade50,
                                    Colors.orange.shade100,
                                  ],
                                  begin: Alignment.topCenter,
                                  end: Alignment.bottomCenter,
                                ),
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(
                                  color: !isServerA
                                      ? Colors.orange.shade800
                                      : Colors.orange.shade300,
                                  width: !isServerA ? 3 : 1,
                                ),
                              ),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  if (!isServerA)
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 10,
                                        vertical: 4,
                                      ),
                                      decoration: BoxDecoration(
                                        color: Colors.orange,
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: const Text(
                                        '🏸 GIAO CẦU',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 11,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ),
                                  const SizedBox(height: 8),
                                  Text(
                                    teamBName,
                                    textAlign: TextAlign.center,
                                    maxLines: 2,
                                    style: const TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.orange,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    '$scoreB',
                                    style: const TextStyle(
                                      fontSize: 90,
                                      fontWeight: FontWeight.w900,
                                      color: Colors.orange,
                                    ),
                                  ),
                                  const Text(
                                    'Chạm để +1 điểm',
                                    style: TextStyle(
                                      color: Colors.grey,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                // THANH NÚT ĐIỀU KHIỂN DƯỚI
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  child: Row(
                    children: [
                      ElevatedButton.icon(
                        onPressed: _scoreHistory.isNotEmpty ? _undoPoint : null,
                        icon: const Icon(Icons.undo, size: 18),
                        label: const Text('Hoàn tác (-1)'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.grey.shade200,
                          foregroundColor: Colors.black87,
                        ),
                      ),
                      const Spacer(),
                      ElevatedButton.icon(
                        onPressed: _resetMatch,
                        icon: const Icon(Icons.refresh, size: 18),
                        label: const Text('Trận Mới'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.red.shade50,
                          foregroundColor: Colors.red,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            // ================= TAB 2: SỔ NỢ KÈO TRONG NGÀY =================
            _debtLedger.isEmpty
                ? const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.sports_bar, size: 60, color: Colors.grey),
                        SizedBox(height: 12),
                        Text(
                          'Chưa có kèo nào kết thúc.',
                          style: TextStyle(color: Colors.grey, fontSize: 16),
                        ),
                        Text(
                          'Hãy đánh xong 1 trận ở Bảng Điểm để ghi nợ!',
                          style: TextStyle(color: Colors.grey, fontSize: 13),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: _debtLedger.length,
                    itemBuilder: (context, index) {
                      final item = _debtLedger[index];
                      return Card(
                        elevation: 2,
                        margin: const EdgeInsets.only(bottom: 10),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    '⏰ ${item.time}',
                                    style: const TextStyle(
                                      color: Colors.grey,
                                      fontSize: 12,
                                    ),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 3,
                                    ),
                                    decoration: BoxDecoration(
                                      color: item.isPaid
                                          ? Colors.green.shade100
                                          : Colors.red.shade100,
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: Text(
                                      item.isPaid ? 'ĐÃ TRẢ KÈO' : 'CHƯA TRẢ',
                                      style: TextStyle(
                                        color: item.isPaid
                                            ? Colors.green
                                            : Colors.red,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 11,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(
                                'Tỷ số: ${item.teamA} (${item.scoreA}) - (${item.scoreB}) ${item.teamB}',
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Container(
                                padding: const EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: Colors.amber.shade50,
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Row(
                                  children: [
                                    const Icon(
                                      Icons.arrow_right,
                                      color: Colors.deepOrange,
                                    ),
                                    Expanded(
                                      child: Text(
                                        '${item.loser} nợ ${item.winner}: ${item.betType}',
                                        style: const TextStyle(
                                          fontWeight: FontWeight.w600,
                                          color: Colors.deepOrange,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 8),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.end,
                                children: [
                                  TextButton.icon(
                                    onPressed: () {
                                      setState(() {
                                        item.isPaid = !item.isPaid;
                                      });
                                    },
                                    icon: Icon(
                                      item.isPaid
                                          ? Icons.close
                                          : Icons.check_circle,
                                      size: 18,
                                    ),
                                    label: Text(
                                      item.isPaid
                                          ? 'Đánh dấu chưa trả'
                                          : 'Đã thanh toán',
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),

            // ================= TAB 3: CHIA TIỀN & VIETQR =================
            SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Tính tiền & tạo mã VietQR thu tiền 1 chạm',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: courtCostCtrl,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Tiền sân (VNĐ)',
                            border: OutlineInputBorder(),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: shuttleCostCtrl,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Tiền cầu (VNĐ)',
                            border: OutlineInputBorder(),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: peopleCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Số người tham gia',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        flex: 1,
                        child: TextField(
                          controller: bankCtrl,
                          decoration: const InputDecoration(
                            labelText: 'Ngân hàng (MB, VCB...)',
                            border: OutlineInputBorder(),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        flex: 2,
                        child: TextField(
                          controller: accCtrl,
                          decoration: const InputDecoration(
                            labelText: 'Số tài khoản',
                            border: OutlineInputBorder(),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: nameCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Tên chủ tài khoản',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      onPressed: _calculateBill,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppConstants.primaryColor,
                        foregroundColor: Colors.white,
                      ),
                      child: const Text(
                        'TÍNH TIỀN & TẠO VIETQR',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                  if (qrUrl != null) ...[
                    const Divider(height: 30),
                    Center(
                      child: Column(
                        children: [
                          Text(
                            'Mỗi người: ${NumberFormat('#,###').format(costPerPerson)} VNĐ',
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                              color: Colors.green,
                            ),
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'Quét mã để chuyển khoản ngay:',
                            style: TextStyle(color: Colors.grey),
                          ),
                          const SizedBox(height: 12),
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(12),
                              boxShadow: const [
                                BoxShadow(color: Colors.black12, blurRadius: 8),
                              ],
                            ),
                            child: Image.network(
                              qrUrl!,
                              width: 220,
                              height: 220,
                              fit: BoxFit.contain,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
            // ================= TAB 4: XOAY TUA SÂN =================
            const FairMatchmaker(),
            
            // ================= TAB 5: BẢNG XẾP HẠNG =================
            const LeaderboardScreen(),
          ],
        ),
      ),
    );
  }
}
