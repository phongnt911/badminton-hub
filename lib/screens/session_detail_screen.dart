import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../core/app_constants.dart';
import '../core/app_routes.dart';
import '../core/auth_guard.dart';
import '../core/time_utils.dart';
import '../models/session.dart';
import '../providers/auth_provider.dart';
import '../providers/club_provider.dart';
import '../providers/session_provider.dart';
import 'session_form_screen.dart';

/// Nhãn tiếng Việt cho trạng thái đăng ký (giá trị lưu ở DB vẫn là tiếng Anh).
String registrationStatusLabel(String status) {
  switch (status) {
    case 'pending':
      return 'Chờ duyệt';
    case 'confirmed':
      return 'Đã xác nhận';
    case 'waitlisted':
      return 'Danh sách chờ';
    case 'cancelled':
      return 'Đã huỷ';
    case 'rejected':
      return 'Bị từ chối';
    default:
      return status;
  }
}

String attendanceStatusLabel(String status) {
  switch (status) {
    case 'present':
      return 'Có mặt';
    case 'no_show':
      return 'Vắng';
    case 'not_checked_in':
      return 'Chưa điểm danh';
    default:
      return status;
  }
}

/// Chi tiết buổi chơi — đọc qua `get_session_public_detail` (projection whitelist).
///
/// Guest mở được link public/unlisted; draft/private sẽ bị server từ chối và hiển
/// thị thông điệp tương ứng. Guest bấm đăng ký sẽ được đưa qua đăng nhập rồi trở
/// lại đúng buổi này (PD-01). Mọi mutation đi qua RPC có `request_id` (BH-05).
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

  /// Chạy mutation và phản hồi kết quả; khoá nút trong lúc gửi (`isSubmitting`).
  Future<void> _runAction(
    Future<bool> Function() action,
    String success,
  ) async {
    final provider = context.read<SessionProvider>();
    final ok = await action();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          ok ? success : (provider.submitErrorMessage ?? 'Thao tác thất bại.'),
        ),
        backgroundColor: ok ? AppConstants.primaryColor : Colors.red,
      ),
    );
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
            child: const Text('Không'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Đồng ý'),
          ),
        ],
      ),
    );
    return result == true;
  }

  Future<String?> _askReason(String title) async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'Lý do (tùy chọn)',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Huỷ bỏ'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Xác nhận'),
          ),
        ],
      ),
    );
    controller.dispose();
    return result;
  }

  /// Đăng ký tham gia: guest được đưa qua đăng nhập rồi trở lại đúng buổi.
  Future<void> _join() async {
    final ok = await requireAuth(
      context,
      returnRoute: AppRoutes.sessionPath(widget.sessionId),
    );
    if (!ok || !mounted) return;
    await _reload();
    if (!mounted) return;
    await _runAction(
      () => context.read<SessionProvider>().requestJoinSession(),
      'Đã gửi yêu cầu tham gia buổi chơi.',
    );
  }

  Future<void> _cancelOwnRegistration() async {
    final reg = context.read<SessionProvider>().currentSession?.myRegistration;
    if (reg == null) return;
    if (!await _confirm('Huỷ đăng ký', 'Bạn chắc chắn muốn huỷ đăng ký buổi này?')) {
      return;
    }
    if (!mounted) return;
    await _runAction(
      () => context.read<SessionProvider>().cancelRegistration(playerId: reg.playerId),
      'Đã huỷ đăng ký.',
    );
  }

  Future<void> _acceptInvitation() async {
    final invitation = context.read<SessionProvider>().myInvitation;
    if (invitation == null) return;
    await _runAction(
      () => context.read<SessionProvider>().acceptWaitlistInvitation(
        invitationId: invitation.invitationId,
      ),
      'Đã xác nhận chỗ trong buổi.',
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
    final confirmed = await _confirm(
      'Huỷ buổi chơi',
      'Bạn chắc chắn muốn huỷ buổi chơi này?',
    );
    if (!confirmed || !mounted) return;
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
      success:
          'Đã nhân bản buổi chơi thành bản nháp mới (không kèm người/tiền).',
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

  Future<void> _addPlayer() async {
    final session = context.read<SessionProvider>().currentSession;
    if (session == null) return;
    final request = await showDialog<_AddPlayerRequest>(
      context: context,
      builder: (_) => _AddPlayerDialog(
        clubId: session.clubId,
        canSetFeeExempt: session.canViewFinance,
      ),
    );
    if (request == null || !mounted) return;
    await _runAction(
      () => context.read<SessionProvider>().addSessionPlayer(
        memberId: request.memberId,
        guestName: request.guestName,
        contact: request.contact,
        feeExempt: request.feeExempt,
        allowWaitlist: request.allowWaitlist,
      ),
      'Đã thêm người vào buổi.',
    );
  }

  Future<void> _decide(SessionPlayer player, String decision) async {
    if (decision == 'rejected') {
      if (!await _confirm(
        'Từ chối đăng ký',
        'Từ chối đăng ký của ${player.displayName}?',
      )) {
        return;
      }
      if (!mounted) return;
    }
    await _runAction(
      () => context.read<SessionProvider>().decideRegistration(
        playerId: player.id,
        decision: decision,
      ),
      'Đã cập nhật đăng ký.',
    );
  }

  Future<void> _hostCancel(SessionPlayer player) async {
    final reason = await _askReason('Huỷ đăng ký của ${player.displayName}');
    if (reason == null || !mounted) return;
    await _runAction(
      () => context.read<SessionProvider>().cancelRegistration(
        playerId: player.id,
        reason: reason,
      ),
      'Đã huỷ đăng ký.',
    );
  }

  Future<void> _invite(SessionPlayer player) async {
    await _runAction(
      () => context.read<SessionProvider>().inviteWaitlistedPlayer(playerId: player.id),
      'Đã gửi lời mời nhận chỗ.',
    );
  }

  Future<void> _revoke(SessionPlayer player) async {
    final invitationId = player.pendingInvitationId;
    if (invitationId == null) return;
    await _runAction(
      () => context.read<SessionProvider>().revokeWaitlistInvitation(
        invitationId: invitationId,
      ),
      'Đã thu hồi lời mời.',
    );
  }

  Future<void> _attendance(SessionPlayer player, String status) async {
    await _runAction(
      () => context.read<SessionProvider>().recordAttendance(
        playerId: player.id,
        attendance: status,
      ),
      'Đã cập nhật điểm danh.',
    );
  }

  void _showResult(Session? result, {required String success, String? error}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          result != null ? success : (error ?? 'Thao tác thất bại.'),
        ),
        backgroundColor: result != null
            ? AppConstants.primaryColor
            : Colors.red,
      ),
    );
  }

  Future<void> _copyShareLink() async {
    String path;
    try {
      path = AppRoutes.sessionUrl(widget.sessionId);
      await Clipboard.setData(ClipboardData(text: path));
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Chưa cấu hình liên kết chia sẻ APP_BASE_URL.'),
          ),
        );
      }
      return;
    }
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text('Đã sao chép liên kết: $path')));
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<SessionProvider>();
    final auth = context.watch<AuthProvider>();
    final session = provider.currentSession;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Chi tiết buổi chơi',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
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
                  onPressed: () async {
                    final ok = await requireAuth(
                      context,
                      returnRoute: AppRoutes.sessionPath(widget.sessionId),
                    );
                    if (ok && mounted) await _reload();
                  },
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
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
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
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
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
                  Text(
                    '📍 ${session.venueName ?? 'Chưa có sân'}'
                    '${session.venueArea != null ? ' · ${session.venueArea}' : ''}',
                  ),
                  if (session.venueAddress != null)
                    Text(
                      session.venueAddress!,
                      style: TextStyle(color: Colors.grey[700]),
                    ),
                  Text(
                    '⏰ ${formatVietnamRange(session.startsAt, session.endsAt)}',
                  ),
                  Text(
                    '👥 ${session.confirmedCount}/${session.capacity} người · ${session.seatsLeft} chỗ trống',
                  ),
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
                subtitle: const Text(
                  'Link nội bộ (không chứa token/số điện thoại)',
                ),
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
            _PlayerRegistrationCard(
              session: session,
              invitation: provider.myInvitation,
              isLoadingInvitation: provider.isLoadingInvitation,
              invitationErrorMessage: provider.invitationErrorMessage,
              submitting: submitted,
              onJoin: _join,
              onCancel: _cancelOwnRegistration,
              onAccept: _acceptInvitation,
              onRetryInvitation: () =>
                  provider.fetchMyInvitation(widget.sessionId),
            )
          else
            Center(
              child: ElevatedButton.icon(
                onPressed: _join,
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
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Danh sách đăng ký',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
                TextButton.icon(
                  onPressed: submitted ? null : _addPlayer,
                  icon: const Icon(Icons.person_add_alt),
                  label: const Text('Thêm người'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (provider.isLoadingPlayers)
              const Center(child: CircularProgressIndicator())
            else if (provider.playersErrorMessage != null)
              Column(
                children: [
                  const Text('Không thể tải danh sách đăng ký.'),
                  TextButton(
                    onPressed: () =>
                        provider.fetchSessionPlayers(widget.sessionId),
                    child: const Text('Thử lại danh sách'),
                  ),
                ],
              )
            else
              _PlayersList(
                players: provider.currentPlayers,
                session: session,
                submitting: submitted,
                onDecide: _decide,
                onCancel: _hostCancel,
                onInvite: _invite,
                onRevoke: _revoke,
                onAttendance: _attendance,
              ),
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

/// Trạng thái đăng ký của chính người chơi + hành động hợp lệ.
class _PlayerRegistrationCard extends StatelessWidget {
  final Session session;
  final WaitlistInvitation? invitation;
  final bool isLoadingInvitation;
  final String? invitationErrorMessage;
  final bool submitting;
  final VoidCallback onJoin;
  final VoidCallback onCancel;
  final VoidCallback onAccept;
  final VoidCallback onRetryInvitation;

  const _PlayerRegistrationCard({
    required this.session,
    required this.invitation,
    required this.isLoadingInvitation,
    required this.invitationErrorMessage,
    required this.submitting,
    required this.onJoin,
    required this.onCancel,
    required this.onAccept,
    required this.onRetryInvitation,
  });

  @override
  Widget build(BuildContext context) {
    final reg = session.myRegistration;
    if (reg == null) {
      if (!session.isShareable) {
        return Card(
          child: ListTile(
            leading: const Icon(Icons.info_outline),
            title: const Text('Buổi chưa mở đăng ký'),
          ),
        );
      }
      // C2: buổi còn mở đăng ký thì luôn cho gửi yêu cầu; RPC quyết định chỗ
      // trống (auto_confirm → waitlisted) hay chờ host duyệt (pending).
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (session.isFull)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                'Buổi đã đủ người. Đăng ký để vào danh sách chờ.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey[700]),
              ),
            ),
          Center(
            child: ElevatedButton.icon(
              onPressed: submitting ? null : onJoin,
              icon: const Icon(Icons.how_to_reg),
              label: const Text('Đăng ký tham gia'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppConstants.primaryColor,
                foregroundColor: Colors.white,
              ),
            ),
          ),
        ],
      );
    }

    final active = reg.registrationStatus == 'pending' ||
        reg.registrationStatus == 'confirmed' ||
        reg.registrationStatus == 'waitlisted';
    final isWaitlisted = reg.registrationStatus == 'waitlisted';
    // C1: chỉ coi là "có lời mời" khi tải thành công; lỗi/đang tải thì không
    // trình bày dữ liệu cũ như lời mời đã xác minh.
    final hasInvitation =
        isWaitlisted && invitationErrorMessage == null && invitation != null;
    final canAccept = isWaitlisted && hasInvitation;

    return Card(
      color: Colors.green.shade50,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.event_available, color: Colors.green),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Đăng ký của bạn: ${registrationStatusLabel(reg.registrationStatus)}',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            if (isWaitlisted && isLoadingInvitation)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  'Đang tải lời mời…',
                  style: TextStyle(color: Colors.grey[800]),
                ),
              )
            else if (isWaitlisted && invitationErrorMessage != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      invitationErrorMessage!,
                      style: const TextStyle(color: Colors.red),
                    ),
                    TextButton(
                      onPressed: submitting ? null : onRetryInvitation,
                      child: const Text('Thử lại lời mời'),
                    ),
                  ],
                ),
              )
            else if (hasInvitation)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  'Lời mời nhận chỗ còn hiệu lực đến '
                  '${formatVietnamDateTime(invitation!.expiresAt)}.',
                  style: TextStyle(color: Colors.grey[800]),
                ),
              ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (canAccept)
                  FilledButton.icon(
                    onPressed: submitting ? null : onAccept,
                    icon: const Icon(Icons.check),
                    label: const Text('Chấp nhận lời mời'),
                  ),
                if (active)
                  OutlinedButton.icon(
                    onPressed: submitting ? null : onCancel,
                    icon: const Icon(Icons.cancel_outlined),
                    label: const Text('Huỷ đăng ký'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _PlayersList extends StatelessWidget {
  final List<SessionPlayer> players;
  final Session session;
  final bool submitting;
  final void Function(SessionPlayer, String) onDecide;
  final void Function(SessionPlayer) onCancel;
  final void Function(SessionPlayer) onInvite;
  final void Function(SessionPlayer) onRevoke;
  final void Function(SessionPlayer, String) onAttendance;

  const _PlayersList({
    required this.players,
    required this.session,
    required this.submitting,
    required this.onDecide,
    required this.onCancel,
    required this.onInvite,
    required this.onRevoke,
    required this.onAttendance,
  });

  @override
  Widget build(BuildContext context) {
    if (players.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 12),
        child: Text(
          'Chưa có ai đăng ký.',
          style: TextStyle(color: Colors.grey),
        ),
      );
    }
    return Column(
      children: players
          .map((p) => _PlayerRow(
                player: p,
                inProgress: session.isInProgress,
                submitting: submitting,
                onDecide: onDecide,
                onCancel: onCancel,
                onInvite: onInvite,
                onRevoke: onRevoke,
                onAttendance: onAttendance,
              ))
          .toList(),
    );
  }
}

