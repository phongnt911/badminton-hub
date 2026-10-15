-- BH-05A — forward fixes sau review doc lap 7fcbdee (vong sua 1).
-- Chi sua A1 (P1: gate quyen tai chinh khi doi tap confirmed sau chot phi) va
-- A2 (P1: chan ha capacity duoi so confirmed). KHONG sua migration da chia se
-- (20261015163000_bh04_sessions.sql, 20261015170500_bh05_registrations.sql) va
-- KHONG xoa nguoi de ep vua capacity. Forward-only, CREATE OR REPLACE.
--
-- A3 (P2: huy buoi chua thu hoi loi moi pending) khong nam trong pham vi vong nay.

-- ============================================================================
-- A2. update_session — chan ha capacity duoi so nguoi da confirmed
-- Giu nguyen dinh nghia BH-04, chi them kiem invariant trong cung transaction
-- dang giu khoa session (FOR UPDATE) truoc khi UPDATE.
-- ============================================================================
CREATE OR REPLACE FUNCTION public.update_session(
  p_session_id UUID,
  p_version BIGINT,
  p_venue_id UUID,
  p_title TEXT,
  p_starts_at TIMESTAMPTZ,
  p_ends_at TIMESTAMPTZ,
  p_capacity INT,
  p_court_count INT,
  p_description TEXT DEFAULT NULL,
  p_level_requirement TEXT DEFAULT NULL,
  p_visibility TEXT DEFAULT 'unlisted',
  p_approval_mode TEXT DEFAULT 'host_approval',
  p_fee_mode TEXT DEFAULT 'split_actual',
  p_member_fee_vnd BIGINT DEFAULT NULL,
  p_guest_fee_vnd BIGINT DEFAULT NULL,
  p_registration_deadline TIMESTAMPTZ DEFAULT NULL,
  p_cancellation_deadline TIMESTAMPTZ DEFAULT NULL,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_session RECORD;
  v_confirmed INT;
  v_view JSONB;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để cập nhật buổi chơi' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;

  IF NOT public.has_session_management_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Không có quyền sửa buổi chơi' USING ERRCODE = '42501';
  END IF;
  IF v_session.lifecycle NOT IN ('draft', 'published') THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ sửa được buổi nháp hoặc đã công bố' USING ERRCODE = '22023';
  END IF;

  p_title := NULLIF(trim(COALESCE(p_title, '')), '');
  IF p_title IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: Tiêu đề buổi chơi không được để trống' USING ERRCODE = '22023';
  END IF;

  PERFORM public.validate_session_config(
    p_venue_id, p_starts_at, p_ends_at, p_capacity, p_court_count, p_visibility,
    p_approval_mode, p_fee_mode, p_member_fee_vnd, p_guest_fee_vnd,
    p_registration_deadline, p_cancellation_deadline);

  v_payload_hash := md5(jsonb_build_array(
    p_session_id, p_version, p_venue_id, p_title, p_starts_at, p_ends_at, p_capacity, p_court_count,
    p_description, p_level_requirement, p_visibility, p_approval_mode, p_fee_mode,
    p_member_fee_vnd, p_guest_fee_vnd, p_registration_deadline, p_cancellation_deadline)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('update_session', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  IF p_version IS NULL OR p_version <> v_session.version THEN
    RAISE EXCEPTION 'VERSION_CONFLICT: Buổi chơi đã thay đổi ở nơi khác' USING ERRCODE = '40001';
  END IF;

  -- A2: capacity không được nhỏ hơn số người đã confirmed (đang giữ khóa session).
  SELECT count(*)::int INTO v_confirmed
  FROM public.session_players
  WHERE session_id = p_session_id AND registration_status = 'confirmed';
  IF p_capacity < v_confirmed THEN
    RAISE EXCEPTION 'CAPACITY_FULL: Sức chứa mới nhỏ hơn số người đã xác nhận (%)', v_confirmed
      USING ERRCODE = '22023';
  END IF;

  UPDATE public.sessions SET
    venue_id = p_venue_id,
    title = p_title,
    description = NULLIF(trim(COALESCE(p_description, '')), ''),
    starts_at = p_starts_at,
    ends_at = p_ends_at,
    capacity = p_capacity,
    court_count = p_court_count,
    level_requirement = NULLIF(trim(COALESCE(p_level_requirement, '')), ''),
    visibility = p_visibility,
    approval_mode = p_approval_mode,
    fee_mode = p_fee_mode,
    member_fee_vnd = p_member_fee_vnd,
    guest_fee_vnd = p_guest_fee_vnd,
    registration_deadline = p_registration_deadline,
    cancellation_deadline = p_cancellation_deadline,
    version = version + 1,
    updated_at = now()
  WHERE id = p_session_id;

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'session', p_session_id, 'UPDATE_SESSION',
    jsonb_build_object('version', v_session.version, 'title', v_session.title),
    jsonb_build_object('version', v_session.version + 1, 'title', p_title),
    'Cập nhật buổi chơi', p_request_id);

  v_view := public.get_session_public_detail(p_session_id);
  PERFORM public.record_idempotency('update_session', p_request_id, v_payload_hash, v_view);
  RETURN v_view;
END;
$$;
REVOKE ALL ON FUNCTION public.update_session(UUID, BIGINT, UUID, TEXT, TIMESTAMPTZ, TIMESTAMPTZ, INT, INT, TEXT, TEXT, TEXT, TEXT, TEXT, BIGINT, BIGINT, TIMESTAMPTZ, TIMESTAMPTZ, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.update_session(UUID, BIGINT, UUID, TEXT, TIMESTAMPTZ, TIMESTAMPTZ, INT, INT, TEXT, TEXT, TEXT, TEXT, TEXT, BIGINT, BIGINT, TIMESTAMPTZ, TIMESTAMPTZ, UUID) TO authenticated;

-- ============================================================================
-- A1. add_session_player — them nguoi vao tap confirmed sau chot phi can finance
-- Giu nguyen dinh nghia BH-05, chi them gate sau khi xac dinh trang thai.
-- ============================================================================
CREATE OR REPLACE FUNCTION public.add_session_player(
  p_session_id UUID,
  p_member_id UUID DEFAULT NULL,
  p_guest_name TEXT DEFAULT NULL,
  p_contact TEXT DEFAULT NULL,
  p_fee_exempt BOOLEAN DEFAULT FALSE,
  p_allow_waitlist BOOLEAN DEFAULT FALSE,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_session RECORD;
  v_member RECORD;
  v_existing RECORD;
  v_has_existing BOOLEAN := FALSE;
  v_player_id UUID;
  v_user_id UUID;
  v_display TEXT;
  v_guest_name TEXT;
  v_contact TEXT;
  v_participant TEXT;
  v_status TEXT;
  v_fee BIGINT;
  v_confirmed INT;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để thêm người vào buổi' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  v_guest_name := NULLIF(trim(COALESCE(p_guest_name, '')), '');
  v_contact := NULLIF(trim(COALESCE(p_contact, '')), '');

  IF (p_member_id IS NULL) = (v_guest_name IS NULL) THEN
    RAISE EXCEPTION 'INVALID_INPUT: Chọn đúng một thành viên CLB hoặc tên khách' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_management_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ host/quản lý buổi mới thêm người' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(
    p_session_id, p_member_id, v_guest_name, v_contact, COALESCE(p_fee_exempt, FALSE),
    COALESCE(p_allow_waitlist, FALSE))::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('add_session_player', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  IF v_session.lifecycle NOT IN ('published', 'in_progress') THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ thêm người vào buổi đã công bố hoặc đang diễn ra' USING ERRCODE = '22023';
  END IF;

  -- Miễn phí chỉ khi có quyền tài chính (cohost vận hành không tự miễn tiền)
  IF COALESCE(p_fee_exempt, FALSE) AND NOT public.has_session_finance_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ người có quyền tài chính mới được miễn phí' USING ERRCODE = '42501';
  END IF;

  IF p_member_id IS NOT NULL THEN
    SELECT * INTO v_member FROM public.club_members WHERE id = p_member_id;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'NOT_FOUND: Thành viên CLB không tồn tại' USING ERRCODE = 'P0002';
    END IF;
    IF v_session.club_id IS NULL OR v_member.club_id <> v_session.club_id THEN
      RAISE EXCEPTION 'INVALID_INPUT: Thành viên không thuộc CLB của buổi' USING ERRCODE = '22023';
    END IF;
    IF v_member.status <> 'active' THEN
      RAISE EXCEPTION 'INVALID_INPUT: Thành viên không còn hoạt động' USING ERRCODE = '22023';
    END IF;
    v_user_id := v_member.user_id;
    v_display := v_member.display_name;
    v_participant := 'member';
  ELSE
    v_user_id := NULL;
    v_display := v_guest_name;
    v_participant := 'guest';
  END IF;

  -- Chống trùng theo ID đã xác thực (không gộp theo tên/SĐT)
  IF v_user_id IS NOT NULL THEN
    SELECT * INTO v_existing FROM public.session_players
    WHERE session_id = p_session_id AND user_id = v_user_id FOR UPDATE;
    v_has_existing := FOUND;
  ELSIF p_member_id IS NOT NULL THEN
    SELECT * INTO v_existing FROM public.session_players
    WHERE session_id = p_session_id AND club_member_id = p_member_id FOR UPDATE;
    v_has_existing := FOUND;
  END IF;

  IF v_has_existing THEN
    IF v_existing.registration_status IN ('pending', 'confirmed', 'waitlisted') THEN
      RAISE EXCEPTION 'DUPLICATE_PARTICIPANT: Người này đã có đăng ký cho buổi' USING ERRCODE = '23505';
    END IF;
  END IF;

  SELECT count(*)::int INTO v_confirmed
  FROM public.session_players
  WHERE session_id = p_session_id AND registration_status = 'confirmed';

  IF v_confirmed < v_session.capacity THEN
    v_status := 'confirmed';
  ELSIF COALESCE(p_allow_waitlist, FALSE) THEN
    v_status := 'waitlisted';
  ELSE
    RAISE EXCEPTION 'CAPACITY_FULL: Buổi chơi đã đủ chỗ' USING ERRCODE = '22023';
  END IF;

  -- A1: sau khi đã chốt phí (có revision active), thêm người vào tập confirmed
  -- làm thay đổi phần phải thu nên cần quyền tài chính (ADR-08).
  IF v_status = 'confirmed'
     AND EXISTS (SELECT 1 FROM public.charge_revisions cr
                 WHERE cr.session_id = p_session_id AND cr.status = 'active')
     AND NOT public.has_session_finance_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để thêm người đã xác nhận sau khi chốt phí' USING ERRCODE = '42501';
  END IF;

  v_fee := CASE
    WHEN v_status = 'confirmed' AND v_session.fee_mode = 'fixed' THEN
      CASE WHEN v_participant = 'member'
           THEN COALESCE(v_session.member_fee_vnd, 0)
           ELSE COALESCE(v_session.guest_fee_vnd, 0) END
    ELSE NULL END;

  IF v_has_existing THEN
    UPDATE public.session_players SET
      registration_status = v_status,
      participant_type = v_participant,
      club_member_id = p_member_id,
      user_id = v_user_id,
      display_name = v_display,
      source = 'host',
      agreed_fee_vnd = v_fee,
      fee_exempt = COALESCE(p_fee_exempt, FALSE),
      attendance_status = 'not_checked_in',
      checked_in_at = NULL,
      checked_in_by = NULL,
      requested_at = now(),
      confirmed_at = CASE WHEN v_status = 'confirmed' THEN now() ELSE NULL END,
      cancelled_at = NULL,
      updated_at = now()
    WHERE id = v_existing.id;
    v_player_id := v_existing.id;
  ELSE
    INSERT INTO public.session_players (
      session_id, user_id, club_member_id, display_name, registration_status,
      attendance_status, source, participant_type, fee_exempt, agreed_fee_vnd,
      requested_at, confirmed_at, created_by
    ) VALUES (
      p_session_id, v_user_id, p_member_id, v_display, v_status,
      'not_checked_in', 'host', v_participant, COALESCE(p_fee_exempt, FALSE), v_fee,
      now(), CASE WHEN v_status = 'confirmed' THEN now() ELSE NULL END, v_actor
    ) RETURNING id INTO v_player_id;
  END IF;

  IF v_contact IS NOT NULL THEN
    INSERT INTO public.session_player_contacts (player_id, phone_number, updated_at)
    VALUES (v_player_id, v_contact, now())
    ON CONFLICT (player_id) DO UPDATE
      SET phone_number = EXCLUDED.phone_number, updated_at = now();
  END IF;

  IF v_status = 'confirmed' THEN
    PERFORM public.bump_billing_input_version(p_session_id);
  END IF;

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'session_player', v_player_id, 'ADD_SESSION_PLAYER',
    NULL, jsonb_build_object('registration_status', v_status, 'participant_type', v_participant,
                             'fee_exempt', COALESCE(p_fee_exempt, FALSE)),
    'Host thêm người vào buổi', p_request_id);

  v_res := public.registration_result(p_session_id, v_player_id);
  PERFORM public.record_idempotency('add_session_player', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.add_session_player(UUID, UUID, TEXT, TEXT, BOOLEAN, BOOLEAN, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.add_session_player(UUID, UUID, TEXT, TEXT, BOOLEAN, BOOLEAN, UUID) TO authenticated;

-- ============================================================================
-- A1. decide_registration — duyet vao tap confirmed sau chot phi can finance
-- ============================================================================
CREATE OR REPLACE FUNCTION public.decide_registration(
  p_session_id UUID,
  p_player_id UUID,
  p_decision TEXT,
  p_reason TEXT DEFAULT NULL,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_session RECORD;
  v_player RECORD;
  v_fee BIGINT;
  v_confirmed INT;
  v_reason TEXT;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để duyệt đăng ký' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;
  IF p_decision NOT IN ('confirmed', 'rejected', 'waitlisted') THEN
    RAISE EXCEPTION 'INVALID_INPUT: Quyết định không hợp lệ' USING ERRCODE = '22023';
  END IF;

  v_reason := NULLIF(trim(COALESCE(p_reason, '')), '');

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_management_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ host/quản lý buổi mới duyệt đăng ký' USING ERRCODE = '42501';
  END IF;

  SELECT * INTO v_player FROM public.session_players
  WHERE id = p_player_id AND session_id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Đăng ký không tồn tại trong buổi' USING ERRCODE = 'P0002';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_session_id, p_player_id, p_decision, v_reason)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('decide_registration', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  IF v_session.lifecycle NOT IN ('published', 'in_progress') THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ duyệt đăng ký khi buổi đã công bố hoặc đang diễn ra' USING ERRCODE = '22023';
  END IF;

  IF v_player.registration_status = 'confirmed' THEN
    RAISE EXCEPTION 'INVALID_STATE: Người đã confirmed — dùng huỷ đăng ký nếu cần' USING ERRCODE = '22023';
  END IF;
  IF v_player.registration_status NOT IN ('pending', 'waitlisted') THEN
    RAISE EXCEPTION 'INVALID_STATE: Đăng ký ở trạng thái này không duyệt được' USING ERRCODE = '22023';
  END IF;
  -- Không duyệt thẳng waitlisted -> confirmed; phải dùng lời mời (ADR-09)
  IF v_player.registration_status = 'waitlisted' AND p_decision = 'confirmed' THEN
    RAISE EXCEPTION 'INVALID_STATE: Người trong danh sách chờ cần lời mời, không duyệt thẳng' USING ERRCODE = '22023';
  END IF;

  IF p_decision = 'confirmed' THEN
    IF v_session.registration_deadline IS NOT NULL AND now() > v_session.registration_deadline THEN
      RAISE EXCEPTION 'DEADLINE_PASSED: Đã quá hạn đăng ký buổi chơi' USING ERRCODE = '22023';
    END IF;
    SELECT count(*)::int INTO v_confirmed
    FROM public.session_players
    WHERE session_id = p_session_id AND registration_status = 'confirmed';
    IF v_confirmed >= v_session.capacity THEN
      RAISE EXCEPTION 'CAPACITY_FULL: Buổi chơi đã đủ chỗ' USING ERRCODE = '22023';
    END IF;
    -- A1: duyệt vào tập confirmed sau khi đã chốt phí cần quyền tài chính (ADR-08).
    IF EXISTS (SELECT 1 FROM public.charge_revisions cr
               WHERE cr.session_id = p_session_id AND cr.status = 'active')
       AND NOT public.has_session_finance_access(p_session_id, v_actor) THEN
      RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để duyệt người đã xác nhận sau khi chốt phí' USING ERRCODE = '42501';
    END IF;
    v_fee := CASE WHEN v_session.fee_mode = 'fixed'
                  THEN CASE WHEN v_player.participant_type = 'member'
                            THEN COALESCE(v_session.member_fee_vnd, 0)
                            ELSE COALESCE(v_session.guest_fee_vnd, 0) END
                  ELSE NULL END;
  ELSE
    v_fee := NULL;
  END IF;

  UPDATE public.session_players SET
    registration_status = p_decision,
    agreed_fee_vnd = v_fee,
    confirmed_at = CASE WHEN p_decision = 'confirmed' THEN now() ELSE NULL END,
    updated_at = now()
  WHERE id = p_player_id;

  -- Từ chối thì thu hồi mọi lời mời pending của người này (cùng transaction)
  IF p_decision = 'rejected' THEN
    UPDATE public.waitlist_invitations SET
      status = 'revoked', revoked_by = v_actor, revoked_at = now(), updated_at = now()
    WHERE session_player_id = p_player_id AND status = 'pending';
  END IF;

  IF p_decision = 'confirmed' THEN
    PERFORM public.bump_billing_input_version(p_session_id);
  END IF;

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'session_player', p_player_id, 'DECIDE_REGISTRATION',
    jsonb_build_object('registration_status', v_player.registration_status),
    jsonb_build_object('registration_status', p_decision),
    COALESCE(v_reason, 'Duyệt đăng ký'), p_request_id);

  v_res := public.registration_result(p_session_id, p_player_id);
  PERFORM public.record_idempotency('decide_registration', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.decide_registration(UUID, UUID, TEXT, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.decide_registration(UUID, UUID, TEXT, TEXT, UUID) TO authenticated;

-- ============================================================================
-- A1. cancel_registration — roi tap confirmed sau chot phi can finance
-- ============================================================================
CREATE OR REPLACE FUNCTION public.cancel_registration(
  p_session_id UUID,
  p_player_id UUID,
  p_reason TEXT DEFAULT NULL,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_session RECORD;
  v_player RECORD;
  v_is_manager BOOLEAN;
  v_is_self BOOLEAN;
  v_has_payment BOOLEAN;
  v_reason TEXT;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để hủy đăng ký' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  v_reason := NULLIF(trim(COALESCE(p_reason, '')), '');

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;

  SELECT * INTO v_player FROM public.session_players
  WHERE id = p_player_id AND session_id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Đăng ký không tồn tại trong buổi' USING ERRCODE = 'P0002';
  END IF;

  v_is_manager := public.has_session_management_access(p_session_id, v_actor);
  v_is_self := (v_player.user_id IS NOT NULL AND v_player.user_id = v_actor);
  IF NOT v_is_manager AND NOT v_is_self THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ người đăng ký hoặc host/quản lý mới hủy được' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_session_id, p_player_id, v_reason)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('cancel_registration', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  IF v_session.lifecycle IN ('completed', 'cancelled') THEN
    RAISE EXCEPTION 'INVALID_STATE: Buổi chơi đã kết thúc hoặc đã huỷ' USING ERRCODE = '22023';
  END IF;
  IF v_player.registration_status NOT IN ('pending', 'confirmed', 'waitlisted') THEN
    RAISE EXCEPTION 'INVALID_STATE: Đăng ký này đã đóng' USING ERRCODE = '22023';
  END IF;

  -- Người chơi tự hủy phải trong hạn hủy
  IF v_is_self AND NOT v_is_manager
     AND v_session.cancellation_deadline IS NOT NULL
     AND now() > v_session.cancellation_deadline THEN
    RAISE EXCEPTION 'DEADLINE_PASSED: Đã quá hạn hủy đăng ký' USING ERRCODE = '22023';
  END IF;

  -- Không hủy người đã điểm danh present hoặc đã có payment nếu thiếu quyền tài chính
  SELECT EXISTS (
    SELECT 1 FROM public.payments p
    WHERE p.session_player_id = p_player_id AND p.status IN ('submitted', 'confirmed')
  ) INTO v_has_payment;
  IF (v_player.attendance_status = 'present' OR v_has_payment)
     AND NOT public.has_session_finance_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để hủy người đã điểm danh/đã thu tiền' USING ERRCODE = '42501';
  END IF;

  -- A1: rời khỏi tập confirmed sau khi đã chốt phí cũng làm thay đổi phần phải thu
  -- nên cần quyền tài chính (ADR-08).
  IF v_player.registration_status = 'confirmed'
     AND EXISTS (SELECT 1 FROM public.charge_revisions cr
                 WHERE cr.session_id = p_session_id AND cr.status = 'active')
     AND NOT public.has_session_finance_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để hủy người đã xác nhận sau khi chốt phí' USING ERRCODE = '42501';
  END IF;

  UPDATE public.session_players SET
    registration_status = 'cancelled',
    attendance_status = 'not_checked_in',
    checked_in_at = NULL,
    checked_in_by = NULL,
    confirmed_at = NULL,
    cancelled_at = now(),
    agreed_fee_vnd = NULL,
    updated_at = now()
  WHERE id = p_player_id;

  -- Thu hồi mọi lời mời pending của người này trong cùng transaction
  UPDATE public.waitlist_invitations SET
    status = 'revoked', revoked_by = v_actor, revoked_at = now(), updated_at = now()
  WHERE session_player_id = p_player_id AND status = 'pending';

  IF v_player.registration_status = 'confirmed' THEN
    PERFORM public.bump_billing_input_version(p_session_id);
  END IF;

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'session_player', p_player_id, 'CANCEL_REGISTRATION',
    jsonb_build_object('registration_status', v_player.registration_status),
    jsonb_build_object('registration_status', 'cancelled'),
    COALESCE(v_reason, 'Hủy đăng ký'), p_request_id);

  v_res := public.registration_result(p_session_id, p_player_id);
  PERFORM public.record_idempotency('cancel_registration', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.cancel_registration(UUID, UUID, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.cancel_registration(UUID, UUID, TEXT, UUID) TO authenticated;

-- ============================================================================
-- A1. accept_waitlist_invitation — nhan cho sau chot phi can finance
-- ============================================================================
CREATE OR REPLACE FUNCTION public.accept_waitlist_invitation(
  p_session_id UUID,
  p_invitation_id UUID,
  p_consent_note TEXT DEFAULT NULL,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_session RECORD;
  v_inv RECORD;
  v_player RECORD;
  v_confirmed INT;
  v_mode TEXT;
  v_consent TEXT;
  v_fee BIGINT;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để chấp nhận lời mời' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  v_consent := NULLIF(trim(COALESCE(p_consent_note, '')), '');

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;

  SELECT wi.*, sp.session_id AS player_session_id
  INTO v_inv
  FROM public.waitlist_invitations wi
  JOIN public.session_players sp ON sp.id = wi.session_player_id
  WHERE wi.id = p_invitation_id;
  IF NOT FOUND OR v_inv.player_session_id <> p_session_id THEN
    RAISE EXCEPTION 'NOT_FOUND: Lời mời không thuộc buổi này' USING ERRCODE = 'P0002';
  END IF;

  SELECT * INTO v_player
  FROM public.session_players WHERE id = v_inv.session_player_id FOR UPDATE;

  v_payload_hash := md5(jsonb_build_array(p_session_id, p_invitation_id, v_consent)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('accept_waitlist_invitation', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  SELECT * INTO v_inv
  FROM public.waitlist_invitations WHERE id = p_invitation_id FOR UPDATE;

  -- Xác định chế độ chấp nhận
  IF v_player.user_id IS NOT NULL AND v_player.user_id = v_actor THEN
    v_mode := 'self';
  ELSIF public.has_session_management_access(p_session_id, v_actor)
        AND v_player.user_id IS NULL AND v_consent IS NOT NULL THEN
    v_mode := 'host_recorded';
  ELSE
    RAISE EXCEPTION 'FORBIDDEN: Chỉ đúng người nhận hoặc host ghi nhận đồng ý cho khách' USING ERRCODE = '42501';
  END IF;

  IF v_inv.status = 'accepted' THEN
    IF v_player.registration_status = 'confirmed' THEN
      -- Retry hợp lệ: trả kết quả hiện tại, không thêm slot
      v_res := public.registration_result(p_session_id, v_player.id)
        || jsonb_build_object('invitation_id', p_invitation_id, 'invitation_status', 'accepted');
      PERFORM public.record_idempotency('accept_waitlist_invitation', p_request_id, v_payload_hash, v_res);
      RETURN v_res;
    END IF;
    RAISE EXCEPTION 'INVALID_STATE: Lời mời đã dùng nhưng đăng ký không còn confirmed' USING ERRCODE = '22023';
  END IF;
  IF v_inv.status = 'revoked' THEN
    RAISE EXCEPTION 'INVITATION_REVOKED: Lời mời đã bị thu hồi' USING ERRCODE = '22023';
  END IF;
  IF v_inv.status = 'expired' OR v_inv.expires_at <= now() THEN
    IF v_inv.status = 'pending' THEN
      UPDATE public.waitlist_invitations SET status = 'expired', updated_at = now()
      WHERE id = p_invitation_id;
    END IF;
    RAISE EXCEPTION 'INVITATION_EXPIRED: Lời mời đã hết hạn' USING ERRCODE = '22023';
  END IF;

  IF v_player.registration_status <> 'waitlisted' THEN
    RAISE EXCEPTION 'INVALID_STATE: Người chơi không ở trong danh sách chờ' USING ERRCODE = '22023';
  END IF;
  IF v_session.lifecycle <> 'published' THEN
    RAISE EXCEPTION 'INVALID_STATE: Buổi chơi chưa mở đăng ký' USING ERRCODE = '22023';
  END IF;
  IF v_session.registration_deadline IS NOT NULL AND now() > v_session.registration_deadline THEN
    RAISE EXCEPTION 'DEADLINE_PASSED: Đã quá hạn đăng ký buổi chơi' USING ERRCODE = '22023';
  END IF;

  SELECT count(*)::int INTO v_confirmed
  FROM public.session_players
  WHERE session_id = p_session_id AND registration_status = 'confirmed';
  IF v_confirmed >= v_session.capacity THEN
    -- Giữ lời mời pending để có thể thử lại tới hạn
    RAISE EXCEPTION 'CAPACITY_FULL: Buổi chơi đã đủ chỗ, lời mời vẫn còn hiệu lực' USING ERRCODE = '22023';
  END IF;

  -- A1: nhận chỗ đưa người vào tập confirmed; sau khi đã chốt phí cần quyền
  -- tài chính (ADR-08).
  IF EXISTS (SELECT 1 FROM public.charge_revisions cr
             WHERE cr.session_id = p_session_id AND cr.status = 'active')
     AND NOT public.has_session_finance_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để nhận chỗ sau khi chốt phí' USING ERRCODE = '42501';
  END IF;

  v_fee := CASE WHEN v_session.fee_mode = 'fixed'
                THEN CASE WHEN v_player.participant_type = 'member'
                          THEN COALESCE(v_session.member_fee_vnd, 0)
                          ELSE COALESCE(v_session.guest_fee_vnd, 0) END
                ELSE NULL END;

  UPDATE public.session_players SET
    registration_status = 'confirmed',
    agreed_fee_vnd = v_fee,
    confirmed_at = now(),
    cancelled_at = NULL,
    updated_at = now()
  WHERE id = v_player.id;

  UPDATE public.waitlist_invitations SET
    status = 'accepted',
    accepted_by = v_actor,
    accepted_at = now(),
    acceptance_mode = v_mode,
    consent_note = CASE WHEN v_mode = 'host_recorded' THEN v_consent ELSE NULL END,
    updated_at = now()
  WHERE id = p_invitation_id;

  PERFORM public.bump_billing_input_version(p_session_id);

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'waitlist_invitation', p_invitation_id,
    'ACCEPT_WAITLIST_INVITATION',
    jsonb_build_object('registration_status', 'waitlisted'),
    jsonb_build_object('registration_status', 'confirmed', 'acceptance_mode', v_mode),
    CASE WHEN v_mode = 'host_recorded' THEN v_consent ELSE 'Người chơi chấp nhận lời mời' END,
    p_request_id);

  v_res := public.registration_result(p_session_id, v_player.id)
    || jsonb_build_object('invitation_id', p_invitation_id, 'invitation_status', 'accepted');
  PERFORM public.record_idempotency('accept_waitlist_invitation', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.accept_waitlist_invitation(UUID, UUID, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.accept_waitlist_invitation(UUID, UUID, TEXT, UUID) TO authenticated;
