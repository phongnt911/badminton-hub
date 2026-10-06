import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import 'package:provider/provider.dart';
import '../core/app_constants.dart';
import '../providers/session_provider.dart';
import 'session_detail_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SessionProvider>().fetchSessions();
    });
  }

  // Hộp thoại tạo kèo mới nhanh trong 15s
  void _showCreateDialog() {
    final venueCtrl = TextEditingController(
      text: 'Sân Cầu Lông Đa Năng Khánh Hòa',
    );
    final timeCtrl = TextEditingController(text: '17:30 - 19:30');
    final slotsCtrl = TextEditingController(text: '6');
    final costCtrl = TextEditingController(text: '40000');
    final phoneCtrl = TextEditingController(text: '0905123456');

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('🏸 Đăng Kèo Tìm Vãng Lai'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: venueCtrl,
                decoration: const InputDecoration(labelText: 'Tên sân'),
              ),
              TextField(
                controller: timeCtrl,
                decoration: const InputDecoration(
                  labelText: 'Khung giờ (VD: 17:30 - 19:30)',
                ),
              ),
              TextField(
                controller: slotsCtrl,
                decoration: const InputDecoration(
                  labelText: 'Tổng slot tối đa',
                ),
                keyboardType: TextInputType.number,
              ),
              TextField(
                controller: costCtrl,
                decoration: const InputDecoration(
                  labelText: 'Phí dự kiến (VNĐ/người)',
                ),
                keyboardType: TextInputType.number,
              ),
              TextField(
                controller: phoneCtrl,
                decoration: const InputDecoration(
                  labelText: 'SĐT / Zalo chủ kèo',
                ),
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
            style: ElevatedButton.styleFrom(
              backgroundColor: AppConstants.primaryColor,
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              await context.read<SessionProvider>().createSession(
                venueCtrl.text,
                '17:30 - 19:30',
                int.tryParse(slotsCtrl.text) ?? 6,
                int.tryParse(costCtrl.text) ?? 40000,
                phoneCtrl.text,
              );
              if (!ctx.mounted) return;
              Navigator.pop(ctx);
              
              if (!mounted) return;
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Đã đăng kèo thành công!')),
              );
            },
            child: const Text('Đăng Kèo'),
          ),
        ],
      ),
    );
  }

  // Hộp thoại nhập tên và sđt khi giữ chỗ
  void _showJoinDialog(String sessionId, int currentJoined, int maxSlots) {
    final nameCtrl = TextEditingController();
    final phoneCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('📝 Đăng Ký Tham Gia'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameCtrl,
              decoration: const InputDecoration(labelText: 'Tên hiển thị'),
            ),
            TextField(
              controller: phoneCtrl,
              decoration: const InputDecoration(labelText: 'Số điện thoại'),
              keyboardType: TextInputType.phone,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Hủy'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppConstants.primaryColor,
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              if (nameCtrl.text.isEmpty || phoneCtrl.text.isEmpty) {
                ScaffoldMessenger.of(ctx).showSnackBar(
                  const SnackBar(content: Text('Vui lòng nhập đủ thông tin!')),
                );
                return;
              }

              await context.read<SessionProvider>().joinSession(
                sessionId,
                nameCtrl.text,
                phoneCtrl.text,
                currentJoined,
                maxSlots,
              );

              if (!ctx.mounted) return;
              Navigator.pop(ctx);
              
              if (!mounted) return;
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Đăng ký slot thành công!'),
                ),
              );
            },
            child: const Text('Giữ Chỗ'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          '🏸 Kèo Cầu Lông Nha Trang',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showCreateDialog,
        backgroundColor: AppConstants.accentColor,
        icon: const Icon(Icons.add, color: Colors.white),
        label: const Text(
          'ĐĂNG KÈO',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () async => context.read<SessionProvider>().fetchSessions(),
        child: ListView(
          padding: const EdgeInsets.all(12),
          children: [
            // 1. BANNER TIẾP THỊ LIÊN KẾT (AFFILIATE SHOPEE) KIẾM THU NHẬP THỤ ĐỘNG
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFFE8F5E9), Color(0xFFC8E6C9)],
                ),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.local_fire_department, color: Colors.red),
                      SizedBox(width: 6),
                      Text(
                        'Góc Phụ Kiện Cầu Lông Giá Tốt',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    height: 80,
                    child: ListView.builder(
                      scrollDirection: Axis.horizontal,
                      itemCount: AppConstants.affiliateItems.length,
                      itemBuilder: (ctx, i) {
                        final item = AppConstants.affiliateItems[i];
                        return Container(
                          width: 200,
                          margin: const EdgeInsets.only(right: 8),
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                item['title']!,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 12,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    item['price']!,
                                    style: const TextStyle(
                                      color: Colors.orange,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 12,
                                    ),
                                  ),
                                  const Text(
                                    'Xem ngay 👉',
                                    style: TextStyle(
                                      color: Colors.blue,
                                      fontSize: 11,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),
            const Text(
              '🔥 Kèo Đang Thiếu Chân Hôm Nay',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),

            // 2. DANH SÁCH KÈO LẤY TỪ PROVIDER
            Consumer<SessionProvider>(
              builder: (context, provider, child) {
                if (provider.isLoading) {
                  return const Center(
                    child: Padding(
                      padding: EdgeInsets.all(32),
                      child: CircularProgressIndicator(),
                    ),
                  );
                }
                final sessions = provider.sessions;
                if (sessions.isEmpty) {
                  return const Center(
                    child: Text(
                      'Chưa có kèo nào hôm nay. Hãy bấm "+ ĐĂNG KÈO" đầu tiên!',
                    ),
                  );
                }

                return Column(
                  children: sessions.map((s) {
                    final joined = s['joined_count'] ?? 1;
                    final max = s['max_slots'] ?? 6;
                    final isFull = joined >= max;

                    return InkWell(
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (ctx) => SessionDetailScreen(
                              sessionId: s['id'],
                            ),
                          ),
                        );
                      },
                      child: Card(
                        elevation: 2,
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
                                    s['venue_name'] ?? '',
                                    style: const TextStyle(
                                      fontSize: 16,
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
                                    color: isFull
                                        ? Colors.red.shade100
                                        : Colors.green.shade100,
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Text(
                                    isFull
                                        ? 'ĐÃ ĐỦ NGƯỜI'
                                        : 'CÒN ${max - joined} CHỖ',
                                    style: TextStyle(
                                      color: isFull ? Colors.red : Colors.green,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 12,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              '⏰ Giờ chơi: ${s['start_time']} - ${s['end_time']}',
                              style: const TextStyle(
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            Text(
                              '💰 Phí dự kiến: ${NumberFormat('#,###').format(s['estimated_cost'] ?? 40000)} VNĐ/người',
                              style: const TextStyle(
                                color: Colors.orange,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              '📞 Liên hệ: ${s['contact_phone'] ?? 'Chưa có'}',
                              style: TextStyle(color: Colors.grey[700]),
                            ),
                            const Divider(height: 16),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text('Đã tham gia: $joined / $max người'),
                                ElevatedButton(
                                  onPressed: isFull
                                      ? null
                                      : () => _showJoinDialog(s['id'], joined, max),

                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppConstants.primaryColor,
                                    foregroundColor: Colors.white,
                                  ),
                                  child: const Text('GIỮ CHỖ'),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                      ),
                    );
                  }).toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
