import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../core/app_constants.dart';
import '../providers/club_provider.dart';

class ClubsScreen extends StatefulWidget {
  const ClubsScreen({super.key});

  @override
  State<ClubsScreen> createState() => _ClubsScreenState();
}

class _ClubsScreenState extends State<ClubsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ClubProvider>().fetchClubs();
    });
  }

  void _showCreateClubDialog() {
    final nameCtrl = TextEditingController();
    final phoneCtrl = TextEditingController();
    final bankAccountCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Tạo Câu Lạc Bộ Mới'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameCtrl,
                decoration: const InputDecoration(labelText: 'Tên CLB (VD: CLB Biển Xanh)'),
              ),
              TextField(
                controller: phoneCtrl,
                decoration: const InputDecoration(labelText: 'Hotline chủ nhiệm'),
                keyboardType: TextInputType.phone,
              ),
              TextField(
                controller: bankAccountCtrl,
                decoration: const InputDecoration(labelText: 'STK Ngân hàng nhận quỹ'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy')),
          ElevatedButton(
            onPressed: () async {
              if (nameCtrl.text.isEmpty) return;
              await context.read<ClubProvider>().createClub(
                nameCtrl.text,
                phoneCtrl.text,
                bankAccountCtrl.text,
              );
              if (!ctx.mounted) return;
              Navigator.pop(ctx);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppConstants.primaryColor,
              foregroundColor: Colors.white,
            ),
            child: const Text('Tạo CLB'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Quản Lý Nhóm & CLB', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showCreateClubDialog,
        backgroundColor: AppConstants.accentColor,
        icon: const Icon(Icons.add, color: Colors.white),
        label: const Text('TẠO CLB MỚI', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
      ),
      body: Consumer<ClubProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          final clubs = provider.clubs;
          if (clubs.isEmpty) {
            return const Center(child: Text('Chưa có CLB nào. Hãy tạo mới!'));
          }
          
          return ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: clubs.length,
            itemBuilder: (ctx, index) {
              final club = clubs[index];
              return Card(
                elevation: 2,
                margin: const EdgeInsets.only(bottom: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: ListTile(
                  contentPadding: const EdgeInsets.all(16),
                  leading: const CircleAvatar(
                    backgroundColor: Colors.blue,
                    child: Icon(Icons.group, color: Colors.white),
                  ),
                  title: Text(club['name'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 4),
                      Text('📞 Chủ nhiệm: ${club['owner_phone'] ?? '---'}'),
                      const SizedBox(height: 4),
                      Text(
                        '💰 Số dư quỹ: ${NumberFormat('#,###').format(club['balance'] ?? 0)} VNĐ',
                        style: const TextStyle(color: Colors.green, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => ClubDetailScreen(club: club),
                      ),
                    );
                  },
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class ClubDetailScreen extends StatefulWidget {
  final Map<String, dynamic> club;
  const ClubDetailScreen({super.key, required this.club});

  @override
  State<ClubDetailScreen> createState() => _ClubDetailScreenState();
}

class _ClubDetailScreenState extends State<ClubDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ClubProvider>().fetchClubDetails(widget.club['id']);
    });
  }

  void _showAddTransactionDialog(String type) {
    final titleCtrl = TextEditingController();
    final amountCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(type == 'thu' ? 'Thêm Khoản Thu' : 'Thêm Khoản Chi'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: titleCtrl,
              decoration: const InputDecoration(labelText: 'Lý do (VD: Thu quỹ tháng)'),
            ),
            TextField(
              controller: amountCtrl,
              decoration: const InputDecoration(labelText: 'Số tiền (VNĐ)'),
              keyboardType: TextInputType.number,
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy')),
          ElevatedButton(
            onPressed: () async {
              if (titleCtrl.text.isEmpty || amountCtrl.text.isEmpty) return;
              final amount = int.tryParse(amountCtrl.text) ?? 0;
              if (amount <= 0) return;

              await context.read<ClubProvider>().addTransaction(
                type,
                titleCtrl.text,
                amount,
              );

              if (!ctx.mounted) return;
              Navigator.pop(ctx);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: type == 'thu' ? Colors.green : Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('Lưu'),
          ),
        ],
      ),
    );
  }
  
  void _showStatement() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Báo Cáo Sao Kê', textAlign: TextAlign.center),
        content: const Text('Tính năng chụp màn hình báo cáo đang được phát triển.\n\nSử dụng để gửi vào nhóm Zalo minh bạch quỹ.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('ĐÓNG')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.club['name']),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.share),
            onPressed: _showStatement,
            tooltip: 'Xuất Báo Cáo Sao Kê',
          )
        ],
      ),
      body: Consumer<ClubProvider>(
        builder: (context, provider, child) {
          if (provider.isDetailLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          
          final currentBalance = provider.currentClub?['balance'] ?? widget.club['balance'] ?? 0;
          final transactions = provider.currentTransactions;
          
          return Column(
            children: [
              Container(
                padding: const EdgeInsets.all(24),
                width: double.infinity,
                color: Colors.blue.shade50,
                child: Column(
                  children: [
                    const Text('SỐ DƯ QUỸ HIỆN TẠI', style: TextStyle(fontSize: 14, color: Colors.grey, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    Text(
                      '${NumberFormat('#,###').format(currentBalance)} VNĐ',
                      style: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.blue),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        ElevatedButton.icon(
                          icon: const Icon(Icons.add),
                          label: const Text('THU'),
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.green, foregroundColor: Colors.white),
                          onPressed: () => _showAddTransactionDialog('thu'),
                        ),
                        const SizedBox(width: 16),
                        ElevatedButton.icon(
                          icon: const Icon(Icons.remove),
                          label: const Text('CHI'),
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.red, foregroundColor: Colors.white),
                          onPressed: () => _showAddTransactionDialog('chi'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              const Padding(
                padding: EdgeInsets.all(16),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Lịch sử Thu / Chi', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                ),
              ),
              Expanded(
                child: transactions.isEmpty
                    ? const Center(child: Text('Chưa có giao dịch nào.'))
                    : ListView.builder(
                        itemCount: transactions.length,
                        itemBuilder: (ctx, index) {
                          final tx = transactions[index];
                          final isThu = tx['type'] == 'thu';
                          return ListTile(
                            leading: CircleAvatar(
                              backgroundColor: isThu ? Colors.green.shade100 : Colors.red.shade100,
                              child: Icon(
                                isThu ? Icons.arrow_downward : Icons.arrow_upward,
                                color: isThu ? Colors.green : Colors.red,
                              ),
                            ),
                            title: Text(tx['title']),
                            subtitle: Text(DateFormat('dd/MM/yyyy HH:mm').format(DateTime.parse(tx['created_at']))),
                            trailing: Text(
                              '${isThu ? '+' : '-'}${NumberFormat('#,###').format(tx['amount'])} đ',
                              style: TextStyle(
                                color: isThu ? Colors.green : Colors.red,
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                          );
                        },
                      ),
              ),
            ],
          );
        },
      ),
    );
  }
}
