import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide Session;

import 'package:badminton_hub/data/session_repository.dart';
import 'package:badminton_hub/models/session.dart';
import 'package:badminton_hub/providers/auth_provider.dart';
import 'package:badminton_hub/providers/session_provider.dart';

class MockSessionRepository extends Mock implements SessionRepository {}

class FakeAuth extends Mock implements AuthProvider {
  final callbacks = <VoidCallback>[];
  User? user;

  @override
  User? get currentUser => user;

  @override
  void addListener(VoidCallback listener) => callbacks.add(listener);

  @override
  void removeListener(VoidCallback listener) => callbacks.remove(listener);

  void changeUser(String? id) {
    user = id == null
        ? null
        : User(
            id: id,
            appMetadata: {},
            userMetadata: {},
            aud: 'authenticated',
            createdAt: '2026-10-15',
          );
    for (final listener in List<VoidCallback>.of(callbacks)) {
      listener();
    }
  }
}

void main() {
  late MockSessionRepository repo;
  late FakeAuth auth;

  const session = Session(
    id: 's1',
    title: 'Buổi test',
    capacity: 8,
    lifecycle: 'published',
    canManage: false,
    confirmedCount: 2,
  );

  const managedSession = Session(
    id: 's2',
    title: 'Buổi của tôi',
    capacity: 8,
    lifecycle: 'draft',
    canManage: true,
    version: 1,
  );

  setUpAll(() {
    registerFallbackValue(DateTime(2020));
  });

  setUp(() {
    repo = MockSessionRepository();
    auth = FakeAuth();
  });

  SessionProvider buildProvider() {
    return SessionProvider(repository: repo, auth: auth);
  }

  void stubListMySessions(List<Session> result) {
    when(() => repo.listMySessions(
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        )).thenAnswer((_) async => result);
  }

  void stubListPublic(List<Session> result) {
    when(() => repo.listPublicSessions(
          area: any(named: 'area'),
          from: any(named: 'from'),
          to: any(named: 'to'),
          feeMode: any(named: 'feeMode'),
          onlyAvailable: any(named: 'onlyAvailable'),
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        )).thenAnswer((_) async => result);
  }

  final form = SessionFormData(
    venueId: 'v1',
    title: 'Buổi mới',
    startsAt: DateTime.utc(2026, 10, 20, 10),
    endsAt: DateTime.utc(2026, 10, 20, 12),
    capacity: 8,
    courtCount: 2,
  );

  test('khởi tạo rỗng và không loading', () {
    final provider = buildProvider();
    expect(provider.mySessions, isEmpty);
    expect(provider.publicSessions, isEmpty);
    expect(provider.isLoadingMine, isFalse);
    expect(provider.isLoadingPublic, isFalse);
    expect(provider.currentSession, isNull);
    expect(provider.canManagePlayers, isFalse);
    provider.dispose();
  });

  test('fetchPublicSessions truyền bộ lọc và lưu kết quả', () async {
    stubListPublic([session]);
    final provider = buildProvider();

    await provider.fetchPublicSessions(
      filter: const SessionFilter(area: 'Nha Trang', onlyAvailable: true),
    );

    expect(provider.publicSessions, hasLength(1));
    expect(provider.publicSessions.first.id, 's1');
    expect(provider.publicErrorMessage, isNull);

    final captured = verify(() => repo.listPublicSessions(
          area: captureAny(named: 'area'),
          from: captureAny(named: 'from'),
          to: captureAny(named: 'to'),
          feeMode: captureAny(named: 'feeMode'),
          onlyAvailable: captureAny(named: 'onlyAvailable'),
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        )).captured;
    expect(captured, contains('Nha Trang'));
    expect(captured, contains(true));
    provider.dispose();
  });

  test('lỗi domain được ánh xạ sang tiếng Việt, không lộ chi tiết DB', () async {
    when(() => repo.listPublicSessions(
          area: any(named: 'area'),
          from: any(named: 'from'),
          to: any(named: 'to'),
          feeMode: any(named: 'feeMode'),
          onlyAvailable: any(named: 'onlyAvailable'),
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        )).thenThrow(Exception('PostgrestException(FORBIDDEN: raw pg detail)'));

    final provider = buildProvider();
    await provider.fetchPublicSessions();

    expect(provider.publicErrorMessage,
        'Bạn không có quyền thực hiện thao tác này.');
    provider.dispose();
  });

  test('fetchMySessions lỗi rồi retry phục hồi', () async {
    when(() => repo.listMySessions(
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        )).thenThrow(Exception('FORBIDDEN: nope'));

    final provider = buildProvider();
    await provider.fetchMySessions();
    expect(provider.mySessions, isEmpty);
    expect(provider.myErrorMessage, isNotNull);

    stubListMySessions([managedSession]);
    await provider.fetchMySessions();
    expect(provider.myErrorMessage, isNull);
    expect(provider.mySessions, hasLength(1));
    provider.dispose();
  });

  test('fetchSessionDetail tải người đăng ký khi có quyền quản lý', () async {
    when(() => repo.getSessionDetail('s2')).thenAnswer((_) async => managedSession);
    when(() => repo.listSessionPlayers('s2',
            limit: any(named: 'limit'), offset: any(named: 'offset')))
        .thenAnswer((_) async => [
              const SessionPlayer(id: 'p1', displayName: 'An', phoneNumber: '0900'),
            ]);

    final provider = buildProvider();
    await provider.fetchSessionDetail('s2');

    expect(provider.currentSession?.id, 's2');
    expect(provider.canManagePlayers, isTrue);
    expect(provider.currentPlayers, hasLength(1));
    provider.dispose();
  });

  test('fetchSessionDetail KHÔNG tải người đăng ký khi là khách/không quản lý',
      () async {
    when(() => repo.getSessionDetail('s1')).thenAnswer((_) async => session);

    final provider = buildProvider();
    await provider.fetchSessionDetail('s1');

    expect(provider.currentSession?.id, 's1');
    expect(provider.canManagePlayers, isFalse);
    verifyNever(() => repo.listSessionPlayers('s1',
        limit: any(named: 'limit'), offset: any(named: 'offset')));
    provider.dispose();
  });

  test('createSession lỗi rồi retry dùng lại cùng request_id; đổi payload tạo khoá mới',
      () async {
    stubListMySessions([]);
    final keys = <String>[];
    var attempts = 0;
    when(() => repo.createSession(
          requestId: any(named: 'requestId'),
          venueId: any(named: 'venueId'),
          title: any(named: 'title'),
          startsAt: any(named: 'startsAt'),
          endsAt: any(named: 'endsAt'),
          capacity: any(named: 'capacity'),
          courtCount: any(named: 'courtCount'),
          clubId: any(named: 'clubId'),
          description: any(named: 'description'),
          levelRequirement: any(named: 'levelRequirement'),
          visibility: any(named: 'visibility'),
          approvalMode: any(named: 'approvalMode'),
          feeMode: any(named: 'feeMode'),
          memberFeeVnd: any(named: 'memberFeeVnd'),
          guestFeeVnd: any(named: 'guestFeeVnd'),
          registrationDeadline: any(named: 'registrationDeadline'),
          cancellationDeadline: any(named: 'cancellationDeadline'),
        )).thenAnswer((invocation) async {
      keys.add(invocation.namedArguments[#requestId] as String);
      attempts++;
      if (attempts == 1) throw Exception('timeout');
      return managedSession;
    });

    final provider = buildProvider();
    final first = await provider.createSession(form);
    expect(first, isNull);
    expect(provider.submitErrorMessage, isNotNull);

    final second = await provider.createSession(form);
    expect(second, isNotNull);
    expect(keys.first, keys[1], reason: 'retry cùng payload phải dùng lại UUID');

    final third = await provider.createSession(
      SessionFormData(
        venueId: 'v1',
        title: 'Buổi khác',
        startsAt: DateTime.utc(2026, 10, 21, 10),
        endsAt: DateTime.utc(2026, 10, 21, 12),
        capacity: 8,
        courtCount: 2,
      ),
    );
    expect(third, isNotNull);
    expect(keys[2], isNot(keys[1]), reason: 'payload mới phải có UUID mới');
    provider.dispose();
  });

  test('publishSession gửi action publish và làm mới danh sách', () async {
    stubListMySessions([managedSession]);
    when(() => repo.setSessionLifecycle(
          requestId: any(named: 'requestId'),
          sessionId: any(named: 'sessionId'),
          action: any(named: 'action'),
        )).thenAnswer((_) async => managedSession);

    final provider = buildProvider();
    final result = await provider.publishSession('s2');

    expect(result, isNotNull);
    verify(() => repo.setSessionLifecycle(
          requestId: any(named: 'requestId'),
          sessionId: 's2',
          action: 'publish',
        )).called(1);
    verify(() => repo.listMySessions(
        limit: any(named: 'limit'), offset: any(named: 'offset'))).called(1);
    provider.dispose();
  });

  test('đổi người dùng/đăng xuất xoá state riêng tư', () async {
    stubListMySessions([managedSession]);
    stubListPublic([session]);
    when(() => repo.getSessionDetail('s2')).thenAnswer((_) async => managedSession);

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchMySessions();
    await provider.fetchPublicSessions();
    await provider.fetchSessionDetail('s2');
    expect(provider.mySessions, isNotEmpty);
    expect(provider.currentSession, isNotNull);

    auth.changeUser(null);

    expect(provider.mySessions, isEmpty);
    expect(provider.currentSession, isNull);
    expect(provider.publicSessions, isEmpty);
    expect(provider.submitErrorMessage, isNull);
    provider.dispose();
  });
}
