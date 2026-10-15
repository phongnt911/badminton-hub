-- BH-05: đăng ký tham gia, duyệt, hủy, điểm danh và lời mời danh sách chờ.
-- Forward-only. Không sửa migration đã chia sẻ. Không ghi bộ đếm/số dư/role từ client.
-- Mọi mutation: SECURITY DEFINER + search_path cố định, request_id bắt buộc, idempotency
-- theo actor/operation/request + hash canonical chỉ từ input ổn định, audit cùng transaction,
-- REVOKE PUBLIC/anon + GRANT authenticated. Capacity tính từ DB (chỉ confirmed giữ chỗ).

-- ============================================================================
-- 0. Helper nội bộ (không public): kết quả đăng ký + tăng phiên bản input tính phí
-- ============================================================================
CREATE OR REPLACE FUNCTION public.registration_result(p_session_id UUID, p_player_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_player RECORD;
  v_session RECORD;
  v_confirmed INT;
BEGIN
  SELECT capacity, version INTO v_session FROM public.sessions WHERE id = p_session_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;

  SELECT * INTO v_player
  FROM public.session_players
  WHERE id = p_player_id AND session_id = p_session_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Đăng ký không tồn tại trong buổi' USING ERRCODE = 'P0002';
  END IF;

  SELECT count(*)::int INTO v_confirmed
  FROM public.session_players
  WHERE session_id = p_session_id AND registration_status = 'confirmed';

  RETURN jsonb_build_object(
    'player_id', v_player.id,
    'session_id', p_session_id,
    'registration_status', v_player.registration_status,
    'attendance_status', v_player.attendance_status,
    'participant_type', v_player.participant_type,
    'fee_exempt', v_player.fee_exempt,
    'agreed_fee_vnd', v_player.agreed_fee_vnd,
    'confirmed_count', v_confirmed,
    'capacity', v_session.capacity,
    'seats_left', GREATEST(v_session.capacity - v_confirmed, 0),
    'session_version', v_session.version
  );
END;
$$;
REVOKE EXECUTE ON FUNCTION public.registration_result(UUID, UUID) FROM PUBLIC, anon, authenticated;

-- Chỉ tăng khi tập người confirmed hoặc dữ liệu tính phí thay đổi (ADR-08). Client không gọi được.
CREATE OR REPLACE FUNCTION public.bump_billing_input_version(p_session_id UUID)
RETURNS VOID
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  UPDATE public.sessions
  SET billing_input_version = billing_input_version + 1, updated_at = now()
  WHERE id = p_session_id;
$$;
REVOKE EXECUTE ON FUNCTION public.bump_billing_input_version(UUID) FROM PUBLIC, anon, authenticated;

-- ============================================================================
-- 1. Danh sách người đăng ký (management) — bổ sung lời mời pending cho waitlisted
-- ============================================================================
CREATE OR REPLACE FUNCTION public.list_session_players(
  p_session_id UUID,
  p_limit INT DEFAULT 100,
  p_offset INT DEFAULT 0
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem danh sách đăng ký' USING ERRCODE = '42501';
  END IF;
  IF NOT public.has_session_management_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ host/quản lý buổi mới xem được danh sách đăng ký' USING ERRCODE = '42501';
  END IF;

  SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'id', t.id,
      'user_id', t.user_id,
      'display_name', t.display_name,
      'participant_type', t.participant_type,
      'registration_status', t.registration_status,
      'attendance_status', t.attendance_status,
      'fee_exempt', t.fee_exempt,
      'agreed_fee_vnd', t.agreed_fee_vnd,
      'requested_at', t.requested_at,
      'confirmed_at', t.confirmed_at,
      'phone_number', t.phone_number,
      'pending_invitation_id', t.pending_invitation_id,
      'pending_invitation_expires_at', t.pending_invitation_expires_at
    ) ORDER BY t.requested_at ASC, t.id ASC), '[]'::jsonb)
  INTO v_res
  FROM (
    SELECT sp.id, sp.user_id, sp.display_name, sp.participant_type, sp.registration_status,
           sp.attendance_status, sp.fee_exempt, sp.agreed_fee_vnd, sp.requested_at, sp.confirmed_at,
           spc.phone_number,
           wi.pending_invitation_id, wi.pending_invitation_expires_at
    FROM public.session_players sp
    LEFT JOIN public.session_player_contacts spc ON spc.player_id = sp.id
    LEFT JOIN LATERAL (
      SELECT i.id AS pending_invitation_id, i.expires_at AS pending_invitation_expires_at
      FROM public.waitlist_invitations i
      WHERE i.session_player_id = sp.id
        AND i.status = 'pending'
        AND i.expires_at > now()
      ORDER BY i.expires_at DESC
      LIMIT 1
    ) wi ON TRUE
    WHERE sp.session_id = p_session_id
    ORDER BY sp.requested_at ASC, sp.id ASC
    LIMIT LEAST(GREATEST(COALESCE(p_limit, 100), 1), 200)
    OFFSET GREATEST(COALESCE(p_offset, 0), 0)
  ) t;

  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.list_session_players(UUID, INT, INT) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.list_session_players(UUID, INT, INT) TO authenticated;

