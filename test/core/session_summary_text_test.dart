import 'package:flutter_test/flutter_test.dart';

import 'package:badminton_hub/core/session_summary_text.dart';
import 'package:badminton_hub/models/finance.dart';

void main() {
  test('finance copy dùng aggregate server, giữ NULL là dấu gạch', () {
    final summary = SessionSummary(
      sessionId: 's1',
      title: 'Buổi tối',
      clubName: 'CLB A',
      venueName: 'Sân B',
      startsAt: DateTime.utc(2026, 10, 20, 10),
      endsAt: DateTime.utc(2026, 10, 20, 12),
      lifecycle: 'completed',
      canManage: true,
      canViewFinance: true,
      presentCount: 6,
      noShowCount: 1,
      confirmedCount: 7,
      expensesTotalVnd: 450000,
      amountDueTotalVnd: 490000,
      totalPaidVnd: null,
      outstandingTotalVnd: 20000,
    );

    final text = buildSessionSummaryText(summary);

    expect(text, contains('Tổng kết: Buổi tối'));
    expect(text, contains('17:00 - 19:00 20/10/2026'));
    expect(text, contains('Có mặt: 6'));
    expect(text, contains('Vắng: 1'));
    expect(text, contains('Đã xác nhận: 7'));
    expect(text, contains('Tổng chi phí: 450,000 VNĐ'));
    expect(text, contains('Đã thu: —'));
    expect(text, contains('Còn phải thu: 20,000 VNĐ'));
    expect(text, isNot(contains('Đã thu: 0')));
  });

  test('management-only không sao chép phần tài chính', () {
    const summary = SessionSummary(
      sessionId: 's1',
      title: 'Buổi chỉ quản lý',
      canManage: true,
      presentCount: 4,
      confirmedCount: 4,
    );

    final text = buildSessionSummaryText(summary);

    expect(text, contains('Có mặt: 4'));
    expect(text, isNot(contains('Tổng chi phí')));
    expect(text, isNot(contains('Còn phải thu')));
    expect(text, isNot(contains('VNĐ')));
  });

  test('bản sao không chứa contact hay tài khoản ngân hàng', () {
    const summary = SessionSummary(
      sessionId: 's1',
      title: 'Buổi kín',
      canViewFinance: true,
      outstandingTotalVnd: 0,
    );

    final text = buildSessionSummaryText(summary).toLowerCase();

    expect(text, isNot(contains('số điện thoại')));
    expect(text, isNot(contains('ngân hàng')));
    expect(text, isNot(contains('tài khoản')));
    expect(text, isNot(contains('danh sách người')));
  });
}
