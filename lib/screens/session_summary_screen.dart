import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../core/app_constants.dart';
import '../core/session_summary_text.dart';
import '../core/time_utils.dart';
import '../models/finance.dart';
import '../providers/finance_provider.dart';

/// Tổng kết một buổi (BH-07C), chỉ đọc aggregate do `get_session_summary`
/// trả về. Màn hình không tự cộng trừ công nợ, không đọc payment ledger và
/// không hiển thị contact/tài khoản ngân hàng.
///
/// - Management-only chỉ thấy số lượng.
/// - Finance thấy thêm các khoản tổng hợp; trường NULL giữ là "—".
/// - Nút sao chép dùng cùng dữ liệu server và bỏ phần tài chính nếu thiếu quyền.
class SessionSummaryScreen extends StatefulWidget {
  final String sessionId;

  const SessionSummaryScreen({super.key, required this.sessionId});

  @override
  State<SessionSummaryScreen> createState() => _SessionSummaryScreenState();
}

class _SessionSummaryScreenState extends State<SessionSummaryScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _load();
    });
  }

  Future<void> _load() =>
      context.read<FinanceProvider>().fetchSessionSummary(widget.sessionId);

  Future<void> _copy(SessionSummary summary) async {
    try {
      await Clipboard.setData(
        ClipboardData(text: buildSessionSummaryText(summary)),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã sao chép tổng kết buổi.')),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Không sao chép được tổng kết.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<FinanceProvider>();
    final rawSummary = provider.sessionSummary;
    final summary = rawSummary?.sessionId == widget.sessionId
        ? rawSummary
        : null;
    final error = provider.summaryErrorMessage;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Tổng kết buổi',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Tải lại tổng kết',
            onPressed: provider.isLoadingSummary ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            if (provider.isLoadingSummary) const LinearProgressIndicator(),
            if (provider.isLoadingSummary && summary == null) ...[
              const SizedBox(height: 24),
              const Center(child: CircularProgressIndicator()),
            ] else if (error != null && summary == null)
              _SummaryMessageCard(
                key: const Key('bh07c-summary-error'),
                icon: Icons.error_outline,
                title: 'Không tải được tổng kết',
                message: error,
                actionLabel: 'Thử lại',
                onAction: _load,
              )
            else if (summary == null)
              const _SummaryMessageCard(
                key: Key('bh07c-summary-empty'),
                icon: Icons.summarize_outlined,
                title: 'Chưa có tổng kết',
                message: 'Máy chủ chưa trả dữ liệu tổng kết cho buổi này.',
              )
            else ...[
              _headerCard(summary),
              const SizedBox(height: 12),
              _countsCard(summary),
              const SizedBox(height: 12),
              if (summary.canViewFinance)
                _financeCard(summary)
              else
                const _SummaryMessageCard(
                  key: Key('bh07c-summary-management-only'),
                  icon: Icons.lock_outline,
                  title: 'Chỉ xem số lượng',
                  message:
                      'Tài khoản của bạn không có quyền xem tài chính. '
                      'Nội dung sao chép cũng không gồm số tiền.',
                ),
              if (error != null) ...[
                const SizedBox(height: 12),
                _SummaryMessageCard(
                  icon: Icons.cloud_off_outlined,
                  title: 'Chưa làm mới được tổng kết',
                  message: '$error Dữ liệu đang hiển thị là lần tải trước.',
                  actionLabel: 'Thử lại',
                  onAction: _load,
                ),
              ],
              const SizedBox(height: 16),
              FilledButton.icon(
                key: const Key('bh07c-copy-summary'),
                onPressed: () => _copy(summary),
                icon: const Icon(Icons.copy),
                label: const Text('Sao chép tổng kết'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _headerCard(SessionSummary summary) {
    final time = formatVietnamRange(summary.startsAt, summary.endsAt);
    return Card(
      elevation: 3,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    summary.title?.trim().isNotEmpty == true
                        ? summary.title!.trim()
                        : 'Buổi chơi',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                Chip(label: Text(_lifecycleLabel(summary.lifecycle))),
              ],
            ),
            if (summary.clubName?.trim().isNotEmpty == true)
              Text('🏸 ${summary.clubName!.trim()}'),
            if (summary.venueName?.trim().isNotEmpty == true)
              Text('📍 ${summary.venueName!.trim()}'),
            Text(
              time.isEmpty ? '⏰ Chưa có thời gian' : '⏰ $time',
              style: TextStyle(color: Colors.grey[700]),
            ),
          ],
        ),
      ),
    );
  }

  Widget _countsCard(SessionSummary summary) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Số lượng người',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            _countRow(
              key: const Key('bh07c-summary-present'),
              icon: Icons.check_circle_outline,
              label: 'Có mặt',
              value: summary.presentCount,
            ),
            _countRow(
              key: const Key('bh07c-summary-no-show'),
              icon: Icons.person_off_outlined,
              label: 'Vắng',
              value: summary.noShowCount,
            ),
            _countRow(
              key: const Key('bh07c-summary-confirmed'),
              icon: Icons.how_to_reg,
              label: 'Đã xác nhận',
              value: summary.confirmedCount,
            ),
          ],
        ),
      ),
    );
  }

  Widget _countRow({
    required Key key,
    required IconData icon,
    required String label,
    required int value,
  }) {
    return Padding(
      key: key,
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(label)),
          Text('$value', style: const TextStyle(fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Widget _financeCard(SessionSummary summary) {
    return Card(
      key: const Key('bh07c-summary-finance'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Tài chính tổng hợp',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
                if (summary.billingState != null)
                  Chip(label: Text(_billingLabel(summary.billingState!))),
              ],
            ),
            const SizedBox(height: 8),
            _moneyRow('Tổng chi phí', summary.expensesTotalVnd),
            _moneyRow('Tổng phải thu', summary.amountDueTotalVnd),
            _moneyRow('Đã thu', summary.totalPaidVnd),
            _moneyRow(
              'Còn phải thu',
              summary.outstandingTotalVnd,
              highlight: true,
            ),
            const Divider(height: 20),
            Text(
              'Số liệu do máy chủ tổng hợp; màn hình không tự tính công nợ.',
              style: TextStyle(fontSize: 12, color: Colors.grey[700]),
            ),
          ],
        ),
      ),
    );
  }

  Widget _moneyRow(String label, int? value, {bool highlight = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(child: Text(label)),
          Text(
            formatSummaryMoney(value),
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: highlight ? AppConstants.primaryColor : null,
            ),
          ),
        ],
      ),
    );
  }

  String _lifecycleLabel(String lifecycle) {
    switch (lifecycle) {
      case 'draft':
        return 'Bản nháp';
      case 'published':
        return 'Đã công bố';
      case 'in_progress':
        return 'Đang diễn ra';
      case 'completed':
        return 'Đã kết thúc';
      case 'cancelled':
        return 'Đã huỷ';
      default:
        return lifecycle;
    }
  }

  String _billingLabel(String state) {
    switch (state) {
      case 'current':
        return 'Đang hiệu lực';
      case 'stale':
        return 'Đã cũ';
      case 'not_finalized':
        return 'Chưa chốt phí';
      default:
        return state;
    }
  }
}

class _SummaryMessageCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  const _SummaryMessageCard({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(message),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 8),
              TextButton(
                key: const Key('bh07c-summary-retry'),
                onPressed: onAction,
                child: Text(actionLabel!),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
