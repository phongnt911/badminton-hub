import 'package:flutter_test/flutter_test.dart';
import 'package:badminton_hub/models/club.dart';

void main() {
  group('Club Model Tests', () {
    test('deserialize and serialize Club correctly', () {
      final json = {
        'id': 'club-123',
        'owner_user_id': 'user-1',
        'name': 'CLB Cầu Lông ABC',
        'description': 'Mô tả CLB',
        'visibility': 'public',
        'status': 'active',
        'my_role': 'owner',
        'balance_vnd': 1500000,
        'member_count': 12,
        'created_at': '2026-10-15T12:00:00.000Z',
      };

      final club = Club.fromJson(json);

      expect(club.id, 'club-123');
      expect(club.ownerUserId, 'user-1');
      expect(club.name, 'CLB Cầu Lông ABC');
      expect(club.description, 'Mô tả CLB');
      expect(club.visibility, 'public');
      expect(club.myRole, 'owner');
      expect(club.isOwner, isTrue);
      expect(club.canManageMembers, isTrue);
      expect(club.canViewBalance, isTrue);
      expect(club.canConfigureBank, isTrue);
      expect(club.balanceVnd, 1500000);
      expect(club.memberCount, 12);
      expect(club.createdAt, isNotNull);

      final outJson = club.toJson();
      expect(outJson['id'], 'club-123');
      expect(outJson['balance_vnd'], 1500000);
    });

    test('Club role getters for regular member', () {
      final json = {
        'id': 'club-456',
        'owner_user_id': 'user-other',
        'name': 'CLB Bạn Bè',
        'my_role': 'member',
        'balance_vnd': null, // Bị giấu bởi privacy
      };

      final club = Club.fromJson(json);
      expect(club.isOwner, isFalse);
      expect(club.isHost, isFalse);
      expect(club.isTreasurer, isFalse);
      expect(club.canManageMembers, isFalse);
      expect(club.canViewBalance, isFalse);
      expect(club.canConfigureBank, isFalse);
      expect(club.balanceVnd, isNull);
    });

    test('Club role getters for treasurer', () {
      final json = {
        'id': 'club-789',
        'owner_user_id': 'user-owner',
        'name': 'CLB Tài Chính',
        'my_role': 'treasurer',
        'balance_vnd': 3000000,
      };

      final club = Club.fromJson(json);
      expect(club.isTreasurer, isTrue);
      expect(club.canViewBalance, isTrue);
      expect(club.canConfigureBank, isFalse);
    });
  });

  group('ClubMember Model Tests', () {
    test('deserialize offline member with private contact', () {
      final json = {
        'id': 'member-1',
        'club_id': 'club-123',
        'user_id': null, // Offline member
        'display_name': 'Anh Nam Offline',
        'role': 'member',
        'status': 'active',
        'phone_number': '0901234567',
        'contact_note': 'Bạn anh Nam',
        'joined_at': '2026-10-15T12:00:00.000Z',
      };

      final member = ClubMember.fromJson(json);
      expect(member.id, 'member-1');
      expect(member.isOffline, isTrue);
      expect(member.displayName, 'Anh Nam Offline');
      expect(member.role, 'member');
      expect(member.phoneNumber, '0901234567');
      expect(member.contactNote, 'Bạn anh Nam');
    });

    test('deserialize linked member with host role', () {
      final json = {
        'id': 'member-2',
        'club_id': 'club-123',
        'user_id': 'user-555',
        'display_name': 'Host Huy',
        'role': 'host',
        'status': 'active',
      };

      final member = ClubMember.fromJson(json);
      expect(member.isOffline, isFalse);
      expect(member.isHost, isTrue);
      expect(member.isOwner, isFalse);
    });
  });

  group('BankAccount Model Tests', () {
    test('preserves leading zeros in account number', () {
      final json = {
        'id': 'bank-1',
        'club_id': 'club-123',
        'bank_code': 'VCB',
        'account_number': '0071000123456',
        'account_name': 'NGUYEN VAN CHU NHIEM',
        'status': 'active',
      };

      final bank = BankAccount.fromJson(json);
      expect(bank.bankCode, 'VCB');
      expect(bank.accountNumber, '0071000123456');
      expect(bank.accountNumber.startsWith('00'), isTrue);
      expect(bank.accountName, 'NGUYEN VAN CHU NHIEM');
    });
  });
}
