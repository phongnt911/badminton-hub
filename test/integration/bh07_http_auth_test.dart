import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
// ignore: depend_on_referenced_packages
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart'
    show AuthException, PostgrestException, SupabaseClient, User;

import 'package:badminton_hub/data/auth_repository.dart';
import 'package:badminton_hub/data/finance_repository.dart';
import 'package:badminton_hub/data/session_repository.dart';
import 'package:badminton_hub/models/finance.dart';
import 'package:badminton_hub/models/session.dart';

/// BH-07 HTTP/Auth verification.
///
/// This test deliberately uses:
///   * a real local Supabase stack (Kong -> GoTrue + PostgREST);
///   * GoTrue password sign-in and the resulting JWT access token;
///   * the real AuthRepository, SessionRepository and FinanceRepository;
///   * real RPC calls for every mutation.
///
/// It is disabled unless `BH07_HTTP_TEST=1` so the normal Flutter suite does
/// not require a running local Supabase. The runner
/// `scripts/bh07_http/run.ps1` resets the isolated local database, creates Auth
/// users through GoTrue Admin API, applies `seed.sql`, then runs this file.
///
/// No repository mock, SET ROLE, Auth stub or direct RPC replacement is used
/// for the functional assertions. The service-role client is used only to read
/// side-effect counters after the real HTTP calls.
const _password = 'bh07-http-pass-123456';

const clubA = 'aaaaaaaa-1111-4111-8111-111111111111';
const clubB = 'bbbbbbbb-2222-4222-8222-222222222222';
const venue = 'cccccccc-3333-4333-8333-333333333333';

const sessionDebt = '10000000-0000-4000-8000-000000000001';
const sessionFree = '10000000-0000-4000-8000-000000000002';
const sessionStale = '10000000-0000-4000-8000-000000000003';
const sessionVersion = '10000000-0000-4000-8000-000000000004';
const sessionFin = '10000000-0000-4000-8000-000000000005';
const sessionCancelled = '10000000-0000-4000-8000-000000000006';
const sessionPrivate = '10000000-0000-4000-8000-000000000007';
const sessionClubB = '20000000-0000-4000-8000-000000000001';

const sessionCcComplete = '20000000-0000-4000-8000-000000000002';
const sessionCcCompeting = '20000000-0000-4000-8000-000000000003';
const sessionCcPay = '20000000-0000-4000-8000-000000000004';
const sessionCcDrop = '20000000-0000-4000-8000-000000000005';

const playerCcComplete = '30000000-0000-4000-8000-000000000021';
const playerCcCompeting = '30000000-0000-4000-8000-000000000022';
const playerCcPay = '30000000-0000-4000-8000-000000000023';
const playerCcDrop = '30000000-0000-4000-8000-000000000024';

const completeCcReplayReq = 'c0000000-0000-4000-8000-000000000021';
const completeCcCompA = 'c0000000-0000-4000-8000-000000000022';
const completeCcCompB = 'c0000000-0000-4000-8000-000000000023';
const cashCcReplayReq = 'c0000000-0000-4000-8000-000000000024';
const cashCcCompA = 'c0000000-0000-4000-8000-000000000025';
const cashCcCompB = 'c0000000-0000-4000-8000-000000000026';
const submitMemberCcReq = 'c0000000-0000-4000-8000-000000000028';
const confirmCcReq = 'c0000000-0000-4000-8000-000000000029';
const dropResponseReq = 'c0000000-0000-4000-8000-000000000027';

const expenseDebt = '50000000-0000-4000-8000-000000000001';
const expenseFin = '50000000-0000-4000-8000-000000000002';
const seededDebtPayment = '60000000-0000-4000-8000-000000000001';

const freePlayer = '30000000-0000-4000-8000-000000000003';
const freeRevision = '40000000-0000-4000-8000-000000000002';
const memberAContactRow = 'a0000004-0000-4000-8000-000000000004';

const privateMemberPhone = '+84900000004';
const privateContactNote = 'BH07-PRIVATE-MEMBER-CONTACT';
const privatePlayerPhone = '+84900000003';
const privateBankCode = 'BH07BANK';
const privateAccountNumber = '0000000007';
const privateAccountName = 'BH07 PRIVATE RECEIVER';

const historyProjectionKeys = <String>{
  'id',
  'club_id',
  'club_name',
  'title',
  'starts_at',
  'ends_at',
  'capacity',
  'court_count',
  'visibility',
  'lifecycle',
  'fee_mode',
  'member_fee_vnd',
  'guest_fee_vnd',
  'venue_name',
  'venue_area',
  'confirmed_count',
  'version',
};

const summaryProjectionKeys = <String>{
  'session_id',
  'title',
  'club_id',
  'club_name',
  'venue_name',
  'starts_at',
  'ends_at',
  'lifecycle',
  'fee_mode',
  'session_version',
  'can_manage',
  'can_view_finance',
  'present_count',
  'no_show_count',
  'confirmed_count',
  'billing_state',
  'active_revision_id',
  'revision_no',
  'source_version',
  'expenses_total_vnd',
  'amount_due_total_vnd',
  'total_paid_vnd',
  'outstanding_total_vnd',
};

const summaryFinanceProjectionKeys = <String>{
  'billing_state',
  'active_revision_id',
  'revision_no',
  'source_version',
  'expenses_total_vnd',
  'amount_due_total_vnd',
  'total_paid_vnd',
  'outstanding_total_vnd',
};

const privateProjectionTokens = <String>[
  'contact',
  'phone',
  'bank',
  'account',
  'receiver',
];

Set<String> _normalizedKeys(Map value) =>
    value.keys.map((key) => key.toString().toLowerCase()).toSet();

bool _hasPrivateProjectionField(Object? value) {
  if (value is Map) {
    for (final entry in value.entries) {
      final key = entry.key.toString().toLowerCase();
      if (privateProjectionTokens.any(key.contains)) return true;
      if (_hasPrivateProjectionField(entry.value)) return true;
    }
  } else if (value is List) {
    for (final item in value) {
      if (_hasPrivateProjectionField(item)) return true;
    }
  }
  return false;
}

List<String> _projectionIssues(Object? value, Set<String> allowedKeys) {
  if (value is! Map) return const ['payload is not an object'];
  final keys = _normalizedKeys(value);
  final issues = <String>[];
  final missing = allowedKeys.difference(keys).toList()..sort();
  final extra = keys.difference(allowedKeys).toList()..sort();
  if (missing.isNotEmpty) issues.add('missing=${missing.join(',')}');
  if (extra.isNotEmpty) issues.add('extra=${extra.join(',')}');
  if (_hasPrivateProjectionField(value)) issues.add('private-key');
  return issues;
}

List<String> _historyProjectionIssues(Object? value) {
  if (value is! List) return const ['payload is not an array'];
  final issues = <String>[];
  if (value.isEmpty) issues.add('empty-history');
  for (var index = 0; index < value.length; index++) {
    final rowIssues = _projectionIssues(value[index], historyProjectionKeys);
    if (rowIssues.isNotEmpty) {
      issues.add('row[$index]: ${rowIssues.join(';')}');
    }
  }
  return issues;
}

const completeDebtRequest = 'c0000000-0000-4000-8000-000000000001';
const completeFreeRequest = 'c0000000-0000-4000-8000-000000000002';
const reversePaymentRequest = 'c0000000-0000-4000-8000-000000000003';
const cashRequest = 'c0000000-0000-4000-8000-000000000004';
const submitMemberRequest = 'c0000000-0000-4000-8000-000000000005';
const confirmMemberRequest = 'c0000000-0000-4000-8000-000000000006';
const refinalizeDebtRequest = 'c0000000-0000-4000-8000-000000000007';
const reverseExpenseRequest = 'c0000000-0000-4000-8000-000000000008';
const refinalizeFinRequest = 'c0000000-0000-4000-8000-000000000009';
const submitRejectRequest = 'c0000000-0000-4000-8000-000000000010';
const rejectRequest = 'c0000000-0000-4000-8000-000000000011';
const postExpenseAttemptRequest = 'c0000000-0000-4000-8000-000000000012';
const versionAttemptRequest = 'c0000000-0000-4000-8000-000000000013';
const crossClubCompleteRequest = 'c0000000-0000-4000-8000-000000000014';
const participantCompleteRequest = 'c0000000-0000-4000-8000-000000000015';
const staleCompleteRequest = 'c0000000-0000-4000-8000-000000000016';
const anonymousCompleteRequest = 'c0000000-0000-4000-8000-000000000017';

class StaticStatusClient extends http.BaseClient {
  final int statusCode;
  StaticStatusClient(this.statusCode);

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    return http.StreamedResponse(
      Stream.fromIterable([<int>[]]),
      statusCode,
      request: request,
    );
  }
}

class DropResponseAfterCommitClient extends http.BaseClient {
  final http.Client _inner;
  final String targetPath;
  bool shouldDrop = true;
  bool dropped = false;
  int? droppedStatusCode;
  bool drained = false;

  DropResponseAfterCommitClient(this._inner, {required this.targetPath});

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final response = await _inner.send(request);
    if (shouldDrop && request.url.path.contains(targetPath)) {
      if (response.statusCode == 200) {
        shouldDrop = false;
        dropped = true;
        droppedStatusCode = response.statusCode;
        await response.stream.drain();
        drained = true;
        throw http.ClientException(
          'Simulated transport drop: connection closed by peer after server commit (HTTP 200)',
          request.url,
        );
      }
    }
    return response;
  }
}

bool isCompleteConflictError(Object? error) {
  if (error is! PostgrestException) return false;
  final code = error.code ?? '';
  final msg = error.message;
  final isConflictDomain = msg.contains('VERSION_CONFLICT') || msg.contains('INVALID_STATE');
  final isExpectedCode = code == '22023' || code == '409';
  return isConflictDomain && isExpectedCode;
}

bool isCashOvercollectError(Object? error) {
  if (error is! PostgrestException) return false;
  final code = error.code ?? '';
  final msg = error.message;
  final isOvercollectDomain = msg.contains('PAYMENT_EXCEEDS_OUTSTANDING');
  final isExpectedCode = code == '22023';
  return isOvercollectDomain && isExpectedCode;
}

