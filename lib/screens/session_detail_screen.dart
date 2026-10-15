import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../core/app_constants.dart';
import '../core/app_routes.dart';
import '../core/auth_guard.dart';
import '../core/time_utils.dart';
import '../models/session.dart';
import '../providers/auth_provider.dart';
import '../providers/session_provider.dart';
import 'session_form_screen.dart';

/// Chi tiết buổi chơi — đọc qua `get_session_public_detail` (projection whitelist).
///
/// Guest mở được link public/unlisted; draft/private sẽ bị server từ chối và hiển
/// thị thông điệp tương ứng. Guest bấm đăng ký sẽ được đưa qua đăng nhập rồi trở
/// lại đúng buổi này (PD-01).
class SessionDetailScreen extends StatefulWidget {
  final String sessionId;

  const SessionDetailScreen({super.key, required this.sessionId});

  @override
  State<SessionDetailScreen> createState() => _SessionDetailScreenState();
}

class _SessionDetailScreenState extends State<SessionDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SessionProvider>().fetchSessionDetail(widget.sessionId);
    });
  }

  Future<void> _reload() =>
      context.read<SessionProvider>().fetchSessionDetail(widget.sessionId);

  Future<void> _register() async {
    final ok = await requireAuth(
      context,
      returnRoute: AppRoutes.sessionPath(widget.sessionId),
    );
    if (!ok || !mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Chức năng đăng ký tham gia sẽ có ở BH-05.'),
      ),
    );
  }

  Future<void> _publish() async {
    final provider = context.read<SessionProvider>();
    final result = await provider.publishSession(widget.sessionId);
    if (!mounted) return;
    _showResult(
      result,
      success: 'Đã công bố buổi chơi.',
      error: provider.submitErrorMessage,
    );
    if (result != null) await _reload();
  }

  Future<void> _cancel() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Huỷ buổi chơi'),
        content: const Text('Bạn chắc chắn muốn huỷ buổi chơi này?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Không'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Huỷ buổi'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    final provider = context.read<SessionProvider>();
    final result = await provider.cancelSession(widget.sessionId);
    if (!mounted) return;
    _showResult(
      result,
      success: 'Đã huỷ buổi chơi.',
      error: provider.submitErrorMessage,
    );
    if (result != null) await _reload();
  }

  Future<void> _duplicate() async {
    final source = context.read<SessionProvider>().currentSession;
    if (source?.startsAt == null || source?.endsAt == null) return;
    final duration = source!.endsAt!.difference(source.startsAt!);
    final nextStart = source.startsAt!.add(const Duration(days: 7));
    final provider = context.read<SessionProvider>();
    final result = await provider.duplicateSession(
      widget.sessionId,
      startsAt: nextStart,
      endsAt: nextStart.add(duration),
    );
    if (!mounted) return;
    _showResult(
      result,
      success: 'Đã nhân bản buổi chơi thành bản nháp mới (không kèm người/tiền).',
      error: provider.submitErrorMessage,
    );
  }

  Future<void> _edit() async {
    final session = context.read<SessionProvider>().currentSession;
    if (session == null) return;
    final updated = await Navigator.of(context).push<Session>(
      MaterialPageRoute(builder: (_) => SessionFormScreen(session: session)),
    );
    if (!mounted) return;
    if (updated != null) await _reload();
  }

  void _showResult(Session? result, {required String success, String? error}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(result != null ? success : (error ?? 'Thao tác thất bại.')),
        backgroundColor: result != null ? AppConstants.primaryColor : Colors.red,
      ),
    );
  }

  void _copyShareLink() {
    final path = AppRoutes.sessionPath(widget.sessionId);
    Clipboard.setData(ClipboardData(text: path));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Đã sao chép liên kết: $path')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<SessionProvider>();
    final auth = context.watch<AuthProvider>();
    final session = provider.currentSession;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Chi tiết buổi chơi',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Tải lại',
            onPressed: _reload,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _buildBody(provider, auth, session),
    );
  }

  Widget _buildBody(
    SessionProvider provider,
    AuthProvider auth,
    Session? session,
  ) {
    if (provider.isLoadingDetail && session == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.detailErrorMessage != null && session == null) {
      final needsLogin = provider.detailErrorMessage!.contains('đăng nhập');
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                provider.detailErrorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.red),
              ),
              const SizedBox(height: 12),
              if (needsLogin && !auth.isAuthenticated)
                ElevatedButton(
                  onPressed: () => requireAuth(
                    context,
                    returnRoute: AppRoutes.sessionPath(widget.sessionId),
                  ),
                  child: const Text('Đăng nhập'),
                ),
              const SizedBox(height: 8),
              OutlinedButton(onPressed: _reload, child: const Text('Thử lại')),
            ],
          ),
        ),
      );
    }
    if (session == null) {
      return const Center(child: Text('Không tìm thấy buổi chơi.'));
    }

    final submitted = provider.isSubmitting;

    return RefreshIndicator(
      onRefresh: _reload,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            elevation: 4,
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
                          session.title,
                          style: const TextStyle(
                              fontSize: 20, fontWeight: FontWeight.bold),
                        ),
                      ),
                      Chip(label: Text(session.lifecycleLabel)),
                    ],
                  ),
                  if (session.description != null &&
                      session.description!.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(session.description!),
                  ],
                  const SizedBox(height: 8),
                  Text('📍 ${session.venueName ?? 'Chưa có sân'}'
                      '${session.venueArea != null ? ' · ${session.venueArea}' : ''}'),
                  if (session.venueAddress != null)
                    Text(session.venueAddress!,
                        style: TextStyle(color: Colors.grey[700])),
                  Text(
                      '⏰ ${formatVietnamRange(session.startsAt, session.endsAt)}'),
                  Text(
                      '👥 ${session.confirmedCount}/${session.capacity} người · ${session.seatsLeft} chỗ trống'),
                  Text('💰 ${session.feeLabel}'),
                  if (session.hostDisplayName != null)
                    Text('🙋 Chủ buổi: ${session.hostDisplayName}'),
                  if (session.levelRequirement != null &&
                      session.levelRequirement!.isNotEmpty)
                    Text('🎯 Trình độ: ${session.levelRequirement}'),
                ],
              ),
            ),
          ),
          if (session.isShareable || session.canManage) ...[
            const SizedBox(height: 12),
            Card(
              child: ListTile(
                leading: const Icon(Icons.link),
                title: Text(AppRoutes.sessionPath(session.id)),
                subtitle: const Text('Link nội bộ (không chứa token/số điện thoại)'),
                trailing: IconButton(
                  tooltip: 'Sao chép link',
                  onPressed: _copyShareLink,
                  icon: const Icon(Icons.copy),
                ),
              ),
            ),
          ],
          const SizedBox(height: 16),
          if (session.canManage)
            _ManagementActions(
              session: session,
              submitting: submitted,
              onEdit: _edit,
              onPublish: _publish,
              onCancel: _cancel,
              onDuplicate: _duplicate,
            )
          else if (auth.isAuthenticated)
            _RegistrationStatus(session: session, onRegister: _register)
          else
            Center(
              child: ElevatedButton.icon(
                onPressed: _register,
                icon: const Icon(Icons.login),
                label: const Text('Đăng nhập để đăng ký'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppConstants.primaryColor,
                  foregroundColor: Colors.white,
                ),
              ),
            ),
          if (provider.canManagePlayers) ...[
            const SizedBox(height: 24),
            const Text('Danh sách đăng ký',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            _PlayersList(players: provider.currentPlayers),
          ],
        ],
      ),
    );
  }
}

