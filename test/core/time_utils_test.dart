import 'package:flutter_test/flutter_test.dart';

import 'package:badminton_hub/core/time_utils.dart';

void main() {
  test('ngày Việt Nam đổi sang UTC+7 không phụ thuộc múi giờ thiết bị', () {
    final start = vietnamDayStartUtc(DateTime(2026, 10, 20));
    final end = vietnamDayEndUtc(DateTime(2026, 10, 20));

    expect(start, DateTime.utc(2026, 10, 19, 17));
    expect(start.isUtc, isTrue);
    expect(end, DateTime.utc(2026, 10, 20, 16, 59, 59, 999, 999));
    expect(end.isUtc, isTrue);
    expect(toVietnamCalendarDate(start), DateTime(2026, 10, 20));
  });

  test('mốc ngày Việt Nam bao phủ từ nửa đêm đến hết ngày', () {
    final start = vietnamDayStartUtc(DateTime(2026, 10, 20));
    final end = vietnamDayEndUtc(DateTime(2026, 10, 20));
    final midnight = DateTime.utc(2026, 10, 19, 17);
    final lateNight = DateTime.utc(2026, 10, 20, 16, 59, 59, 999);
    final nextMidnight = DateTime.utc(2026, 10, 20, 17);

    expect(start.isAtSameMomentAs(midnight), isTrue);
    expect(end.isBefore(lateNight), isFalse);
    expect(end.isBefore(nextMidnight), isTrue);
  });
}