-- ============================================================================
-- 2. request_join_session — người chơi tự gửi yêu cầu tham gia buổi published
-- ============================================================================
CREATE OR REPLACE FUNCTION public.request_join_session(
  p_session_id UUID,
  p_contact TEXT DEFAULT NULL,
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
  v_has_player BOOLEAN := FALSE;
  v_player_id UUID;
  v_member_id UUID;
  v_display TEXT;
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
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để đăng ký tham gia' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  v_contact := NULLIF(trim(COALESCE(p_contact, '')), '');

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;

  -- Buổi private chỉ cho thành viên CLB hoặc quản lý buổi
  IF v_session.visibility = 'private'
     AND NOT public.has_session_management_access(p_session_id, v_actor)
     AND NOT (v_session.club_id IS NOT NULL AND public.is_club_member_active(v_session.club_id, v_actor)) THEN
    RAISE EXCEPTION 'FORBIDDEN: Buổi nội bộ chỉ dành cho thành viên CLB' USING ERRCODE = '42501';
  END IF;

  -- Hash canonical chỉ từ input ổn định (không gồm version/DB thời gian)
  v_payload_hash := md5(jsonb_build_array(p_session_id, v_contact)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('request_join_session', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  IF v_session.lifecycle <> 'published' THEN
    RAISE EXCEPTION 'INVALID_STATE: Buổi chơi chưa mở đăng ký' USING ERRCODE = '22023';
  END IF;
  IF v_session.starts_at <= now() THEN
    RAISE EXCEPTION 'INVALID_STATE: Buổi chơi đã bắt đầu' USING ERRCODE = '22023';
  END IF;
  IF v_session.registration_deadline IS NOT NULL AND now() > v_session.registration_deadline THEN
    RAISE EXCEPTION 'DEADLINE_PASSED: Đã quá hạn đăng ký buổi chơi' USING ERRCODE = '22023';
  END IF;

  SELECT display_name INTO v_display FROM public.profiles WHERE id = v_actor;
  v_display := COALESCE(NULLIF(trim(COALESCE(v_display, '')), ''), 'Người chơi');

  IF v_session.club_id IS NOT NULL THEN
    SELECT cm.id INTO v_member_id
    FROM public.club_members cm
    WHERE cm.club_id = v_session.club_id AND cm.user_id = v_actor AND cm.status = 'active'
    LIMIT 1;
  END IF;
  v_participant := CASE WHEN v_member_id IS NOT NULL THEN 'member' ELSE 'guest' END;

  SELECT * INTO v_player
  FROM public.session_players
  WHERE session_id = p_session_id AND user_id = v_actor
  FOR UPDATE;
  v_has_player := FOUND;

  IF v_has_player THEN
    IF v_player.registration_status IN ('pending', 'confirmed', 'waitlisted') THEN
      RAISE EXCEPTION 'DUPLICATE_PARTICIPANT: Bạn đã có đăng ký cho buổi này' USING ERRCODE = '23505';
    END IF;
  END IF;

  SELECT count(*)::int INTO v_confirmed
  FROM public.session_players
  WHERE session_id = p_session_id AND registration_status = 'confirmed';

  IF v_session.approval_mode = 'host_approval' THEN
    v_status := 'pending';
    v_fee := NULL;
  ELSIF v_confirmed < v_session.capacity THEN
    v_status := 'confirmed';
    v_fee := CASE WHEN v_session.fee_mode = 'fixed'
                  THEN CASE WHEN v_participant = 'member'
                            THEN COALESCE(v_session.member_fee_vnd, 0)
                            ELSE COALESCE(v_session.guest_fee_vnd, 0) END
                  ELSE NULL END;
  ELSE
    v_status := 'waitlisted';
    v_fee := NULL;
  END IF;

  IF v_has_player THEN
    -- Đăng ký lại sau cancelled/rejected: dùng lại bản ghi cũ, không thêm ID
    UPDATE public.session_players SET
      registration_status = v_status,
      participant_type = v_participant,
      club_member_id = v_member_id,
      display_name = v_display,
      source = 'self',
      agreed_fee_vnd = v_fee,
      fee_exempt = FALSE,
      attendance_status = 'not_checked_in',
      checked_in_at = NULL,
      checked_in_by = NULL,
      requested_at = now(),
      confirmed_at = CASE WHEN v_status = 'confirmed' THEN now() ELSE NULL END,
      cancelled_at = NULL,
      updated_at = now()
    WHERE id = v_player.id;
    v_player_id := v_player.id;
  ELSE
    INSERT INTO public.session_players (
      session_id, user_id, club_member_id, display_name, registration_status,
      attendance_status, source, participant_type, agreed_fee_vnd, requested_at,
      confirmed_at, created_by
    ) VALUES (
      p_session_id, v_actor, v_member_id, v_display, v_status,
      'not_checked_in', 'self', v_participant, v_fee, now(),
      CASE WHEN v_status = 'confirmed' THEN now() ELSE NULL END, v_actor
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
    v_session.club_id, p_session_id, 'session_player', v_player_id, 'REQUEST_JOIN_SESSION',
    NULL, jsonb_build_object('registration_status', v_status, 'participant_type', v_participant),
    'Người chơi gửi yêu cầu tham gia', p_request_id);

  v_res := public.registration_result(p_session_id, v_player_id);
  PERFORM public.record_idempotency('request_join_session', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.request_join_session(UUID, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.request_join_session(UUID, TEXT, UUID) TO authenticated;

-- ============================================================================
-- 3. add_session_player — host/cohost thêm thành viên CLB hoặc khách chưa account
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
-- 4. decide_registration — host/cohost duyệt/từ chối/đưa vào danh sách chờ
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
-- 5. cancel_registration — người chơi tự hủy theo hạn; host xử lý theo quyền
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
-- 6. record_attendance — điểm danh khi buổi đang diễn ra
-- ============================================================================
CREATE OR REPLACE FUNCTION public.record_attendance(
  p_session_id UUID,
  p_player_id UUID,
  p_attendance TEXT,
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
  v_finalized BOOLEAN;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để điểm danh' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;
  IF p_attendance NOT IN ('present', 'no_show', 'not_checked_in') THEN
    RAISE EXCEPTION 'INVALID_INPUT: Trạng thái điểm danh không hợp lệ' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_management_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ host/quản lý buổi mới điểm danh' USING ERRCODE = '42501';
  END IF;

  SELECT * INTO v_player FROM public.session_players
  WHERE id = p_player_id AND session_id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Đăng ký không tồn tại trong buổi' USING ERRCODE = 'P0002';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_session_id, p_player_id, p_attendance)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('record_attendance', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  IF v_session.lifecycle <> 'in_progress' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ điểm danh khi buổi đang diễn ra' USING ERRCODE = '22023';
  END IF;
  IF v_player.registration_status <> 'confirmed' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ điểm danh người đã confirmed' USING ERRCODE = '22023';
  END IF;

  -- Sau khi chốt phí: thay điểm danh cần quyền tài chính (ADR-08)
  SELECT EXISTS (
    SELECT 1 FROM public.charge_revisions cr
    WHERE cr.session_id = p_session_id AND cr.status = 'active'
  ) INTO v_finalized;
  IF v_finalized AND NOT public.has_session_finance_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để sửa điểm danh sau khi chốt phí' USING ERRCODE = '42501';
  END IF;

  UPDATE public.session_players SET
    attendance_status = p_attendance,
    checked_in_at = CASE WHEN p_attendance = 'present' THEN now() ELSE NULL END,
    checked_in_by = CASE WHEN p_attendance = 'present' THEN v_actor ELSE NULL END,
    updated_at = now()
  WHERE id = p_player_id;

  PERFORM public.bump_billing_input_version(p_session_id);

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'session_player', p_player_id, 'RECORD_ATTENDANCE',
    jsonb_build_object('attendance_status', v_player.attendance_status),
    jsonb_build_object('attendance_status', p_attendance),
    'Điểm danh', p_request_id);

  v_res := public.registration_result(p_session_id, p_player_id);
  PERFORM public.record_idempotency('record_attendance', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.record_attendance(UUID, UUID, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.record_attendance(UUID, UUID, TEXT, UUID) TO authenticated;

-- ============================================================================
-- 7. invite_waitlisted_player — host phát hành lời mời (không giữ slot)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.invite_waitlisted_player(
  p_session_id UUID,
  p_player_id UUID,
  p_expires_at TIMESTAMPTZ DEFAULT NULL,
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
  v_bound TIMESTAMPTZ;
  v_expires TIMESTAMPTZ;
  v_invitation_id UUID;
  v_invited_at TIMESTAMPTZ;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để mời người trong danh sách chờ' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_management_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ host/quản lý buổi mới phát hành lời mời' USING ERRCODE = '42501';
  END IF;

  SELECT * INTO v_player FROM public.session_players
  WHERE id = p_player_id AND session_id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Đăng ký không tồn tại trong buổi' USING ERRCODE = 'P0002';
  END IF;

  -- Hash chỉ từ input ổn định (không gồm expires_at mặc định tính tại chỗ)
  v_payload_hash := md5(jsonb_build_array(p_session_id, p_player_id, p_expires_at)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('invite_waitlisted_player', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  IF v_session.lifecycle <> 'published' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ mời khi buổi đã công bố' USING ERRCODE = '22023';
  END IF;
  IF v_player.registration_status <> 'waitlisted' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ mời người đang trong danh sách chờ' USING ERRCODE = '22023';
  END IF;
  IF v_session.registration_deadline IS NOT NULL AND now() >= v_session.registration_deadline THEN
    RAISE EXCEPTION 'DEADLINE_PASSED: Đã quá hạn đăng ký buổi chơi' USING ERRCODE = '22023';
  END IF;

  -- Trần thời gian: không vượt hạn đăng ký hoặc giờ bắt đầu
  v_bound := LEAST(
    COALESCE(v_session.registration_deadline, 'infinity'::timestamptz),
    v_session.starts_at);
  v_expires := COALESCE(p_expires_at, LEAST(now() + interval '30 minutes', v_bound));

  IF v_expires <= now() THEN
    RAISE EXCEPTION 'INVALID_INPUT: Thời hạn lời mời phải ở tương lai' USING ERRCODE = '22023';
  END IF;
  IF v_expires > v_bound THEN
    RAISE EXCEPTION 'INVALID_INPUT: Thời hạn lời mời vượt hạn đăng ký/giờ bắt đầu' USING ERRCODE = '22023';
  END IF;

  -- Hết hiệu lực lời mời cũ (còn pending) trước khi tạo mới
  UPDATE public.waitlist_invitations SET status = 'expired', updated_at = now()
  WHERE session_player_id = p_player_id AND status = 'pending';

  INSERT INTO public.waitlist_invitations (
    session_player_id, invited_by, invited_at, expires_at, status
  ) VALUES (
    p_player_id, v_actor, now(), v_expires, 'pending'
  ) RETURNING id, invited_at INTO v_invitation_id, v_invited_at;

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'waitlist_invitation', v_invitation_id,
    'INVITE_WAITLISTED_PLAYER',
    NULL, jsonb_build_object('player_id', p_player_id, 'expires_at', v_expires),
    'Phát hành lời mời danh sách chờ', p_request_id);

  v_saved_result := jsonb_build_object(
    'invitation_id', v_invitation_id,
    'session_id', p_session_id,
    'player_id', p_player_id,
    'status', 'pending',
    'invited_at', v_invited_at,
    'expires_at', v_expires
  );
  PERFORM public.record_idempotency('invite_waitlisted_player', p_request_id, v_payload_hash, v_saved_result);
  RETURN v_saved_result;
END;
$$;
REVOKE ALL ON FUNCTION public.invite_waitlisted_player(UUID, UUID, TIMESTAMPTZ, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.invite_waitlisted_player(UUID, UUID, TIMESTAMPTZ, UUID) TO authenticated;

-- ============================================================================
-- 8. revoke_waitlist_invitation — thu hồi lời mời pending
-- ============================================================================
CREATE OR REPLACE FUNCTION public.revoke_waitlist_invitation(
  p_session_id UUID,
  p_invitation_id UUID,
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
  v_inv RECORD;
  v_lock_id UUID;
  v_reason TEXT;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để thu hồi lời mời' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  v_reason := NULLIF(trim(COALESCE(p_reason, '')), '');

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_management_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ host/quản lý buổi mới thu hồi lời mời' USING ERRCODE = '42501';
  END IF;

  SELECT wi.*, sp.session_id AS player_session_id
  INTO v_inv
  FROM public.waitlist_invitations wi
  JOIN public.session_players sp ON sp.id = wi.session_player_id
  WHERE wi.id = p_invitation_id;
  IF NOT FOUND OR v_inv.player_session_id <> p_session_id THEN
    RAISE EXCEPTION 'NOT_FOUND: Lời mời không thuộc buổi này' USING ERRCODE = 'P0002';
  END IF;

  SELECT id INTO v_lock_id FROM public.session_players WHERE id = v_inv.session_player_id FOR UPDATE;

  v_payload_hash := md5(jsonb_build_array(p_session_id, p_invitation_id, v_reason)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('revoke_waitlist_invitation', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  SELECT * INTO v_inv
  FROM public.waitlist_invitations WHERE id = p_invitation_id FOR UPDATE;

  IF v_inv.status = 'accepted' THEN
    RAISE EXCEPTION 'INVALID_STATE: Lời mời đã được chấp nhận — dùng hủy đăng ký' USING ERRCODE = '22023';
  END IF;
  IF v_inv.status = 'expired' THEN
    RAISE EXCEPTION 'INVALID_STATE: Lời mời đã hết hạn' USING ERRCODE = '22023';
  END IF;

  IF v_inv.status = 'pending' THEN
    UPDATE public.waitlist_invitations SET
      status = 'revoked', revoked_by = v_actor, revoked_at = now(), updated_at = now()
    WHERE id = p_invitation_id;

    PERFORM public.log_audit_event(
      v_session.club_id, p_session_id, 'waitlist_invitation', p_invitation_id,
      'REVOKE_WAITLIST_INVITATION',
      jsonb_build_object('status', 'pending'), jsonb_build_object('status', 'revoked'),
      COALESCE(v_reason, 'Thu hồi lời mời'), p_request_id);
  END IF;

  v_saved_result := jsonb_build_object(
    'invitation_id', p_invitation_id,
    'session_id', p_session_id,
    'player_id', v_inv.session_player_id,
    'status', 'revoked',
    'expires_at', v_inv.expires_at
  );
  PERFORM public.record_idempotency('revoke_waitlist_invitation', p_request_id, v_payload_hash, v_saved_result);
  RETURN v_saved_result;
END;
$$;
REVOKE ALL ON FUNCTION public.revoke_waitlist_invitation(UUID, UUID, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.revoke_waitlist_invitation(UUID, UUID, TEXT, UUID) TO authenticated;

-- ============================================================================
-- 9. accept_waitlist_invitation — self (đúng người) hoặc host_recorded (guest + consent)
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

-- ============================================================================
-- 10. get_my_waitlist_invitation — người chơi đọc lời mời pending của chính mình
-- ============================================================================
CREATE OR REPLACE FUNCTION public.get_my_waitlist_invitation(p_session_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_player_id UUID;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RETURN NULL;
  END IF;

  SELECT id INTO v_player_id
  FROM public.session_players
  WHERE session_id = p_session_id AND user_id = v_actor;
  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  SELECT jsonb_build_object(
    'invitation_id', wi.id,
    'player_id', wi.session_player_id,
    'session_id', p_session_id,
    'status', wi.status,
    'invited_at', wi.invited_at,
    'expires_at', wi.expires_at
  ) INTO v_res
  FROM public.waitlist_invitations wi
  WHERE wi.session_player_id = v_player_id
    AND wi.status = 'pending'
    AND wi.expires_at > now()
  ORDER BY wi.expires_at DESC
  LIMIT 1;

  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.get_my_waitlist_invitation(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_my_waitlist_invitation(UUID) TO authenticated;
