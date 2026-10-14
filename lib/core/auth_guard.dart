import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../screens/auth_screen.dart';

/// Helper kiểm tra trạng thái đăng nhập trước khi thực hiện hành vi yêu cầu tài khoản
///
/// Nếu chưa đăng nhập, tự động mở AuthScreen với returnRoute và trả về `true`
/// nếu người dùng đăng nhập thành công, hoặc `false` nếu hủy/thất bại.
Future<bool> requireAuth(
  BuildContext context, {
  String? returnRoute,
}) async {
  final auth = context.read<AuthProvider>();
  if (auth.isAuthenticated) {
    return true;
  }

  final result = await Navigator.of(context).push<bool>(
    MaterialPageRoute(
      builder: (_) => AuthScreen(returnRoute: returnRoute),
    ),
  );

  return result == true;
}

/// Widget bọc để chỉ hiển thị nội dung khi người dùng đã đăng nhập.
/// Nếu chưa đăng nhập, hiển thị fallback hoặc nút yêu cầu đăng nhập.
class AuthGuard extends StatelessWidget {
  final Widget child;
  final Widget? fallback;

  const AuthGuard({
    super.key,
    required this.child,
    this.fallback,
  });

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    if (auth.isAuthenticated) {
      return child;
    }

    if (fallback != null) {
      return fallback!;
    }

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.lock_outline, size: 48, color: Colors.grey),
            const SizedBox(height: 16),
            const Text(
              'Tính năng yêu cầu đăng nhập',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Vui lòng đăng nhập bằng tài khoản email để sử dụng tính năng này.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: () => requireAuth(context),
              child: const Text('Đăng Nhập Ngay'),
            ),
          ],
        ),
      ),
    );
  }
}
