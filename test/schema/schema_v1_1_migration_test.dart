import 'dart:io';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Kiểm thử cấu trúc Schema Migration v1.1 (BH-02)', () {
    late String sqlContent;

    setUpAll(() {
      final migrationFile = File('supabase/migrations/20261015051808_init_schema_v1_1.sql');
      expect(migrationFile.existsSync(), isTrue, reason: 'File migration v1.1 phải tồn tại');
      sqlContent = migrationFile.readAsStringSync();
      expect(sqlContent.isNotEmpty, isTrue, reason: 'File migration không được rỗng');
    });

    test('Chứa đầy đủ 21 bảng theo đặc tả docs/03_DATABASE.md', () {
      final expectedTables = [
        'profiles',
        'profile_private',
        'app_roles',
        'clubs',
        'club_members',
        'member_contacts',
        'club_bank_accounts',
        'host_bank_accounts',
        'venues',
        'sessions',
        'session_staff',
        'session_players',
        'session_player_contacts',
        'waitlist_invitations',
        'session_expenses',
        'charge_revisions',
        'session_charges',
        'payments',
        'club_transactions',
        'audit_events',
        'operation_requests',
      ];

      for (final table in expectedTables) {
        expect(
          sqlContent.contains('CREATE TABLE IF NOT EXISTS public.$table'),
          isTrue,
          reason: 'Bảng $table phải được định nghĩa bằng CREATE TABLE IF NOT EXISTS',
        );
      }
    });

    test('Kích hoạt Row Level Security (RLS) trên toàn bộ các bảng nghiệp vụ', () {
      final rlsTables = [
        'profiles',
        'profile_private',
        'app_roles',
        'clubs',
        'club_members',
        'member_contacts',
        'club_bank_accounts',
        'host_bank_accounts',
        'venues',
        'sessions',
        'session_staff',
        'session_players',
        'session_player_contacts',
        'waitlist_invitations',
        'session_expenses',
        'charge_revisions',
        'session_charges',
        'payments',
        'club_transactions',
        'audit_events',
        'operation_requests',
      ];

      for (final table in rlsTables) {
        expect(
          sqlContent.contains('ALTER TABLE public.$table ENABLE ROW LEVEL SECURITY;'),
          isTrue,
          reason: 'Bảng $table phải được bật RLS',
        );
      }
    });

    test('Thu hồi quyền ghi trực tiếp từ anon và authenticated', () {
      expect(
        sqlContent.contains('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;'),
        isTrue,
        reason: 'Phải thu hồi toàn bộ direct writes trên schema public để chống cập nhật tùy tiện',
      );
    });

    test('Định nghĩa đầy đủ các Security Views & Projections với security_invoker = true', () {
      expect(sqlContent.contains('CREATE OR REPLACE VIEW public.public_session_summary'), isTrue);
      expect(sqlContent.contains('CREATE OR REPLACE VIEW public.club_balance'), isTrue);
      expect(sqlContent.contains('CREATE OR REPLACE VIEW public.player_outstanding'), isTrue);
      expect(sqlContent.contains('WITH (security_invoker = true)'), isTrue);
    });

    test('Định nghĩa đầy đủ các Security Helper Functions tránh đệ quy RLS', () {
      final helperFunctions = [
        'is_app_admin',
        'is_club_owner',
        'is_club_member_active',
        'has_club_role',
        'is_session_host',
        'has_session_staff_role',
        'has_session_management_access',
        'has_session_finance_access',
        'is_session_participant',
      ];

      for (final fn in helperFunctions) {
        expect(
          sqlContent.contains('FUNCTION public.$fn'),
          isTrue,
          reason: 'Hàm helper $fn phải được định nghĩa',
        );
      }
    });

    test('Định nghĩa hợp đồng Idempotency và Audit Trail', () {
      expect(sqlContent.contains('FUNCTION public.check_idempotency'), isTrue);
      expect(sqlContent.contains('FUNCTION public.record_idempotency'), isTrue);
      expect(sqlContent.contains('FUNCTION public.log_audit_event'), isTrue);
      expect(sqlContent.contains('IDEMPOTENCY_CONFLICT'), isTrue);
    });

    test('Định nghĩa RPC public / private whitelist đọc dữ liệu', () {
      expect(sqlContent.contains('FUNCTION public.get_session_public_detail'), isTrue);
      expect(sqlContent.contains('FUNCTION public.get_my_registration'), isTrue);
    });

    test('Bảo vệ tính tương thích và chuyển đổi dữ liệu không làm mất dữ liệu cũ', () {
      expect(sqlContent.contains('ALTER TABLE public.venues ADD COLUMN IF NOT EXISTS status'), isTrue);
      expect(sqlContent.contains('ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS host_user_id'), isTrue);
      expect(sqlContent.contains('ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS billing_input_version'), isTrue);
      expect(sqlContent.contains('ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS attendance_status'), isTrue);
      expect(sqlContent.contains('ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS registration_status'), isTrue);
    });

    test('Chứa các ràng buộc (Constraints) quan trọng theo ADR-02, ADR-08, ADR-09', () {
      // 1. Partial unique owner CLB
      expect(sqlContent.contains('idx_club_members_unique_owner'), isTrue);
      // 2. Partial unique waitlist invitation pending
      expect(sqlContent.contains('idx_waitlist_invitations_pending'), isTrue);
      // 3. Partial unique active charge revision
      expect(sqlContent.contains('idx_charge_revisions_active'), isTrue);
      // 4. Unique reversibility trên club_transactions
      expect(sqlContent.contains('idx_club_tx_reversal_of'), isTrue);
      // 5. Kiểm tra thời gian buổi chơi ends_at > starts_at
      expect(sqlContent.contains('chk_session_times CHECK (ends_at > starts_at)'), isTrue);
    });
  });
}
