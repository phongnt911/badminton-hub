import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';

import 'package:badminton_hub/data/finance_repository.dart';
import 'package:badminton_hub/models/club.dart';
import 'package:badminton_hub/models/finance.dart';
import 'package:badminton_hub/providers/finance_provider.dart';
import 'package:badminton_hub/screens/club_fund_screen.dart';

class MockFinanceRepository extends Mock implements FinanceRepository {}

void main() {
  late MockFinanceRepository repo;

  const ownerClub = Club(
    id: 'c1',
    ownerUserId: 'u1',
    name: 'CLB Test',
    myRole: 'owner',
    balanceVnd: 2000000,
  );

  const memberClub = Club(
    id: 'c1',
    ownerUserId: 'u2',
    name: 'CLB Test',
    myRole: 'member',
  );

  setUp(() {
    repo = MockFinanceRepository();
  });

  Widget build(Club club, FinanceProvider provider) {
    return ChangeNotifierProvider<FinanceProvider>.value(
      value: provider,
      child: MaterialApp(home: ClubFundScreen(club: club)),
    );
  }

  FinanceProvider provider() {
    final instance = FinanceProvider(repository: repo);
    addTearDown(instance.dispose);
    return instance;
  }

  /// Cửa sổ cao để mọi mục trong ListView được dựng (ListView dựng lười).
  Future<void> pumpScreen(
    WidgetTester tester,
    Club club,
    FinanceProvider provider,
  ) async {
    tester.view.physicalSize = const Size(1200, 3200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(build(club, provider));
  }

  testWidgets('chủ nhiệm thấy số dư, giao dịch và nạp thêm trang', (tester) async {
    final offsets = <int>[];
    when(() => repo.getClubLedger(
          'c1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        )).thenAnswer((invocation) async {
      final offset = invocation.namedArguments[#offset] as int;
      final limit = invocation.namedArguments[#limit] as int;
      offsets.add(offset);
      if (offset == 0) {
        return ClubLedger(
          clubId: 'c1',
          balanceVnd: 2000000,
          limit: limit,
          offset: offset,
          entries: [
            const ClubLedgerEntry(
              transactionId: 't1',
              direction: 'income',
              amountVnd: 200000,
              title: 'Thu quỹ',
              sourceType: 'manual',
            ),
            const ClubLedgerEntry(
              transactionId: 't2',
              direction: 'expense',
              amountVnd: 100000,
              title: 'Chi sân',
              sourceType: 'manual',
            ),
            for (var i = 2; i < limit; i++)
              ClubLedgerEntry(
                transactionId: 't${i + 1}',
                direction: 'income',
                amountVnd: 1000,
                sourceType: 'session_payment',
              ),
          ],
        );
      }
      return ClubLedger(
        clubId: 'c1',
        balanceVnd: 1900000,
        limit: limit,
        offset: offset,
        entries: const [
          ClubLedgerEntry(
            transactionId: 't99',
            direction: 'income',
            amountVnd: 150000,
            title: 'Thu từ buổi',
            sourceType: 'session_payment',
          ),
        ],
      );
    });

    final instance = provider();
    await pumpScreen(tester, ownerClub, instance);
    await tester.pumpAndSettle();

    expect(find.text('2,000,000 VNĐ'), findsOneWidget);
    expect(find.text('Thu quỹ'), findsOneWidget);
    expect(find.text('+200,000 VNĐ'), findsOneWidget);
    expect(find.text('-100,000 VNĐ'), findsOneWidget);

    await tester.tap(find.byKey(const Key('bh06c-ledger-more')));
    await tester.pumpAndSettle();

    expect(offsets, [0, 20]);
    expect(instance.ledger?.entries, hasLength(21));
    expect(find.text('+150,000 VNĐ'), findsOneWidget);
    expect(find.byKey(const Key('bh06c-ledger-more')), findsNothing);
  });

  testWidgets('không phải chủ nhiệm/thủ quỹ: bị chặn, không gọi sổ quỹ',
      (tester) async {
    final instance = provider();
    await pumpScreen(tester, memberClub, instance);
    await tester.pumpAndSettle();

    expect(find.text('Chỉ Chủ nhiệm và Thủ quỹ xem được sổ quỹ.'), findsOneWidget);
    expect(find.byKey(const Key('bh06c-manual-income')), findsNothing);
    verifyNever(() => repo.getClubLedger(
          any(),
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        ));
  });

  testWidgets('lỗi đọc sổ quỹ hiện Thử lại và tải lại', (tester) async {
    when(() => repo.getClubLedger(
          'c1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        )).thenThrow(Exception('offline'));

    final instance = provider();
    await pumpScreen(tester, ownerClub, instance);
    await tester.pumpAndSettle();

    expect(find.text('Thử lại'), findsOneWidget);

    when(() => repo.getClubLedger(
          'c1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        )).thenAnswer((_) async => const ClubLedger(clubId: 'c1', balanceVnd: 500000));

    await tester.tap(find.text('Thử lại'));
    await tester.pumpAndSettle();

    expect(find.text('500,000 VNĐ'), findsOneWidget);
    expect(find.text('Sổ quỹ chưa có giao dịch.'), findsOneWidget);
  });

  testWidgets('ghi thu thủ công gửi đúng hướng và số tiền', (tester) async {
    when(() => repo.getClubLedger(
          'c1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        )).thenAnswer((_) async => const ClubLedger(clubId: 'c1', balanceVnd: 2000000));
    when(() => repo.postManualClubTransaction(
          requestId: any(named: 'requestId'),
          clubId: 'c1',
          direction: 'income',
          amountVnd: 500000,
          title: 'Thu quỹ',
        )).thenAnswer(
      (_) async => const ClubTransactionResult(
        transactionId: 'tx1',
        clubId: 'c1',
        direction: 'income',
        amountVnd: 500000,
      ),
    );

    final instance = provider();
    await pumpScreen(tester, ownerClub, instance);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('bh06c-manual-income')));
    await tester.pumpAndSettle();
    expect(find.text('Ghi thu quỹ'), findsOneWidget);

    await tester.enterText(find.byType(TextField).at(1), '500000');
    await tester.tap(find.text('Ghi sổ'));
    await tester.pumpAndSettle();

    verify(() => repo.postManualClubTransaction(
          requestId: any(named: 'requestId'),
          clubId: 'c1',
          direction: 'income',
          amountVnd: 500000,
          title: 'Thu quỹ',
        )).called(1);
    expect(find.text('Đã ghi giao dịch quỹ.'), findsOneWidget);
  });

  testWidgets('hoàn tác bút toán thủ công gửi kèm lý do', (tester) async {
    when(() => repo.getClubLedger(
          'c1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        )).thenAnswer(
      (_) async => const ClubLedger(
        clubId: 'c1',
        balanceVnd: 2000000,
        entries: [
          ClubLedgerEntry(
            transactionId: 't1',
            direction: 'income',
            amountVnd: 200000,
            title: 'Thu quỹ',
            sourceType: 'manual',
          ),
        ],
      ),
    );
    when(() => repo.reverseClubTransaction(
          requestId: any(named: 'requestId'),
          transactionId: 't1',
          reason: 'nhập sai số tiền',
        )).thenAnswer(
      (_) async => const ClubTransactionResult(
        transactionId: 't1',
        clubId: 'c1',
      ),
    );

    final instance = provider();
    await pumpScreen(tester, ownerClub, instance);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('bh06c-reverse-ledger-t1')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'nhập sai số tiền');
    await tester.tap(find.text('Xác nhận'));
    await tester.pumpAndSettle();

    verify(() => repo.reverseClubTransaction(
          requestId: any(named: 'requestId'),
          transactionId: 't1',
          reason: 'nhập sai số tiền',
        )).called(1);
  });

  testWidgets('đang tải sổ quỹ thì hiện vòng xoay', (tester) async {
    final pending = Completer<ClubLedger>();
    when(() => repo.getClubLedger(
          'c1',
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
        )).thenAnswer((_) => pending.future);

    final instance = provider();
    await pumpScreen(tester, ownerClub, instance);
    await tester.pump();

    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    pending.complete(const ClubLedger(clubId: 'c1', balanceVnd: 100000));
    await tester.pumpAndSettle();
    expect(find.text('100,000 VNĐ'), findsOneWidget);
  });
}
