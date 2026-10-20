import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../core/app_constants.dart';
import '../models/club.dart';
import '../providers/club_provider.dart';
import 'club_fund_screen.dart';

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
    final descCtrl = TextEditingController();
    String visibility = 'private';
    String? localError;
    final clubProvider = context.read<ClubProvider>();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => ChangeNotifierProvider.value(
        value: clubProvider,
        child: StatefulBuilder(
          builder: (context, setDialogState) {
            final isSubmitting = context.watch<ClubProvider>().isSubmitting;
            final submitError = context.watch<ClubProvider>().submitErrorMessage;

          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: const Text('Tạo Câu Lạc Bộ Mới', style: TextStyle(fontWeight: FontWeight.bold)),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: nameCtrl,
                    decoration: InputDecoration(
                      labelText: 'Tên CLB *',
                      hintText: 'VD: CLB Cầu Lông Thần Tốc',
                      errorText: localError,
                      border: const OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: descCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Mô tả hoạt động',
                      hintText: 'Thời gian, địa điểm, trình độ...',
                      border: OutlineInputBorder(),
                    ),
                    maxLines: 2,
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: visibility,
                    decoration: const InputDecoration(
                      labelText: 'Chế độ hiển thị',
                      border: OutlineInputBorder(),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'private', child: Text('Nội bộ (Chỉ thành viên xem được)')),
                      DropdownMenuItem(value: 'public', child: Text('Công khai (Mọi người đều tìm thấy)')),
                    ],
                    onChanged: (val) {
                      if (val != null) setDialogState(() => visibility = val);
                    },
                  ),
                  if (submitError != null) ...[
                    const SizedBox(height: 12),
                    Text(submitError, style: const TextStyle(color: Colors.red, fontSize: 13)),
                  ],
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: isSubmitting ? null : () => Navigator.pop(ctx),
                child: const Text('HỦY'),
              ),
              ElevatedButton(
                onPressed: isSubmitting
                    ? null
                    : () async {
                        final name = nameCtrl.text.trim();
                        if (name.isEmpty) {
                          setDialogState(() => localError = 'Vui lòng nhập tên CLB');
                          return;
                        }
                        setDialogState(() => localError = null);

                        final newClub = await context.read<ClubProvider>().createClub(
                              name: name,
                              description: descCtrl.text.trim().isNotEmpty ? descCtrl.text.trim() : null,
                              visibility: visibility,
                            );

                        if (newClub != null && ctx.mounted) {
                          Navigator.pop(ctx);
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Đã tạo thành công CLB "${newClub.name}"')),
                          );
                        }
                      },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppConstants.primaryColor,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                child: isSubmitting
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('TẠO CLB'),
              ),
            ],
          );
        },
      ),
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
          if (provider.isLoadingClubs) {
            return const Center(child: CircularProgressIndicator());
          }

          if (provider.clubsErrorMessage != null) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline, size: 48, color: Colors.red),
                    const SizedBox(height: 12),
                    Text(provider.clubsErrorMessage!, textAlign: TextAlign.center, style: const TextStyle(fontSize: 16)),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      icon: const Icon(Icons.refresh),
                      label: const Text('Thử lại'),
                      onPressed: () => provider.fetchClubs(),
                    )
                  ],
                ),
              ),
            );
          }

          final clubs = provider.clubs;
          if (clubs.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(32.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.groups_outlined, size: 72, color: Colors.grey.shade400),
                    const SizedBox(height: 16),
                    const Text(
                      'Bạn chưa tham gia câu lạc bộ nào',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Tạo CLB để quản lý danh sách thành viên, lịch sinh hoạt và minh bạch thu chi.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.grey.shade600),
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton.icon(
                      icon: const Icon(Icons.add),
                      label: const Text('Tạo CLB đầu tiên'),
                      onPressed: _showCreateClubDialog,
                    ),
                  ],
                ),
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () => provider.fetchClubs(),
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              itemCount: clubs.length,
              itemBuilder: (ctx, index) {
                final club = clubs[index];
                return _buildClubCard(context, club);
              },
            ),
          );
        },
      ),
    );
  }

  Widget _buildClubCard(BuildContext context, Club club) {
    String roleLabel = 'Thành viên';
    Color roleColor = Colors.grey.shade700;

    if (club.isOwner) {
      roleLabel = 'Chủ nhiệm';
      roleColor = Colors.amber.shade800;
    } else if (club.isHost) {
      roleLabel = 'Quản lý';
      roleColor = Colors.blue.shade700;
    } else if (club.isTreasurer) {
      roleLabel = 'Thủ quỹ';
      roleColor = Colors.green.shade700;
    }

    return Card(
      elevation: 2,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => ClubDetailScreen(clubId: club.id, clubName: club.name),
            ),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  CircleAvatar(
                    radius: 24,
                    backgroundColor: AppConstants.primaryColor.withValues(alpha: 0.12),
                    child: const Icon(Icons.groups, color: AppConstants.primaryColor, size: 28),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          club.name,
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                        ),
                        if (club.description != null && club.description!.isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Text(
                            club.description!,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                          ),
                        ],
                      ],
                    ),
                  ),
                  Chip(
                    label: Text(
                      roleLabel,
                      style: TextStyle(color: roleColor, fontWeight: FontWeight.bold, fontSize: 11),
                    ),
                    backgroundColor: roleColor.withValues(alpha: 0.1),
                    padding: EdgeInsets.zero,
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const Divider(height: 1),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(
                        club.visibility == 'public' ? Icons.public : Icons.lock_outline,
                        size: 16,
                        color: Colors.grey.shade600,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        club.visibility == 'public' ? 'Công khai' : 'Nội bộ',
                        style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                      ),
                    ],
                  ),

                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class ClubDetailScreen extends StatefulWidget {
  final String clubId;
  final String clubName;

  const ClubDetailScreen({
    super.key,
    required this.clubId,
    required this.clubName,
  });

  @override
  State<ClubDetailScreen> createState() => _ClubDetailScreenState();
}

