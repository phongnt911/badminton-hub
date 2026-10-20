import '../models/finance.dart';
import 'money.dart';
import 'time_utils.dart';

/// Định dạng một trường tiền của tổng kết. `null` phải giữ là "—" (chưa có
/// dữ liệu), tuyệt đối không đổi thành 0 vì UI không được tự tính công nợ.
String formatSummaryMoney(int? amountVnd) =>
    amountVnd == null ? '—' : '${formatVnd(amountVnd)} VNĐ';

/// Nội dung sao chép tổng kết, chỉ dùng aggregate server-side.
///
/// - Management-only không thấy phần tài chính.
/// - Finance thấy đúng các trường aggregate; trường NULL hiển thị "—".
/// - Không chứa danh sách người chơi, số điện thoại hay tài khoản ngân hàng.
String buildSessionSummaryText(SessionSummary summary) {
  final lines = <String>[];
  final title = summary.title?.trim();
  lines.add(
    title == null || title.isEmpty
        ? '🏸 Tổng kết buổi chơi'
        : '🏸 Tổng kết: $title',
  );

  final place = [summary.venueName, summary.clubName]
      .whereType<String>()
      .map((value) => value.trim())
      .where((value) => value.isNotEmpty)
      .join(' · ');
  if (place.isNotEmpty) lines.add('📍 $place');

  final time = formatVietnamRange(summary.startsAt, summary.endsAt);
  if (time.isNotEmpty) lines.add('⏰ $time');

  lines.add(
    '👥 Có mặt: ${summary.presentCount} · '
    'Vắng: ${summary.noShowCount} · '
    'Đã xác nhận: ${summary.confirmedCount}',
  );

  if (summary.canViewFinance) {
    lines.add(
      '💰 Tổng chi phí: ${formatSummaryMoney(summary.expensesTotalVnd)}',
    );
    lines.add(
      '🧾 Tổng phải thu: ${formatSummaryMoney(summary.amountDueTotalVnd)}',
    );
    lines.add('✅ Đã thu: ${formatSummaryMoney(summary.totalPaidVnd)}');
    lines.add(
      '⏳ Còn phải thu: ${formatSummaryMoney(summary.outstandingTotalVnd)}',
    );
  }

  return lines.join('\n');
}
