/// Ánh xạ lỗi domain từ RPC sang thông điệp tiếng Việt ổn định.
///
/// Không hiển thị chi tiết kỹ thuật của Postgres cho người dùng (ADR-12/X6).
const Map<String, String> kDomainErrorMessages = {
  'UNAUTHENTICATED': 'Bạn cần đăng nhập để thực hiện thao tác này.',
  'FORBIDDEN': 'Bạn không có quyền thực hiện thao tác này.',
  'NOT_FOUND': 'Không tìm thấy dữ liệu yêu cầu.',
  'INVALID_INPUT': 'Dữ liệu chưa hợp lệ. Vui lòng kiểm tra lại.',
  'INVALID_STATE': 'Trạng thái hiện tại không cho phép thao tác này.',
  'VERSION_CONFLICT': 'Buổi chơi đã được thay đổi ở nơi khác. Vui lòng tải lại.',
  'IDEMPOTENCY_CONFLICT': 'Yêu cầu bị trùng khoá với dữ liệu khác.',
  'CAPACITY_FULL': 'Buổi chơi đã đủ chỗ.',
  'DUPLICATE_PARTICIPANT': 'Người chơi đã đăng ký buổi này.',
  'DEADLINE_PASSED': 'Đã quá hạn đăng ký/huỷ.',
  'PAYMENT_EXCEEDS_OUTSTANDING': 'Số tiền vượt quá khoản còn phải thu.',
  'NO_BILLABLE_PLAYERS': 'Chưa có người chơi nào để tính phí.',
  'BILLING_NOT_FINALIZED': 'Buổi chơi chưa chốt phí.',
  'BILLING_STALE': 'Phí đã lỗi thời so với thay đổi mới nhất.',
  'INVITATION_REQUIRED': 'Cần lời mời hợp lệ để thực hiện.',
  'INVITATION_EXPIRED': 'Lời mời đã hết hạn.',
  'INVITATION_REVOKED': 'Lời mời đã bị thu hồi.',
};

const String kUnknownErrorMessage =
    'Đã xảy ra lỗi. Vui lòng thử lại sau.';

/// Trả về thông điệp tiếng Việt cho một lỗi bất kỳ, ưu tiên mã lỗi domain.
String domainErrorMessage(Object error) {
  final text = error.toString();
  final match = RegExp(r'\b([A-Z][A-Z_]{3,})\b').firstMatch(text);
  final code = match?.group(1);
  if (code != null && kDomainErrorMessages.containsKey(code)) {
    return kDomainErrorMessages[code]!;
  }
  return kUnknownErrorMessage;
}
