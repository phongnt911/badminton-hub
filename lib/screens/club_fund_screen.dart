import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../core/app_constants.dart';
import '../core/money.dart';
import '../core/time_utils.dart';
import '../models/club.dart';
import '../models/finance.dart';
import '../providers/finance_provider.dart';

/// Sổ quỹ CLB (BH-06C), chỉ dành cho vai trò được xem số dư
/// (`Club.canViewBalance`: chủ nhiệm/thủ quỹ).
///
/// Hiển thị số dư server-side, các bút toán thu/chi (phân trang) và cho phép
/// ghi thu/chi thủ công hoặc hoàn tác bút toán thủ công. Không tự tính số dư
/// ở client; mọi thay đổi dựa trên kết quả RPC rồi tải lại.
class ClubFundScreen extends StatefulWidget {
  const ClubFundScreen({super.key, required this.club, this.initialAction});

  final Club club;

  /// `'income'` hoặc `'expense'` để mở sẵn hộp thoại ghi thu/chi.
  final String? initialAction;

  @override
  State<ClubFundScreen> createState() => _ClubFundScreenState();
}

class _ClubFundScreenState extends State<ClubFundScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !widget.club.canViewBalance) return;
      context.read<FinanceProvider>().fetchClubLedger(widget.club.id);
      final action = widget.initialAction;
      if (action == 'income' || action == 'expense') {
        _openManualDialog(action!);
      }
    });
  }

  void _showSnack(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _openManualDialog(String direction) async {
    final titleController = TextEditingController(
      text: direction == 'income' ? 'Thu quỹ' : 'Chi quỹ',
    );
    final amountController = TextEditingController();
    final submitted = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(direction == 'income' ? 'Ghi thu quỹ' : 'Ghi chi quỹ'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: titleController,
              decoration: const InputDecoration(labelText: 'Nội dung *'),
            ),
            TextField(
              controller: amountController,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              decoration: const InputDecoration(labelText: 'Số tiền (VNĐ) *'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Huỷ'),
          ),
          FilledButton(
            onPressed: () {
              final title = titleController.text.trim();
              final amount = parseVnd(amountController.text);
              if (title.isEmpty || amount == null || amount <= 0) return;
              Navigator.pop(ctx, true);
            },
            child: const Text('Ghi sổ'),
          ),
        ],
      ),
    );
    if (submitted != true || !mounted) return;
    final provider = context.read<FinanceProvider>();
    final result = await provider.postManualClubTransaction(
      clubId: widget.club.id,
      direction: direction,
      amountVnd: parseVnd(amountController.text) ?? 0,
      title: titleController.text.trim(),
    );
    if (!mounted) return;
    if (result == null) {
      _showSnack(provider.submitErrorMessage ?? 'Không ghi được giao dịch quỹ.');
      return;
    }
    _showSnack('Đã ghi giao dịch quỹ.');
  }

  Future<void> _reverseEntry(ClubLedgerEntry entry) async {
    final controller = TextEditingController();
    final reason = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Hoàn tác giao dịch quỹ'),
        content: TextField(
          controller: controller,
          autofocus: true,
          maxLines: 2,
          decoration: const InputDecoration(labelText: 'Lý do *'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Huỷ'),
          ),
          FilledButton(
            onPressed: () {
              final value = controller.text.trim();
              if (value.isEmpty) return;
              Navigator.pop(ctx, value);
            },
            child: const Text('Xác nhận'),
          ),
        ],
      ),
    );
    if (reason == null || !mounted) return;
    final provider = context.read<FinanceProvider>();
    final result = await provider.reverseClubTransaction(
      transactionId: entry.transactionId,
      reason: reason,
    );
    if (!mounted) return;
    if (result == null) {
      _showSnack(provider.submitErrorMessage ?? 'Không hoàn tác được giao dịch.');
      return;
    }
    _showSnack('Đã hoàn tác giao dịch quỹ.');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Sổ quỹ ${widget.club.name}'),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
      ),
      body: widget.club.canViewBalance ? _buildLedger() : _buildDenied(),
    );
  }

  Widget _buildDenied() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.shield_outlined, size: 48, color: Colors.grey),
            const SizedBox(height: 12),
            const Text(
              'Chỉ Chủ nhiệm và Thủ quỹ xem được sổ quỹ.',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLedger() {
    return Consumer<FinanceProvider>(
      builder: (context, provider, child) {
        final ledger = provider.ledger;
        if (provider.isLoadingLedger && ledger == null) {
          return const Center(child: CircularProgressIndicator());
        }
        if (provider.ledgerErrorMessage != null && ledger == null) {
          return Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, size: 48, color: Colors.red),
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Text(provider.ledgerErrorMessage!, textAlign: TextAlign.center),
                ),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () => context.read<FinanceProvider>().fetchClubLedger(widget.club.id),
                  child: const Text('Thử lại'),
                ),
              ],
            ),
          );
        }
        return RefreshIndicator(
          onRefresh: () async {
            await context.read<FinanceProvider>().fetchClubLedger(widget.club.id);
          },
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _balanceCard(provider),
              const SizedBox(height: 12),
              _actions(provider),
              if (provider.ledgerErrorMessage != null) ...[
                const SizedBox(height: 8),
                Text(
                  provider.ledgerErrorMessage!,
                  style: const TextStyle(color: Colors.red),
                ),
              ],
              const SizedBox(height: 16),
              Text('Giao dịch', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              if (ledger == null || ledger.entries.isEmpty)
                const Text('Sổ quỹ chưa có giao dịch.')
              else
                ...ledger.entries.map((e) => _entryTile(e, provider)),
              if (provider.hasMoreLedger) ...[
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    key: const Key('bh06c-ledger-more'),
                    onPressed: provider.isLoadingMoreLedger
                        ? null
                        : () => context.read<FinanceProvider>().loadMoreLedger(),
                    child: provider.isLoadingMoreLedger
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Tải thêm'),
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _balanceCard(FinanceProvider provider) {
    final balance = provider.ledger?.balanceVnd;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const Text(
              'SỐ DƯ QUỸ HIỆN TẠI',
              style: TextStyle(fontSize: 13, color: Colors.grey, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              balance == null ? '—' : '${formatVnd(balance)} VNĐ',
              style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.blue),
            ),
          ],
        ),
      ),
    );
  }

  Widget _actions(FinanceProvider provider) {
    final busy = provider.isSubmitting;
    return Row(
      children: [
        Expanded(
          child: ElevatedButton.icon(
            key: const Key('bh06c-manual-income'),
            icon: const Icon(Icons.add),
            label: const Text('Ghi thu'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.green,
              foregroundColor: Colors.white,
            ),
            onPressed: busy ? null : () => _openManualDialog('income'),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: ElevatedButton.icon(
            key: const Key('bh06c-manual-expense'),
            icon: const Icon(Icons.remove),
            label: const Text('Ghi chi'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.orange,
              foregroundColor: Colors.white,
            ),
            onPressed: busy ? null : () => _openManualDialog('expense'),
          ),
        ),
      ],
    );
  }

  Widget _entryTile(ClubLedgerEntry entry, FinanceProvider provider) {
    final isIncome = entry.isIncome;
    return Card(
      child: ListTile(
        leading: Icon(
          isIncome ? Icons.south_west : Icons.north_east,
          color: isIncome ? Colors.green : Colors.orange,
        ),
        title: Text(entry.title ?? _sourceLabel(entry)),
        subtitle: Text(
          [
            _sourceLabel(entry),
            if (entry.createdAt != null) formatVietnamDateTime(entry.createdAt),
          ].join(' • '),
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '${isIncome ? '+' : '-'}${formatVnd(entry.amountVnd)} VNĐ',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: isIncome ? Colors.green : Colors.orange,
              ),
            ),
            if (entry.isManual && !entry.isReversal)
              TextButton(
                key: Key('bh06c-reverse-ledger-${entry.transactionId}'),
                onPressed: provider.isSubmitting ? null : () => _reverseEntry(entry),
                child: const Text('Hoàn tác'),
              ),
          ],
        ),
      ),
    );
  }

  String _sourceLabel(ClubLedgerEntry entry) {
    if (entry.isReversal) return 'Hoàn tác';
    switch (entry.sourceType) {
      case 'manual':
        return 'Thủ công';
      case 'session_payment':
      case 'payment':
        return 'Thu từ buổi';
      case 'session_expense':
      case 'expense':
        return 'Chi từ buổi';
      default:
        return entry.sourceType ?? 'Khác';
    }
  }
}
