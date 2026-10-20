import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide Session;

import 'package:badminton_hub/data/finance_repository.dart';
import 'package:badminton_hub/data/session_repository.dart';
import 'package:badminton_hub/models/session.dart';

class MockSupabaseClient extends Mock implements SupabaseClient {}

/// Builder RPC giả: `await` chỉ cần `then` trả về JSON đã chuẩn bị.
class FakeRpcBuilder extends Fake implements PostgrestFilterBuilder<dynamic> {
  FakeRpcBuilder(this._result);

  final dynamic _result;

  @override
  Future<R> then<R>(
    FutureOr<R> Function(dynamic value) onValue, {
    Function? onError,
  }) {
    return Future.value(onValue(_result));
  }
}

void main() {
  late MockSupabaseClient client;
  String? calledFunction;
  Map<String, dynamic>? calledParams;

  setUpAll(() {
    registerFallbackValue('');
    registerFallbackValue(<String, dynamic>{});
  });

  setUp(() {
    client = MockSupabaseClient();
    calledFunction = null;
    calledParams = null;
  });

  void stubRpc(dynamic result) {
    when(
      () => client.rpc(any(), params: any(named: 'params')),
    ).thenAnswer((invocation) {
      calledFunction = invocation.positionalArguments[0] as String;
      calledParams = Map<String, dynamic>.from(
        invocation.namedArguments[#params] as Map,
      );
      return FakeRpcBuilder(result);
    });
  }

  test('getSessionSummary gọi đúng RPC/DTO và giữ tiền null', () async {
    stubRpc({
      'session_id': 's1',
      'lifecycle': 'completed',
      'can_manage': true,
      'can_view_finance': false,
      'present_count': 3,
      'no_show_count': 0,
      'confirmed_count': 3,
      'expenses_total_vnd': null,
      'amount_due_total_vnd': null,
      'total_paid_vnd': null,
      'outstanding_total_vnd': null,
    });

    final summary = await FinanceRepository(
      client: client,
    ).getSessionSummary('s1');

    expect(calledFunction, 'get_session_summary');
    expect(calledParams, {'p_session_id': 's1'});
    expect(summary.canViewFinance, isFalse);
    expect(summary.outstandingTotalVnd, isNull);
    expect(summary.presentCount, 3);
  });

  test('listMySessionHistory gửi limit/offset/filter đúng signature A', () async {
    stubRpc([
      {
        'id': 'h1',
        'title': 'Buổi đã xong',
        'lifecycle': 'completed',
        'starts_at': '2026-10-20T10:00:00Z',
        'version': 4,
      },
    ]);

    final page = await SessionRepository(client: client).listMySessionHistory(
      filter: SessionHistoryFilter(
        clubId: 'c1',
        from: DateTime.utc(2026, 10, 1),
        to: DateTime.utc(2026, 10, 31),
      ),
      limit: 500,
      offset: -5,
    );

    expect(calledFunction, 'list_my_session_history');
    expect(calledParams, {
      'p_limit': 100,
      'p_offset': 0,
      'p_club_id': 'c1',
      'p_from': '2026-10-01T00:00:00.000Z',
      'p_to': '2026-10-31T00:00:00.000Z',
    });
    expect(page.sessions.single.id, 'h1');
    expect(page.sessions.single.isCompleted, isTrue);
    expect(page.sessions.single.version, 4);
    expect(page.hasMore, isFalse);
  });
}