bool verifyH2NegativeControls() {
  final unrelatedP0001 = PostgrestException(message: 'FORBIDDEN', code: 'P0001');
  final forbidden42501 = PostgrestException(
    message: 'FORBIDDEN: Chỉ host/quản lý buổi mới kết thúc buổi',
    code: '42501',
  );
  final notFoundP0002 = PostgrestException(
    message: 'NOT_FOUND: Buổi chơi không tồn tại',
    code: 'P0002',
  );
  final invalidInputAmount = PostgrestException(
    message: 'INVALID_INPUT: Số tiền phải là số nguyên dương VNĐ',
    code: '22023',
  );
  final genericClientErr = http.ClientException('Simulated network timeout');

  if (isCompleteConflictError(unrelatedP0001)) return false;
  if (isCompleteConflictError(forbidden42501)) return false;
  if (isCompleteConflictError(notFoundP0002)) return false;
  if (isCompleteConflictError(genericClientErr)) return false;

  if (isCashOvercollectError(unrelatedP0001)) return false;
  if (isCashOvercollectError(forbidden42501)) return false;
  if (isCashOvercollectError(notFoundP0002)) return false;
  if (isCashOvercollectError(invalidInputAmount)) return false;
  if (isCashOvercollectError(genericClientErr)) return false;

  return true;
}

class HttpActor {
  final String name;
  final User user;
  final SupabaseClient client;
  final AuthRepository auth;
  final SessionRepository sessions;
  final FinanceRepository finance;

  HttpActor({
    required this.name,
    required this.user,
    required this.client,
    required this.auth,
    required this.sessions,
    required this.finance,
  });
}

