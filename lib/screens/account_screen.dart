import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/app_constants.dart';
import '../providers/auth_provider.dart';
import 'auth_screen.dart';

/// Màn hình Tài khoản: Quản lý hồ sơ, đổi mật khẩu và đăng xuất
class AccountScreen extends StatefulWidget {
  const AccountScreen({super.key});

  @override
  State<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends State<AccountScreen> {
  void _openAuthScreen() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AuthScreen(
          onSuccess: () {
            // Đã đăng nhập xong, màn hình sẽ tự rebuild theo AuthProvider
          },
        ),
      ),
    );
  }

  void _showChangePasswordDialog() {
    final passwordCtrl = TextEditingController();
    final confirmCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Đổi Mật Khẩu'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: passwordCtrl,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Mật khẩu mới (tối thiểu 6 ký tự)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: confirmCtrl,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Xác nhận lại mật khẩu',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Hủy'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppConstants.primaryColor,
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              final newPass = passwordCtrl.text;
              final confirmPass = confirmCtrl.text;

              if (newPass.length < 6) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Mật khẩu mới phải có ít nhất 6 ký tự.')),
                );
                return;
              }
              if (newPass != confirmPass) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Mật khẩu xác nhận không khớp.')),
                );
                return;
              }

              Navigator.of(ctx).pop();
              final auth = context.read<AuthProvider>();
              final success = await auth.updatePassword(newPass);

              if (!mounted) return;
              if (success) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(auth.successMessage ?? 'Đổi mật khẩu thành công!'),
                    backgroundColor: AppConstants.primaryColor,
                  ),
                );
              } else {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(auth.errorMessage ?? 'Đổi mật khẩu thất bại.'),
                    backgroundColor: Colors.red,
                  ),
                );
              }
            },
            child: const Text('Lưu Mật Khẩu'),
          ),
        ],
      ),
    );
  }

  void _confirmLogout() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Xác Nhận Đăng Xuất'),
        content: const Text('Bạn có chắc chắn muốn đăng xuất khỏi tài khoản không?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Hủy'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red, foregroundColor: Colors.white),
            onPressed: () async {
              Navigator.of(ctx).pop();
              await context.read<AuthProvider>().logout();
            },
            child: const Text('Đăng Xuất'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.currentUser;
    final isAuthenticated = auth.isAuthenticated;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Tài Khoản Của Tôi'),
      ),
      body: auth.isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20.0),
              child: !isAuthenticated
                  ? _buildGuestView()
                  : _buildAuthenticatedView(user!),
            ),
    );
  }

  Widget _buildGuestView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 32),
        const CircleAvatar(
          radius: 48,
          backgroundColor: Color(0xFFE8F5E9),
          child: Icon(Icons.person_outline, size: 48, color: AppConstants.primaryColor),
        ),
        const SizedBox(height: 20),
        const Text(
          'Bạn đang xem dưới dạng khách',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        const Text(
          'Bạn có thể tự do xem danh sách sân và các kèo công khai. Đăng nhập để tạo buổi chơi, quản lý CLB hoặc đăng ký slot nhanh chóng.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey, height: 1.4),
        ),
        const SizedBox(height: 32),
        ElevatedButton.icon(
          key: const Key('account_login_button'),
          onPressed: _openAuthScreen,
          icon: const Icon(Icons.login),
          label: const Text('Đăng Nhập / Đăng Ký'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppConstants.primaryColor,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        ),
      ],
    );
  }

  Widget _buildAuthenticatedView(dynamic user) {
    final email = user.email ?? 'Chưa có email';
    final metadata = user.userMetadata ?? {};
    final displayName = metadata['display_name'] ?? metadata['name'] ?? 'Thành viên Badminton Hub';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          elevation: 2,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: Padding(
            padding: const EdgeInsets.all(20.0),
            child: Column(
              children: [
                const CircleAvatar(
                  radius: 40,
                  backgroundColor: AppConstants.primaryColor,
                  child: Icon(Icons.person, size: 48, color: Colors.white),
                ),
                const SizedBox(height: 12),
                Text(
                  displayName.toString(),
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  email,
                  style: const TextStyle(color: Colors.grey),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.green.shade50,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Text(
                    'Đã xác thực',
                    style: TextStyle(color: Colors.green, fontSize: 12, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),
        const Text(
          'Cài đặt & Bảo mật',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        Card(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Column(
            children: [
              ListTile(
                leading: const Icon(Icons.lock_reset, color: AppConstants.primaryColor),
                title: const Text('Đổi mật khẩu'),
                trailing: const Icon(Icons.chevron_right),
                onTap: _showChangePasswordDialog,
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(Icons.logout, color: Colors.red),
                title: const Text('Đăng xuất', style: TextStyle(color: Colors.red)),
                trailing: const Icon(Icons.chevron_right),
                onTap: _confirmLogout,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
