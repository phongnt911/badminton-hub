import 'package:flutter_test/flutter_test.dart';
import 'package:badminton_hub/models/session.dart';

void main() {
  group('Session.fromJson', () {
    test('map đầy đủ projection chi tiết', () {
      final session = Session.fromJson({
        'id': 's1',
        'club_id': 'c1',
        'title': 'Buổi tối',
        'description': 'Giao lưu',
        'starts_at': '2026-10-16T10:30:00+00:00',
        'ends_at': '2026-10-16T12:30:00+00:00',
        'capacity': 8,
        'court_count': 2,
        'visibility': 'public',
        'lifecycle': 'published',
        'approval_mode': 'auto_confirm',
        'fee_mode': 'fixed',
        'member_fee_vnd': 50000,
        'guest_fee_vnd': 70000,
        'venue_id': 'v1',
        'venue_name': 'Sân A',
        'venue_area': 'Nha Trang',
        'host_display_name': 'Chủ buổi',
        'version': 3,
        'is_host': true,
        'can_manage': true,
        'can_view_finance': true,
        'confirmed_count': 5,
        'my_registration': {
          'player_id': 'p1',
          'registration_status': 'confirmed',
          'attendance_status': 'not_checked_in',
          'participant_type': 'member',
          'agreed_fee_vnd': 50000,
        },
      });

      expect(session.id, 's1');
      expect(session.clubId, 'c1');
      expect(session.capacity, 8);
      expect(session.startsAt?.isUtc, isTrue);
      expect(session.startsAt?.toUtc(), DateTime.utc(2026, 10, 16, 10, 30));
      expect(session.isPublished, isTrue);
      expect(session.canManage, isTrue);
      expect(session.isHost, isTrue);
      expect(session.seatsLeft, 3);
      expect(session.isFull, isFalse);
      expect(session.myRegistration?.registrationStatus, 'confirmed');
      expect(session.myRegistration?.agreedFeeVnd, 50000);
    });

    test('map danh sách quản lý (thiếu cờ quyền) dùng giá trị mặc định an toàn', () {
      final session = Session.fromJson({
        'id': 's2',
        'title': 'Buổi nháp',
        'starts_at': '2026-10-17T09:00:00+00:00',
        'ends_at': '2026-10-17T11:00:00+00:00',
        'capacity': 6,
        'court_count': 1,
        'visibility': 'unlisted',
        'lifecycle': 'draft',
        'fee_mode': 'split_actual',
        'confirmed_count': 0,
      });

      expect(session.canManage, isFalse);
      expect(session.isHost, isFalse);
      expect(session.canViewFinance, isFalse);
      expect(session.isDraft, isTrue);
      expect(session.myRegistration, isNull);
      expect(session.capacity, 6);
    });

    test('null/absent an toàn', () {
      final session = Session.fromJson({'id': 's3'});
      expect(session.title, '');
      expect(session.capacity, 0);
      expect(session.startsAt, isNull);
      expect(session.feeLabel, 'Chia theo chi phí thực tế');
    });
  });

  group('Session nhãn và chỗ trống', () {
    test('lifecycleLabel tiếng Việt', () {
      expect(
        const Session(id: 'a', title: 't', lifecycle: 'draft').lifecycleLabel,
        'Bản nháp',
      );
      expect(
        const Session(id: 'a', title: 't', lifecycle: 'published').lifecycleLabel,
        'Đã công bố',
      );
      expect(
        const Session(id: 'a', title: 't', lifecycle: 'cancelled').lifecycleLabel,
        'Đã huỷ',
      );
    });

    test('isShareable chỉ đúng khi đã công bố/đang diễn ra', () {
      expect(
        const Session(id: 'a', title: 't', lifecycle: 'draft').isShareable,
        isFalse,
      );
      expect(
        const Session(id: 'a', title: 't', lifecycle: 'published').isShareable,
        isTrue,
      );
      expect(
        const Session(id: 'a', title: 't', lifecycle: 'cancelled').isShareable,
        isFalse,
      );
    });

    test('seatsLeft không âm, isFull khi đủ chỗ', () {
      const full = Session(
        id: 'a',
        title: 't',
        capacity: 4,
        confirmedCount: 5,
      );
      expect(full.seatsLeft, 0);
      expect(full.isFull, isTrue);
    });

    test('visibilityLabel', () {
      expect(
        const Session(id: 'a', title: 't', visibility: 'public').visibilityLabel,
        'Công khai',
      );
      expect(
        const Session(id: 'a', title: 't', visibility: 'unlisted').visibilityLabel,
        'Có link',
      );
      expect(
        const Session(id: 'a', title: 't', visibility: 'private').visibilityLabel,
        'Riêng tư',
      );
    });
  });
}