class _ManagementActions extends StatelessWidget {
  final Session session;
  final bool submitting;
  final VoidCallback onEdit;
  final VoidCallback onPublish;
  final VoidCallback onCancel;
  final VoidCallback onDuplicate;

  const _ManagementActions({
    required this.session,
    required this.submitting,
    required this.onEdit,
    required this.onPublish,
    required this.onCancel,
    required this.onDuplicate,
  });

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        if (session.isDraft)
          FilledButton.icon(
            onPressed: submitting ? null : onPublish,
            icon: const Icon(Icons.publish),
            label: const Text('Công bố'),
          ),
        if (session.canManage && (session.isDraft || session.isPublished))
          OutlinedButton.icon(
            onPressed: submitting ? null : onEdit,
            icon: const Icon(Icons.edit),
            label: const Text('Sửa'),
          ),
        OutlinedButton.icon(
          onPressed: submitting ? null : onDuplicate,
          icon: const Icon(Icons.copy_all),
          label: const Text('Nhân bản'),
        ),
        if (session.isActionable)
          OutlinedButton.icon(
            onPressed: submitting ? null : onCancel,
            icon: const Icon(Icons.cancel_outlined),
            label: const Text('Huỷ buổi'),
          ),
      ],
    );
  }
}

class _RegistrationStatus extends StatelessWidget {
  final Session session;
  final VoidCallback onRegister;

  const _RegistrationStatus({required this.session, required this.onRegister});

  @override
  Widget build(BuildContext context) {
    final reg = session.myRegistration;
    if (reg != null) {
      return Card(
        color: Colors.green.shade50,
        child: ListTile(
          leading: const Icon(Icons.check_circle, color: Colors.green),
          title: const Text('Bạn đã đăng ký buổi này'),
          subtitle: Text('Trạng thái: ${reg.registrationStatus}'),
        ),
      );
    }
    if (!session.isShareable || session.isFull) {
      return Card(
        child: ListTile(
          leading: const Icon(Icons.info_outline),
          title: Text(session.isFull
              ? 'Buổi đã đủ người'
              : 'Buổi chưa mở đăng ký'),
        ),
      );
    }
    return Center(
      child: ElevatedButton.icon(
        onPressed: onRegister,
        icon: const Icon(Icons.how_to_reg),
        label: const Text('Đăng ký tham gia'),
        style: ElevatedButton.styleFrom(
          backgroundColor: AppConstants.primaryColor,
          foregroundColor: Colors.white,
        ),
      ),
    );
  }
}

class _PlayersList extends StatelessWidget {
  final List<SessionPlayer> players;
  const _PlayersList({required this.players});

  @override
  Widget build(BuildContext context) {
    if (players.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 12),
        child: Text('Chưa có ai đăng ký.', style: TextStyle(color: Colors.grey)),
      );
    }
    return Column(
      children: players
          .map((p) => Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: AppConstants.primaryColor,
                    child: Text(
                      p.displayName.isNotEmpty ? p.displayName[0] : '?',
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),
                  title: Text(p.displayName),
                  subtitle: Text(
                    '${p.registrationStatus}'
                    '${p.phoneNumber != null ? ' · ${p.phoneNumber}' : ''}',
                  ),
                ),
              ))
          .toList(),
    );
  }
}
