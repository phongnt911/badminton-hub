import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_constants.dart';
import '../core/auth_guard.dart';
import '../core/time_utils.dart';
import '../models/session.dart';
import '../providers/auth_provider.dart';
import '../providers/session_provider.dart';
import 'public_sessions_screen.dart';
import 'session_detail_screen.dart';
import 'session_form_screen.dart';
import 'session_history_screen.dart';

/// Tab "Buổi chơi": danh sách buổi host quản lý + lối vào khám phá buổi công khai.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _refresh());
  }

  Future<void> _refresh() async {
    if (!mounted) return;
    final auth = context.read<AuthProvider>();
    final sessions = context.read<SessionProvider>();
    if (auth.isAuthenticated) {
      await sessions.fetchMySessions();
    }
  }

  Future<void> _createSession() async {
    final ok = await requireAuth(context);
    if (!ok || !mounted) return;
    final created = await Navigator.of(context).push<Session>(
      MaterialPageRoute(builder: (_) => const SessionFormScreen()),
    );
    if (!mounted) return;
    if (created != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã tạo buổi chơi (bản nháp).')),
      );
    }
  }

  Future<void> _openDiscovery() async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const PublicSessionsScreen()),
    );
  }

  Future<void> _openHistory() async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const SessionHistoryScreen()),
    );
  }

  void _openSession(String sessionId) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => SessionDetailScreen(sessionId: sessionId),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final sessions = context.watch<SessionProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          '🏸 Buổi Chơi',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Khám phá buổi công khai',
            onPressed: _openDiscovery,
            icon: const Icon(Icons.explore_outlined),
          ),
        ],
      ),
      floatingActionButton: auth.isAuthenticated
          ? FloatingActionButton.extended(
              onPressed: _createSession,
              backgroundColor: AppConstants.accentColor,
              icon: const Icon(Icons.add, color: Colors.white),
              label: const Text(
                'TẠO BUỔI',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
              ),
            )
          : null,
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          padding: const EdgeInsets.all(12),
          children: [
            _DiscoveryTile(onTap: _openDiscovery),
            if (auth.isAuthenticated) ...[
              const SizedBox(height: 8),
              _HistoryTile(onTap: _openHistory),
            ],
            const SizedBox(height: 16),
            if (!auth.isAuthenticated)
              _GuestNote(onLogin: () => requireAuth(context))
            else ...[
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Buổi tôi quản lý',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                  ),
                  if (sessions.isLoadingMine)
                    const SizedBox(
                      height: 16,
                      width: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              _MySessionsSection(
                provider: sessions,
                onRetry: () => sessions.fetchMySessions(),
                onOpen: _openSession,
                onCreate: _createSession,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DiscoveryTile extends StatelessWidget {
  final VoidCallback onTap;
  const _DiscoveryTile({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        leading: const Icon(Icons.search, color: AppConstants.primaryColor),
        title: const Text(
          'Khám phá buổi công khai',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: const Text('Lọc theo khu vực, thời gian, còn chỗ và cách thu phí'),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  final VoidCallback onTap;
  const _HistoryTile({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        key: const Key('bh07c-history-entry'),
        leading: const Icon(Icons.history, color: AppConstants.primaryColor),
        title: const Text(
          'Lịch sử buổi',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: const Text(
          'Buổi đã kết thúc/đã huỷ, tổng kết và công nợ còn lại',
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}

class _GuestNote extends StatelessWidget {
  final VoidCallback onLogin;
  const _GuestNote({required this.onLogin});

  @override
  Widget build(BuildContext context) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Bạn đang xem dưới dạng khách',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Đăng nhập để tạo buổi, quản lý đăng ký và theo dõi khoản thu.',
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: onLogin,
              icon: const Icon(Icons.login),
              label: const Text('Đăng nhập'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppConstants.primaryColor,
                foregroundColor: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MySessionsSection extends StatelessWidget {
  final SessionProvider provider;
  final VoidCallback onRetry;
  final void Function(String sessionId) onOpen;
  final VoidCallback onCreate;

  const _MySessionsSection({
    required this.provider,
    required this.onRetry,
    required this.onOpen,
    required this.onCreate,
  });

  @override
  Widget build(BuildContext context) {
    if (provider.myErrorMessage != null) {
      return _ErrorBox(
        message: provider.myErrorMessage!,
        onRetry: onRetry,
      );
    }
    if (provider.mySessions.isEmpty) {
      return _EmptyBox(
        message: 'Bạn chưa có buổi chơi nào.',
        actionLabel: 'Tạo buổi đầu tiên',
        onAction: onCreate,
      );
    }
    return Column(
      children: provider.mySessions
          .map((s) => SessionCard(session: s, onTap: () => onOpen(s.id)))
          .toList(),
    );
  }
}

/// Thẻ buổi chơi dùng chung cho danh sách quản lý và khám phá.
class SessionCard extends StatelessWidget {
  final Session session;
  final VoidCallback onTap;

  const SessionCard({super.key, required this.session, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      session.title,
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  _StatusChip(session: session),
                ],
              ),
              const SizedBox(height: 6),
              Text('📍 ${session.venueName ?? 'Chưa có sân'}'
                  '${session.venueArea != null ? ' · ${session.venueArea}' : ''}'),
              Text('⏰ ${formatVietnamRange(session.startsAt, session.endsAt)}'),
              Text('👥 ${session.confirmedCount}/${session.capacity} người · ${session.feeLabel}'),
              if (session.clubName != null)
                Text('🏟️ ${session.clubName}',
                    style: TextStyle(color: Colors.grey[700])),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final Session session;
  const _StatusChip({required this.session});

  @override
  Widget build(BuildContext context) {
    final isLive = session.isPublished || session.isInProgress;
    final color = session.isCancelled
        ? Colors.red
        : (isLive ? Colors.green : Colors.grey);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        session.lifecycleLabel,
        style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12),
      ),
    );
  }
}

class _ErrorBox extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorBox({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Text(message, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 8),
            OutlinedButton(onPressed: onRetry, child: const Text('Thử lại')),
          ],
        ),
      ),
    );
  }
}

class _EmptyBox extends StatelessWidget {
  final String message;
  final String actionLabel;
  final VoidCallback onAction;
  const _EmptyBox({
    required this.message,
    required this.actionLabel,
    required this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Text(message, style: const TextStyle(color: Colors.grey)),
            const SizedBox(height: 8),
            OutlinedButton(onPressed: onAction, child: Text(actionLabel)),
          ],
        ),
      ),
    );
  }
}
