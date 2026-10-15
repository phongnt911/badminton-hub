/// Route tài nguyên nội bộ, ví dụ `/sessions/:id` (PD-01).
///
/// Quyết định routing: giữ `Navigator`/`MaterialPageRoute` hiện có và KHÔNG thêm
/// router package (docs/09: "chưa thêm SDK map/router tự động"). Lớp này chỉ
/// chuẩn hoá/kiểm hợp lệ link tài nguyên trước khi điều hướng nội bộ; deep link
/// cấp hệ điều hành (App Links/Universal Links) cần cấu hình tên miền + SDK
/// riêng nên chưa bật trong lượt này.
class AppRoute {
  /// 'session' hoặc 'club'.
  final String name;

  /// Tham số path đã kiểm hợp lệ (ví dụ `{'id': 'uuid'}`).
  final Map<String, String> params;

  const AppRoute(this.name, this.params);

  String? get id => params['id'];
}

class AppRoutes {
  AppRoutes._();

  /// Host được chấp nhận cho link tài nguyên.
  static const Set<String> allowedHosts = {
    'badminton-hub.app',
    'app.badminton-hub.vn',
  };

  static const Set<String> allowedSchemes = {'https', 'http'};

  /// Chỉ chấp nhận query đã định nghĩa; key khác ⇒ link không hợp lệ.
  static const Set<String> allowedQueryKeys = {'src', 'invite'};

  static final RegExp _uuid = RegExp(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
  );

  static bool isUuid(String? value) => value != null && _uuid.hasMatch(value);

  /// Sinh path nội bộ cho buổi chơi.
  static String sessionPath(String sessionId) => '/sessions/$sessionId';

  /// Sinh path nội bộ cho CLB.
  static String clubPath(String clubId) => '/clubs/$clubId';

  /// Phân tích một link tài nguyên thành [AppRoute]. Trả `null` nếu không hợp lệ.
  ///
  /// Chấp nhận: path nội bộ (`/sessions/:id`) hoặc URL tuyệt đối có scheme và
  /// host nằm trong allowlist. Query lạ hoặc path lạ đều bị từ chối.
  static AppRoute? parse(String? raw) {
    if (raw == null) return null;
    final trimmed = raw.trim();
    if (trimmed.isEmpty) return null;

    final uri = Uri.tryParse(trimmed);
    if (uri == null) return null;

    if (uri.hasScheme && uri.host.isNotEmpty) {
      if (!allowedSchemes.contains(uri.scheme.toLowerCase())) return null;
      if (!allowedHosts.contains(uri.host.toLowerCase())) return null;
    }

    for (final key in uri.queryParameters.keys) {
      if (!allowedQueryKeys.contains(key)) return null;
    }

    final segments = uri.pathSegments.where((s) => s.isNotEmpty).toList();
    if (segments.length != 2) return null;
    final id = segments[1];
    if (!isUuid(id)) return null;

    switch (segments[0].toLowerCase()) {
      case 'sessions':
        return AppRoute('session', {'id': id.toLowerCase()});
      case 'clubs':
        return AppRoute('club', {'id': id.toLowerCase()});
      default:
        return null;
    }
  }

  /// Link có phải return route nội bộ hợp lệ không (dùng sau đăng nhập).
  static bool isSafeReturnRoute(String? raw) => parse(raw) != null;
}
