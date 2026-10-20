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
    registerFallbackValue(const SessionHistoryFilter());
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

  void stubHistory(SessionHistoryPage page) {
    when(
      () => repo.listMySessionHistory(
        filter: any(named: 'filter'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) async => page);
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

  // --- Vòng sửa review 135d7bd: B1 (lời mời lỗi bị nuốt) & B2 (lời mời cũ) -- //

  const waitlistedSession = Session(
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

  const confirmedSession = Session(
    id: 's1',
    title: 'Buổi chờ',
    capacity: 8,
    lifecycle: 'published',
    confirmedCount: 8,
    myRegistration: SessionRegistration(
      playerId: 'p1',
      registrationStatus: 'confirmed',
    ),
  );

  const invitation = WaitlistInvitation(
    invitationId: 'i1',
    playerId: 'p1',
    sessionId: 's1',
  );

  test('B1 lời mời: tải lỗi phải lộ error, không bị coi là rỗng', () async {
    when(
      () => repo.getSessionDetail('s1'),
    ).thenAnswer((_) async => waitlistedSession);
    when(
      () => repo.getMyWaitlistInvitation('s1'),
    ).thenThrow(Exception('offline'));

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionDetail('s1');

    expect(provider.myInvitation, isNull);
    expect(provider.invitationErrorMessage, isNotNull);
    expect(provider.isLoadingInvitation, isFalse);
    provider.dispose();
  });

  test('B1 lời mời: bật loading trong khi đang tải', () async {
    final completer = Completer<WaitlistInvitation?>();
    when(
      () => repo.getSessionDetail('s1'),
    ).thenAnswer((_) async => waitlistedSession);
    when(
      () => repo.getMyWaitlistInvitation('s1'),
    ).thenAnswer((_) => completer.future);

    final provider = buildProvider();
    auth.changeUser('user-a');
    final pending = provider.fetchSessionDetail('s1');
    await pumpEventQueue();
    expect(provider.isLoadingInvitation, isTrue);

    completer.complete(null);
    await pending;
    expect(provider.isLoadingInvitation, isFalse);
    expect(provider.myInvitation, isNull);
    expect(provider.invitationErrorMessage, isNull);
    provider.dispose();
  });

  test('B1 lời mời: response null hợp lệ là rỗng, không phải lỗi', () async {
    when(
      () => repo.getSessionDetail('s1'),
    ).thenAnswer((_) async => waitlistedSession);
    when(
      () => repo.getMyWaitlistInvitation('s1'),
    ).thenAnswer((_) async => null);

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionDetail('s1');

    expect(provider.myInvitation, isNull);
    expect(provider.invitationErrorMessage, isNull);
    expect(provider.isLoadingInvitation, isFalse);
    provider.dispose();
  });

  test('B1 lời mời: retry sau lỗi phục hồi và nhận lời mời', () async {
    when(
      () => repo.getSessionDetail('s1'),
    ).thenAnswer((_) async => waitlistedSession);
    var calls = 0;
    when(() => repo.getMyWaitlistInvitation('s1')).thenAnswer((_) async {
      calls++;
      if (calls == 1) throw Exception('offline');
      return invitation;
    });

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionDetail('s1');
    expect(provider.invitationErrorMessage, isNotNull);

    await provider.fetchMyInvitation('s1');
    expect(provider.invitationErrorMessage, isNull);
    expect(provider.myInvitation?.invitationId, 'i1');
    provider.dispose();
  });

  test('B2 lời mời: làm mới sang confirmed thì xoá lời mời cũ', () async {
    var calls = 0;
    when(() => repo.getSessionDetail('s1')).thenAnswer((_) async {
      calls++;
      return calls == 1 ? waitlistedSession : confirmedSession;
    });
    when(
      () => repo.getMyWaitlistInvitation('s1'),
    ).thenAnswer((_) async => invitation);

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionDetail('s1');
    expect(provider.myInvitation?.invitationId, 'i1');

    await provider.fetchSessionDetail('s1');
    expect(provider.myInvitation, isNull);
    provider.dispose();
  });

  test('B2 lời mời: làm mới khi không còn đăng ký thì xoá lời mời cũ', () async {
    var calls = 0;
    when(() => repo.getSessionDetail('s1')).thenAnswer((_) async {
      calls++;
      return calls == 1 ? waitlistedSession : session;
    });
    when(
      () => repo.getMyWaitlistInvitation('s1'),
    ).thenAnswer((_) async => invitation);

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionDetail('s1');
    expect(provider.myInvitation?.invitationId, 'i1');

    await provider.fetchSessionDetail('s1');
    expect(provider.myInvitation, isNull);
    provider.dispose();
  });

  test('B2 lời mời: phản hồi đến trễ không khôi phục state đã xoá', () async {
    final invitationCompleter = Completer<WaitlistInvitation?>();
    var calls = 0;
    when(() => repo.getSessionDetail('s1')).thenAnswer((_) async {
      calls++;
      return calls == 1 ? waitlistedSession : confirmedSession;
    });
    when(
      () => repo.getMyWaitlistInvitation('s1'),
    ).thenAnswer((_) => invitationCompleter.future);

    final provider = buildProvider();
    auth.changeUser('user-a');
    final first = provider.fetchSessionDetail('s1');
    await pumpEventQueue();
    expect(provider.isLoadingInvitation, isTrue);

    await provider.fetchSessionDetail('s1');
    expect(provider.myInvitation, isNull);

    invitationCompleter.complete(invitation);
    await first;
    expect(provider.myInvitation, isNull);
    provider.dispose();
  });

  // --- BH-07B: lịch sử --------------------------------------------------- //

  const completed = Session(
    id: 'h1',
    title: 'Buổi đã xong',
    lifecycle: 'completed',
    version: 4,
    confirmedCount: 6,
  );
  const cancelled = Session(
    id: 'h2',
    title: 'Buổi đã huỷ',
    lifecycle: 'cancelled',
    version: 2,
  );

  test('history: empty/error/retry giữ đúng trạng thái và filter', () async {
    final filters = <SessionHistoryFilter?>[];
    final offsets = <int>[];
    var calls = 0;
    when(
      () => repo.listMySessionHistory(
        filter: any(named: 'filter'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((invocation) async {
      calls++;
      filters.add(invocation.namedArguments[#filter] as SessionHistoryFilter?);
      offsets.add(invocation.namedArguments[#offset] as int);
      if (calls == 1) {
        return const SessionHistoryPage(limit: 2, offset: 0);
      }
      if (calls == 2) throw Exception('offline');
      return const SessionHistoryPage(
        sessions: [completed],
        limit: 2,
        offset: 0,
      );
    });

    final provider = buildProvider();
    auth.changeUser('user-a');
    const filter = SessionHistoryFilter(clubId: 'c1');

    await provider.fetchSessionHistory(filter: filter, limit: 2);
    expect(provider.hasLoadedHistory, isTrue);
    expect(provider.isHistoryEmpty, isTrue);
    expect(provider.historyErrorMessage, isNull);
    expect(provider.isLoadingHistory, isFalse);
    expect(filters.first, filter);
    expect(offsets.first, 0);

    await provider.fetchSessionHistory(filter: filter, limit: 2);
    expect(provider.historyErrorMessage, isNotNull);
    expect(
      provider.historyItems,
      isEmpty,
      reason: 'lỗi cùng scope giữ trang cũ (đang rỗng), không biến thành dữ liệu mới',
    );

    await provider.fetchSessionHistory(filter: filter, limit: 2);
    expect(provider.historyErrorMessage, isNull);
    expect(provider.historyItems.single.id, 'h1');
    provider.dispose();
  });

  test('history: loadMore nối đúng offset, dừng khi hết trang', () async {
    final offsets = <int>[];
    when(
      () => repo.listMySessionHistory(
        filter: any(named: 'filter'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((invocation) async {
      final offset = invocation.namedArguments[#offset] as int;
      offsets.add(offset);
      return offset == 0
          ? const SessionHistoryPage(
              sessions: [completed, cancelled],
              limit: 2,
              offset: 0,
            )
          : const SessionHistoryPage(
              sessions: [Session(id: 'h3', title: 'Cũ hơn')],
              limit: 2,
              offset: 2,
            );
    });

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionHistory(limit: 2);
    expect(provider.historyItems, hasLength(2));
    expect(provider.hasMoreHistory, isTrue);

    await provider.loadMoreHistory();
    expect(offsets, [0, 2]);
    expect(provider.historyItems, hasLength(3));
    expect(provider.historyItems.last.id, 'h3');
    expect(provider.hasMoreHistory, isFalse);
    expect(provider.isLoadingMoreHistory, isFalse);

    await provider.loadMoreHistory();
    expect(offsets, [0, 2], reason: 'hết trang thì không phát RPC nữa');
    provider.dispose();
  });

  test(
    'history: trang chồng lấn dedupe theo ID, offset theo dòng thô [0,2,4]',
    () async {
      const d = Session(id: 'd', title: 'Mới nhất', lifecycle: 'completed');
      const c = Session(id: 'c', title: 'Buổi C', lifecycle: 'completed');
      const b = Session(id: 'b', title: 'Buổi B', lifecycle: 'completed');
      const a = Session(id: 'a', title: 'Cũ nhất', lifecycle: 'completed');
      final offsets = <int>[];
      when(
        () => repo.listMySessionHistory(
          filter: any(named: 'filter'),
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ),
      ).thenAnswer((invocation) async {
        final offset = invocation.namedArguments[#offset] as int;
        offsets.add(offset);
        return switch (offset) {
          0 => const SessionHistoryPage(
            sessions: [d, c],
            limit: 2,
            offset: 0,
          ),
          2 => const SessionHistoryPage(
            sessions: [c, b],
            limit: 2,
            offset: 2,
          ),
          _ => const SessionHistoryPage(
            sessions: [a],
            limit: 2,
            offset: 4,
          ),
        };
      });

      final provider = buildProvider();
      auth.changeUser('user-a');
      await provider.fetchSessionHistory(limit: 2);
      await provider.loadMoreHistory();
      await provider.loadMoreHistory();

      expect(
        offsets,
        [0, 2, 4],
        reason: 'offset kế tiếp theo số dòng thô, không theo số ID sau dedupe',
      );
      expect(
        provider.historyItems.map((session) => session.id).toList(),
        ['d', 'c', 'b', 'a'],
        reason: 'mỗi session ID chỉ xuất hiện một lần khi trang chồng lấn',
      );
      expect(provider.hasMoreHistory, isFalse);
      expect(provider.isLoadingMoreHistory, isFalse);
      provider.dispose();
    },
  );

  test('history: đổi CLB xoá trang cũ và bỏ phản hồi đến trễ', () async {
    final slowC2 = Completer<SessionHistoryPage>();
    when(
      () => repo.listMySessionHistory(
        filter: any(named: 'filter'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((invocation) {
      final filter =
          invocation.namedArguments[#filter] as SessionHistoryFilter?;
      if (filter?.clubId == 'c2') return slowC2.future;
      return Future.value(
        SessionHistoryPage(
          sessions: [
            Session(
              id: filter?.clubId == 'c3' ? 'h3' : 'h1',
              title: 'Lịch sử ${filter?.clubId}',
              lifecycle: 'completed',
            ),
          ],
          limit: invocation.namedArguments[#limit] as int,
          offset: invocation.namedArguments[#offset] as int,
        ),
      );
    });

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionHistory(
      filter: const SessionHistoryFilter(clubId: 'c1'),
    );
    expect(provider.historyItems.single.id, 'h1');

    final pending = provider.fetchSessionHistory(
      filter: const SessionHistoryFilter(clubId: 'c2'),
    );
    expect(provider.history, isNull, reason: 'đổi CLB phải xoá dữ liệu CLB cũ');
    expect(provider.isLoadingHistory, isTrue);

    await provider.fetchSessionHistory(
      filter: const SessionHistoryFilter(clubId: 'c3'),
    );
    slowC2.complete(
      const SessionHistoryPage(
        sessions: [Session(id: 'late-c2', title: 'Trễ')],
        limit: 20,
        offset: 0,
      ),
    );
    await pending;

    expect(provider.historyFilter.clubId, 'c3');
    expect(provider.historyItems.single.id, 'h3');
    expect(provider.isLoadingHistory, isFalse);
    provider.dispose();
  });

  test('history: logout/đổi actor xoá state và chặn phản hồi cũ', () async {
    final slow = Completer<SessionHistoryPage>();
    var calls = 0;
    when(
      () => repo.listMySessionHistory(
        filter: any(named: 'filter'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).thenAnswer((_) {
      calls++;
      if (calls == 1) {
        return Future.value(
          const SessionHistoryPage(sessions: [completed], limit: 20, offset: 0),
        );
      }
      return slow.future;
    });

    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionHistory();
    expect(provider.historyItems, isNotEmpty);

    final pending = provider.fetchSessionHistory();
    auth.changeUser(null);
    expect(provider.history, isNull);
    expect(provider.isLoadingHistory, isFalse);

    slow.complete(
      const SessionHistoryPage(sessions: [cancelled], limit: 20, offset: 0),
    );
    await pending;
    expect(
      provider.history,
      isNull,
      reason: 'phản hồi của actor cũ không được khôi phục state',
    );
    provider.dispose();
  });

  test('history: đổi actor A→B xoá state của actor cũ', () async {
    stubHistory(
      const SessionHistoryPage(
        sessions: [completed],
        limit: 20,
        offset: 0,
      ),
    );
    final provider = buildProvider();
    auth.changeUser('user-a');
    await provider.fetchSessionHistory();
    expect(provider.historyItems, isNotEmpty);

    auth.changeUser('user-b');
    expect(provider.history, isNull);
    expect(provider.historyFilter.isEmpty, isTrue);
    expect(provider.historyErrorMessage, isNull);
    provider.dispose();
  });

  test('history: refreshHistoryIfLoaded chỉ gọi khi tab đã tải', () async {
    stubHistory(
      const SessionHistoryPage(sessions: [completed], limit: 20, offset: 0),
    );
    final provider = buildProvider();
    auth.changeUser('user-a');

    await provider.refreshHistoryIfLoaded();
    verifyNever(
      () => repo.listMySessionHistory(
        filter: any(named: 'filter'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    );

    await provider.fetchSessionHistory();
    await provider.refreshHistoryIfLoaded();
    verify(
      () => repo.listMySessionHistory(
        filter: any(named: 'filter'),
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      ),
    ).called(2);
    provider.dispose();
  });
}