class _PlayerRow extends StatelessWidget {
  final SessionPlayer player;
  final bool inProgress;
  final bool submitting;
  final void Function(SessionPlayer, String) onDecide;
  final void Function(SessionPlayer) onCancel;
  final void Function(SessionPlayer) onInvite;
  final void Function(SessionPlayer) onRevoke;
  final void Function(SessionPlayer, String) onAttendance;

  const _PlayerRow({
    required this.player,
    required this.inProgress,
    required this.submitting,
    required this.onDecide,
    required this.onCancel,
    required this.onInvite,
    required this.onRevoke,
    required this.onAttendance,
  });

  @override
  Widget build(BuildContext context) {
    final active = player.registrationStatus == 'pending' ||
        player.registrationStatus == 'confirmed' ||
        player.registrationStatus == 'waitlisted';
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: AppConstants.primaryColor,
                  child: Text(
                    player.displayName.isNotEmpty ? player.displayName[0] : '?',
                    style: const TextStyle(color: Colors.white),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        player.displayName,
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text(
                        '${registrationStatusLabel(player.registrationStatus)}'
                        '${player.registrationStatus == 'confirmed' ? ' · ${attendanceStatusLabel(player.attendanceStatus)}' : ''}'
                        '${player.phoneNumber != null ? ' · ${player.phoneNumber}' : ''}',
                        style: TextStyle(color: Colors.grey[700], fontSize: 13),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                if (player.isPending)
                  TextButton(
                    onPressed: submitting ? null : () => onDecide(player, 'confirmed'),
                    child: const Text('Duyệt'),
                  ),
                if (player.isPending)
                  TextButton(
                    onPressed: submitting ? null : () => onDecide(player, 'waitlisted'),
                    child: const Text('Chờ chỗ'),
                  ),
                if (player.isPending)
                  TextButton(
                    onPressed: submitting ? null : () => onDecide(player, 'rejected'),
                    child: const Text('Từ chối'),
                  ),
                if (player.isWaitlisted && !player.hasPendingInvitation)
                  TextButton(
                    onPressed: submitting ? null : () => onInvite(player),
                    child: const Text('Mời nhận chỗ'),
                  ),
                if (player.isWaitlisted && player.hasPendingInvitation)
                  TextButton(
                    onPressed: submitting ? null : () => onRevoke(player),
                    child: const Text('Thu hồi lời mời'),
                  ),
                if (player.isConfirmed && inProgress &&
                    player.attendanceStatus != 'present')
                  TextButton(
                    onPressed: submitting ? null : () => onAttendance(player, 'present'),
                    child: const Text('Có mặt'),
                  ),
                if (player.isConfirmed && inProgress &&
                    player.attendanceStatus != 'no_show')
                  TextButton(
                    onPressed: submitting ? null : () => onAttendance(player, 'no_show'),
                    child: const Text('Vắng'),
                  ),
                if (active)
                  TextButton(
                    onPressed: submitting ? null : () => onCancel(player),
                    child: const Text('Huỷ'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _AddPlayerRequest {
  final String? memberId;
  final String? guestName;
  final String? contact;
  final bool feeExempt;
  final bool allowWaitlist;

  const _AddPlayerRequest({
    this.memberId,
    this.guestName,
    this.contact,
    this.feeExempt = false,
    this.allowWaitlist = false,
  });
}

/// Thêm thành viên CLB (theo ID đã xác thực) hoặc khách chưa có tài khoản.
class _AddPlayerDialog extends StatefulWidget {
  final String? clubId;
  final bool canSetFeeExempt;

  const _AddPlayerDialog({this.clubId, this.canSetFeeExempt = false});

  @override
  State<_AddPlayerDialog> createState() => _AddPlayerDialogState();
}

class _AddPlayerDialogState extends State<_AddPlayerDialog> {
  final _guestName = TextEditingController();
  final _contact = TextEditingController();
  bool _guestMode = true;
  String? _memberId;
  bool _feeExempt = false;
  bool _allowWaitlist = false;
  bool _rosterRequested = false;

  @override
  void initState() {
    super.initState();
    _guestMode = widget.clubId == null;
  }

  static ClubProvider? _tryClubProvider(BuildContext context) {
    try {
      return Provider.of<ClubProvider>(context, listen: false);
    } catch (_) {
      return null;
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Tải roster theo đúng CLB của buổi, kể cả khi màn CLB chưa từng chọn CLB đó.
    if (_rosterRequested) return;
    final clubId = widget.clubId;
    if (clubId == null) return;
    final provider = _tryClubProvider(context);
    if (provider == null) return;
    _rosterRequested = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) provider.fetchClubRoster(clubId);
    });
  }

  @override
  void dispose() {
    _guestName.dispose();
    _contact.dispose();
    super.dispose();
  }

  void _submit() {
    final clubId = widget.clubId;
    final hasClub = clubId != null && _tryClubProvider(context) != null;
    final memberMode = !_guestMode && hasClub;
    final memberId = _memberId;
    final name = _guestName.text.trim();
    if (memberMode && memberId == null) return;
    if (!memberMode && name.isEmpty) return;
    Navigator.pop(
      context,
      _AddPlayerRequest(
        memberId: memberMode ? memberId : null,
        guestName: memberMode ? null : name,
        contact: _contact.text.trim().isEmpty ? null : _contact.text.trim(),
        feeExempt: widget.canSetFeeExempt && _feeExempt,
        allowWaitlist: _allowWaitlist,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Nghe ClubProvider để cập nhật khi roster đang tải/xong/lỗi.
    ClubProvider? provider;
    try {
      provider = Provider.of<ClubProvider>(context);
    } catch (_) {
      provider = null;
    }
    final clubId = widget.clubId;
    final hasClub = clubId != null && provider != null;
    final memberMode = !_guestMode && hasClub;

    return AlertDialog(
      title: const Text('Thêm người vào buổi'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (hasClub)
              Wrap(
                spacing: 8,
                children: [
                  ChoiceChip(
                    label: const Text('Khách mới'),
                    selected: !memberMode,
                    onSelected: (_) => setState(() => _guestMode = true),
                  ),
                  ChoiceChip(
                    label: const Text('Thành viên CLB'),
                    selected: memberMode,
                    onSelected: (_) => setState(() => _guestMode = false),
                  ),
                ],
              ),
            const SizedBox(height: 8),
            if (!memberMode) ...[
              TextField(
                controller: _guestName,
                decoration: const InputDecoration(
                  labelText: 'Tên khách',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _contact,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(
                  labelText: 'Số điện thoại (tùy chọn)',
                  border: OutlineInputBorder(),
                ),
              ),
            ] else ..._buildMemberPicker(provider, clubId),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Vào danh sách chờ nếu hết chỗ'),
              value: _allowWaitlist,
              onChanged: (v) => setState(() => _allowWaitlist = v),
            ),
            if (widget.canSetFeeExempt)
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Miễn phí (cần quyền tài chính)'),
                value: _feeExempt,
                onChanged: (v) => setState(() => _feeExempt = v),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Huỷ'),
        ),
        ElevatedButton(onPressed: _submit, child: const Text('Thêm')),
      ],
    );
  }

  List<Widget> _buildMemberPicker(ClubProvider provider, String clubId) {
    if (provider.isLoadingRoster) {
      return [
        Text(
          'Đang tải danh sách thành viên…',
          style: TextStyle(color: Colors.grey[700], fontSize: 12),
        ),
      ];
    }
    if (provider.rosterErrorMessage != null) {
      return [
        Text(
          provider.rosterErrorMessage!,
          style: const TextStyle(color: Colors.red, fontSize: 12),
        ),
        TextButton(
          onPressed: () => provider.fetchClubRoster(clubId),
          child: const Text('Thử lại'),
        ),
      ];
    }
    final activeMembers =
        provider.rosterMembers.where((m) => m.status == 'active').toList();
    if (activeMembers.isEmpty) {
      return [
        Text(
          'CLB chưa có thành viên đang hoạt động.',
          style: TextStyle(color: Colors.grey[700], fontSize: 12),
        ),
      ];
    }
    return [
      DropdownButtonFormField<String>(
        initialValue: _memberId,
        decoration: const InputDecoration(
          labelText: 'Thành viên CLB',
          border: OutlineInputBorder(),
        ),
        items: activeMembers
            .map(
              (m) => DropdownMenuItem(value: m.id, child: Text(m.displayName)),
            )
            .toList(),
        onChanged: (value) => setState(() => _memberId = value),
      ),
    ];
  }
}