class _ClubDetailScreenState extends State<ClubDetailScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ClubProvider>().fetchClubDetails(widget.clubId);
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _showAddMemberDialog() {
    final nameCtrl = TextEditingController();
    final phoneCtrl = TextEditingController();
    final noteCtrl = TextEditingController();
    String? localError;

    final clubProvider = context.read<ClubProvider>();
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => ChangeNotifierProvider.value(
        value: clubProvider,
        child: StatefulBuilder(
          builder: (context, setDialogState) {
            final isSubmitting = context.watch<ClubProvider>().isSubmitting;
            final submitError = context.watch<ClubProvider>().submitErrorMessage;

          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: const Text('Thêm Thành Viên', style: TextStyle(fontWeight: FontWeight.bold)),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: nameCtrl,
                    decoration: InputDecoration(
                      labelText: 'Tên thành viên *',
                      hintText: 'VD: Anh Nam',
                      errorText: localError,
                      border: const OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: phoneCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Số điện thoại liên hệ (riêng tư)',
                      hintText: '090xxxxxxx',
                      border: OutlineInputBorder(),
                    ),
                    keyboardType: TextInputType.phone,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: noteCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Ghi chú liên hệ',
                      hintText: 'Bạn của ai, vãng lai...',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Lưu ý: Thành viên thêm mới ở trạng thái offline (chưa liên kết tài khoản). Số điện thoại được bảo vệ và chỉ chủ nhiệm/quản lý nhìn thấy.',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontStyle: FontStyle.italic),
                  ),
                  if (submitError != null) ...[
                    const SizedBox(height: 8),
                    Text(submitError, style: const TextStyle(color: Colors.red, fontSize: 13)),
                  ],
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: isSubmitting ? null : () => Navigator.pop(ctx),
                child: const Text('HỦY'),
              ),
              ElevatedButton(
                onPressed: isSubmitting
                    ? null
                    : () async {
                        final name = nameCtrl.text.trim();
                        if (name.isEmpty) {
                          setDialogState(() => localError = 'Vui lòng nhập tên');
                          return;
                        }
                        setDialogState(() => localError = null);

                        final ok = await context.read<ClubProvider>().addMember(
                              clubId: widget.clubId,
                              displayName: name,
                              phoneNumber: phoneCtrl.text.trim().isNotEmpty ? phoneCtrl.text.trim() : null,
                              contactNote: noteCtrl.text.trim().isNotEmpty ? noteCtrl.text.trim() : null,
                            );

                        if (ok && ctx.mounted) {
                          Navigator.pop(ctx);
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Đã thêm thành viên "$name"')),
                          );
                        }
                      },
                style: ElevatedButton.styleFrom(backgroundColor: AppConstants.primaryColor, foregroundColor: Colors.white),
                child: isSubmitting
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('THÊM'),
              ),
            ],
          );
        },
      ),
    ),
    );
  }

  void _showConfigureBankDialog(BankAccount? currentBank) {
    final bankCodeCtrl = TextEditingController(text: currentBank?.bankCode ?? 'VCB');
    final accNumCtrl = TextEditingController(text: currentBank?.accountNumber ?? '');
    final accNameCtrl = TextEditingController(text: currentBank?.accountName ?? '');
    String? localError;
    final clubProvider = context.read<ClubProvider>();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => ChangeNotifierProvider.value(
        value: clubProvider,
        child: StatefulBuilder(
          builder: (context, setDialogState) {
            final isSubmitting = context.watch<ClubProvider>().isSubmitting;
            final submitError = context.watch<ClubProvider>().submitErrorMessage;

          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: const Text('Cấu Hình Tài Khoản Nhận Quỹ', style: TextStyle(fontWeight: FontWeight.bold)),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: bankCodeCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Mã ngân hàng (VD: VCB, TCB, MB, ACB) *',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: accNumCtrl,
                    decoration: InputDecoration(
                      labelText: 'Số tài khoản *',
                      hintText: 'Nhập chính xác (giữ các số 0 ở đầu)',
                      errorText: localError,
                      border: const OutlineInputBorder(),
                    ),
                    keyboardType: TextInputType.text,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: accNameCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Tên chủ tài khoản (Viết in hoa không dấu) *',
                      hintText: 'NGUYEN VAN A',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Tài khoản này chỉ hiển thị cho Chủ nhiệm và Thủ quỹ. Cập nhật mới sẽ tự động lưu trữ tài khoản cũ vào lịch sử.',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontStyle: FontStyle.italic),
                  ),
                  if (submitError != null) ...[
                    const SizedBox(height: 8),
                    Text(submitError, style: const TextStyle(color: Colors.red, fontSize: 13)),
                  ],
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: isSubmitting ? null : () => Navigator.pop(ctx),
                child: const Text('HỦY'),
              ),
              ElevatedButton(
                onPressed: isSubmitting
                    ? null
                    : () async {
                        final code = bankCodeCtrl.text.trim();
                        final num = accNumCtrl.text.trim();
                        final name = accNameCtrl.text.trim();

                        if (code.isEmpty || num.isEmpty || name.isEmpty) {
                          setDialogState(() => localError = 'Vui lòng điền đủ thông tin');
                          return;
                        }

                        final ok = await context.read<ClubProvider>().setClubBankAccount(
                              clubId: widget.clubId,
                              bankCode: code,
                              accountNumber: num,
                              accountName: name,
                            );

                        if (ok && ctx.mounted) {
                          Navigator.pop(ctx);
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Đã cập nhật tài khoản ngân hàng CLB')),
                          );
                        }
                      },
                style: ElevatedButton.styleFrom(backgroundColor: AppConstants.primaryColor, foregroundColor: Colors.white),
                child: isSubmitting
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('LƯU'),
              ),
            ],
          );
        },
      ),
    ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<ClubProvider>(
      builder: (context, provider, child) {
        final club = provider.currentClub;
        final isLoading = provider.isLoadingDetail;
        final error = provider.detailErrorMessage;

        return Scaffold(
          appBar: AppBar(
            title: Text(club?.name ?? widget.clubName, style: const TextStyle(fontWeight: FontWeight.bold)),
            backgroundColor: AppConstants.primaryColor,
            foregroundColor: Colors.white,
            bottom: TabBar(
              controller: _tabController,
              indicatorColor: Colors.white,
              labelColor: Colors.white,
              unselectedLabelColor: Colors.white70,
              tabs: const [
                Tab(icon: Icon(Icons.info_outline), text: 'Tổng quan'),
                Tab(icon: Icon(Icons.people_outline), text: 'Thành viên'),
                Tab(icon: Icon(Icons.account_balance), text: 'Tài khoản quỹ'),
              ],
            ),
          ),
          body: isLoading
              ? const Center(child: CircularProgressIndicator())
              : error != null
                  ? Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.error_outline, size: 48, color: Colors.red),
                          const SizedBox(height: 12),
                          Text(error, textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          ElevatedButton(
                            onPressed: () => provider.fetchClubDetails(widget.clubId),
                            child: const Text('Tải lại'),
                          ),
                        ],
                      ),
                    )
                  : club == null
                      ? const Center(child: Text('Không tìm thấy thông tin CLB'))
                      : TabBarView(
                          controller: _tabController,
                          children: [
                            _buildOverviewTab(club),
                            _buildMembersTab(club, provider),
                            _buildBankTab(club, provider),
                          ],
                        ),
        );
      },
    );
  }

  void _openFund(Club club, String direction) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => ClubFundScreen(club: club, initialAction: direction),
      ),
    );
  }

  Widget _buildOverviewTab(Club club) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(club.name, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Text(
                    club.description ?? 'Chưa có mô tả cho câu lạc bộ này.',
                    style: TextStyle(color: Colors.grey.shade700, fontSize: 14),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Icon(club.visibility == 'public' ? Icons.public : Icons.lock_outline, size: 18, color: Colors.grey),
                      const SizedBox(width: 6),
                      Text('Hiển thị: ${club.visibility == 'public' ? 'Công khai' : 'Nội bộ'}'),
                      const Spacer(),
                      const Icon(Icons.group, size: 18, color: Colors.grey),
                      const SizedBox(width: 6),
                      Text('${club.memberCount ?? 0} thành viên'),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (club.canViewBalance) ...[
            Container(
              padding: const EdgeInsets.all(20),
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.blue.shade200),
              ),
              child: Column(
                children: [
                  const Text('SỐ DƯ QUỸ HIỆN TẠI', style: TextStyle(fontSize: 13, color: Colors.grey, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Text(
                    '${NumberFormat('#,###').format(club.balanceVnd ?? 0)} VNĐ',
                    style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.blue),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      ElevatedButton.icon(
                        icon: const Icon(Icons.add),
                        label: const Text('THU QUỸ'),
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.green, foregroundColor: Colors.white),
                        onPressed: () => _openFund(club, 'income'),
                      ),
                      const SizedBox(width: 16),
                      ElevatedButton.icon(
                        icon: const Icon(Icons.remove),
                        label: const Text('CHI QUỸ'),
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.orange, foregroundColor: Colors.white),
                        onPressed: () => _openFund(club, 'expense'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '* Ghi thu/chi thủ công thuộc sổ quỹ và chỉ dành cho Chủ nhiệm/Thủ quỹ.',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontStyle: FontStyle.italic),
                  ),
                ],
              ),
            ),
          ] else ...[
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Icon(Icons.shield_outlined, color: Colors.grey.shade600),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Thông tin quỹ chỉ hiển thị cho Chủ nhiệm và Thủ quỹ của câu lạc bộ.',
                      style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildMembersTab(Club club, ClubProvider provider) {
    final members = provider.currentMembers;
    final canManage = club.canManageMembers;

    return Scaffold(
      floatingActionButton: canManage
          ? FloatingActionButton(
              onPressed: _showAddMemberDialog,
              backgroundColor: AppConstants.accentColor,
              child: const Icon(Icons.person_add, color: Colors.white),
            )
          : null,
      body: provider.isLoadingMembers
          ? const Center(child: CircularProgressIndicator())
          : provider.membersErrorMessage != null
              ? _loadError('Không thể tải thành viên.', () => provider.fetchMembers(widget.clubId))
              : members.isEmpty
              ? const Center(child: Text('Chưa có thành viên nào.'))
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: members.length,
                  itemBuilder: (ctx, index) {
                    final member = members[index];
                    return _buildMemberTile(club, member);
                  },
                ),
    );
  }

  Widget _buildMemberTile(Club club, ClubMember member) {
    String roleLabel = 'Thành viên';
    Color roleColor = Colors.grey.shade600;

    if (member.isOwner) {
      roleLabel = 'Chủ nhiệm';
      roleColor = Colors.amber.shade800;
    } else if (member.isHost) {
      roleLabel = 'Quản lý';
      roleColor = Colors.blue.shade700;
    } else if (member.isTreasurer) {
      roleLabel = 'Thủ quỹ';
      roleColor = Colors.green.shade700;
    }

    return Card(
      elevation: 1,
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: roleColor.withValues(alpha: 0.15),
          child: Icon(Icons.person, color: roleColor),
        ),
        title: Row(
          children: [
            Expanded(
              child: Text(member.displayName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            ),
            Chip(
              label: Text(roleLabel, style: TextStyle(color: roleColor, fontSize: 11, fontWeight: FontWeight.bold)),
              backgroundColor: roleColor.withValues(alpha: 0.1),
              padding: EdgeInsets.zero,
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (member.isOffline) ...[
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.orange.shade50,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: Colors.orange.shade200),
                ),
                child: Text('Chưa liên kết tài khoản', style: TextStyle(fontSize: 11, color: Colors.orange.shade900)),
              ),
            ],
            if (member.phoneNumber != null) ...[
              const SizedBox(height: 4),
              Row(
                children: [
                  const Icon(Icons.phone, size: 14, color: Colors.grey),
                  const SizedBox(width: 4),
                  Text(member.phoneNumber!, style: const TextStyle(fontSize: 13)),
                ],
              ),
            ],
            if (member.contactNote != null) ...[
              const SizedBox(height: 2),
              Text('Ghi chú: ${member.contactNote!}', style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
            ],
          ],
        ),
        trailing: club.isOwner && !member.isOwner
            ? PopupMenuButton<String>(
                onSelected: (val) async {
                  if (val == 'role') {
                    if (member.isOffline) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Chỉ có thể cấp vai trò quản lý cho người đã liên kết tài khoản thật')),
                      );
                      return;
                    }
                    _showRoleDialog(member);
                  }
                },
                itemBuilder: (ctx) => [
                  PopupMenuItem(
                    value: 'role',
                    enabled: !member.isOffline,
                    child: Text(member.isOffline ? 'Phân quyền (Cần liên kết TK)' : 'Đổi vai trò'),
                  ),
                ],
              )
            : null,
      ),
    );
  }

  Widget _loadError(String message, VoidCallback retry) => Center(
    child: Column(mainAxisSize: MainAxisSize.min, children: [
      Text(message),
      TextButton(onPressed: retry, child: const Text('Thử lại')),
    ]),
  );

  void _showRoleDialog(ClubMember member) {
    final provider = context.read<ClubProvider>();
    bool submitting = false;
    String? error;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(builder: (ctx, update) => AlertDialog(
        title: Text('Đổi vai trò cho ${member.displayName}'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          if (error != null) Text(error!, style: const TextStyle(color: Colors.red)),
          for (final role in {'host': 'Quản lý', 'treasurer': 'Thủ quỹ', 'member': 'Thành viên'}.entries)
            ListTile(title: Text(role.value), onTap: submitting ? null : () async {
              update(() { submitting = true; error = null; });
              final ok = await provider.setMemberRole(clubId: widget.clubId, memberId: member.id, role: role.key);
              if (!ctx.mounted) return;
              if (ok) { Navigator.pop(ctx); } else {
                update(() { submitting = false; error = 'Không thể đổi vai trò. Vui lòng thử lại.'; });
              }
            }),
          if (submitting) const CircularProgressIndicator(),
        ]),
        actions: [TextButton(onPressed: submitting ? null : () => Navigator.pop(ctx), child: const Text('Đóng'))],
      )),
    );
  }

  Widget _buildBankTab(Club club, ClubProvider provider) {
    final canConfig = club.canConfigureBank;
    final canView = club.canViewBalance;
    final bank = provider.currentBankAccount;

    if (canView || canConfig) {
      if (provider.isLoadingBank) return const Center(child: CircularProgressIndicator());
      if (provider.bankErrorMessage != null) {
        return _loadError('Không thể tải tài khoản nhận tiền.', () => provider.fetchClubBankAccount(widget.clubId));
      }
    }

    if (!canView && !canConfig) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.lock_outline, size: 64, color: Colors.grey.shade400),
              const SizedBox(height: 16),
              const Text(
                'Tài khoản quỹ được bảo mật',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                'Chỉ chủ nhiệm và thủ quỹ mới có quyền xem thông tin tài khoản ngân hàng nhận quỹ của CLB.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey.shade600),
              ),
            ],
          ),
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (bank != null) ...[
            Card(
              elevation: 3,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  gradient: LinearGradient(
                    colors: [Colors.blue.shade800, Colors.blue.shade600],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          bank.bankCode,
                          style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text('ĐANG DÙNG', style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    Text(
                      bank.accountNumber,
                      style: const TextStyle(color: Colors.white, fontSize: 24, letterSpacing: 2, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      bank.accountName.toUpperCase(),
                      style: const TextStyle(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.w500),
                    ),
                  ],
                ),
              ),
            ),
          ] else ...[
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Center(
                child: Column(
                  children: [
                    Icon(Icons.credit_card_off_outlined, size: 48, color: Colors.grey.shade400),
                    const SizedBox(height: 8),
                    const Text('Chưa cấu hình tài khoản ngân hàng nhận quỹ', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text('Chủ nhiệm cần cấu hình tài khoản để tiện nhận tiền đóng quỹ', style: TextStyle(color: Colors.grey.shade600, fontSize: 13)),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 24),
          if (canConfig) ...[
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.edit),
                label: Text(bank == null ? 'CẤU HÌNH TÀI KHOẢN' : 'ĐỔI TÀI KHOẢN KHÁC'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppConstants.primaryColor,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () => _showConfigureBankDialog(bank),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
