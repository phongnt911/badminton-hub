import 'package:flutter_test/flutter_test.dart';
import 'package:badminton_hub/core/app_routes.dart';

void main() {
  const uuid = '11111111-2222-3333-4444-555555555555';
  const upper = '11111111-2222-3333-4444-55555555555A';

  test('share link contains configured origin and round trips', () {
    final url = AppRoutes.sessionUrl(
      uuid,
      baseUrl: 'https://badminton-hub.app',
    );
    expect(url, 'https://badminton-hub.app/sessions/$uuid');
    expect(AppRoutes.parse(url)?.id, uuid);
    expect(AppRoutes.parse('//evil.example/sessions/$uuid'), isNull);
    expect(AppRoutes.parse('javascript:/sessions/$uuid'), isNull);
  });

  group('AppRoutes.parse', () {
    test('chấp nhận path nội bộ /sessions/:id', () {
      final route = AppRoutes.parse('/sessions/$uuid');
      expect(route, isNotNull);
      expect(route!.name, 'session');
      expect(route.id, uuid);
    });

    test('chấp nhận URL tuyệt đối với host trong allowlist', () {
      final route = AppRoutes.parse('https://badminton-hub.app/sessions/$uuid');
      expect(route?.name, 'session');
      expect(route?.id, uuid);
    });

    test('chuẩn hoá UUID về chữ thường', () {
      final route = AppRoutes.parse('/sessions/$upper');
      expect(route?.id, upper.toLowerCase());
    });

    test('từ chối host lạ', () {
      expect(
        AppRoutes.parse('https://evil.example.com/sessions/$uuid'),
        isNull,
      );
    });

    test('từ chối scheme lạ', () {
      expect(
        AppRoutes.parse('javascript://badminton-hub.app/sessions/$uuid'),
        isNull,
      );
    });

    test('từ chối path không nằm trong allowlist', () {
      expect(AppRoutes.parse('/admin/$uuid'), isNull);
      expect(AppRoutes.parse('/sessions/$uuid/extra'), isNull);
    });

    test('từ chối id không phải UUID', () {
      expect(AppRoutes.parse('/sessions/not-a-uuid'), isNull);
      expect(AppRoutes.parse('/sessions/123'), isNull);
    });

    test('từ chối query chưa định nghĩa (không nhận token lạ)', () {
      expect(AppRoutes.parse('/sessions/$uuid?token=abc'), isNull);
      expect(AppRoutes.parse('/sessions/$uuid?access_token=abc'), isNull);
    });

    test('chấp nhận query đã định nghĩa', () {
      expect(AppRoutes.parse('/sessions/$uuid?src=zalo')?.name, 'session');
    });

    test('hỗ trợ /clubs/:id', () {
      expect(AppRoutes.parse('/clubs/$uuid')?.name, 'club');
    });

    test('trả null cho chuỗi rỗng/null', () {
      expect(AppRoutes.parse(null), isNull);
      expect(AppRoutes.parse('   '), isNull);
    });
  });

  group('AppRoutes helpers', () {
    test('sessionPath và clubPath', () {
      expect(AppRoutes.sessionPath(uuid), '/sessions/$uuid');
      expect(AppRoutes.clubPath(uuid), '/clubs/$uuid');
    });

    test('isSafeReturnRoute chỉ nhận route nội bộ hợp lệ', () {
      expect(AppRoutes.isSafeReturnRoute('/sessions/$uuid'), isTrue);
      expect(AppRoutes.isSafeReturnRoute('/sessions/$uuid?token=x'), isFalse);
      expect(AppRoutes.isSafeReturnRoute('/nope/$uuid'), isFalse);
      expect(AppRoutes.isSafeReturnRoute(null), isFalse);
    });
  });
}
