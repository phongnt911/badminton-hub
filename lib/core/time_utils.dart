import 'package:intl/intl.dart';

/// Supabase lưu `timestamptz` theo UTC. Giao diện hiển thị theo giờ Việt Nam (UTC+7).
const Duration kVietnamOffset = Duration(hours: 7);

/// Chuyển một mốc UTC sang giờ Việt Nam để hiển thị.
DateTime toVietnamTime(DateTime value) => value.toUtc().add(kVietnamOffset);

/// Chuyển một mốc giờ Việt Nam (người dùng nhập) sang UTC để lưu/validate.
DateTime vietnamToUtc(DateTime value) => value.subtract(kVietnamOffset);

/// Mốc bắt đầu ngày lịch Việt Nam ở UTC.
///
/// Chỉ đọc các trường year/month/day của [calendarDate]; không dựa vào múi giờ
/// của thiết bị. Ví dụ 20/10/2026 Việt Nam -> 19/10/2026 17:00 UTC.
DateTime vietnamDayStartUtc(DateTime calendarDate) =>
    DateTime.utc(calendarDate.year, calendarDate.month, calendarDate.day)
        .subtract(kVietnamOffset);

/// Mốc cuối ngày lịch Việt Nam ở UTC, bao gồm toàn bộ giây/ms/µs cuối ngày.
DateTime vietnamDayEndUtc(DateTime calendarDate) =>
    DateTime.utc(calendarDate.year, calendarDate.month, calendarDate.day)
        .add(const Duration(days: 1))
        .subtract(kVietnamOffset)
        .subtract(const Duration(microseconds: 1));

/// Ngày lịch Việt Nam (theo các trường year/month/day) từ một instant UTC.
DateTime toVietnamCalendarDate(DateTime utc) {
  final vietnam = toVietnamTime(utc);
  return DateTime(vietnam.year, vietnam.month, vietnam.day);
}

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
