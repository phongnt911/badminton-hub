import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_constants.dart';
import '../core/time_utils.dart';
import '../data/venue_repository.dart';
import '../models/session.dart';
import '../models/venue.dart';
import '../providers/club_provider.dart';
import '../providers/session_provider.dart';

/// Form tạo/sửa buổi chơi. Người dùng nhập theo giờ Việt Nam; giá trị gửi đi ở UTC.
class SessionFormScreen extends StatefulWidget {
  final Session? session;

  const SessionFormScreen({super.key, this.session});

  bool get isEdit => session != null;

  @override
  State<SessionFormScreen> createState() => _SessionFormScreenState();
}

class _SessionFormScreenState extends State<SessionFormScreen> {
  final VenueRepository _venueRepository = VenueRepository();
  final _formKey = GlobalKey<FormState>();

  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _levelController = TextEditingController();
  final _capacityController = TextEditingController(text: '8');
  final _courtController = TextEditingController(text: '2');
  final _memberFeeController = TextEditingController();
  final _guestFeeController = TextEditingController();

  List<Venue> _venues = [];
  bool _loadingVenues = true;
  String? _venueId;
  String? _clubId;
  String _visibility = 'unlisted';
  String _approvalMode = 'host_approval';
  String _feeMode = 'split_actual';

  late DateTime _date;
  late TimeOfDay _startTime;
  late TimeOfDay _endTime;
  String? _formError;