void main() {
  if (Platform.environment['BH07_HTTP_TEST'] != '1') {
    test(
      'BH-07 HTTP/Auth verification is disabled',
      () {},
      skip: 'Set BH07_HTTP_TEST=1 and use scripts/bh07_http/run.ps1',
    );
    return;
  }

  TestWidgetsFlutterBinding.ensureInitialized();
  HttpOverrides.global = null;

  late String baseUrl;
  late String anonKey;
  late String serviceRoleKey;
  late SupabaseClient admin;
  late List<Map<String, Object?>> checks;
  late DateTime startedAt;

  void check(String id, String description, bool ok, [Object? detail]) {
    checks.add({
      'id': id,
      'description': description,
      'status': ok ? 'PASS' : 'FAIL',
      'detail': detail?.toString(),
    });
  }

  String errorText(Object error) {
    if (error is PostgrestException) {
      return 'POSTGREST code=${error.code} message=${error.message} '
          'details=${error.details} hint=${error.hint}';
    }
    if (error is AuthException) {
      return 'AUTH ${error.message}';
    }
    return error.toString();
  }

  Future<void> expectError(
    String id,
    String description,
    Future<Object?> Function() body,
    String expected,
  ) async {
    try {
      final unexpected = await body();
      check(
        id,
        description,
        false,
        'unexpected success: ${unexpected.runtimeType}',
      );
    } catch (error) {
      final text = errorText(error);
      check(id, description, text.contains(expected), text);
    }
  }

  Map<String, dynamic> jwtPayload(String token) {
    final parts = token.split('.');
    return Map<String, dynamic>.from(
      jsonDecode(utf8.decode(base64Url.decode(base64Url.normalize(parts[1]))))
          as Map,
    );
  }

  Future<HttpActor> login(
    String name,
    String email, {
    http.Client? httpClient,
    bool recordAuthCheck = true,
  }) async {
    final client = SupabaseClient(baseUrl, anonKey, httpClient: httpClient);
    final auth = AuthRepository(client: client);
    final response = await auth.signInWithEmail(
      email: email,
      password: _password,
    );
    final token = response.session?.accessToken;
    final user = response.user;
    var tokenOk = false;
    var jwtRole = '';
    if (token != null && token.split('.').length == 3 && user != null) {
      final payload = jwtPayload(token);
      jwtRole = payload['role']?.toString() ?? '';
      tokenOk =
          jwtRole == 'authenticated' &&
          payload['sub']?.toString() == user.id &&
          (payload['exp'] is num) &&
          (payload['exp'] as num).toInt() >
              DateTime.now().millisecondsSinceEpoch ~/ 1000;
    }
    if (recordAuthCheck) {
      check(
        'auth.$name.jwt',
        '$name signs in through GoTrue and receives an authenticated JWT',
        tokenOk,
        'user=${user?.id} role=$jwtRole segments=${token?.split('.').length}',
      );
    }
    if (!tokenOk || user == null) {
      throw StateError('GoTrue sign-in failed for $name');
    }
    return HttpActor(
      name: name,
      user: user,
      client: client,
      auth: auth,
      sessions: SessionRepository(client: client),
      finance: FinanceRepository(client: client),
    );
  }

  Future<int> countRows(
    SupabaseClient client,
    String table, {
    String? column,
    Object? value,
    String? secondColumn,
    Object? secondValue,
    String? thirdColumn,
    Object? thirdValue,
  }) async {
    var query = client.from(table).select('*');
    if (column != null) query = query.eq(column, value!);
    if (secondColumn != null) query = query.eq(secondColumn, secondValue!);
    if (thirdColumn != null) query = query.eq(thirdColumn, thirdValue!);
    final rows = await query;
    return (rows as List).length;
  }

  Future<List<Map<String, dynamic>>> rows(
    SupabaseClient client,
    String table, {
    required String columns,
    String? column,
    Object? value,
  }) async {
    var query = client.from(table).select(columns);
    if (column != null) query = query.eq(column, value!);
    final result = await query;
    return (result as List)
        .whereType<Map>()
        .map((row) => Map<String, dynamic>.from(row))
        .toList();
  }

  test('BH-07 HTTP/Auth matrix', () async {
    startedAt = DateTime.now().toUtc();
    checks = [];
    baseUrl = Platform.environment['BH07_HTTP_URL'] ?? '';
    anonKey = Platform.environment['BH07_HTTP_ANON_KEY'] ?? '';
    serviceRoleKey = Platform.environment['BH07_HTTP_SERVICE_ROLE_KEY'] ?? '';
    if (baseUrl.isEmpty || anonKey.isEmpty || serviceRoleKey.isEmpty) {
      fail(
        'BH07_HTTP_URL, BH07_HTTP_ANON_KEY and '
        'BH07_HTTP_SERVICE_ROLE_KEY are required',
      );
    }
    admin = SupabaseClient(baseUrl, serviceRoleKey);

    final ownerA = await login('ownerA', 'ownera@example.test');
    final financeA = await login('financeA', 'financea@example.test');
    final cohostA = await login('cohostA', 'cohosta@example.test');
    final memberA = await login('memberA', 'membera@example.test');
    final guestA = await login('guestA', 'guesta@example.test');
    final ownerB = await login('ownerB', 'ownerb@example.test');
    final outsider = await login('outsider', 'outsider@example.test');

    final anonymousClient = SupabaseClient(baseUrl, anonKey);
    final anonymousSessions = SessionRepository(client: anonymousClient);
    final anonymousFinance = FinanceRepository(client: anonymousClient);

    await expectError(
      'auth.bad-password',
      'GoTrue rejects a wrong password',
      () async {
        final client = SupabaseClient(baseUrl, anonKey);
        await AuthRepository(client: client).signInWithEmail(
          email: 'membera@example.test',
          password: 'wrong-password',
        );
        return 'unexpected';
      },
      'Email hoặc mật khẩu',
    );

    // --- Management / finance / participant / guest and cross-club ACL ---
    await expectError(
      'acl.cross-club.complete',
      'owner B cannot complete a club A session',
      () => ownerB.finance.completeSession(
        requestId: crossClubCompleteRequest,
        sessionId: sessionVersion,
        expectedVersion: 5,
      ),
      'FORBIDDEN',
    );
    await expectError(
      'acl.participant.complete',
      'participant cannot complete a session',
      () => memberA.finance.completeSession(
        requestId: participantCompleteRequest,
        sessionId: sessionVersion,
        expectedVersion: 5,
      ),
      'FORBIDDEN',
    );
    await expectError(
      'acl.anonymous.complete',
      'anonymous request is denied at the function privilege boundary',
      () => anonymousFinance.completeSession(
        requestId: anonymousCompleteRequest,
        sessionId: sessionVersion,
        expectedVersion: 5,
      ),
      'permission denied for function complete_session',
    );

    await expectError(
      'acl.cross-club.finance',
      'owner B cannot read club A finance',
      () => ownerB.finance.getSessionFinance(sessionDebt),
      'FORBIDDEN',
    );
    await expectError(
      'acl.cross-club.summary',
      'owner B cannot read club A summary',
      () => ownerB.finance.getSessionSummary(sessionDebt),
      'FORBIDDEN',
    );
    await expectError(
      'acl.participant.summary',
      'participant cannot read summary',
      () => memberA.finance.getSessionSummary(sessionDebt),
      'FORBIDDEN',
    );
    await expectError(
      'acl.guest.summary',
      'guest cannot read summary',
      () => guestA.finance.getSessionSummary(sessionDebt),
      'FORBIDDEN',
    );
    await expectError(
      'acl.participant.finance',
      'participant cannot read session finance',
      () => memberA.finance.getSessionFinance(sessionDebt),
      'FORBIDDEN',
    );
    await expectError(
      'acl.cohost.finance',
      'management-only cohost cannot read session finance',
      () => cohostA.finance.getSessionFinance(sessionDebt),
      'FORBIDDEN',
    );

    await expectError(
      'privacy.cross-club.private-detail',
      'owner B cannot read a private club A session',
      () => ownerB.sessions.getSessionDetail(sessionPrivate),
      'FORBIDDEN',
    );
    await expectError(
      'privacy.outsider.private-detail',
      'outsider cannot read a private session',
      () => outsider.sessions.getSessionDetail(sessionPrivate),
      'FORBIDDEN',
    );
    await expectError(
      'privacy.anonymous.private-detail',
      'anonymous cannot read a private session',
      () => anonymousSessions.getSessionDetail(sessionPrivate),
      'UNAUTHENTICATED',
    );

    final privateAsMember = await memberA.sessions.getSessionDetail(
      sessionPrivate,
    );
    check(
      'privacy.club-member.private-detail',
      'active club member can read the private club session',
      privateAsMember.id == sessionPrivate &&
          privateAsMember.title == 'HTTP private history',
      'lifecycle=${privateAsMember.lifecycle}',
    );

    final guestDetail = await guestA.sessions.getSessionDetail(sessionDebt);
    check(
      'scope.participant.detail',
      'participant reads public detail with own registration',
      guestDetail.id == sessionDebt &&
          guestDetail.myRegistration != null &&
          guestDetail.myRegistration!.registrationStatus == 'confirmed' &&
          guestDetail.myRegistration!.attendanceStatus == 'present',
      'registration=${guestDetail.myRegistration?.registrationStatus} '
          'attendance=${guestDetail.myRegistration?.attendanceStatus}',
    );

    final outsiderDetail = await outsider.sessions.getSessionDetail(
      sessionDebt,
    );
    check(
      'scope.guest.public-detail',
      'signed-in non-participant reads public detail without management rights',
      outsiderDetail.id == sessionDebt &&
          !outsiderDetail.canManage &&
          !outsiderDetail.canViewFinance &&
          outsiderDetail.myRegistration == null,
      'manage=${outsiderDetail.canManage} '
          'finance=${outsiderDetail.canViewFinance}',
    );

    final anonymousDetail = await anonymousSessions.getSessionDetail(
      sessionDebt,
    );
    check(
      'scope.anonymous.public-detail',
      'anonymous reads public detail without management rights',
      anonymousDetail.id == sessionDebt &&
          !anonymousDetail.canManage &&
          !anonymousDetail.canViewFinance,
      'manage=${anonymousDetail.canManage} '
          'finance=${anonymousDetail.canViewFinance}',
    );

    // --- Stale and version conflict before any completion ---
    await expectError(
      'complete.stale',
      'complete rejects a stale billing revision',
      () => ownerA.finance.completeSession(
        requestId: staleCompleteRequest,
        sessionId: sessionStale,
        expectedVersion: 2,
      ),
      'BILLING_STALE',
    );
    final staleDetail = await ownerA.sessions.getSessionDetail(sessionStale);
    check(
      'complete.stale.unchanged',
      'stale rejection leaves lifecycle and version unchanged',
      staleDetail.lifecycle == 'in_progress' && staleDetail.version == 2,
      'lifecycle=${staleDetail.lifecycle} version=${staleDetail.version}',
    );

    await expectError(
      'complete.version-conflict',
      'complete rejects an outdated expected version',
      () => ownerA.finance.completeSession(
        requestId: versionAttemptRequest,
        sessionId: sessionVersion,
        expectedVersion: 4,
      ),
      'VERSION_CONFLICT',
    );
    final versionDetail = await ownerA.sessions.getSessionDetail(
      sessionVersion,
    );
    check(
      'complete.version-conflict.unchanged',
      'version conflict leaves lifecycle and version unchanged',
      versionDetail.lifecycle == 'in_progress' && versionDetail.version == 5,
      'lifecycle=${versionDetail.lifecycle} version=${versionDetail.version}',
    );

    // --- Current billing with debt: complete, retry, summary, history ---
    final debtBefore = await ownerA.sessions.getSessionDetail(sessionDebt);
    check(
      'complete.current.precondition',
      'debt fixture starts in_progress at version 7 with current billing',
      debtBefore.lifecycle == 'in_progress' && debtBefore.version == 7,
      'lifecycle=${debtBefore.lifecycle} version=${debtBefore.version}',
    );

    final debtFinanceBefore = await financeA.finance.getSessionFinance(
      sessionDebt,
    );
    check(
      'finance.current.before-complete',
      'finance sees current revision, due total and remaining debt before complete',
      debtFinanceBefore.isCurrent &&
          debtFinanceBefore.sessionVersion == 7 &&
          debtFinanceBefore.activeRevision?.revisionNo == 1 &&
          debtFinanceBefore.activeRevision?.allocationTotalVnd == 300000 &&
          debtFinanceBefore.expensesTotalVnd == 300000 &&
          debtFinanceBefore.outstandingTotalVnd == 250000 &&
          debtFinanceBefore.charges.length == 2 &&
          debtFinanceBefore.charges.fold<int>(
                0,
                (sum, charge) => sum + charge.amountDueVnd,
              ) ==
              300000 &&
          debtFinanceBefore.payments.length == 1 &&
          debtFinanceBefore.payments.single.status == 'confirmed',
      'state=${debtFinanceBefore.billingState} '
          'version=${debtFinanceBefore.sessionVersion} '
          'due=${debtFinanceBefore.activeRevision?.allocationTotalVnd} '
          'outstanding=${debtFinanceBefore.outstandingTotalVnd} '
          'charges=${debtFinanceBefore.charges.length} '
          'payments=${debtFinanceBefore.payments.length}',
    );

    final debtPlayers = await ownerA.sessions.listSessionPlayers(sessionDebt);
    final memberPlayer = debtPlayers.singleWhere(
      (player) => player.userId == memberA.user.id,
    );
    final guestPlayer = debtPlayers.singleWhere(
      (player) => player.userId == guestA.user.id,
    );
    check(
      'complete.players',
      'real list_session_players returns both confirmed participants',
      debtPlayers.length == 2 &&
          memberPlayer.registrationStatus == 'confirmed' &&
          guestPlayer.registrationStatus == 'confirmed',
      'players=${debtPlayers.length}',
    );

    final completedDebt = await ownerA.finance.completeSession(
      requestId: completeDebtRequest,
      sessionId: sessionDebt,
      expectedVersion: 7,
    );
    check(
      'complete.current.success',
      'management completes current billing with outstanding debt',
      completedDebt.lifecycle == 'completed' && completedDebt.version == 8,
      'lifecycle=${completedDebt.lifecycle} version=${completedDebt.version}',
    );

    final completedDebtRetry = await ownerA.finance.completeSession(
      requestId: completeDebtRequest,
      sessionId: sessionDebt,
      expectedVersion: 7,
    );
    final completeAuditCount = await countRows(
      admin,
      'audit_events',
      column: 'session_id',
      value: sessionDebt,
      secondColumn: 'action',
      secondValue: 'SESSION_COMPLETED',
    );
    final completeOperationCount = await countRows(
      admin,
      'operation_requests',
      column: 'operation',
      value: 'complete_session',
      secondColumn: 'request_id',
      secondValue: completeDebtRequest,
    );
    final debtAfterRetry = await ownerA.sessions.getSessionDetail(sessionDebt);
    check(
      'complete.retry-idempotent',
      'same complete request_id replays without a second lifecycle/audit side effect',
      completedDebtRetry.lifecycle == 'completed' &&
          completedDebtRetry.version == 8 &&
          debtAfterRetry.version == 8 &&
          completeAuditCount == 1 &&
          completeOperationCount == 1,
      'retryVersion=${completedDebtRetry.version} '
          'detailVersion=${debtAfterRetry.version} '
          'audit=$completeAuditCount operations=$completeOperationCount',
    );

    final debtFinanceAfter = await financeA.finance.getSessionFinance(
      sessionDebt,
    );
    check(
      'finance.current.after-complete',
      'completed session keeps current revision, charges and outstanding debt',
      debtFinanceAfter.lifecycle == 'completed' &&
          debtFinanceAfter.isCurrent &&
          debtFinanceAfter.sessionVersion == 8 &&
          debtFinanceAfter.outstandingTotalVnd == 250000 &&
          debtFinanceAfter.charges.length == 2 &&
          debtFinanceAfter.payments.length == 1,
      'lifecycle=${debtFinanceAfter.lifecycle} '
          'state=${debtFinanceAfter.billingState} '
          'outstanding=${debtFinanceAfter.outstandingTotalVnd}',
    );

    final financeSummary = await financeA.finance.getSessionSummary(
      sessionDebt,
    );
    check(
      'summary.finance',
      'finance summary returns server aggregates and preserves outstanding debt',
      financeSummary.canManage == false &&
          financeSummary.canViewFinance == true &&
          financeSummary.presentCount == 2 &&
          financeSummary.noShowCount == 0 &&
          financeSummary.confirmedCount == 2 &&
          financeSummary.billingState == 'current' &&
          financeSummary.revisionNo == 1 &&
          financeSummary.sourceVersion == 2 &&
          financeSummary.expensesTotalVnd == 300000 &&
          financeSummary.amountDueTotalVnd == 300000 &&
          financeSummary.totalPaidVnd == 50000 &&
          financeSummary.outstandingTotalVnd == 250000,
      'manage=${financeSummary.canManage} '
          'finance=${financeSummary.canViewFinance} '
          'present=${financeSummary.presentCount} '
          'due=${financeSummary.amountDueTotalVnd} '
          'paid=${financeSummary.totalPaidVnd} '
          'outstanding=${financeSummary.outstandingTotalVnd}',
    );

    final managementSummary = await cohostA.finance.getSessionSummary(
      sessionDebt,
    );
    check(
      'summary.management-null-money',
      'management-only cohost sees counts but every finance field is null',
      managementSummary.canManage == true &&
          managementSummary.canViewFinance == false &&
          managementSummary.presentCount == 2 &&
          managementSummary.confirmedCount == 2 &&
          managementSummary.billingState == null &&
          managementSummary.activeRevisionId == null &&
          managementSummary.revisionNo == null &&
          managementSummary.sourceVersion == null &&
          managementSummary.expensesTotalVnd == null &&
          managementSummary.amountDueTotalVnd == null &&
          managementSummary.totalPaidVnd == null &&
          managementSummary.outstandingTotalVnd == null,
      'manage=${managementSummary.canManage} '
          'finance=${managementSummary.canViewFinance} '
          'billing=${managementSummary.billingState} '
          'due=${managementSummary.amountDueTotalVnd}',
    );

    final rawSummary = await financeA.client.rpc(
      'get_session_summary',
      params: {'p_session_id': sessionDebt},
    );
    final rawSummaryMap = Map<String, dynamic>.from(rawSummary as Map);
    final summaryProjectionProblems = _projectionIssues(
      rawSummaryMap,
      summaryProjectionKeys,
    );
    check(
      'summary.privacy',
      'finance summary has exactly the public projection and no private fields',
      summaryProjectionProblems.isEmpty,
      'keys=${rawSummaryMap.keys.join(',')} '
          'issues=${summaryProjectionProblems.join(';')}',
    );

    final rawManagementSummary = await cohostA.client.rpc(
      'get_session_summary',
      params: {'p_session_id': sessionDebt},
    );
    final rawManagementSummaryMap = Map<String, dynamic>.from(
      rawManagementSummary as Map,
    );
    final managementProjectionProblems = _projectionIssues(
      rawManagementSummaryMap,
      summaryProjectionKeys,
    );
    final managementFinanceKeysPresentAndNull = summaryFinanceProjectionKeys
        .every(
          (key) =>
              rawManagementSummaryMap.containsKey(key) &&
              rawManagementSummaryMap[key] == null,
        );
    check(
      'summary.management-raw-null',
      'management raw summary keeps every finance key present with null',
      managementProjectionProblems.isEmpty &&
          managementFinanceKeysPresentAndNull,
      'keys=${rawManagementSummaryMap.keys.join(',')} '
          'financePresentAndNull=$managementFinanceKeysPresentAndNull '
          'issues=${managementProjectionProblems.join(';')}',
    );

    final rawHistory = await financeA.client.rpc(
      'list_my_session_history',
      params: {
        'p_limit': 100,
        'p_offset': 0,
        'p_club_id': null,
        'p_from': null,
        'p_to': null,
      },
    );
    final rawHistoryRows = (rawHistory as List)
        .whereType<Map>()
        .map((row) => Map<String, dynamic>.from(row))
        .toList();
    final historyProjectionProblems = _historyProjectionIssues(rawHistory);
    check(
      'history.privacy',
      'every history row has exactly the public projection and no private fields',
      rawHistoryRows.isNotEmpty && historyProjectionProblems.isEmpty,
      'rows=${rawHistoryRows.length} '
          'issues=${historyProjectionProblems.join(';')}',
    );

    final cleanHistoryRow = rawHistoryRows.isEmpty
        ? <String, dynamic>{}
        : Map<String, dynamic>.from(rawHistoryRows.first);
    final laterRowPrivatePayload = <Map<String, dynamic>>[
      cleanHistoryRow,
      <String, dynamic>{
        ...cleanHistoryRow,
        'receiver_snapshot': <String, dynamic>{
          'bank_code': privateBankCode,
          'account_number': privateAccountNumber,
        },
      },
    ];
    final topLevelPrivateHistory = <String, dynamic>{
      ...cleanHistoryRow,
      'account_number': privateAccountNumber,
    };
    final nestedPrivateHistory = <String, dynamic>{
      ...cleanHistoryRow,
      'club_name': <String, dynamic>{
        'ordinary_label': 'HTTP Club A',
        'receiver_snapshot': <String, dynamic>{
          'account_number': privateAccountNumber,
        },
      },
    };
    final laterRowProblems = _historyProjectionIssues(laterRowPrivatePayload);
    check(
      'history.privacy.negative-controls',
      'history validator rejects top-level, nested and later-row private fields',
      _projectionIssues(
            topLevelPrivateHistory,
            historyProjectionKeys,
          ).isNotEmpty &&
          _projectionIssues(
            nestedPrivateHistory,
            historyProjectionKeys,
          ).isNotEmpty &&
          laterRowProblems.any((issue) => issue.contains('row[1]')),
      'top=${_projectionIssues(topLevelPrivateHistory, historyProjectionKeys)} '
          'nested=${_projectionIssues(nestedPrivateHistory, historyProjectionKeys)} '
          'later=$laterRowProblems',
    );

    final topLevelPrivateSummary = <String, dynamic>{
      ...rawSummaryMap,
      'bank_code': privateBankCode,
    };
    final nestedPrivateSummary = <String, dynamic>{
      ...rawSummaryMap,
      'club_name': <String, dynamic>{
        'ordinary_label': 'HTTP Club A',
        'receiver_snapshot': <String, dynamic>{
          'bank_code': privateBankCode,
          'account_number': privateAccountNumber,
        },
      },
    };
    check(
      'summary.privacy.negative-controls',
      'summary validator rejects top-level and nested bank/account/receiver fields',
      _projectionIssues(
            topLevelPrivateSummary,
            summaryProjectionKeys,
          ).isNotEmpty &&
          _projectionIssues(
            nestedPrivateSummary,
            summaryProjectionKeys,
          ).isNotEmpty,
      'top=${_projectionIssues(topLevelPrivateSummary, summaryProjectionKeys)} '
          'nested=${_projectionIssues(nestedPrivateSummary, summaryProjectionKeys)}',
    );

    final sourceMemberContacts = await rows(
      admin,
      'member_contacts',
      columns: 'member_id,phone_number,contact_note',
    );
    final sourcePlayerContacts = await rows(
      admin,
      'session_player_contacts',
      columns: 'player_id,phone_number',
    );
    final sourceClubBanks = await rows(
      admin,
      'club_bank_accounts',
      columns: 'bank_code,account_number,account_name',
    );
    final sourceHostBanks = await rows(
      admin,
      'host_bank_accounts',
      columns: 'bank_code,account_number,account_name',
    );
    final sourceReceivers = await rows(
      admin,
      'sessions',
      columns: 'id,receiver_snapshot',
      column: 'id',
      value: sessionPrivate,
    );
    final privateFixtureRowsPresent =
        sourceMemberContacts.any(
          (row) =>
              row['member_id'] == memberAContactRow &&
              row['phone_number'] == privateMemberPhone &&
              row['contact_note'] == privateContactNote,
        ) &&
        sourcePlayerContacts.any(
          (row) => row['phone_number'] == privatePlayerPhone,
        ) &&
        sourceClubBanks.any(
          (row) =>
              row['bank_code'] == privateBankCode &&
              row['account_number'] == privateAccountNumber &&
              row['account_name'] == privateAccountName,
        ) &&
        sourceHostBanks.isNotEmpty &&
        sourceReceivers.any((row) {
          final snapshot = row['receiver_snapshot'];
          return snapshot is Map &&
              snapshot['bank_code'] == privateBankCode &&
              snapshot['account_number'] == privateAccountNumber;
        });
    check(
      'privacy.fixture-private-data',
      'fixture stores fake phone, bank, account and receiver markers outside projections',
      privateFixtureRowsPresent,
      'memberContacts=${sourceMemberContacts.length} '
          'playerContacts=${sourcePlayerContacts.length} '
          'clubBanks=${sourceClubBanks.length} '
          'hostBanks=${sourceHostBanks.length} '
          'privateReceivers=${sourceReceivers.length}',
    );

    // --- Finance actions allowed after complete ---
    await expectError(
      'finance.post-expense-after-complete.rejected',
      'new expense is rejected after complete',
      () => financeA.finance.postSessionExpense(
        requestId: postExpenseAttemptRequest,
        sessionId: sessionDebt,
        category: 'other',
        title: 'HTTP should not be posted',
        amountVnd: 1000,
      ),
      'INVALID_STATE',
    );
    final afterRejectedExpense = await financeA.finance.getSessionFinance(
      sessionDebt,
    );
    check(
      'finance.post-expense-after-complete.no-side-effect',
      'rejected post-expense adds no expense and does not bump billing input',
      afterRejectedExpense.expenses.length == 1 &&
          afterRejectedExpense.billingInputVersion == 2,
      'expenses=${afterRejectedExpense.expenses.length} '
          'billingInputVersion=${afterRejectedExpense.billingInputVersion}',
    );

    final reversePayment = await financeA.finance.reversePayment(
      requestId: reversePaymentRequest,
      paymentId: seededDebtPayment,
      reason: 'HTTP reverse after complete',
    );
    final reversePaymentRetry = await financeA.finance.reversePayment(
      requestId: reversePaymentRequest,
      paymentId: seededDebtPayment,
      reason: 'HTTP reverse after complete',
    );
    final paymentLedgers = await rows(
      admin,
      'club_transactions',
      columns: 'id',
      column: 'source_payment_id',
      value: seededDebtPayment,
    );
    final paymentLedgerId = paymentLedgers.single['id'].toString();
    final paymentReversalCount = await countRows(
      admin,
      'club_transactions',
      column: 'reversal_of',
      value: paymentLedgerId,
    );
    final debtAfterReverse = await financeA.finance.getSessionFinance(
      sessionDebt,
    );
    check(
      'finance.reverse-payment-after-complete',
      'finance reverses a confirmed payment after complete; retry keeps one reversal and history',
      reversePayment.status == 'reversed' &&
          reversePaymentRetry.paymentId == reversePayment.paymentId &&
          reversePaymentRetry.status == 'reversed' &&
          paymentReversalCount == 1 &&
          debtAfterReverse.outstandingTotalVnd == 300000 &&
          debtAfterReverse.payments.single.status == 'reversed',
      'status=${reversePayment.status} reversals=$paymentReversalCount '
          'outstanding=${debtAfterReverse.outstandingTotalVnd}',
    );

    final cashPayment = await financeA.finance.recordCashPayment(
      requestId: cashRequest,
      playerId: guestPlayer.id,
      amountVnd: 100000,
      reference: 'HTTP-CASH-AFTER-COMPLETE',
    );
    final cashPaymentRetry = await financeA.finance.recordCashPayment(
      requestId: cashRequest,
      playerId: guestPlayer.id,
      amountVnd: 100000,
      reference: 'HTTP-CASH-AFTER-COMPLETE',
    );
    final guestPaymentCount = await countRows(
      admin,
      'payments',
      column: 'session_player_id',
      value: guestPlayer.id,
    );
    final cashLedgerCount = await countRows(
      admin,
      'club_transactions',
      column: 'source_payment_id',
      value: cashPayment.paymentId,
      secondColumn: 'source_type',
      secondValue: 'payment',
    );
    final afterCash = await financeA.finance.getSessionFinance(sessionDebt);
    check(
      'finance.cash-after-complete',
      'cash payment is allowed after complete; retry produces one payment and one ledger entry',
      cashPayment.status == 'confirmed' &&
          cashPaymentRetry.paymentId == cashPayment.paymentId &&
          guestPaymentCount == 1 &&
          cashLedgerCount == 1 &&
          afterCash.outstandingTotalVnd == 200000,
      'status=${cashPayment.status} guestPayments=$guestPaymentCount '
          'ledger=$cashLedgerCount outstanding=${afterCash.outstandingTotalVnd}',
    );

    final submittedMember = await memberA.finance.submitPayment(
      requestId: submitMemberRequest,
      playerId: memberPlayer.id,
      amountVnd: 100000,
      reference: 'HTTP-BANK-MEMBER',
    );
    final submittedMemberRetry = await memberA.finance.submitPayment(
      requestId: submitMemberRequest,
      playerId: memberPlayer.id,
      amountVnd: 100000,
      reference: 'HTTP-BANK-MEMBER',
    );
    check(
      'finance.submit-payment-after-complete',
      'participant submit is allowed after complete and request_id replays the same payment',
      submittedMember.status == 'submitted' &&
          submittedMemberRetry.paymentId == submittedMember.paymentId &&
          submittedMemberRetry.status == 'submitted',
      'status=${submittedMember.status} id=${submittedMember.paymentId}',
    );

    final confirmedMember = await financeA.finance.confirmPayment(
      requestId: confirmMemberRequest,
      paymentId: submittedMember.paymentId,
    );
    final confirmedMemberRetry = await financeA.finance.confirmPayment(
      requestId: confirmMemberRequest,
      paymentId: submittedMember.paymentId,
    );
    final memberPaymentCount = await countRows(
      admin,
      'payments',
      column: 'session_player_id',
      value: memberPlayer.id,
    );
    final memberLedgerCount = await countRows(
      admin,
      'club_transactions',
      column: 'source_payment_id',
      value: submittedMember.paymentId,
      secondColumn: 'source_type',
      secondValue: 'payment',
    );
    final confirmOperationCount = await countRows(
      admin,
      'operation_requests',
      column: 'operation',
      value: 'confirm_payment',
      secondColumn: 'request_id',
      secondValue: confirmMemberRequest,
    );
    final afterConfirm = await financeA.finance.getSessionFinance(sessionDebt);
    check(
      'finance.confirm-payment-after-complete',
      'finance confirms participant payment after complete; retry adds no duplicate ledger',
      confirmedMember.status == 'confirmed' &&
          confirmedMemberRetry.paymentId == confirmedMember.paymentId &&
          confirmedMemberRetry.status == 'confirmed' &&
          memberPaymentCount == 2 &&
          memberLedgerCount == 1 &&
          confirmOperationCount == 1 &&
          afterConfirm.outstandingTotalVnd == 100000,
      'status=${confirmedMember.status} '
          'payments=$memberPaymentCount ledger=$memberLedgerCount '
          'operations=$confirmOperationCount '
          'outstanding=${afterConfirm.outstandingTotalVnd}',
    );

    final instructions = await memberA.finance.getPaymentInstructions(
      sessionDebt,
    );
    check(
      'finance.instructions-after-complete',
      'participant payment instructions stay current after complete',
      instructions.isCurrent &&
          instructions.amountDueVnd == 150000 &&
          instructions.totalPaidVnd == 100000 &&
          instructions.outstandingVnd == 50000,
      'state=${instructions.billingState} due=${instructions.amountDueVnd} '
          'paid=${instructions.totalPaidVnd} '
          'outstanding=${instructions.outstandingVnd}',
    );

    final beforeRefinalize = await financeA.finance.getSessionFinance(
      sessionDebt,
    );
    final refinalizedDebt = await financeA.finance.finalizeSessionCharges(
      requestId: refinalizeDebtRequest,
      sessionId: sessionDebt,
      expectedVersion: beforeRefinalize.sessionVersion!,
      expectedBillingInputVersion: beforeRefinalize.billingInputVersion,
      reason: 'HTTP refinalize after complete',
    );
    final refinalizedDebtRetry = await financeA.finance.finalizeSessionCharges(
      requestId: refinalizeDebtRequest,
      sessionId: sessionDebt,
      expectedVersion: beforeRefinalize.sessionVersion!,
      expectedBillingInputVersion: beforeRefinalize.billingInputVersion,
      reason: 'HTTP refinalize after complete',
    );
    final debtRevisionCount = await countRows(
      admin,
      'charge_revisions',
      column: 'session_id',
      value: sessionDebt,
    );
    final debtActiveRevisionCount = await countRows(
      admin,
      'charge_revisions',
      column: 'session_id',
      value: sessionDebt,
      secondColumn: 'status',
      secondValue: 'active',
    );
    final afterRefinalize = await financeA.finance.getSessionFinance(
      sessionDebt,
    );
    check(
      'finance.refinalize-after-complete',
      'refinalize is allowed after complete; retry reuses revision 2 with one active revision',
      refinalizedDebt.revisionNo == 2 &&
          refinalizedDebt.allocationTotalVnd == 300000 &&
          refinalizedDebt.billingState == 'current' &&
          refinalizedDebtRetry.revisionId == refinalizedDebt.revisionId &&
          debtRevisionCount == 2 &&
          debtActiveRevisionCount == 1 &&
          afterRefinalize.isCurrent &&
          afterRefinalize.activeRevision?.revisionNo == 2 &&
          afterRefinalize.outstandingTotalVnd == 100000,
      'revision=${refinalizedDebt.revisionNo} '
          'retryRevision=${refinalizedDebtRetry.revisionNo} '
          'revisions=$debtRevisionCount active=$debtActiveRevisionCount '
          'outstanding=${afterRefinalize.outstandingTotalVnd}',
    );

    final submittedReject = await memberA.finance.submitPayment(
      requestId: submitRejectRequest,
      playerId: memberPlayer.id,
      amountVnd: 20000,
      reference: 'HTTP-REJECT-MEMBER',
    );
    final rejectedPayment = await financeA.finance.rejectPayment(
      requestId: rejectRequest,
      paymentId: submittedReject.paymentId,
      reason: 'HTTP reject after complete',
    );
    final rejectedPaymentRetry = await financeA.finance.rejectPayment(
      requestId: rejectRequest,
      paymentId: submittedReject.paymentId,
      reason: 'HTTP reject after complete',
    );
    final debtFinalSummary = await financeA.finance.getSessionSummary(
      sessionDebt,
    );
    check(
      'finance.reject-payment-after-complete',
      'finance rejects a submitted payment after complete; retry is idempotent and does not change paid total',
      rejectedPayment.status == 'rejected' &&
          rejectedPaymentRetry.paymentId == rejectedPayment.paymentId &&
          rejectedPaymentRetry.status == 'rejected' &&
          debtFinalSummary.totalPaidVnd == 200000 &&
          debtFinalSummary.outstandingTotalVnd == 100000 &&
          debtFinalSummary.revisionNo == 2,
      'status=${rejectedPayment.status} paid=${debtFinalSummary.totalPaidVnd} '
          'outstanding=${debtFinalSummary.outstandingTotalVnd} '
          'revision=${debtFinalSummary.revisionNo}',
    );

    // --- Free current session completes with zero allocation and one zero charge ---
    final freeBefore = await ownerA.sessions.getSessionDetail(sessionFree);
    final freeFinanceBefore = await financeA.finance.getSessionFinance(
      sessionFree,
    );
    final freePlayersBefore = await ownerA.sessions.listSessionPlayers(
      sessionFree,
    );
    final freeChargeBefore = freeFinanceBefore.charges.length == 1
        ? freeFinanceBefore.charges.single
        : null;
    check(
      'complete.free-current.precondition',
      'free fixture has one exempt present player, current zero revision and one zero charge',
      freeBefore.lifecycle == 'in_progress' &&
          freeBefore.version == 3 &&
          freePlayersBefore.length == 1 &&
          freePlayersBefore.single.id == freePlayer &&
          freePlayersBefore.single.registrationStatus == 'confirmed' &&
          freePlayersBefore.single.attendanceStatus == 'present' &&
          freePlayersBefore.single.feeExempt &&
          freeFinanceBefore.isCurrent &&
          freeFinanceBefore.sessionVersion == 3 &&
          freeFinanceBefore.activeRevision?.revisionId == freeRevision &&
          freeFinanceBefore.activeRevision?.revisionNo == 1 &&
          freeFinanceBefore.activeRevision?.sourceVersion == 1 &&
          freeFinanceBefore.activeRevision?.allocationTotalVnd == 0 &&
          freeFinanceBefore.charges.length == 1 &&
          freeChargeBefore?.playerId == freePlayer &&
          freeChargeBefore?.amountDueVnd == 0 &&
          freeFinanceBefore.outstandingTotalVnd == 0,
      'lifecycle=${freeBefore.lifecycle} version=${freeBefore.version} '
          'players=${freePlayersBefore.length} '
          'revision=${freeFinanceBefore.activeRevision?.revisionId} '
          'revisionNo=${freeFinanceBefore.activeRevision?.revisionNo} '
          'allocation=${freeFinanceBefore.activeRevision?.allocationTotalVnd} '
          'charges=${freeFinanceBefore.charges.length} '
          'chargePlayer=${freeChargeBefore?.playerId} '
          'chargeDue=${freeChargeBefore?.amountDueVnd} '
          'outstanding=${freeFinanceBefore.outstandingTotalVnd}',
    );
    final completedFree = await ownerA.finance.completeSession(
      requestId: completeFreeRequest,
      sessionId: sessionFree,
      expectedVersion: 3,
    );
    final completedFreeRetry = await ownerA.finance.completeSession(
      requestId: completeFreeRequest,
      sessionId: sessionFree,
      expectedVersion: 3,
    );
    final freeAuditCount = await countRows(
      admin,
      'audit_events',
      column: 'session_id',
      value: sessionFree,
      secondColumn: 'action',
      secondValue: 'SESSION_COMPLETED',
    );
    final freeSummary = await financeA.finance.getSessionSummary(sessionFree);
    check(
      'complete.free-current.success',
      'free current session completes and retry does not duplicate audit',
      completedFree.lifecycle == 'completed' &&
          completedFree.version == 4 &&
          completedFreeRetry.version == 4 &&
          freeAuditCount == 1 &&
          freeSummary.presentCount == 1 &&
          freeSummary.confirmedCount == 1 &&
          freeSummary.billingState == 'current' &&
          freeSummary.amountDueTotalVnd == 0 &&
          freeSummary.totalPaidVnd == 0 &&
          freeSummary.outstandingTotalVnd == 0,
      'lifecycle=${completedFree.lifecycle} version=${completedFree.version} '
          'audit=$freeAuditCount due=${freeSummary.amountDueTotalVnd} '
          'outstanding=${freeSummary.outstandingTotalVnd}',
    );

    final freeFinanceAfter = await financeA.finance.getSessionFinance(
      sessionFree,
    );
    final freeChargeAfter = freeFinanceAfter.charges.length == 1
        ? freeFinanceAfter.charges.single
        : null;
    final freeRevisionRows = await rows(
      admin,
      'charge_revisions',
      columns: 'id,status,source_version',
      column: 'session_id',
      value: sessionFree,
    );
    final freeChargeRows = await rows(
      admin,
      'session_charges',
      columns: 'id,revision_id,session_player_id,amount_due_vnd',
      column: 'revision_id',
      value: freeRevision,
    );
    check(
      'complete.free-current.charge-preserved',
      'zero charge keeps the same player/revision after complete and retry',
      freeFinanceAfter.lifecycle == 'completed' &&
          freeFinanceAfter.isCurrent &&
          freeFinanceAfter.sessionVersion == 4 &&
          freeFinanceAfter.activeRevision?.revisionId == freeRevision &&
          freeFinanceAfter.activeRevision?.revisionNo == 1 &&
          freeFinanceAfter.activeRevision?.allocationTotalVnd == 0 &&
          freeFinanceAfter.charges.length == 1 &&
          freeChargeAfter?.playerId == freePlayer &&
          freeChargeAfter?.amountDueVnd == 0 &&
          freeFinanceAfter.outstandingTotalVnd == 0 &&
          freeRevisionRows.length == 1 &&
          freeRevisionRows.single['id'] == freeRevision &&
          freeRevisionRows.single['status'] == 'active' &&
          freeRevisionRows.single['source_version'] == 1 &&
          freeChargeRows.length == 1 &&
          freeChargeRows.single['revision_id'] == freeRevision &&
          freeChargeRows.single['session_player_id'] == freePlayer &&
          freeChargeRows.single['amount_due_vnd'] == 0,
      'lifecycle=${freeFinanceAfter.lifecycle} '
          'revision=${freeFinanceAfter.activeRevision?.revisionId} '
          'charges=${freeFinanceAfter.charges.length} '
          'chargePlayer=${freeChargeAfter?.playerId} '
          'chargeDue=${freeChargeAfter?.amountDueVnd} '
          'revisionRows=${freeRevisionRows.length} '
          'chargeRows=${freeChargeRows.length}',
    );

    // --- History scope, filters, pagination and participant privacy ---
    final ownerHistory = await ownerA.sessions.listMySessionHistory(limit: 100);
    final ownerHistoryIds = ownerHistory.sessions
        .map((session) => session.id)
        .toList();
    check(
      'history.owner-scope',
      'owner history contains completed/cancelled sessions and excludes in-progress sessions',
      ownerHistoryIds.length == 5 &&
          ownerHistoryIds.contains(sessionDebt) &&
          ownerHistoryIds.contains(sessionFree) &&
          ownerHistoryIds.contains(sessionFin) &&
          ownerHistoryIds.contains(sessionCancelled) &&
          ownerHistoryIds.contains(sessionPrivate) &&
          !ownerHistoryIds.contains(sessionStale) &&
          !ownerHistoryIds.contains(sessionVersion) &&
          ownerHistory.sessions.every(
            (session) =>
                session.lifecycle == 'completed' ||
                session.lifecycle == 'cancelled',
          ),
      'ids=${ownerHistoryIds.join(',')}',
    );

    final historyOrder = ownerHistoryIds;
    check(
      'history.order',
      'history is ordered newest first',
      historyOrder.length == 5 &&
          historyOrder[0] == sessionDebt &&
          historyOrder[1] == sessionFree &&
          historyOrder[2] == sessionCancelled &&
          historyOrder[3] == sessionFin &&
          historyOrder[4] == sessionPrivate,
      'order=${historyOrder.join(',')}',
    );

    final clubAFilter = await ownerA.sessions.listMySessionHistory(
      filter: const SessionHistoryFilter(clubId: clubA),
      limit: 100,
    );
    final clubBFilter = await ownerA.sessions.listMySessionHistory(
      filter: const SessionHistoryFilter(clubId: clubB),
      limit: 100,
    );
    check(
      'history.club-filter',
      'history club filter returns only the requested club',
      clubAFilter.sessions.length == 5 && clubBFilter.sessions.isEmpty,
      'clubA=${clubAFilter.sessions.length} '
          'clubB=${clubBFilter.sessions.length}',
    );

    final dateFilter = await ownerA.sessions.listMySessionHistory(
      filter: SessionHistoryFilter(
        from: DateTime.utc(2026, 10, 19),
        to: DateTime.utc(2026, 10, 20, 23, 59, 59),
      ),
      limit: 100,
    );
    final dateFilterIds = dateFilter.sessions
        .map((session) => session.id)
        .toList();
    check(
      'history.date-filter',
      'history date bounds include only 19-20 October sessions',
      dateFilterIds.length == 2 &&
          dateFilterIds.contains(sessionDebt) &&
          dateFilterIds.contains(sessionFree),
      'ids=${dateFilterIds.join(',')}',
    );

    final pageOne = await ownerA.sessions.listMySessionHistory(
      limit: 2,
      offset: 0,
    );
    final pageTwo = await ownerA.sessions.listMySessionHistory(
      limit: 2,
      offset: 2,
    );
    final pageThree = await ownerA.sessions.listMySessionHistory(
      limit: 2,
      offset: 4,
    );
    final pagedIds = [
      ...pageOne.sessions.map((session) => session.id),
      ...pageTwo.sessions.map((session) => session.id),
      ...pageThree.sessions.map((session) => session.id),
    ];
    check(
      'history.pagination',
      'history pagination does not duplicate or drop rows',
      pageOne.sessions.length == 2 &&
          pageTwo.sessions.length == 2 &&
          pageThree.sessions.length == 1 &&
          pagedIds.toSet().length == 5 &&
          pagedIds.join(',') == historyOrder.join(','),
      'pages=${pageOne.sessions.length}/${pageTwo.sessions.length}/'
          '${pageThree.sessions.length} ids=${pagedIds.join(',')}',
    );

    final cohostHistory = await cohostA.sessions.listMySessionHistory(
      limit: 100,
    );
    check(
      'history.cohost-scope',
      'cohost history includes only sessions with management access',
      cohostHistory.sessions.length == 1 &&
          cohostHistory.sessions.single.id == sessionDebt,
      'ids=${cohostHistory.sessions.map((session) => session.id).join(',')}',
    );

    final financeHistory = await financeA.sessions.listMySessionHistory(
      limit: 100,
    );
    check(
      'history.finance-scope',
      'club treasurer history includes club finance sessions',
      financeHistory.sessions.length == 5 &&
          financeHistory.sessions.any((session) => session.id == sessionDebt),
      'count=${financeHistory.sessions.length}',
    );

    final participantHistory = await memberA.sessions.listMySessionHistory(
      limit: 100,
    );
    final outsiderHistory = await outsider.sessions.listMySessionHistory(
      limit: 100,
    );
    final ownerBHistory = await ownerB.sessions.listMySessionHistory(
      limit: 100,
    );
    check(
      'history.participant-and-guest-scope',
      'participant, outsider and cross-club histories do not leak managed sessions',
      participantHistory.sessions.isEmpty &&
          outsiderHistory.sessions.isEmpty &&
          ownerBHistory.sessions.length == 1 &&
          ownerBHistory.sessions.single.id == sessionClubB,
      'participant=${participantHistory.sessions.length} '
          'outsider=${outsiderHistory.sessions.length} '
          'ownerB=${ownerBHistory.sessions.map((session) => session.id).join(',')}',
    );

    await expectError(
      'history.invalid-range',
      'history rejects a reversed date range',
      () => ownerA.sessions.listMySessionHistory(
        filter: SessionHistoryFilter(
          from: DateTime.utc(2026, 10, 20),
          to: DateTime.utc(2026, 10, 19),
        ),
        limit: 20,
      ),
      'INVALID_INPUT',
    );

    final ownerManaged = await ownerA.sessions.listMySessions(limit: 100);
    final cohostManaged = await cohostA.sessions.listMySessions(limit: 100);
    check(
      'list.after-complete',
      'completed sessions remain in management lists for owner and cohost',
      ownerManaged.any((session) => session.id == sessionDebt) &&
          ownerManaged.any((session) => session.id == sessionFree) &&
          cohostManaged.any((session) => session.id == sessionDebt),
      'owner=${ownerManaged.length} cohost=${cohostManaged.length}',
    );

    final participantDetailAfter = await memberA.sessions.getSessionDetail(
      sessionDebt,
    );
    check(
      'scope.participant.detail-after-complete',
      'participant still reads completed detail with own registration',
      participantDetailAfter.lifecycle == 'completed' &&
          participantDetailAfter.version == 8 &&
          participantDetailAfter.myRegistration?.registrationStatus ==
              'confirmed',
      'lifecycle=${participantDetailAfter.lifecycle} '
          'version=${participantDetailAfter.version}',
    );

    // --- Finance after complete: reverse expense, stale, refinalize, no new expense ---
    final finBefore = await financeA.finance.getSessionFinance(sessionFin);
    check(
      'finance.completed.precondition',
      'finance fixture is completed with current 100000 allocation',
      finBefore.lifecycle == 'completed' &&
          finBefore.isCurrent &&
          finBefore.sessionVersion == 4 &&
          finBefore.outstandingTotalVnd == 100000 &&
          finBefore.expenses.length == 1,
      'lifecycle=${finBefore.lifecycle} state=${finBefore.billingState} '
          'outstanding=${finBefore.outstandingTotalVnd}',
    );

    final reversedExpense = await financeA.finance.reverseSessionExpense(
      requestId: reverseExpenseRequest,
      sessionId: sessionFin,
      expenseId: expenseFin,
      reason: 'HTTP reverse expense after complete',
    );
    final reversedExpenseRetry = await financeA.finance.reverseSessionExpense(
      requestId: reverseExpenseRequest,
      sessionId: sessionFin,
      expenseId: expenseFin,
      reason: 'HTTP reverse expense after complete',
    );
    final finExpenseLedgers = await rows(
      admin,
      'club_transactions',
      columns: 'id',
      column: 'source_expense_id',
      value: expenseFin,
    );
    final finExpenseLedgerId = finExpenseLedgers.single['id'].toString();
    final finExpenseReversalCount = await countRows(
      admin,
      'club_transactions',
      column: 'reversal_of',
      value: finExpenseLedgerId,
    );
    final finAfterReverse = await financeA.finance.getSessionFinance(
      sessionFin,
    );
    check(
      'finance.reverse-expense-after-complete',
      'expense reversal is allowed after complete, is idempotent and makes billing stale',
      reversedExpense.status == 'reversed' &&
          reversedExpenseRetry.expenseId == reversedExpense.expenseId &&
          reversedExpenseRetry.status == 'reversed' &&
          finExpenseReversalCount == 1 &&
          finAfterReverse.isStale &&
          finAfterReverse.outstandingTotalVnd == 100000,
      'status=${reversedExpense.status} reversals=$finExpenseReversalCount '
          'state=${finAfterReverse.billingState} '
          'outstanding=${finAfterReverse.outstandingTotalVnd}',
    );

    await expectError(
      'finance.post-expense-fin-after-complete.rejected',
      'new expense remains rejected on a completed session',
      () => financeA.finance.postSessionExpense(
        requestId: postExpenseAttemptRequest,
        sessionId: sessionFin,
        category: 'other',
        title: 'HTTP should not be posted on completed',
        amountVnd: 1000,
      ),
      'INVALID_STATE',
    );
    final finExpenseRows = await countRows(
      admin,
      'session_expenses',
      column: 'session_id',
      value: sessionFin,
    );
    check(
      'finance.post-expense-fin-after-complete.no-side-effect',
      'rejected completed-session expense leaves one historical expense row',
      finExpenseRows == 1,
      'expenses=$finExpenseRows',
    );

    final refinalizedFin = await financeA.finance.finalizeSessionCharges(
      requestId: refinalizeFinRequest,
      sessionId: sessionFin,
      expectedVersion: 4,
      expectedBillingInputVersion: 5,
      reason: 'HTTP refinalize after reversing expense',
    );
    final refinalizedFinRetry = await financeA.finance.finalizeSessionCharges(
      requestId: refinalizeFinRequest,
      sessionId: sessionFin,
      expectedVersion: 4,
      expectedBillingInputVersion: 5,
      reason: 'HTTP refinalize after reversing expense',
    );
    final finRevisionCount = await countRows(
      admin,
      'charge_revisions',
      column: 'session_id',
      value: sessionFin,
    );
    final finActiveRevisionCount = await countRows(
      admin,
      'charge_revisions',
      column: 'session_id',
      value: sessionFin,
      secondColumn: 'status',
      secondValue: 'active',
    );
    final finSummary = await financeA.finance.getSessionSummary(sessionFin);
    check(
      'finance.refinalize-fin-after-complete',
      'refinalize after complete and expense reversal creates one current zero revision',
      refinalizedFin.revisionNo == 2 &&
          refinalizedFin.allocationTotalVnd == 0 &&
          refinalizedFin.billingState == 'current' &&
          refinalizedFinRetry.revisionId == refinalizedFin.revisionId &&
          finRevisionCount == 2 &&
          finActiveRevisionCount == 1 &&
          finSummary.billingState == 'current' &&
          finSummary.expensesTotalVnd == 0 &&
          finSummary.amountDueTotalVnd == 0 &&
          finSummary.outstandingTotalVnd == 0,
      'revision=${refinalizedFin.revisionNo} '
          'allocation=${refinalizedFin.allocationTotalVnd} '
          'revisions=$finRevisionCount active=$finActiveRevisionCount '
          'expenses=${finSummary.expensesTotalVnd}',
    );

    // --- Concurrency HTTP / Auth verification (competing clients & idempotency) ---
    final ownerB1 = ownerB;
    final ownerB2 = await login(
      'ownerB-client2',
      'ownerb@example.test',
      recordAuthCheck: false,
    );

    // 1. Concurrent complete with same request_id (idempotent replay)
    List<Session>? ccCompleteResults;
    Object? ccCompleteErr;
    try {
      ccCompleteResults = await Future.wait([
        ownerB1.finance.completeSession(
          requestId: completeCcReplayReq,
          sessionId: sessionCcComplete,
          expectedVersion: 3,
        ),
        ownerB2.finance.completeSession(
          requestId: completeCcReplayReq,
          sessionId: sessionCcComplete,
          expectedVersion: 3,
        ),
      ]);
    } catch (e) {
      ccCompleteErr = e;
    }
    final ccCompleteAuditCount = await countRows(
      admin,
      'audit_events',
      column: 'session_id',
      value: sessionCcComplete,
      secondColumn: 'action',
      secondValue: 'SESSION_COMPLETED',
    );
    final ccCompleteOpCount = await countRows(
      admin,
      'operation_requests',
      column: 'operation',
      value: 'complete_session',
      secondColumn: 'request_id',
      secondValue: completeCcReplayReq,
    );
    check(
      'concurrency.complete.replay-idempotent',
      'concurrent complete requests with same request_id replay identically without duplicating audit or version',
      ccCompleteResults != null &&
          ccCompleteResults.length == 2 &&
          ccCompleteResults[0].lifecycle == 'completed' &&
          ccCompleteResults[0].version == 4 &&
          ccCompleteResults[1].lifecycle == 'completed' &&
          ccCompleteResults[1].version == 4 &&
          ccCompleteAuditCount == 1 &&
          ccCompleteOpCount == 1,
      ccCompleteErr != null
          ? errorText(ccCompleteErr)
          : 'v1=${ccCompleteResults?[0].version} v2=${ccCompleteResults?[1].version} '
              'audit=$ccCompleteAuditCount ops=$ccCompleteOpCount',
    );

    // 2. Concurrent complete with different request_ids (competing version conflict)
    Session? ccCompWinner;
    Object? ccCompLoserError;
    Object? ccCompGeneralErr;
    try {
      Future<void> runCompleteA() async {
        try {
          final res = await ownerB1.finance.completeSession(
            requestId: completeCcCompA,
            sessionId: sessionCcCompeting,
            expectedVersion: 3,
          );
          ccCompWinner = res;
        } catch (e) {
          ccCompLoserError = e;
        }
      }

      Future<void> runCompleteB() async {
        try {
          final res = await ownerB2.finance.completeSession(
            requestId: completeCcCompB,
            sessionId: sessionCcCompeting,
            expectedVersion: 3,
          );
          ccCompWinner = res;
        } catch (e) {
          ccCompLoserError = e;
        }
      }

      await Future.wait([runCompleteA(), runCompleteB()]);
    } catch (e) {
      ccCompGeneralErr = e;
    }
    final ccCompAuditCount = await countRows(
      admin,
      'audit_events',
      column: 'session_id',
      value: sessionCcCompeting,
      secondColumn: 'action',
      secondValue: 'SESSION_COMPLETED',
    );
    final loserErrStr = ccCompLoserError != null ? errorText(ccCompLoserError!) : '';
    final h2CompleteNegativeControlsOk = verifyH2NegativeControls();
    check(
      'concurrency.complete.competing-conflict',
      'concurrent complete requests with different request_ids allow only one commit and reject competitor with conflict',
      ccCompGeneralErr == null &&
          ccCompWinner != null &&
          ccCompWinner!.lifecycle == 'completed' &&
          ccCompWinner!.version == 4 &&
          ccCompLoserError != null &&
          isCompleteConflictError(ccCompLoserError) &&
          h2CompleteNegativeControlsOk &&
          ccCompAuditCount == 1,
      ccCompGeneralErr != null
          ? errorText(ccCompGeneralErr)
          : 'winnerVersion=${ccCompWinner?.version} loserError=$loserErrStr '
              'isConflictDomain=${isCompleteConflictError(ccCompLoserError)} '
              'negControls=$h2CompleteNegativeControlsOk audit=$ccCompAuditCount',
    );

    // 3. Concurrent cash payment with same request_id (idempotent replay)
    List<PaymentResult>? ccCashResults;
    Object? ccCashErr;
    try {
      ccCashResults = await Future.wait([
        ownerB1.finance.recordCashPayment(
          requestId: cashCcReplayReq,
          playerId: playerCcPay,
          amountVnd: 50000,
        ),
        ownerB2.finance.recordCashPayment(
          requestId: cashCcReplayReq,
          playerId: playerCcPay,
          amountVnd: 50000,
        ),
      ]);
    } catch (e) {
      ccCashErr = e;
    }
    final ccCashPaymentsCount = await countRows(
      admin,
      'payments',
      column: 'session_player_id',
      value: playerCcPay,
      secondColumn: 'amount_vnd',
      secondValue: 50000,
    );
    final ccCashLedgerCount = ccCashResults != null && ccCashResults.isNotEmpty
        ? await countRows(
            admin,
            'club_transactions',
            column: 'source_payment_id',
            value: ccCashResults[0].paymentId,
          )
        : 0;
    final ccCashOpCount = await countRows(
      admin,
      'operation_requests',
      column: 'operation',
      value: 'record_cash_payment',
      secondColumn: 'request_id',
      secondValue: cashCcReplayReq,
    );
    check(
      'concurrency.cash.replay-idempotent',
      'concurrent cash payments with same request_id produce one payment, one ledger entry and idempotent result',
      ccCashResults != null &&
          ccCashResults.length == 2 &&
          ccCashResults[0].paymentId == ccCashResults[1].paymentId &&
          ccCashResults[0].status == 'confirmed' &&
          ccCashResults[1].status == 'confirmed' &&
          ccCashPaymentsCount == 1 &&
          ccCashLedgerCount == 1 &&
          ccCashOpCount == 1,
      ccCashErr != null
          ? errorText(ccCashErr)
          : 'p1=${ccCashResults?[0].paymentId} p2=${ccCashResults?[1].paymentId} '
              'payments=$ccCashPaymentsCount ledger=$ccCashLedgerCount ops=$ccCashOpCount',
    );

    // 4. Concurrent competing cash payments with different request_ids (no over-collect)
    PaymentResult? ccPayWinner;
    Object? ccPayLoserError;
    Object? ccPayGeneralErr;
    try {
      Future<void> runPayA() async {
        try {
          final res = await ownerB1.finance.recordCashPayment(
            requestId: cashCcCompA,
            playerId: playerCcPay,
            amountVnd: 70000,
          );
          ccPayWinner = res;
        } catch (e) {
          ccPayLoserError = e;
        }
      }

      Future<void> runPayB() async {
        try {
          final res = await ownerB2.finance.recordCashPayment(
            requestId: cashCcCompB,
            playerId: playerCcPay,
            amountVnd: 70000,
          );
          ccPayWinner = res;
        } catch (e) {
          ccPayLoserError = e;
        }
      }

      await Future.wait([runPayA(), runPayB()]);
    } catch (e) {
      ccPayGeneralErr = e;
    }
    final totalConfirmedPayRows = await countRows(
      admin,
      'payments',
      column: 'session_player_id',
      value: playerCcPay,
      secondColumn: 'status',
      secondValue: 'confirmed',
    );
    SessionSummary? summaryAfterComp;
    try {
      summaryAfterComp = await ownerB1.finance.getSessionSummary(sessionCcPay);
    } catch (e) {
      ccPayGeneralErr ??= e;
    }
    final payLoserErrStr = ccPayLoserError != null ? errorText(ccPayLoserError!) : '';
    final h2CashNegativeControlsOk = verifyH2NegativeControls();
    check(
      'concurrency.cash.competing-no-overcollect',
      'concurrent competing cash payments with different request_ids reject over-collection and preserve correct debt',
      ccPayGeneralErr == null &&
          ccPayWinner != null &&
          ccPayWinner!.status == 'confirmed' &&
          ccPayLoserError != null &&
          isCashOvercollectError(ccPayLoserError) &&
          h2CashNegativeControlsOk &&
          totalConfirmedPayRows == 2 &&
          summaryAfterComp != null &&
          summaryAfterComp.totalPaidVnd == 120000 &&
          summaryAfterComp.outstandingTotalVnd == 30000,
      ccPayGeneralErr != null
          ? errorText(ccPayGeneralErr)
          : 'winnerPay=${ccPayWinner?.paymentId} loserErr=$payLoserErrStr '
              'isOvercollectDomain=${isCashOvercollectError(ccPayLoserError)} '
              'negControls=$h2CashNegativeControlsOk '
              'totalPays=$totalConfirmedPayRows paid=${summaryAfterComp?.totalPaidVnd} '
              'outstanding=${summaryAfterComp?.outstandingTotalVnd}',
    );

    // 5. Concurrent confirm payment with same request_id (idempotent replay)
    PaymentResult? submittedMemberPay;
    List<PaymentResult>? ccConfirmResults;
    Object? ccConfirmErr;
    try {
      submittedMemberPay = await memberA.finance.submitPayment(
        requestId: submitMemberCcReq,
        playerId: playerCcPay,
        amountVnd: 30000,
        reference: 'MEMBER-A-CLEAR-DEBT',
      );
      ccConfirmResults = await Future.wait([
        ownerB1.finance.confirmPayment(
          requestId: confirmCcReq,
          paymentId: submittedMemberPay.paymentId,
        ),
        ownerB2.finance.confirmPayment(
          requestId: confirmCcReq,
          paymentId: submittedMemberPay.paymentId,
        ),
      ]);
    } catch (e) {
      ccConfirmErr = e;
    }
    final confirmLedgerCount = submittedMemberPay != null
        ? await countRows(
            admin,
            'club_transactions',
            column: 'source_payment_id',
            value: submittedMemberPay.paymentId,
          )
        : 0;
    final confirmOpCount = await countRows(
      admin,
      'operation_requests',
      column: 'operation',
      value: 'confirm_payment',
      secondColumn: 'request_id',
      secondValue: confirmCcReq,
    );
    SessionSummary? finalCcPaySummary;
    try {
      finalCcPaySummary = await ownerB1.finance.getSessionSummary(sessionCcPay);
    } catch (e) {
      ccConfirmErr ??= e;
    }
    check(
      'concurrency.confirm.replay-idempotent',
      'concurrent confirm_payment requests with same request_id produce one ledger entry and clear debt',
      ccConfirmErr == null &&
          ccConfirmResults != null &&
          ccConfirmResults.length == 2 &&
          ccConfirmResults[0].status == 'confirmed' &&
          ccConfirmResults[1].status == 'confirmed' &&
          confirmLedgerCount == 1 &&
          confirmOpCount == 1 &&
          finalCcPaySummary != null &&
          finalCcPaySummary.outstandingTotalVnd == 0,
      ccConfirmErr != null
          ? errorText(ccConfirmErr)
          : 'status1=${ccConfirmResults?[0].status} status2=${ccConfirmResults?[1].status} '
              'ledger=$confirmLedgerCount ops=$confirmOpCount outstanding=${finalCcPaySummary?.outstandingTotalVnd}',
    );

    // 6. Transport drop response after server commit, then retry
    final dropProxy = DropResponseAfterCommitClient(
      http.Client(),
      targetPath: 'record_cash_payment',
    );
    final dropActor = await login(
      'ownerB-drop',
      'ownerb@example.test',
      httpClient: dropProxy,
      recordAuthCheck: false,
    );
    var simulatedDropCaught = false;
    try {
      await dropActor.finance.recordCashPayment(
        requestId: dropResponseReq,
        playerId: playerCcDrop,
        amountVnd: 60000,
      );
    } catch (e) {
      simulatedDropCaught = e is http.ClientException &&
          dropProxy.dropped &&
          dropProxy.droppedStatusCode == 200 &&
          dropProxy.drained;
    }

    // H1 Pre-retry verification: prove server committed BEFORE retry
    final preRetryOps = await admin
        .from('operation_requests')
        .select()
        .eq('request_id', dropResponseReq);
    final preRetryPayments = await admin
        .from('payments')
        .select()
        .eq('session_player_id', playerCcDrop)
        .eq('amount_vnd', 60000)
        .eq('status', 'confirmed');
    final String? baselinePaymentId = preRetryPayments.isNotEmpty
        ? preRetryPayments[0]['id'] as String?
        : null;
    final preRetryLedger = baselinePaymentId != null
        ? await admin
            .from('club_transactions')
            .select()
            .eq('source_payment_id', baselinePaymentId)
        : <Map<String, dynamic>>[];
    final preRetrySummary = await ownerB1.finance.getSessionSummary(sessionCcDrop);
    final preRetryCommitted = preRetryOps.length == 1 &&
        preRetryOps[0]['operation'] == 'record_cash_payment' &&
        preRetryOps[0]['actor_user_id'] == dropActor.user.id &&
        preRetryPayments.length == 1 &&
        baselinePaymentId != null &&
        preRetryLedger.length == 1 &&
        preRetrySummary.outstandingTotalVnd == 40000;

    // H1 Negative control: mock client with non-200 (HTTP 400) must NOT be dropped as post-commit
    var h1NegativeControlPassed = false;
    final non200Proxy = DropResponseAfterCommitClient(
      StaticStatusClient(400),
      targetPath: 'record_cash_payment',
    );
    try {
      final dummyReq = http.Request(
        'POST',
        Uri.parse('http://127.0.0.1:54321/rest/v1/rpc/record_cash_payment'),
      );
      final non200Resp = await non200Proxy.send(dummyReq);
      h1NegativeControlPassed = !non200Proxy.dropped &&
          non200Proxy.droppedStatusCode == null &&
          non200Resp.statusCode == 400;
    } catch (_) {
      h1NegativeControlPassed = false;
    }

    PaymentResult? dropRetryResult;
    Object? dropRetryErr;
    try {
      dropRetryResult = await ownerB1.finance.recordCashPayment(
        requestId: dropResponseReq,
        playerId: playerCcDrop,
        amountVnd: 60000,
      );
    } catch (e) {
      dropRetryErr = e;
    }
    final dropPaymentRows = await countRows(
      admin,
      'payments',
      column: 'session_player_id',
      value: playerCcDrop,
      secondColumn: 'amount_vnd',
      secondValue: 60000,
    );
    final dropLedgerRows = dropRetryResult != null
        ? await countRows(
            admin,
            'club_transactions',
            column: 'source_payment_id',
            value: dropRetryResult.paymentId,
          )
        : 0;
    final dropOpRows = await countRows(
      admin,
      'operation_requests',
      column: 'operation',
      value: 'record_cash_payment',
      secondColumn: 'request_id',
      secondValue: dropResponseReq,
    );
    SessionSummary? dropSummary;
    try {
      dropSummary = await ownerB1.finance.getSessionSummary(sessionCcDrop);
    } catch (e) {
      dropRetryErr ??= e;
    }
    check(
      'concurrency.drop-response.retry-no-duplicate',
      'simulated network drop after server commit succeeds on retry without duplicate payment or ledger entries',
      dropRetryErr == null &&
          simulatedDropCaught &&
          preRetryCommitted &&
          h1NegativeControlPassed &&
          dropRetryResult != null &&
          dropRetryResult.status == 'confirmed' &&
          dropRetryResult.paymentId == baselinePaymentId &&
          dropPaymentRows == 1 &&
          dropLedgerRows == 1 &&
          dropOpRows == 1 &&
          dropSummary != null &&
          dropSummary.outstandingTotalVnd == 40000,
      dropRetryErr != null
          ? errorText(dropRetryErr)
          : 'dropCaught=$simulatedDropCaught preCommitted=$preRetryCommitted '
              'negControl=$h1NegativeControlPassed baselineId=$baselinePaymentId '
              'retryId=${dropRetryResult?.paymentId} payments=$dropPaymentRows '
              'ledger=$dropLedgerRows ops=$dropOpRows '
              'outstanding=${dropSummary?.outstandingTotalVnd}',
    );

    final passed = checks.where((item) => item['status'] == 'PASS').length;
    final failed = checks.where((item) => item['status'] == 'FAIL').length;
    final finishedAt = DateTime.now().toUtc();
    final evidenceDir = Platform.environment['BH07_HTTP_EVIDENCE_DIR'];
    final summary = <String, Object?>{
      'ticket': 'BH-07 HTTP/Auth verification',
      'generated_at_utc': finishedAt.toIso8601String(),
      'started_at_utc': startedAt.toIso8601String(),
      'duration_ms': finishedAt.difference(startedAt).inMilliseconds,
      'base_sha': Platform.environment['BH07_HTTP_BASE_SHA'],
      'tested_sha': Platform.environment['BH07_HTTP_TESTED_SHA'],
      'api_url': baseUrl,
      'runtime': {
        'dart': Platform.version,
        'executable': Platform.resolvedExecutable,
        'operating_system': Platform.operatingSystem,
        'operating_system_version': Platform.operatingSystemVersion,
      },
      'counts': {'total': checks.length, 'passed': passed, 'failed': failed},
      'checks': checks,
    };
    final encoded = const JsonEncoder.withIndent('  ').convert(summary);
    if (evidenceDir != null && evidenceDir.isNotEmpty) {
      final directory = Directory(evidenceDir);
      directory.createSync(recursive: true);
      File('${directory.path}/summary.json').writeAsStringSync(encoded);
    }
    stdout.writeln('BH07_HTTP_SUMMARY $encoded');
    expect(
      failed,
      0,
      reason:
          'Failed checks: ${checks.where((item) => item['status'] == 'FAIL').map((item) => item['id']).join(', ')}',
    );
  });
}
