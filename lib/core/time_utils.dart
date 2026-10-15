import 'package:intl/intl.dart';

/// Supabase lưu `timestamptz` theo UTC. Giao diện hiển thị theo giờ Việt Nam (UTC+7).
const Duration kVietnamOffset = Duration(hours: 7);

/// Chuyển một mốc UTC sang giờ Việt Nam để hiển thị.
DateTime toVietnamTime(DateTime value) => value.toUtc().add(kVietnamOffset);

/// Chuyển một mốc giờ Việt Nam (người dùng nhập) sang UTC để lưu/validate.
DateTime vietnamToUtc(DateTime value) => value.subtract(kVietnamOffset);

final DateFormat _dateTimeFormat = DateFormat('HH:mm dd/MM/yyyy');
final DateFormat _dateFormat = DateFormat('dd/MM/yyyy');
final DateFormat _timeFormat = DateFormat('HH:mm');

String formatVietnamDateTime(DateTime? utc) =>
    utc == null ? '' : _dateTimeFormat.format(toVietnamTime(utc));

String formatVietnamDate(DateTime? utc) =>
    utc == null ? '' : _dateFormat.format(toVietnamTime(utc));

String formatVietnamTime(DateTime? utc) =>
    utc == null ? '' : _timeFormat.format(toVietnamTime(utc));

/// "17:30 - 19:30 16/10/2026" (giờ Việt Nam), xử lý cả buổi qua nửa đêm.
String formatVietnamRange(DateTime? startUtc, DateTime? endUtc) {
  if (startUtc == null || endUtc == null) return '';
  final start = toVietnamTime(startUtc);
  final end = toVietnamTime(endUtc);
  final sameDay = start.year == end.year && start.month == end.month && start.day == end.day;
  if (sameDay) {
    return '${_timeFormat.format(start)} - ${_timeFormat.format(end)} ${_dateFormat.format(start)}';
  }
  return '${_dateTimeFormat.format(start)} - ${_dateTimeFormat.format(end)}';
}
