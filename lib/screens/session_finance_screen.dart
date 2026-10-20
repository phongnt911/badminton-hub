import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../core/app_constants.dart';
import '../core/money.dart';
import '../core/time_utils.dart';
import '../core/vietqr_helper.dart';
import '../models/finance.dart';
import '../models/session.dart';
import '../providers/finance_provider.dart';

/// Màn tài chính BH-06C của một buổi chơi.
///
/// - Vai trò tài chính (`Session.canViewFinance`): xem trạng thái phí
///   current/stale/not_finalized kèm nguồn/version, chi phí, khoản phải thu,
///   thanh toán; chốt/chốt lại phí, ghi chi phí, xác nhận/từ chối/hoàn tác và
///   ghi thu tiền mặt.
/// - Người chơi đã đăng nhập: xem phần phí của mình và QR chuyển khoản; gửi
///   "đã chuyển khoản" ở trạng thái chờ ban quản lý xác nhận.
///
/// QR chỉ là hướng dẫn chuyển khoản: màn hình không xác nhận đã thu, không có
/// webhook ngân hàng và không tự chuyển tiền.
class SessionFinanceScreen extends StatefulWidget {
  const SessionFinanceScreen({super.key, required this.session});

  final Session session;

  @override
  State<SessionFinanceScreen> createState() => _SessionFinanceScreenState();
}

class _SessionFinanceScreenState extends State<SessionFinanceScreen> {
  static const _expenseCategories = <String, String>{
    'court': 'Sân',
    'shuttle': 'Cầu',
    'water': 'Nước',
    'other': 'Khác',
  };

