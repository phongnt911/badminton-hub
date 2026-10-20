import 'package:intl/intl.dart';

final NumberFormat _vndFormat = NumberFormat('#,###');

/// Định dạng số tiền VNĐ (số nguyên) theo nhóm nghìn, ví dụ `1500000` →
/// `1,500,000`. Dùng chung cho các màn tài chính BH-06C.
String formatVnd(int amount) => _vndFormat.format(amount);

/// Đọc số tiền người dùng nhập: bỏ mọi ký tự không phải chữ số.
/// Trả `null` khi không có chữ số nào.
int? parseVnd(String raw) {
  final digits = raw.replaceAll(RegExp(r'[^0-9]'), '');
  if (digits.isEmpty) return null;
  return int.tryParse(digits);
}
