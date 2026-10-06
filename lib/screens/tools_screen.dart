import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../core/app_constants.dart';
import '../core/vietqr_helper.dart';

class ToolsScreen extends StatefulWidget {
  const ToolsScreen({super.key});

  @override
  State<ToolsScreen> createState() => _ToolsScreenState();
}

class _ToolsScreenState extends State<ToolsScreen> {
  // Scoreboard
  int scoreA = 0;
  int scoreB = 0;

  // Split bill
  final courtCostCtrl = TextEditingController(text: '140000');
  final shuttleCostCtrl = TextEditingController(text: '60000');
  final peopleCtrl = TextEditingController(text: '5');
  final bankCtrl = TextEditingController(text: 'MB');
  final accCtrl = TextEditingController(text: '0905123456');
  final nameCtrl = TextEditingController(text: 'NGUYEN VAN A');

  int costPerPerson = 40000;
  String? qrUrl;

  void calculate() {
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
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text(
            '🛠️ Tiện Ích Sân Cầu',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          backgroundColor: AppConstants.primaryColor,
          foregroundColor: Colors.white,
          bottom: const TabBar(
            indicatorColor: Colors.white,
            labelColor: Colors.white,
            tabs: [
              Tab(icon: Icon(Icons.scoreboard), text: 'Bảng Điểm'),
              Tab(icon: Icon(Icons.qr_code), text: 'Chia Tiền VietQR'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            // TAB 1: BẢNG ĐIỂM TRỰC TIẾP TRÊN SÂN
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  const Text(
                    'Chạm vào từng bên để cộng điểm (Set 21 điểm)',
                    style: TextStyle(color: Colors.grey),
                  ),
                  const SizedBox(height: 20),
                  Expanded(
                    child: Row(
                      children: [
                        // Đội A
                        Expanded(
                          child: InkWell(
                            onTap: () => setState(() => scoreA++),
                            child: Container(
                              decoration: BoxDecoration(
                                color: Colors.blue.shade100,
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(
                                  color: Colors.blue,
                                  width: 2,
                                ),
                              ),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  const Text(
                                    'ĐỘI A',
                                    style: TextStyle(
                                      fontSize: 22,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.blue,
                                    ),
                                  ),
                                  Text(
                                    '$scoreA',
                                    style: const TextStyle(
                                      fontSize: 80,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.blue,
                                    ),
                                  ),
                                  const Text(
                                    '+1 Điểm',
                                    style: TextStyle(color: Colors.grey),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                        // Đội B
                        Expanded(
                          child: InkWell(
                            onTap: () => setState(() => scoreB++),
                            child: Container(
                              decoration: BoxDecoration(
                                color: Colors.orange.shade100,
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(
                                  color: Colors.orange,
                                  width: 2,
                                ),
                              ),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  const Text(
                                    'ĐỘI B',
                                    style: TextStyle(
                                      fontSize: 22,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.orange,
                                    ),
                                  ),
                                  Text(
                                    '$scoreB',
                                    style: const TextStyle(
                                      fontSize: 80,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.orange,
                                    ),
                                  ),
                                  const Text(
                                    '+1 Điểm',
                                    style: TextStyle(color: Colors.grey),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton.icon(
                    onPressed: () => setState(() {
                      scoreA = 0;
                      scoreB = 0;
                    }),
                    icon: const Icon(Icons.refresh),
                    label: const Text('Bắt đầu set mới (Reset)'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.grey.shade300,
                      foregroundColor: Colors.black87,
                    ),
                  ),
                ],
              ),
            ),

            // TAB 2: CHIA TIỀN BUỔI VÀ TẠO VIETQR
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
                      onPressed: calculate,
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
          ],
        ),
      ),
    );
  }
}
