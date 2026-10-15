import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_constants.dart';
import '../data/venue_repository.dart';
import '../models/session.dart';
import '../providers/session_provider.dart';
import 'home_screen.dart' show SessionCard;
import 'session_detail_screen.dart';

/// Khám phá buổi công khai (PD-02): lọc thủ công theo khu vực, thời gian,
/// còn chỗ và cách thu phí. Không yêu cầu GPS hay SDK bản đồ.
class PublicSessionsScreen extends StatefulWidget {
  const PublicSessionsScreen({super.key});

  @override
  State<PublicSessionsScreen> createState() => _PublicSessionsScreenState();
}

class _PublicSessionsScreenState extends State<PublicSessionsScreen> {
  final VenueRepository _venueRepository = VenueRepository();
  List<String> _areas = [];
  SessionFilter _filter = const SessionFilter();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadAreas();
      _apply(_filter);
    });
  }

  Future<void> _loadAreas() async {
    try {
      final venues = await _venueRepository.listActiveVenues();
      final areas = venues
          .map((v) => v.area)
          .whereType<String>()
          .where((a) => a.trim().isNotEmpty)
          .toSet()
          .toList()
        ..sort();
      if (mounted) setState(() => _areas = areas);
    } catch (_) {
      // Không chặn khám phá nếu không tải được danh sách khu vực.
    }
  }

  void _apply(SessionFilter filter) {
    setState(() => _filter = filter);
    context.read<SessionProvider>().fetchPublicSessions(filter: filter);
  }

  Future<void> _pickDateRange() async {
    final now = DateTime.now();
    final picked = await showDateRangePicker(
      context: context,
      firstDate: now.subtract(const Duration(days: 1)),
      lastDate: now.add(const Duration(days: 120)),
      initialDateRange: (_filter.from != null && _filter.to != null)
          ? DateTimeRange(start: _filter.from!, end: _filter.to!)
          : null,
    );
    if (picked == null) return;
    _apply(_filter.copyWith(from: picked.start, to: picked.end));
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<SessionProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Khám phá buổi công khai'),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          _FilterBar(
            filter: _filter,
            areas: _areas,
            onChanged: _apply,
            onPickDate: _pickDateRange,
          ),
          const Divider(height: 1),
          Expanded(child: _buildList(provider)),
        ],
      ),
    );
  }

  Widget _buildList(SessionProvider provider) {
    if (provider.isLoadingPublic && provider.publicSessions.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (provider.publicErrorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(provider.publicErrorMessage!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.red)),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () => _apply(_filter),
                child: const Text('Thử lại'),
              ),
            ],
          ),
        ),
      );
    }
    if (provider.publicSessions.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text('Không có buổi công khai nào khớp bộ lọc.'),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: () async => _apply(_filter),
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: provider.publicSessions
            .map((s) => SessionCard(
                  session: s,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => SessionDetailScreen(sessionId: s.id),
                    ),
                  ),
                ))
            .toList(),
      ),
    );
  }
}

class _FilterBar extends StatelessWidget {
  final SessionFilter filter;
  final List<String> areas;
  final void Function(SessionFilter) onChanged;
  final VoidCallback onPickDate;

  const _FilterBar({
    required this.filter,
    required this.areas,
    required this.onChanged,
    required this.onPickDate,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String?>(
                  key: const Key('filter_area'),
                  initialValue: filter.area,
                  decoration: const InputDecoration(
                    labelText: 'Khu vực',
                    isDense: true,
                    border: OutlineInputBorder(),
                  ),
                  items: [
                    const DropdownMenuItem(value: null, child: Text('Tất cả')),
                    ...areas.map(
                      (a) => DropdownMenuItem(value: a, child: Text(a)),
                    ),
                  ],
                  onChanged: (value) => onChanged(
                    value == null
                        ? filter.copyWith(clearArea: true)
                        : filter.copyWith(area: value),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: DropdownButtonFormField<String?>(
                  key: const Key('filter_fee_mode'),
                  initialValue: filter.feeMode,
                  decoration: const InputDecoration(
                    labelText: 'Cách thu phí',
                    isDense: true,
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: null, child: Text('Tất cả')),
                    DropdownMenuItem(value: 'fixed', child: Text('Phí cố định')),
                    DropdownMenuItem(
                      value: 'split_actual',
                      child: Text('Chia thực tế'),
                    ),
                  ],
                  onChanged: (value) => onChanged(
                    value == null
                        ? filter.copyWith(clearFeeMode: true)
                        : filter.copyWith(feeMode: value),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: onPickDate,
                  icon: const Icon(Icons.date_range),
                  label: Text(
                    filter.from != null && filter.to != null
                        ? 'Đã chọn khoảng ngày'
                        : 'Chọn khoảng ngày',
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Row(
                children: [
                  const Text('Còn chỗ'),
                  Switch(
                    key: const Key('filter_available'),
                    value: filter.onlyAvailable,
                    onChanged: (value) =>
                        onChanged(filter.copyWith(onlyAvailable: value)),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
