import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:badminton_hub/data/club_repository.dart';
import 'package:badminton_hub/models/club.dart';
import 'package:badminton_hub/providers/auth_provider.dart';
import 'package:badminton_hub/providers/club_provider.dart';

class MockRepository extends Mock implements ClubRepository {}

class SessionAuth extends Mock implements AuthProvider {
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
  late MockRepository repo;
  late SessionAuth auth;
  late ClubProvider provider;
  const club = Club(
    id: 'private',
    ownerUserId: 'A',
    name: 'Private club',
    myRole: 'owner',
  );
  setUp(() {
    repo = MockRepository();
    auth = SessionAuth()..changeUser('A');
    provider = ClubProvider(repository: repo, auth: auth);
  });
  tearDown(() => provider.dispose());

  test(
    'logout clears cached list and ignores previous-session list response',
    () async {
      when(() => repo.listMyClubs()).thenAnswer((_) async => [club]);
      await provider.fetchClubs();
      expect(provider.clubs, isNotEmpty);
      final pending = Completer<List<Club>>();
      when(() => repo.listMyClubs()).thenAnswer((_) => pending.future);
      final request = provider.fetchClubs();
      auth.changeUser(null);
      auth.changeUser('B');
      pending.complete([club]);
      await request;
      expect(provider.clubs, isEmpty);
      expect(provider.isLoadingClubs, isFalse);
    },
  );

  test('logout clears contacts and ignores late bank response', () async {
    when(() => repo.getClubDetail('private')).thenAnswer((_) async => club);
    when(() => repo.listClubMembers('private')).thenAnswer(
      (_) async => [
        const ClubMember(
          id: 'm',
          clubId: 'private',
          displayName: 'Private member',
          phoneNumber: 'FAKE-PRIVATE',
        ),
      ],
    );
    final pending = Completer<BankAccount?>();
    when(() => repo.getClubBankAccount('private'))
        .thenAnswer((_) => pending.future);
    final request = provider.fetchClubDetails('private');
    await Future<void>.delayed(Duration.zero);
    expect(provider.currentMembers, isNotEmpty);
    auth.changeUser(null);
    pending.complete(
      const BankAccount(
        id: 'bank',
        bankCode: 'TEST',
        accountNumber: '00123',
        accountName: 'Private',
      ),
    );
    await request;
    expect(provider.currentClub, isNull);
    expect(provider.currentMembers, isEmpty);
    expect(provider.currentBankAccount, isNull);
  });

  test(
    'timeout retry reuses UUID; next successful intent has a new UUID',
    () async {
      final keys = <String>[];
      when(
        () => repo.createClub(
          name: any(named: 'name'),
          description: any(named: 'description'),
          visibility: any(named: 'visibility'),
          requestId: any(named: 'requestId'),
        ),
      ).thenAnswer((call) async {
        keys.add(call.namedArguments[#requestId] as String);
        if (keys.length == 1) throw TimeoutException('response lost');
        return club;
      });
      when(() => repo.listMyClubs()).thenAnswer((_) async => [club]);
      expect(await provider.createClub(name: 'Retry'), isNull);
      expect(await provider.createClub(name: 'Retry'), isNotNull);
      expect(await provider.createClub(name: 'Retry'), isNotNull);
      expect(keys[0], keys[1]);
      expect(keys[2], isNot(keys[1]));
      expect(
        keys[0],
        matches(
          RegExp(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
          ),
        ),
      );
    },
  );

  test(
    'changed form payload after timeout creates a new request key',
    () async {
      final keys = <String>[];
      when(
        () => repo.createClub(
          name: any(named: 'name'),
          description: any(named: 'description'),
          visibility: any(named: 'visibility'),
          requestId: any(named: 'requestId'),
        ),
      ).thenAnswer((call) async {
        keys.add(call.namedArguments[#requestId] as String);
        throw TimeoutException('lost');
      });
      await provider.createClub(name: 'Name', description: 'Before');
      await provider.createClub(name: 'Name', description: 'After');
      expect(keys[0], isNot(keys[1]));
    },
  );

  test(
    'late mutation from logged-out user cannot refresh private data',
    () async {
      final pending = Completer<Club>();
      when(
        () => repo.createClub(
          name: any(named: 'name'),
          description: any(named: 'description'),
          visibility: any(named: 'visibility'),
          requestId: any(named: 'requestId'),
        ),
      ).thenAnswer((_) => pending.future);
      final request = provider.createClub(name: 'Private');
      auth.changeUser(null);
      pending.complete(club);
      expect(await request, isNull);
      expect(provider.clubs, isEmpty);
      expect(provider.isSubmitting, isFalse);
      verifyNever(() => repo.listMyClubs());
    },
  );
}