  @override
  void initState() {
    super.initState();
    final session = widget.session;
    if (session != null) {
      _titleController.text = session.title;
      _descriptionController.text = session.description ?? '';
      _levelController.text = session.levelRequirement ?? '';
      _capacityController.text = session.capacity.toString();
      _courtController.text = session.courtCount.toString();
      _memberFeeController.text = session.memberFeeVnd?.toString() ?? '';
      _guestFeeController.text = session.guestFeeVnd?.toString() ?? '';
      _venueId = session.venueId;
      _clubId = session.clubId;
      _visibility = session.visibility;
      _approvalMode = session.approvalMode;
      _feeMode = session.feeMode;
      final startVn = session.startsAt != null
          ? toVietnamTime(session.startsAt!)
          : DateTime.now().add(const Duration(days: 1));
      final endVn = session.endsAt != null
          ? toVietnamTime(session.endsAt!)
          : startVn.add(const Duration(hours: 2));
      _date = DateTime(startVn.year, startVn.month, startVn.day);
      _startTime = TimeOfDay(hour: startVn.hour, minute: startVn.minute);
      _endTime = TimeOfDay(hour: endVn.hour, minute: endVn.minute);
    } else {
      final tomorrow = DateTime.now().add(const Duration(days: 1));
      _date = DateTime(tomorrow.year, tomorrow.month, tomorrow.day);
      _startTime = const TimeOfDay(hour: 17, minute: 30);
      _endTime = const TimeOfDay(hour: 19, minute: 30);
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadVenues();
      final clubProvider = context.read<ClubProvider>();
      if (clubProvider.clubs.isEmpty) clubProvider.fetchClubs();
    });
  }

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    _levelController.dispose();
    _capacityController.dispose();
    _courtController.dispose();
    _memberFeeController.dispose();
    _guestFeeController.dispose();
    super.dispose();
  }

  Future<void> _loadVenues() async {
    try {
      final venues = await _venueRepository.listActiveVenues();
      if (!mounted) return;
      setState(() {
        _venues = venues;
        _loadingVenues = false;
        _venueId ??= venues.isNotEmpty ? venues.first.id : null;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loadingVenues = false);
    }
  }

  /// Ghép ngày + giờ Việt Nam thành mốc UTC.
  DateTime _toUtc(DateTime date, TimeOfDay time, {int extraDays = 0}) {
    final vn = DateTime(
      date.year,
      date.month,
      date.day + extraDays,
      time.hour,
      time.minute,
    );
    return vietnamToUtc(vn);
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      firstDate: DateTime.now().subtract(const Duration(days: 1)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      initialDate: _date,
    );
    if (picked != null) setState(() => _date = picked);
  }

  Future<void> _pickTime(bool isStart) async {
    final picked = await showTimePicker(
      context: context,
      initialTime: isStart ? _startTime : _endTime,
    );
    if (picked == null) return;
    setState(() {
      if (isStart) {
        _startTime = picked;
      } else {
        _endTime = picked;
      }
    });
  }

  Future<void> _submit() async {
    setState(() => _formError = null);
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_venueId == null) {
      setState(() => _formError = 'Vui lòng chọn sân.');
      return;
    }

    var startsAt = _toUtc(_date, _startTime);
    var endsAt = _toUtc(_date, _endTime);
    if (!endsAt.isAfter(startsAt)) {
      // Qua nửa đêm: giờ kết thúc thuộc ngày hôm sau.
      endsAt = _toUtc(_date, _endTime, extraDays: 1);
    }
    if (!endsAt.isAfter(startsAt)) {
      setState(() => _formError = 'Giờ kết thúc phải sau giờ bắt đầu.');
      return;
    }
    if (!widget.isEdit && !startsAt.isAfter(DateTime.now().toUtc())) {
      setState(() => _formError = 'Thời gian bắt đầu phải ở tương lai.');
      return;
    }

    final form = SessionFormData(
      venueId: _venueId!,
      title: _titleController.text.trim(),
      startsAt: startsAt,
      endsAt: endsAt,
      capacity: int.tryParse(_capacityController.text.trim()) ?? 0,
      courtCount: int.tryParse(_courtController.text.trim()) ?? 0,
      clubId: _clubId,
      description: _descriptionController.text.trim().isEmpty
          ? null
          : _descriptionController.text.trim(),
      levelRequirement: _levelController.text.trim().isEmpty
          ? null
          : _levelController.text.trim(),
      visibility: _visibility,
      approvalMode: _approvalMode,
      feeMode: _feeMode,
      memberFeeVnd: _feeMode == 'fixed'
          ? int.tryParse(_memberFeeController.text.trim())
          : null,
      guestFeeVnd: _feeMode == 'fixed'
          ? int.tryParse(_guestFeeController.text.trim())
          : null,
    );

    final provider = context.read<SessionProvider>();
    final Session? result = widget.isEdit
        ? await provider.updateSession(
            form,
            sessionId: widget.session!.id,
            version: widget.session!.version ?? 1,
          )
        : await provider.createSession(form);

    if (!mounted) return;
    if (result != null) {
      Navigator.of(context).pop(result);
    } else {
      setState(() => _formError =
          provider.submitErrorMessage ?? 'Không lưu được buổi chơi.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<SessionProvider>();
    final clubs = context.watch<ClubProvider>().clubs;
    final submitting = provider.isSubmitting;

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEdit ? 'Sửa buổi chơi' : 'Tạo buổi chơi'),
        backgroundColor: AppConstants.primaryColor,
        foregroundColor: Colors.white,
      ),
      body: _loadingVenues
          ? const Center(child: CircularProgressIndicator())
          : Form(
              key: _formKey,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  TextFormField(
                    key: const Key('session_title'),
                    controller: _titleController,
                    decoration: const InputDecoration(
                      labelText: 'Tiêu đề buổi chơi',
                      border: OutlineInputBorder(),
                    ),
                    validator: (v) => (v == null || v.trim().isEmpty)
                        ? 'Nhập tiêu đề buổi chơi'
                        : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _descriptionController,
                    decoration: const InputDecoration(
                      labelText: 'Mô tả (không bắt buộc)',
                      border: OutlineInputBorder(),
                    ),
                    maxLines: 2,
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    key: const Key('session_venue'),
                    initialValue: _venueId,
                    decoration: const InputDecoration(
                      labelText: 'Sân',
                      border: OutlineInputBorder(),
                    ),
                    items: _venues
                        .map((v) => DropdownMenuItem(
                              value: v.id,
                              child: Text(
                                v.area != null ? '${v.name} · ${v.area}' : v.name,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ))
                        .toList(),
                    onChanged: (value) => setState(() => _venueId = value),
                    validator: (v) => v == null ? 'Chọn sân' : null,
                  ),
                  if (_venues.isEmpty)
                    const Padding(
                      padding: EdgeInsets.only(top: 8),
                      child: Text(
                        'Chưa có sân nào đang hoạt động.',
                        style: TextStyle(color: Colors.red),
                      ),
                    ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String?>(
                    initialValue: _clubId,
                    decoration: const InputDecoration(
                      labelText: 'CLB (không bắt buộc)',
                      border: OutlineInputBorder(),
                    ),
                    items: [
                      const DropdownMenuItem(value: null, child: Text('Không gắn CLB')),
                      ...clubs
                          .where((c) => c.canManageMembers)
                          .map((c) => DropdownMenuItem(
                                value: c.id,
                                child: Text(c.name, overflow: TextOverflow.ellipsis),
                              )),
                    ],
                    onChanged: (value) => setState(() => _clubId = value),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          key: const Key('session_pick_date'),
                          onPressed: _pickDate,
                          icon: const Icon(Icons.calendar_today),
                          label: Text(formatVietnamDate(_toUtc(_date, _startTime))),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _pickTime(true),
                          icon: const Icon(Icons.schedule),
                          label: Text('Bắt đầu: ${_startTime.format(context)}'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _pickTime(false),
                          icon: const Icon(Icons.schedule),
                          label: Text('Kết thúc: ${_endTime.format(context)}'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: _capacityController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Sức chứa',
                            border: OutlineInputBorder(),
                          ),
                          validator: (v) {
                            final n = int.tryParse(v?.trim() ?? '');
                            if (n == null || n < 1 || n > 200) {
                              return '1..200';
                            }
                            return null;
                          },
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextFormField(
                          controller: _courtController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Số sân',
                            border: OutlineInputBorder(),
                          ),
                          validator: (v) {
                            final n = int.tryParse(v?.trim() ?? '');
                            if (n == null || n < 1 || n > 50) return '1..50';
                            return null;
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: _visibility,
                    decoration: const InputDecoration(
                      labelText: 'Hiển thị',
                      border: OutlineInputBorder(),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'private', child: Text('Riêng tư')),
                      DropdownMenuItem(value: 'unlisted', child: Text('Có link')),
                      DropdownMenuItem(value: 'public', child: Text('Công khai')),
                    ],
                    onChanged: (v) => setState(() => _visibility = v ?? 'unlisted'),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    key: const Key('session_fee_mode'),
                    initialValue: _feeMode,
                    decoration: const InputDecoration(
                      labelText: 'Cách thu phí',
                      border: OutlineInputBorder(),
                    ),
                    items: const [
                      DropdownMenuItem(
                        value: 'split_actual',
                        child: Text('Chia theo chi phí thực tế'),
                      ),
                      DropdownMenuItem(value: 'fixed', child: Text('Phí cố định')),
                    ],
                    onChanged: (v) => setState(() => _feeMode = v ?? 'split_actual'),
                  ),
                  if (_feeMode == 'fixed') ...[
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _memberFeeController,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(
                              labelText: 'Phí thành viên (VNĐ)',
                              border: OutlineInputBorder(),
                            ),
                            validator: (v) =>
                                (int.tryParse(v?.trim() ?? '') ?? -1) < 0
                                    ? 'Nhập số ≥ 0'
                                    : null,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: TextFormField(
                            controller: _guestFeeController,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(
                              labelText: 'Phí khách (VNĐ)',
                              border: OutlineInputBorder(),
                            ),
                            validator: (v) =>
                                (int.tryParse(v?.trim() ?? '') ?? -1) < 0
                                    ? 'Nhập số ≥ 0'
                                    : null,
                          ),
                        ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: _approvalMode,
                    decoration: const InputDecoration(
                      labelText: 'Duyệt đăng ký',
                      border: OutlineInputBorder(),
                    ),
                    items: const [
                      DropdownMenuItem(
                        value: 'host_approval',
                        child: Text('Chủ buổi duyệt'),
                      ),
                      DropdownMenuItem(
                        value: 'auto_confirm',
                        child: Text('Tự động xác nhận'),
                      ),
                    ],
                    onChanged: (v) =>
                        setState(() => _approvalMode = v ?? 'host_approval'),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _levelController,
                    decoration: const InputDecoration(
                      labelText: 'Trình độ (không bắt buộc)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  if (_formError != null) ...[
                    const SizedBox(height: 12),
                    Text(_formError!, style: const TextStyle(color: Colors.red)),
                  ],
                  const SizedBox(height: 20),
                  ElevatedButton(
                    key: const Key('session_submit'),
                    onPressed: submitting ? null : _submit,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppConstants.primaryColor,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    child: submitting
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor:
                                  AlwaysStoppedAnimation<Color>(Colors.white),
                            ),
                          )
                        : Text(
                            widget.isEdit ? 'Lưu thay đổi' : 'Tạo buổi (bản nháp)',
                            style: const TextStyle(
                                fontSize: 16, fontWeight: FontWeight.bold),
                          ),
                  ),
                ],
              ),
            ),
    );
  }
}
