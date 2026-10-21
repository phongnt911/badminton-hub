import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_constants.dart';
import '../core/time_utils.dart';
import '../models/session.dart';
import '../providers/auth_provider.dart';
import '../providers/club_provider.dart';
import '../providers/session_provider.dart';
import 'session_detail_screen.dart';

/// Lịch sử các buổi đã kết thúc/đã huỷ mà người dùng có quyền quản lý hoặc
/// xem tài chính (BH-07C). Danh sách/filter/pagination do SessionProvider giữ;
/// màn hình chỉ hiển thị, không tự lọc hay tính lại dữ liệu.
class SessionHistoryScreen extends StatefulWidget {
  const SessionHistoryScreen({super.key});

  @override
  State<SessionHistoryScreen> createState() => _SessionHistoryScreenState();
}

class _SessionHistoryScreenState extends State<SessionHistoryScreen> {
  static const _allClubs = '__all_clubs__';

  String? _clubId;
  DateTime? _from;
  DateTime? _to;

  SessionHistoryFilter get _filter => SessionHistoryFilter(
    clubId: _clubId,
    from: _from == null ? null : vietnamDayStartUtc(_from!),
    to: _to == null ? null : vietnamDayEndUtc(_to!),
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (!context.read<AuthProvider>().isAuthenticated) return;
      _loadClubs();
      _reloadHistory();
    });
  }

  void _loadClubs() {
    context.read<ClubProvider>().fetchClubs();
  }

  void _reloadHistory() {
    context.read<SessionProvider>().fetchSessionHistory(filter: _filter);
  }

  Future<void> _refresh() async {
    if (!context.read<AuthProvider>().isAuthenticated) return;
    await context.read<SessionProvider>().fetchSessionHistory(filter: _filter);
    if (!mounted) return;
    await context.read<ClubProvider>().fetchClubs();
  }

  void _changeClub(String? clubId) {
    setState(() => _clubId = clubId);
    _reloadHistory();
  }

  Future<void> _pickDateRange() async {
    final now = DateTime.now();
    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime(now.year + 1, 12, 31),
      initialDateRange: _from != null && _to != null
          ? DateTimeRange(start: _from!, end: _to!)
          : null,
      helpText: 'Lọc lịch sử theo ngày bắt đầu',
    );
    if (picked == null || !mounted) return;
    setState(() {
      _from = DateTime(picked.start.year, picked.start.month, picked.start.day);
      _to = DateTime(picked.end.year, picked.end.month, picked.end.day);
    });
    _reloadHistory();
  }

  void _clearDates() {
    setState(() {
      _from = null;
      _to = null;
    });
    _reloadHistory();
  }

  void _clearFilters() {
    setState(() {
      _clubId = null;
      _from = null;
      _to = null;
    });
    _reloadHistory();
  }

  Future<void> _openSession(String sessionId) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => SessionDetailScreen(sessionId: sessionId),
      ),
    );
    if (!mounted) return;
    await context.read<SessionProvider>().refreshHistoryIfLoaded();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final provider = context.watch<SessionProvider>();
    final clubs = context.watch<ClubProvider>();
    final hasFilters = _clubId != null || _from != null || _to != null;
    final clubError = clubs.clubsErrorMessage;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Lịch sử buổi',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Tải lại lịch sử',
            onPressed: provider.isLoadingHistory ? null : _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(12),
          children: [
            _filterCard(
              clubs: clubs,
              clubError: clubError,
              hasFilters: hasFilters,
            ),
            if (provider.isLoadingHistory) const LinearProgressIndicator(),
            if (!auth.isAuthenticated)
              const _HistoryMessageCard(
                key: Key('bh07c-history-login-required'),
                icon: Icons.login,
                title: 'Cần đăng nhập',
                message:
                    'Đăng nhập để xem lịch sử các buổi bạn quản lý hoặc '
                    'có quyền tài chính.',
              )
            else if (provider.isLoadingHistory && !provider.hasLoadedHistory)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (provider.historyErrorMessage != null &&
                !provider.hasLoadedHistory)
              _HistoryMessageCard(
                key: const Key('bh07c-history-error'),
                icon: Icons.cloud_off_outlined,
                title: 'Không tải được lịch sử',
                message: provider.historyErrorMessage!,
                actionLabel: 'Thử lại',
                onAction: _reloadHistory,
              )
            else if (!provider.hasLoadedHistory)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              )
            else ...[
              if (provider.historyErrorMessage != null)
                _HistoryMessageCard(
                  key: const Key('bh07c-history-inline-error'),
                  icon: Icons.cloud_off_outlined,
                  title: 'Chưa làm mới được lịch sử',
                  message: provider.isHistoryEmpty
                      ? '${provider.historyErrorMessage!} Lần tải trước không '
                            'có buổi nào phù hợp; lần làm mới vừa rồi thất bại.'
                      : '${provider.historyErrorMessage!} Danh sách đang '
                            'hiển thị là lần tải trước.',
                  actionLabel: 'Tải lại',
                  onAction: _reloadHistory,
                ),
              if (provider.isHistoryEmpty)
                _HistoryMessageCard(
                  key: const Key('bh07c-history-empty'),
                  icon: Icons.history_toggle_off,
                  title: 'Chưa có buổi nào',
                  message: hasFilters
                      ? 'Không có buổi đã kết thúc/huỷ khớp bộ lọc hiện tại.'
                      : 'Các buổi đã kết thúc hoặc đã huỷ sẽ xuất hiện ở đây.',
                  actionLabel: hasFilters ? 'Xoá bộ lọc' : null,
                  onAction: hasFilters ? _clearFilters : null,
                )
              else ...[
                ...provider.historyItems.map(
                  (session) => _HistorySessionCard(
                    session: session,
                    onTap: () => _openSession(session.id),
                  ),
                ),
                if (provider.hasMoreHistory)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    child: Center(
                      child: provider.isLoadingMoreHistory
                          ? const CircularProgressIndicator()
                          : OutlinedButton.icon(
                              key: const Key('bh07c-history-load-more'),
                              onPressed: provider.loadMoreHistory,
                              icon: const Icon(Icons.expand_more),
                              label: const Text('Tải thêm'),
                            ),
                    ),
                  ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  Widget _filterCard({
    required ClubProvider clubs,
    required String? clubError,
    required bool hasFilters,
  }) {
    final clubValue = clubs.clubs.any((club) => club.id == _clubId)
        ? _clubId!
        : _allClubs;
    final dateLabel = _from == null || _to == null
        ? 'Chọn khoảng ngày'
        : '${formatVietnamDate(vietnamDayStartUtc(_from!))} - '
              '${formatVietnamDate(vietnamDayStartUtc(_to!))}';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Bộ lọc',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
                if (clubs.isLoadingClubs)
                  const SizedBox(
                    height: 16,
                    width: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                if (hasFilters)
                  TextButton(
                    key: const Key('bh07c-history-clear-filters'),
                    onPressed: _clearFilters,
                    child: const Text('Xoá lọc'),
                  ),
              ],
            ),
            DropdownButton<String>(
              key: const Key('bh07c-history-club-filter'),
              value: clubValue,
              isExpanded: true,
              underline: const SizedBox.shrink(),
              items: [
                const DropdownMenuItem<String>(
                  value: _allClubs,
                  child: Text('Tất cả CLB'),
                ),
                for (final club in clubs.clubs)
                  DropdownMenuItem<String>(
                    value: club.id,
                    child: Text(club.name, overflow: TextOverflow.ellipsis),
                  ),
              ],
              onChanged: clubs.isLoadingClubs
                  ? null
                  : (value) => _changeClub(value == _allClubs ? null : value),
            ),
            if (clubError != null) ...[
              Text(
                'Không tải được danh sách CLB. Vẫn có thể lọc theo ngày.',
                style: TextStyle(fontSize: 12, color: Colors.grey[700]),
              ),
              TextButton(
                key: const Key('bh07c-history-club-retry'),
                onPressed: _loadClubs,
                child: const Text('Thử tải CLB'),
              ),
            ],
            const SizedBox(height: 4),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    key: const Key('bh07c-history-date-filter'),
                    onPressed: _pickDateRange,
                    icon: const Icon(Icons.date_range),
                    label: Text(dateLabel, overflow: TextOverflow.ellipsis),
                  ),
                ),
                if (_from != null) ...[
                  const SizedBox(width: 8),
                  IconButton(
                    key: const Key('bh07c-history-clear-date'),
                    tooltip: 'Xoá lọc ngày',
                    onPressed: _clearDates,
                    icon: const Icon(Icons.close),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _HistorySessionCard extends StatelessWidget {
  final Session session;
  final VoidCallback onTap;

  const _HistorySessionCard({required this.session, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final place = [
      session.venueName,
      session.clubName,
    ].whereType<String>().where((value) => value.isNotEmpty).join(' · ');
    return Card(
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
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Chip(label: Text(session.lifecycleLabel)),
                ],
              ),
              const SizedBox(height: 4),
              Text('⏰ ${formatVietnamRange(session.startsAt, session.endsAt)}'),
              if (place.isNotEmpty) Text('📍 $place'),
              Text(
                '👥 ${session.confirmedCount}/${session.capacity} người đã xác nhận',
                style: TextStyle(color: Colors.grey[700]),
              ),
              const SizedBox(height: 6),
              const Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Text('Xem chi tiết'),
                  Icon(Icons.chevron_right, size: 18),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HistoryMessageCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  const _HistoryMessageCard({
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
              TextButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}