  /// Đang đọc outstanding của một người từ RPC trước khi mở hộp thoại thu tiền.
  bool _loadingOutstanding = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _load();
    });
  }

  void _load() {
    final provider = context.read<FinanceProvider>();
    if (widget.session.canViewFinance) {
      provider.fetchSessionFinance(widget.session.id);
    } else {
      provider.fetchPaymentInstructions(widget.session.id);
    }
  }

  void _showSnack(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<bool> _confirm(String title, String message) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Huỷ'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Đồng ý'),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  Future<String?> _askReason(String title) async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
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
    return (result == null || result.isEmpty) ? null : result;
  }

  Future<int?> _askAmount(String title, {int? initial}) async {
    final controller = TextEditingController(
      text: initial == null ? '' : '$initial',
    );
    final result = await showDialog<int>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          autofocus: true,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(
            labelText: 'Số tiền (VNĐ) *',
            hintText: 'Ví dụ: 450000',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Huỷ'),
          ),
          FilledButton(
            onPressed: () {
              final value = parseVnd(controller.text);
              if (value == null || value <= 0) return;
              Navigator.pop(ctx, value);
            },
            child: const Text('Xác nhận'),
          ),
        ],
      ),
    );
    return result;
  }

  Future<void> _run(
    Future<Object?> Function() action,
    String successMessage,
  ) async {
    final provider = context.read<FinanceProvider>();
    final result = await action();
    if (!mounted) return;
    if (result == null) {
      _showSnack(provider.submitErrorMessage ?? 'Thao tác không thành công.');
      return;
    }
    _showSnack(successMessage);
  }

  // --- Thao tác finance --------------------------------------------------- //

  Future<void> _postExpense(SessionFinance finance) async {
    var category = 'other';
    final titleController = TextEditingController();
    final amountController = TextEditingController();
    final submitted = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          title: const Text('Thêm chi phí'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                initialValue: category,
                decoration: const InputDecoration(labelText: 'Loại chi phí'),
                items: [
                  for (final entry in _expenseCategories.entries)
                    DropdownMenuItem(
                      value: entry.key,
                      child: Text(entry.value),
                    ),
                ],
                onChanged: (value) => setLocal(() => category = value ?? 'other'),
              ),
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
              child: const Text('Ghi chi phí'),
            ),
          ],
        ),
      ),
    );
    if (submitted != true || !mounted) return;
    await _run(
      () => context.read<FinanceProvider>().postExpense(
            sessionId: finance.sessionId,
            category: category,
            title: titleController.text.trim(),
            amountVnd: parseVnd(amountController.text) ?? 0,
          ),
      'Đã ghi chi phí. Phí có thể cần chốt lại.',
    );
  }

  Future<void> _reverseExpense(SessionFinance finance, FinanceExpense expense) async {
    final reason = await _askReason('Hoàn tác chi phí');
    if (reason == null || !mounted) return;
    await _run(
      () => context.read<FinanceProvider>().reverseExpense(
            sessionId: finance.sessionId,
            expenseId: expense.expenseId,
            reason: reason,
          ),
      'Đã hoàn tác chi phí.',
    );
  }

  Future<void> _finalize(SessionFinance finance, int sessionVersion) async {
    final reason = await _askReason(
      finance.isNotFinalized ? 'Chốt phí' : 'Chốt lại phí',
    );
    if (reason == null || !mounted) return;
    await _run(
      () => context.read<FinanceProvider>().finalizeCharges(
            sessionId: finance.sessionId,
            expectedVersion: sessionVersion,
            expectedBillingInputVersion: finance.billingInputVersion,
            reason: reason,
          ),
      'Đã chốt phí.',
    );
  }

  /// Đọc outstanding của đúng người từ RPC tổng hợp phía server trước khi ghi
  /// thu tiền mặt; không prefill bằng phép trừ trên một trang payment.
  Future<void> _recordCash(String playerId) async {
    if (_loadingOutstanding) return;
    final provider = context.read<FinanceProvider>();
    setState(() => _loadingOutstanding = true);
    try {
      await provider.fetchPaymentInstructions(
        widget.session.id,
        playerId: playerId,
      );
      if (!mounted) return;
      final instructions = provider.paymentInstructions;
      if (provider.instructionsErrorMessage != null || instructions == null) {
        _showSnack(
          provider.instructionsErrorMessage ??
              'Không đọc được khoản còn phải thu của người chơi.',
        );
        return;
      }
      if (instructions.outstandingVnd <= 0) {
        _showSnack('Người chơi đã trả đủ.');
        return;
      }
      final value = await _askAmount(
        'Thu tiền mặt',
        initial: instructions.outstandingVnd,
      );
      if (value == null || !mounted) return;
      await _run(
        () => context.read<FinanceProvider>().recordCashPayment(
              playerId: playerId,
              amountVnd: value,
            ),
        'Đã ghi thu tiền mặt.',
      );
    } finally {
      if (mounted) setState(() => _loadingOutstanding = false);
    }
  }

  Future<void> _confirmPayment(FinancePayment payment) async {
    final ok = await _confirm(
      'Xác nhận thanh toán',
      'Xác nhận đã nhận ${formatVnd(payment.amountVnd)} VNĐ?',
    );
    if (!ok || !mounted) return;
    await _run(
      () => context.read<FinanceProvider>().confirmPayment(paymentId: payment.paymentId),
      'Đã xác nhận thanh toán.',
    );
  }

  Future<void> _rejectPayment(FinancePayment payment) async {
    final reason = await _askReason('Từ chối thanh toán');
    if (reason == null || !mounted) return;
    await _run(
      () => context.read<FinanceProvider>().rejectPayment(
            paymentId: payment.paymentId,
            reason: reason,
          ),
      'Đã từ chối thanh toán.',
    );
  }

  Future<void> _reversePayment(FinancePayment payment) async {
    final reason = await _askReason('Hoàn tác thanh toán');
    if (reason == null || !mounted) return;
    await _run(
      () => context.read<FinanceProvider>().reversePayment(
            paymentId: payment.paymentId,
            reason: reason,
          ),
      'Đã hoàn tác thanh toán.',
    );
  }

  Future<void> _submitPayment(PaymentInstructions instructions) async {
    final playerId = instructions.playerId;
    if (playerId.isEmpty) {
      _showSnack('Thiếu thông tin đăng ký để gửi thanh toán.');
      return;
    }
    final ok = await _confirm(
      'Xác nhận đã chuyển khoản',
      'Ghi nhận ${formatVnd(instructions.outstandingVnd)} VNĐ ở trạng thái chờ ban quản lý xác nhận?',
    );
    if (!ok || !mounted) return;
    await _run(
      () => context.read<FinanceProvider>().submitPayment(
            // `submit_payment` tra `session_players.id`, không phải auth user id.
            playerId: playerId,
            amountVnd: instructions.outstandingVnd,
            method: 'bank_transfer',
            // Mã nội dung chuyển khoản của QR là cố định theo đăng ký và đã dùng
            // làm `description` của VietQR; `payments.reference` phải là định danh
            // mới cho từng intent nên để RPC tự sinh (NULL) — không tái dùng mã
            // cố định, tránh va UNIQUE sau khi lần trước bị từ chối.
          ),
      'Đã ghi nhận, chờ ban quản lý xác nhận.',
    );
  }

  // --- Build -------------------------------------------------------------- //

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<FinanceProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Tài chính buổi'),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
      ),
      body: widget.session.canViewFinance
          ? _buildManager(provider)
          : _buildPlayer(provider),
    );
  }

  Widget _buildManager(FinanceProvider provider) {
    final finance = provider.finance;
    if (provider.isLoadingFinance && finance == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.financeErrorMessage != null && finance == null) {
      return _FinanceErrorView(
        message: provider.financeErrorMessage!,
        onRetry: _load,
      );
    }
    if (finance == null) {
      return const _FinanceEmptyView(message: 'Chưa có dữ liệu tài chính cho buổi này.');
    }
    return RefreshIndicator(
      onRefresh: () async {
        await context.read<FinanceProvider>().fetchSessionFinance(widget.session.id);
      },
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _billingCard(finance),
          if (provider.financeErrorMessage != null) ...[
            const SizedBox(height: 8),
            _inlineError(provider.financeErrorMessage!),
          ],
          const SizedBox(height: 12),
          _totalsCard(finance),
          const SizedBox(height: 12),
          _managerActions(finance, provider),
          const SizedBox(height: 16),
          _expensesSection(finance, provider),
          const SizedBox(height: 16),
          _chargesSection(finance, provider),
          const SizedBox(height: 16),
          _paymentsSection(finance, provider),
        ],
      ),
    );
  }

  Widget _buildPlayer(FinanceProvider provider) {
    final instructions = provider.paymentInstructions;
    if (provider.isLoadingInstructions && instructions == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.instructionsErrorMessage != null && instructions == null) {
      return _FinanceErrorView(
        message: provider.instructionsErrorMessage!,
        onRetry: _load,
      );
    }
    if (instructions == null) {
      return const _FinanceEmptyView(message: 'Chưa có thông tin phí cho buổi này.');
    }
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _playerSummaryCard(instructions),
        const SizedBox(height: 16),
        _playerPaymentArea(instructions, provider),
      ],
    );
  }

  Widget _billingCard(SessionFinance finance) {
    final revision = finance.activeRevision;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('Trạng thái phí', style: TextStyle(fontWeight: FontWeight.bold)),
                const Spacer(),
                _billingChip(finance.billingState),
              ],
            ),
            const SizedBox(height: 8),
            Text('Phiên bản dữ liệu: ${finance.billingInputVersion}'),
            if (revision != null)
              Text(
                'Revision #${revision.revisionNo} (nguồn v${revision.sourceVersion ?? '-'})',
              ),
            if (revision?.finalizedAt != null)
              Text('Chốt lúc: ${formatVietnamDateTime(revision!.finalizedAt)}'),
          ],
        ),
      ),
    );
  }

  Widget _totalsCard(SessionFinance finance) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _moneyRow('Tổng chi phí', finance.expensesTotalVnd),
            const Divider(height: 20),
            _moneyRow(
              'Tổng còn phải thu',
              finance.outstandingTotalVnd,
              color: AppConstants.primaryColor,
            ),
          ],
        ),
      ),
    );
  }

  Widget _managerActions(SessionFinance finance, FinanceProvider provider) {
    final version = widget.session.version;
    final busy = provider.isSubmitting;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (finance.isStale)
              _stateNote('Phí đã cũ sau khi dữ liệu thay đổi — chốt lại trước khi thu tiếp.'),
            if (finance.isNotFinalized)
              _stateNote('Buổi chưa chốt phí — hãy chốt phí trước khi thu.'),
            if (version == null)
              _stateNote('Chưa xác định được phiên bản buổi để chốt phí.'),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    key: const Key('bh06c-add-expense'),
                    icon: const Icon(Icons.add),
                    label: const Text('Thêm chi phí'),
                    onPressed: busy ? null : () => _postExpense(finance),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton.icon(
                    key: const Key('bh06c-finalize'),
                    icon: const Icon(Icons.lock_outline),
                    label: Text(finance.isNotFinalized ? 'Chốt phí' : 'Chốt lại phí'),
                    onPressed: (version == null || busy)
                        ? null
                        : () => _finalize(finance, version),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _expensesSection(SessionFinance finance, FinanceProvider provider) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionTitle('Chi phí (${formatVnd(finance.expensesTotalVnd)} VNĐ)'),
        if (finance.expenses.isEmpty)
          const Text('Chưa có chi phí.')
        else
          ...finance.expenses.map((e) => _expenseTile(e, finance, provider)),
      ],
    );
  }

  Widget _expenseTile(FinanceExpense expense, SessionFinance finance, FinanceProvider provider) {
    final label = _expenseCategories[expense.category] ?? expense.category;
    return Card(
      child: ListTile(
        title: Text(expense.title ?? label),
        subtitle: Text(
          expense.isReversed
              ? 'Đã hoàn tác${expense.reversalReason == null ? '' : ' — ${expense.reversalReason}'}'
              : label,
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('${formatVnd(expense.amountVnd)} VNĐ'),
            if (expense.isPosted)
              TextButton(
                key: Key('bh06c-reverse-expense-${expense.expenseId}'),
                onPressed: provider.isSubmitting
                    ? null
                    : () => _reverseExpense(finance, expense),
                child: const Text('Hoàn tác'),
              ),
          ],
        ),
      ),
    );
  }

  Widget _chargesSection(SessionFinance finance, FinanceProvider provider) {
    final collectAllowed = finance.canCollect;
    // Trang payment của `get_session_finance` có thể bị cắt (mặc định 50 bản
    // mới nhất), nên chỉ được suy "còn phải thu" theo người khi biết chắc đã
    // có đủ lịch sử. Ngược lại hiển thị khoản phải trả theo revision (server)
    // và để hộp thoại thu tiền mặt đọc outstanding từ RPC của đúng người.
    final paymentsComplete =
        finance.limit > 0 && finance.payments.length < finance.limit;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionTitle('Khoản phải thu theo người'),
        if (!collectAllowed)
          const Padding(
            padding: EdgeInsets.only(bottom: 8),
            child: Text('Tạm chưa thu mới khi phí chưa ở trạng thái đang hiệu lực.'),
          ),
        if (finance.charges.isEmpty)
          const Text('Chưa có khoản phải thu.')
        else
          ...finance.charges.map((c) {
            final outstanding =
                paymentsComplete ? _outstandingFor(finance, c) : null;
            return Card(
              child: ListTile(
                title: Text(c.displayName ?? c.playerId),
                subtitle: Text(
                  outstanding == null
                      ? 'Phải trả theo phí: ${formatVnd(c.amountDueVnd)} VNĐ'
                      : 'Còn phải thu: ${formatVnd(outstanding)} VNĐ',
                ),
                trailing: TextButton.icon(
                  key: Key('bh06c-cash-${c.playerId}'),
                  icon: const Icon(Icons.payments_outlined),
                  label: const Text('Thu tiền mặt'),
                  onPressed: (collectAllowed &&
                          !provider.isSubmitting &&
                          !_loadingOutstanding)
                      ? () => _recordCash(c.playerId)
                      : null,
                ),
              ),
            );
          }),
      ],
    );
  }

  Widget _paymentsSection(SessionFinance finance, FinanceProvider provider) {
    final busy = provider.isSubmitting;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionTitle('Thanh toán'),
        if (finance.payments.isEmpty)
          const Text('Chưa có thanh toán.')
        else
          ...finance.payments.map((p) {
            return Card(
              child: ListTile(
                title: Text('${formatVnd(p.amountVnd)} VNĐ — ${p.method}'),
                subtitle: Text(
                  [
                    _paymentStatusLabel(p),
                    if (p.reference != null && p.reference!.isNotEmpty) 'Nội dung: ${p.reference}',
                    if (p.createdAt != null) formatVietnamDateTime(p.createdAt),
                  ].join(' • '),
                ),
                trailing: Wrap(
                  spacing: 4,
                  children: [
                    if (p.isSubmitted)
                      TextButton(
                        key: Key('bh06c-confirm-${p.paymentId}'),
                        onPressed: (finance.canCollect && !busy)
                            ? () => _confirmPayment(p)
                            : null,
                        child: const Text('Xác nhận'),
                      ),
                    if (p.isSubmitted || p.isConfirmed)
                      TextButton(
                        key: Key('${p.isSubmitted ? 'bh06c-reject' : 'bh06c-reverse'}-${p.paymentId}'),
                        onPressed: busy
                            ? null
                            : () => p.isSubmitted
                                ? _rejectPayment(p)
                                : _reversePayment(p),
                        child: Text(p.isSubmitted ? 'Từ chối' : 'Hoàn tác'),
                      ),
                  ],
                ),
              ),
            );
          }),
      ],
    );
  }

  Widget _playerSummaryCard(PaymentInstructions instructions) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('Phần phí của bạn', style: TextStyle(fontWeight: FontWeight.bold)),
                const Spacer(),
                _billingChip(instructions.billingState),
              ],
            ),
            const SizedBox(height: 12),
            _moneyRow('Phải trả', instructions.amountDueVnd),
            const Divider(height: 20),
            _moneyRow('Đã trả', instructions.totalPaidVnd),
            const Divider(height: 20),
            _moneyRow('Còn lại', instructions.outstandingVnd, color: AppConstants.primaryColor),
          ],
        ),
      ),
    );
  }

  Widget _playerPaymentArea(
    PaymentInstructions instructions,
    FinanceProvider provider,
  ) {
    if (instructions.outstandingVnd <= 0) {
      return _messageCard('Bạn đã trả đủ.');
    }
    if (instructions.isNotFinalized) {
      return _messageCard('Buổi chưa chốt phí.');
    }
    if (instructions.isStale) {
      return _messageCard('Phí đang được chốt lại, tạm thời chưa thu.');
    }
    if (!instructions.canPay) {
      return _messageCard('Chưa thể thanh toán lúc này.');
    }
    if (!instructions.hasReceiver) {
      return _messageCard('Chưa có tài khoản nhận tiền. Vui lòng liên hệ ban quản lý.');
    }
    return _qrCard(instructions, provider);
  }

  Widget _qrCard(
    PaymentInstructions instructions,
    FinanceProvider provider,
  ) {
    final bankCode = instructions.bankCode ?? '';
    final accountNumber = instructions.accountNumber ?? '';
    final accountName = instructions.accountName ?? '';
    final reference = instructions.reference ?? '';
    final qrUrl = (bankCode.isEmpty || accountNumber.isEmpty)
        ? null
        : VietQRHelper.generateQrUrl(
            bankCode: bankCode,
            accountNumber: accountNumber,
            amount: instructions.outstandingVnd,
            description: reference,
            accountName: accountName,
          );
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Chuyển khoản để thanh toán', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            Center(
              child: qrUrl == null
                  ? const Text('Thiếu thông tin tài khoản để tạo QR.')
                  : Image.network(
                      qrUrl,
                      key: const Key('bh06c-qr'),
                      width: 220,
                      height: 220,
                      fit: BoxFit.contain,
                      loadingBuilder: (context, child, progress) => progress == null
                          ? child
                          : const SizedBox(
                              width: 220,
                              height: 220,
                              child: Center(child: CircularProgressIndicator()),
                            ),
                      errorBuilder: (context, error, stack) => const SizedBox(
                        width: 220,
                        height: 220,
                        child: Center(
                          child: Text(
                            'Không tải được ảnh QR. Dùng thông tin bên dưới để chuyển khoản.',
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ),
                    ),
            ),
            const SizedBox(height: 12),
            _copyRow('Ngân hàng', bankCode),
            _copyRow('Số tài khoản', accountNumber),
            _copyRow('Chủ tài khoản', accountName),
            _copyRow('Số tiền', '${formatVnd(instructions.outstandingVnd)} VNĐ'),
            _copyRow('Nội dung', reference),
            const SizedBox(height: 12),
            const Text(
              'Mã QR chỉ là hướng dẫn chuyển khoản, KHÔNG tự xác nhận đã thu. '
              'Ban quản lý xác nhận thủ công sau khi nhận tiền.',
              style: TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                key: const Key('bh06c-submit-payment'),
                onPressed: (instructions.playerId.isEmpty || provider.isSubmitting)
                    ? null
                    : () => _submitPayment(instructions),
                child: provider.isSubmitting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Tôi đã chuyển khoản'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // --- Tiện ích hiển thị -------------------------------------------------- //

  int _outstandingFor(SessionFinance finance, FinanceCharge charge) {
    var confirmed = 0;
    for (final p in finance.payments) {
      if (p.playerId == charge.playerId && p.isConfirmed) {
        confirmed += p.amountVnd;
      }
    }
    final outstanding = charge.amountDueVnd - confirmed;
    return outstanding < 0 ? 0 : outstanding;
  }

  String _paymentStatusLabel(FinancePayment payment) {
    if (payment.isConfirmed) return 'Đã xác nhận';
    if (payment.isSubmitted) return 'Chờ xác nhận';
    if (payment.isRejected) return 'Đã từ chối';
    if (payment.isReversed) return 'Đã hoàn tác';
    return payment.status;
  }

  Widget _billingChip(String state) {
    late final Color color;
    late final String label;
    switch (state) {
      case 'current':
        color = Colors.green;
        label = 'Đang hiệu lực';
      case 'stale':
        color = Colors.orange;
        label = 'Cần chốt lại';
      case 'not_finalized':
        color = Colors.blueGrey;
        label = 'Chưa chốt phí';
      default:
        color = Colors.blueGrey;
        label = state;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color),
      ),
      child: Text(label, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.bold)),
    );
  }

  Widget _moneyRow(String label, int amount, {Color? color}) {
    return Row(
      children: [
        Text(label),
        const Spacer(),
        Text(
          '${formatVnd(amount)} VNĐ',
          style: TextStyle(fontWeight: FontWeight.bold, color: color),
        ),
      ],
    );
  }

  Widget _sectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
    );
  }

  Widget _stateNote(String message) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          const Icon(Icons.info_outline, size: 18, color: Colors.orange),
          const SizedBox(width: 8),
          Expanded(child: Text(message)),
        ],
      ),
    );
  }

  Widget _inlineError(String message) {
    return Row(
      children: [
        const Icon(Icons.error_outline, size: 18, color: Colors.red),
        const SizedBox(width: 8),
        Expanded(child: Text(message, style: const TextStyle(color: Colors.red))),
      ],
    );
  }

  Widget _messageCard(String message) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Text(message),
      ),
    );
  }

  Widget _copyRow(String label, String value) {
    final display = value.isEmpty ? '—' : value;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          SizedBox(width: 110, child: Text(label, style: const TextStyle(color: Colors.grey))),
          Expanded(child: Text(display)),
          IconButton(
            key: Key('bh06c-copy-$label'),
            tooltip: 'Sao chép $label',
            icon: const Icon(Icons.copy, size: 18),
            onPressed: value.isEmpty
                ? null
                : () async {
                    await Clipboard.setData(ClipboardData(text: value));
                    if (!mounted) return;
                    _showSnack('Đã sao chép $label');
                  },
          ),
        ],
      ),
    );
  }
}

class _FinanceErrorView extends StatelessWidget {
  const _FinanceErrorView({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline, size: 48, color: Colors.red),
          const SizedBox(height: 12),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Text(message, textAlign: TextAlign.center),
          ),
          const SizedBox(height: 12),
          ElevatedButton(onPressed: onRetry, child: const Text('Thử lại')),
        ],
      ),
    );
  }
}

class _FinanceEmptyView extends StatelessWidget {
  const _FinanceEmptyView({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(message, textAlign: TextAlign.center),
    );
  }
}
