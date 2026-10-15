import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:badminton_hub/providers/club_provider.dart';
import 'package:badminton_hub/data/club_repository.dart';
import 'package:badminton_hub/models/club.dart';

class MockClubRepository extends Mock implements ClubRepository {}

void main() {
  late MockClubRepository mockRepo;
  late ClubProvider provider;

  setUp(() {
    mockRepo = MockClubRepository();
    provider = ClubProvider(repository: mockRepo);
  });

  group('ClubProvider List State Tests', () {
    test('initial state is empty and not loading', () {
      expect(provider.clubs, isEmpty);
      expect(provider.isLoadingClubs, isFalse);
      expect(provider.clubsErrorMessage, isNull);
    });

    test('fetchClubs success updates clubs list', () async {
      final mockClubs = [
        const Club(id: 'c1', ownerUserId: 'u1', name: 'CLB 1', myRole: 'owner'),
        const Club(id: 'c2', ownerUserId: 'u2', name: 'CLB 2', myRole: 'member'),
      ];

      when(() => mockRepo.listMyClubs()).thenAnswer((_) async => mockClubs);

      final future = provider.fetchClubs();
      expect(provider.isLoadingClubs, isTrue);

      await future;

      expect(provider.isLoadingClubs, isFalse);
      expect(provider.clubs.length, 2);
      expect(provider.clubs[0].name, 'CLB 1');
      expect(provider.clubsErrorMessage, isNull);
    });

    test('fetchClubs failure sets error message', () async {
      when(() => mockRepo.listMyClubs()).thenThrow(Exception('Network error'));

      await provider.fetchClubs();

      expect(provider.isLoadingClubs, isFalse);
      expect(provider.clubs, isEmpty);
      expect(provider.clubsErrorMessage, contains('Network error'));
    });
  });

  group('ClubProvider Detail & Switch Club Tests', () {
    test('switching club clears previous private data immediately to prevent data leakage', () async {
      const club1 = Club(id: 'c1', ownerUserId: 'u1', name: 'CLB 1', myRole: 'owner', balanceVnd: 500000);
      const member1 = ClubMember(id: 'm1', clubId: 'c1', displayName: 'Thanh vien 1');
      const bank1 = BankAccount(id: 'b1', clubId: 'c1', bankCode: 'VCB', accountNumber: '001', accountName: 'A');

      when(() => mockRepo.getClubDetail('c1')).thenAnswer((_) async => club1);
      when(() => mockRepo.listClubMembers('c1')).thenAnswer((_) async => [member1]);
      when(() => mockRepo.getClubBankAccount('c1')).thenAnswer((_) async => bank1);

      await provider.fetchClubDetails('c1');

      expect(provider.currentClub?.name, 'CLB 1');
      expect(provider.currentMembers.length, 1);
      expect(provider.currentBankAccount?.bankCode, 'VCB');

      // Bắt đầu switch sang CLB 2
      const club2 = Club(id: 'c2', ownerUserId: 'u2', name: 'CLB 2', myRole: 'member');
      when(() => mockRepo.getClubDetail('c2')).thenAnswer((_) async {
        // Trong lúc đang tải CLB 2, dữ liệu của CLB 1 phải bị xóa sạch
        expect(provider.currentClub, isNull);
        expect(provider.currentMembers, isEmpty);
        expect(provider.currentBankAccount, isNull);
        return club2;
      });
      when(() => mockRepo.listClubMembers('c2')).thenAnswer((_) async => []);

      await provider.fetchClubDetails('c2');

      expect(provider.currentClub?.id, 'c2');
    });

    test('clearAll clears list and detail state completely', () async {
      const club = Club(id: 'c1', ownerUserId: 'u1', name: 'CLB 1');
      when(() => mockRepo.listMyClubs()).thenAnswer((_) async => [club]);
      await provider.fetchClubs();

      expect(provider.clubs.length, 1);

      provider.clearAll();

      expect(provider.clubs, isEmpty);
      expect(provider.currentClub, isNull);
      expect(provider.currentMembers, isEmpty);
    });
  });

  group('ClubProvider Mutation & Submitting Guard Tests', () {
    test('createClub blocks concurrent submissions and updates clubs', () async {
      const newClub = Club(id: 'new-c', ownerUserId: 'u1', name: 'CLB Mới');
      when(() => mockRepo.createClub(
        name: any(named: 'name'),
        description: any(named: 'description'),
        visibility: any(named: 'visibility'),
        requestId: any(named: 'requestId'),
      )).thenAnswer((_) async {
        await Future.delayed(const Duration(milliseconds: 20));
        return newClub;
      });
      when(() => mockRepo.listMyClubs()).thenAnswer((_) async => [newClub]);

      final call1 = provider.createClub(name: 'CLB Mới');
      expect(provider.isSubmitting, isTrue);

      // Thao tác thứ 2 trong lúc đang submitting bị từ chối
      final call2 = provider.createClub(name: 'CLB Trùng');
      final res2 = await call2;
      expect(res2, isNull);

      final res1 = await call1;
      expect(res1?.id, 'new-c');
      expect(provider.isSubmitting, isFalse);
    });

    test('createClub failure records submit error message', () async {
      when(() => mockRepo.createClub(
        name: any(named: 'name'),
        description: any(named: 'description'),
        visibility: any(named: 'visibility'),
        requestId: any(named: 'requestId'),
      )).thenThrow(Exception('Tên CLB đã tồn tại'));

      final res = await provider.createClub(name: 'CLB Lỗi');

      expect(res, isNull);
      expect(provider.isSubmitting, isFalse);
      expect(provider.submitErrorMessage, contains('Tên CLB đã tồn tại'));
    });
  });

  group('ClubProvider Scoped Roster Tests (BH-05C)', () {
    const memberC1 = ClubMember(id: 'm1', clubId: 'c1', displayName: 'An');
    const memberC2 = ClubMember(id: 'm2', clubId: 'c2', displayName: 'Bình');

    test('fetchClubRoster tải roster theo clubId và bật/tắt loading', () async {
      when(() => mockRepo.listClubMembers(
        'c1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      )).thenAnswer((_) async => [memberC1]);

      final future = provider.fetchClubRoster('c1');
      expect(provider.isLoadingRoster, isTrue);
      expect(provider.rosterClubId, 'c1');

      await future;

      expect(provider.isLoadingRoster, isFalse);
      expect(provider.rosterMembers.single.displayName, 'An');
      expect(provider.rosterErrorMessage, isNull);
    });

    test('fetchClubRoster lỗi ghi error và thử lại phục hồi', () async {
      var attempts = 0;
      when(() => mockRepo.listClubMembers(
        'c1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      )).thenAnswer((_) async {
        attempts++;
        if (attempts == 1) throw Exception('offline');
        return [memberC1];
      });

      await provider.fetchClubRoster('c1');
      expect(provider.isLoadingRoster, isFalse);
      expect(provider.rosterErrorMessage, isNotNull);
      expect(provider.rosterMembers, isEmpty);

      await provider.fetchClubRoster('c1');
      expect(provider.rosterErrorMessage, isNull);
      expect(provider.rosterMembers.single.displayName, 'An');
    });

    test('đổi CLB xoá roster ngay và bỏ phản hồi đến trễ của CLB cũ', () async {
      final c1 = Completer<List<ClubMember>>();
      when(() => mockRepo.listClubMembers(
        'c1',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      )).thenAnswer((_) => c1.future);
      when(() => mockRepo.listClubMembers(
        'c2',
        limit: any(named: 'limit'),
        offset: any(named: 'offset'),
      )).thenAnswer((_) async => [memberC2]);

      final first = provider.fetchClubRoster('c1');
      expect(provider.rosterClubId, 'c1');

      await provider.fetchClubRoster('c2');
      expect(provider.rosterClubId, 'c2');
      expect(provider.rosterMembers.single.displayName, 'Bình');

      c1.complete([memberC1]);
      await first;

      expect(provider.rosterClubId, 'c2');
      expect(provider.rosterMembers.single.displayName, 'Bình');

      provider.clearAll();
      expect(provider.rosterClubId, isNull);
      expect(provider.rosterMembers, isEmpty);
      expect(provider.isLoadingRoster, isFalse);
    });
  });
}
