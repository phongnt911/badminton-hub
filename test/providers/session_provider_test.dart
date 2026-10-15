import 'dart:async';

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
    when(
      () => repo.listMySessions(
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) async => result);
  }

  void stubListPublic(List<Session> result) {
    when(
      () => repo.listPublicSessions(
        area: any(named: 'area'),
        from: any(named: 'from'),
        to: any(named: 'to'),
        feeMode: any(named: 'feeMode'),
        onlyAvailable: any(named: 'onlyAvailable'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) async => result);
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

    final captured = verify(
      () => repo.listPublicSessions(
        area: captureAny(named: 'area'),
        from: captureAny(named: 'from'),
        to: captureAny(named: 'to'),
        feeMode: captureAny(named: 'feeMode'),
        onlyAvailable: captureAny(named: 'onlyAvailable'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).captured;
    expect(captured, contains('Nha Trang'));
    expect(captured, contains(true));
    provider.dispose();
  });

  test(
    'lỗi domain được ánh xạ sang tiếng Việt, không lộ chi tiết DB',
    () async {
      when(
        () => repo.listPublicSessions(
          area: any(named: 'area'),
          from: any(named: 'from'),
          to: any(named: 'to'),
          feeMode: any(named: 'feeMode'),
          onlyAvailable: any(named: 'onlyAvailable'),
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ),
      ).thenThrow(Exception('PostgrestException(FORBIDDEN: raw pg detail)'));

      final provider = buildProvider();
      await provider.fetchPublicSessions();

      expect(
        provider.publicErrorMessage,
        'Bạn không có quyền thực hiện thao tác này.',
      );
      provider.dispose();
    },
  );

  test('fetchMySessions lỗi rồi retry phục hồi', () async {
    when(
      () => repo.listMySessions(
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenThrow(Exception('FORBIDDEN: nope'));

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
    when(() => repo.getSessionDetail('s2'))
        .thenAnswer((_) async => managedSession);
    when(
      () => repo.listSessionPlayers(
        's2',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer(
      (_) async => [
        const SessionPlayer(id: 'p1', displayName: 'An', phoneNumber: '0900'),
      ],
    );

    final provider = buildProvider();
    await provider.fetchSessionDetail('s2');

    expect(provider.currentSession?.id, 's2');
    expect(provider.canManagePlayers, isTrue);
    expect(provider.currentPlayers, hasLength(1));
    provider.dispose();
  });

  test(
    'fetchSessionDetail KHÔNG tải người đăng ký khi là khách/không quản lý',
    () async {
      when(() => repo.getSessionDetail('s1')).thenAnswer((_) async => session);

      final provider = buildProvider();
      await provider.fetchSessionDetail('s1');

      expect(provider.currentSession?.id, 's1');
      expect(provider.canManagePlayers, isFalse);
      verifyNever(
        () => repo.listSessionPlayers(
          's1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ),
      );
      provider.dispose();
    },
  );

  test('createSession lỗi rồi retry dùng lại cùng request_id; đổi payload tạo khoá mới', () async {
    stubListMySessions([]);
    final keys = <String>[];
    var attempts = 0;
    when(
      () => repo.createSession(
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
      ),
    ).thenAnswer((invocation) async {
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
    expect(
      keys.first,
      keys[1],
      reason: 'retry cùng payload phải dùng lại UUID',
    );

    await provider.createSession(form);
    expect(
      keys[2],
      isNot(keys[1]),
      reason: 'new intent after success rotates UUID',
    );

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
    expect(keys[3], isNot(keys[2]), reason: 'payload mới phải có UUID mới');
    provider.dispose();
  });

  test('publishSession gửi action publish và làm mới danh sách', () async {
    stubListMySessions([managedSession]);
    when(
      () => repo.setSessionLifecycle(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        action: any(named: 'action'),
      ),
    ).thenAnswer((_) async => managedSession);

    final provider = buildProvider();
    final result = await provider.publishSession('s2');

    expect(result, isNotNull);
    verify(
      () => repo.setSessionLifecycle(
        requestId: any(named: 'requestId'),
        sessionId: 's2',
        action: 'publish',
      ),
    ).called(1);
    verify(
      () => repo.listMySessions(
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).called(1);
    provider.dispose();
  });

  test('đổi người dùng/đăng xuất xoá state riêng tư', () async {
    stubListMySessions([managedSession]);
    stubListPublic([session]);
    when(() => repo.getSessionDetail('s2'))
        .thenAnswer((_) async => managedSession);

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

  // --- BH-05 -------------------------------------------------------------- //

  const joinResult = RegistrationResult(
    playerId: 'p1',
    sessionId: 's1',
    registrationStatus: 'pending',
    confirmedCount: 2,
    capacity: 8,
    seatsLeft: 6,
  );

  test('requestJoinSession gửi request_id, làm mới chi tiết và trả true', () async {
    when(() => repo.getSessionDetail('s1')).thenAnswer((_) async => session);
    when(
      () => repo.requestJoinSession(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        contact: any(named: 'contact'),
      ),
    ).thenAnswer((_) async => joinResult);

    final provider = buildProvider();
    await provider.fetchSessionDetail('s1');
    final ok = await provider.requestJoinSession(contact: '0900');

    expect(ok, isTrue);
    verify(
      () => repo.requestJoinSession(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        contact: '0900',
      ),
    ).called(1);
    verify(() => repo.getSessionDetail('s1')).called(2);
    provider.dispose();
  });

  test('requestJoinSession lỗi giữ nguyên request_id khi retry, xoay key sau thành công', () async {
    when(() => repo.getSessionDetail('s1')).thenAnswer((_) async => session);
    final keys = <String>[];
    var attempts = 0;
    when(
      () => repo.requestJoinSession(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        contact: any(named: 'contact'),
      ),
    ).thenAnswer((invocation) async {
      keys.add(invocation.namedArguments[#requestId] as String);
      attempts++;
      if (attempts == 1) throw Exception('timeout');
      return joinResult;
    });

    final provider = buildProvider();
    await provider.fetchSessionDetail('s1');
    expect(await provider.requestJoinSession(), isFalse);
    expect(provider.submitErrorMessage, isNotNull);
    expect(await provider.requestJoinSession(), isTrue);
    expect(keys.first, keys[1], reason: 'retry cùng ý định dùng lại UUID');
    expect(await provider.requestJoinSession(), isTrue);
    expect(keys[2], isNot(keys[1]), reason: 'ý định mới xoay UUID');
    provider.dispose();
  });

  test('chặn double-submit khi đang gửi', () async {
    when(() => repo.getSessionDetail('s1')).thenAnswer((_) async => session);
    final completer = Completer<RegistrationResult>();
    when(
      () => repo.requestJoinSession(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        contact: any(named: 'contact'),
      ),
    ).thenAnswer((_) => completer.future);

    final provider = buildProvider();
    await provider.fetchSessionDetail('s1');
    final first = provider.requestJoinSession();
    expect(provider.isSubmitting, isTrue);
    final second = await provider.requestJoinSession();
    expect(second, isFalse, reason: 'lần nhấn thứ hai bị chặn');

    completer.complete(joinResult);
    await first;
    expect(provider.isSubmitting, isFalse);
    verify(
      () => repo.requestJoinSession(
        requestId: any(named: 'requestId'),
        sessionId: 's1',
        contact: any(named: 'contact'),
      ),
    ).called(1);
    provider.dispose();
  });

  test('buổi waitlisted tải lời mời của tôi', () async {
    const waitlisted = Session(
      id: 's1',
      title: 'Buổi chờ',
      capacity: 8,
      lifecycle: 'published',
      confirmedCount: 8,
      myRegistration: SessionRegistration(
        playerId: 'p1',
        registrationStatus: 'waitlisted',
      ),
    );
    when(() => repo.getSessionDetail('s1')).thenAnswer((_) async => waitlisted);
    when(() => repo.getMyWaitlistInvitation('s1')).thenAnswer(
      (_) async => const WaitlistInvitation(
        invitationId: 'i1',
        playerId: 'p1',
        sessionId: 's1',
      ),
    );

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionDetail('s1');

    expect(provider.myInvitation?.invitationId, 'i1');
    provider.dispose();
  });

  test('accept/cancel/decide/attendance/add/invite/revoke gọi repository đúng', () async {
    when(() => repo.getSessionDetail('s2'))
        .thenAnswer((_) async => managedSession);
    when(
      () => repo.listSessionPlayers(
        's2',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) async => const []);
    when(
      () => repo.decideRegistration(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        playerId: any(named: 'playerId'),
        decision: any(named: 'decision'),
        reason: any(named: 'reason'),
      ),
    ).thenAnswer((_) async => joinResult);
    when(
      () => repo.cancelRegistration(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        playerId: any(named: 'playerId'),
        reason: any(named: 'reason'),
      ),
    ).thenAnswer((_) async => joinResult);
    when(
      () => repo.recordAttendance(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        playerId: any(named: 'playerId'),
        attendance: any(named: 'attendance'),
      ),
    ).thenAnswer((_) async => joinResult);
    when(
      () => repo.addSessionPlayer(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        memberId: any(named: 'memberId'),
        guestName: any(named: 'guestName'),
        contact: any(named: 'contact'),
        feeExempt: any(named: 'feeExempt'),
        allowWaitlist: any(named: 'allowWaitlist'),
      ),
    ).thenAnswer((_) async => joinResult);
    when(
      () => repo.inviteWaitlistedPlayer(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        playerId: any(named: 'playerId'),
        expiresAt: any(named: 'expiresAt'),
      ),
    ).thenAnswer(
      (_) async => const WaitlistInvitation(
        invitationId: 'i1',
        playerId: 'p1',
        sessionId: 's2',
      ),
    );
    when(
      () => repo.revokeWaitlistInvitation(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        invitationId: any(named: 'invitationId'),
        reason: any(named: 'reason'),
      ),
    ).thenAnswer(
      (_) async => const WaitlistInvitation(
        invitationId: 'i1',
        playerId: 'p1',
        sessionId: 's2',
      ),
    );
    when(
      () => repo.acceptWaitlistInvitation(
        requestId: any(named: 'requestId'),
        sessionId: any(named: 'sessionId'),
        invitationId: any(named: 'invitationId'),
        consentNote: any(named: 'consentNote'),
      ),
    ).thenAnswer((_) async => joinResult);

    final provider = buildProvider();
    await provider.fetchSessionDetail('s2');

    expect(await provider.decideRegistration(playerId: 'p1', decision: 'confirmed'), isTrue);
    expect(await provider.cancelRegistration(playerId: 'p1', reason: 'test'), isTrue);
    expect(await provider.recordAttendance(playerId: 'p1', attendance: 'present'), isTrue);
    expect(
      await provider.addSessionPlayer(guestName: 'Khách', allowWaitlist: true),
      isTrue,
    );
    expect(await provider.inviteWaitlistedPlayer(playerId: 'p1'), isTrue);
    expect(await provider.revokeWaitlistInvitation(invitationId: 'i1'), isTrue);
    expect(await provider.acceptWaitlistInvitation(invitationId: 'i1'), isTrue);

    verify(
      () => repo.decideRegistration(
        requestId: any(named: 'requestId'),
        sessionId: 's2',
        playerId: 'p1',
        decision: 'confirmed',
        reason: null,
      ),
    ).called(1);
    verify(
      () => repo.addSessionPlayer(
        requestId: any(named: 'requestId'),
        sessionId: 's2',
        memberId: null,
        guestName: 'Khách',
        contact: null,
        feeExempt: false,
        allowWaitlist: true,
      ),
    ).called(1);
    verify(
      () => repo.recordAttendance(
        requestId: any(named: 'requestId'),
        sessionId: 's2',
        playerId: 'p1',
        attendance: 'present',
      ),
    ).called(1);
    provider.dispose();
  });

  test('phản hồi chi tiết đến muộn của phiên cũ không lộ state', () async {
    final completer = Completer<Session>();
    when(() => repo.getSessionDetail('s1')).thenAnswer((_) => completer.future);

    final provider = buildProvider();
    auth.changeUser('user-a');
    final pending = provider.fetchSessionDetail('s1');
    auth.changeUser('user-b');
    completer.complete(session);
    await pending;

    expect(provider.currentSession, isNull);
    expect(provider.myInvitation, isNull);
    provider.dispose();
  });

  test('đăng xuất xoá lời mời đang chờ', () async {
    const waitlisted = Session(
      id: 's1',
      title: 'Buổi chờ',
      capacity: 8,
      lifecycle: 'published',
      confirmedCount: 8,
      myRegistration: SessionRegistration(
        playerId: 'p1',
        registrationStatus: 'waitlisted',
      ),
    );
    when(() => repo.getSessionDetail('s1')).thenAnswer((_) async => waitlisted);
    when(() => repo.getMyWaitlistInvitation('s1')).thenAnswer(
      (_) async => const WaitlistInvitation(
        invitationId: 'i1',
        playerId: 'p1',
        sessionId: 's1',
      ),
    );

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionDetail('s1');
    expect(provider.myInvitation, isNotNull);

    auth.changeUser(null);
    expect(provider.myInvitation, isNull);
    expect(provider.currentSession, isNull);
    provider.dispose();
  });
}
