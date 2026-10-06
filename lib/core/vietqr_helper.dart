class VietQRHelper {
  /// Sinh URL ảnh VietQR chuẩn mở NAPAS không cần đăng ký tài khoản cổng thanh toán
  static String generateQrUrl({
    required String bankCode, // Ví dụ: 'MB' hoặc 'VCB' hoặc 'ICB' (VietinBank)
    required String accountNumber, // Số tài khoản chủ kèo
    required int amount, // Số tiền cần chia (VD: 40000)
    required String description, // Nội dung chuyển khoản
    required String accountName, // Tên chủ tài khoản
  }) {
    final encodedNote = Uri.encodeComponent(description);
    final encodedName = Uri.encodeComponent(accountName);
    return 'https://img.vietqr.io/image/$bankCode-$accountNumber-compact2.png'
        '?amount=$amount&addInfo=$encodedNote&accountName=$encodedName';
  }
}
