import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:badminton_hub/screens/clubs_screen.dart';
import 'package:badminton_hub/providers/club_provider.dart';
import 'package:badminton_hub/data/club_repository.dart';
import 'package:badminton_hub/models/club.dart';

class MockClubRepository extends Mock implements ClubRepository {}

void main() {
  late MockClubRepository mockRepo;
  late ClubProvider clubProvider;

  setUp(() {
    mockRepo = MockClubRepository();
    clubProvider = ClubProvider(repository: mockRepo);
  });

  Widget createWidgetUnderTest({Widget? child}) {
    return ChangeNotifierProvider<ClubProvider>.value(
      value: clubProvider,
      child: MaterialApp(
        home: child ?? const ClubsScreen(),
      ),
    );
  }

  group('ClubsScreen Widget Tests', () {
    testWidgets('displays empty state when user has no clubs', (tester) async {
      when(() => mockRepo.listMyClubs()).thenAnswer((_) async => []);

      await tester.pumpWidget(createWidgetUnderTest());
      await tester.pumpAndSettle();

      expect(find.text('Bạn chưa tham gia câu lạc bộ nào'), findsOneWidget);
      expect(find.text('Tạo CLB đầu tiên'), findsOneWidget);
    });

    testWidgets('displays clubs with role badges and privacy-aware balance', (tester) async {
      final testClubs = [
        const Club(
          id: 'club-owner',
          ownerUserId: 'u1',
          name: 'CLB Chiến Thần (Owner)',
          visibility: 'private',
          myRole: 'owner',
          balanceVnd: 5000000,
        ),
        const Club(
          id: 'club-member',
          ownerUserId: 'u2',
          name: 'CLB Vui Vẻ (Member)',
          visibility: 'public',
          myRole: 'member',
          balanceVnd: null, // Member không được thấy số dư
        ),
      ];

      when(() => mockRepo.listMyClubs()).thenAnswer((_) async => testClubs);

      await tester.pumpWidget(createWidgetUnderTest());
      await tester.pumpAndSettle();

      expect(find.text('CLB Chiến Thần (Owner)'), findsOneWidget);
      expect(find.text('Chủ nhiệm'), findsOneWidget);
      expect(find.text('Quỹ: 5,000,000 đ'), findsOneWidget);

      expect(find.text('CLB Vui Vẻ (Member)'), findsOneWidget);
      expect(find.text('Thành viên'), findsOneWidget);
      // Không thấy số dư quỹ của CLB Vui Vẻ
      expect(find.text('Quỹ: 0 đ'), findsNothing);
    });

    testWidgets('create club dialog does NOT ask for phone or bank account', (tester) async {
      when(() => mockRepo.listMyClubs()).thenAnswer((_) async => []);

      await tester.pumpWidget(createWidgetUnderTest());
      await tester.pumpAndSettle();

      // Nhấn nút tạo CLB
      await tester.tap(find.text('TẠO CLB MỚI'));
      await tester.pumpAndSettle();

      expect(find.text('Tạo Câu Lạc Bộ Mới'), findsOneWidget);
      expect(find.text('Tên CLB *'), findsOneWidget);
      expect(find.text('Mô tả hoạt động'), findsOneWidget);
      expect(find.text('Chế độ hiển thị'), findsOneWidget);

      // Tuyệt đối không yêu cầu số điện thoại hay tài khoản ngân hàng lúc tạo CLB
      expect(find.text('Hotline chủ nhiệm'), findsNothing);
      expect(find.text('STK Ngân hàng nhận quỹ'), findsNothing);
    });
  });

  group('ClubDetailScreen Widget Tests', () {
    testWidgets('shows tabs and disables direct ledger writes with BH-06 notification', (tester) async {
      const testClub = Club(
        id: 'c1',
        ownerUserId: 'u1',
        name: 'CLB Test Detail',
        myRole: 'owner',
        balanceVnd: 2000000,
      );

      when(() => mockRepo.getClubDetail('c1')).thenAnswer((_) async => testClub);
      when(() => mockRepo.listClubMembers('c1')).thenAnswer((_) async => [
        const ClubMember(id: 'm1', clubId: 'c1', displayName: 'Chủ nhiệm A', role: 'owner'),
        const ClubMember(id: 'm2', clubId: 'c1', displayName: 'Thành viên Offline B', role: 'member', userId: null),
      ]);
      when(() => mockRepo.getClubBankAccount('c1')).thenAnswer((_) async => const BankAccount(
        id: 'b1',
        clubId: 'c1',
        bankCode: 'TCB',
        accountNumber: '190333444555',
        accountName: 'CHU NHIEM A',
      ));

      await tester.pumpWidget(createWidgetUnderTest(
        child: const ClubDetailScreen(clubId: 'c1', clubName: 'CLB Test Detail'),
      ));
      await tester.pumpAndSettle();

      // Kiểm tra các Tab
      expect(find.text('Tổng quan'), findsOneWidget);
      expect(find.text('Thành viên'), findsOneWidget);
      expect(find.text('Tài khoản quỹ'), findsOneWidget);

      // Thẻ số dư quỹ
      expect(find.text('2,000,000 VNĐ'), findsOneWidget);

      // Nhấn nút THU QUỸ -> Phải hiện SnackBar thông báo tính năng thuộc BH-06
      await tester.tap(find.text('THU QUỸ'));
      await tester.pumpAndSettle();
      expect(find.text('Chức năng ghi thu/chi quỹ sẽ khả dụng trong BH-06'), findsOneWidget);

      // Chuyển sang Tab Thành viên
      await tester.tap(find.text('Thành viên'));
      await tester.pumpAndSettle();
      expect(find.text('Chủ nhiệm A'), findsOneWidget);
      expect(find.text('Thành viên Offline B'), findsOneWidget);
      expect(find.text('Chưa liên kết tài khoản'), findsAtLeastNWidgets(1));

      // Chuyển sang Tab Tài khoản quỹ
      await tester.tap(find.text('Tài khoản quỹ'));
      await tester.pumpAndSettle();
      expect(find.text('TCB'), findsOneWidget);
      expect(find.text('190333444555'), findsOneWidget);
      expect(find.text('CHU NHIEM A'), findsOneWidget);
    });
  });
}
