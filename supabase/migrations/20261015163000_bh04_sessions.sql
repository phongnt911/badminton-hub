-- BH-04: buổi chơi (sessions) — RPC nguyên tử + projection whitelist + lọc công khai.
-- Forward-only. Không sửa migration đã chia sẻ. Không ghi joined_count/số dư/role từ client.
-- Thời gian lưu UTC (timestamptz); hiển thị Asia/Ho_Chi_Minh ở client.

-- ============================================================================
-- 1. Chi tiết buổi chơi (whitelist) — public/unlisted mở theo link,
--    draft/private yêu cầu quyền. Bổ sung cờ quản lý + đăng ký của chính mình.
-- ============================================================================
CREATE OR REPLACE FUNCTION public.get_session_public_detail(p_session_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_session RECORD;
  v_can_manage BOOLEAN := FALSE;
  v_can_view_finance BOOLEAN := FALSE;
  v_is_host BOOLEAN := FALSE;
  v_registration JSONB := NULL;
BEGIN
  SELECT s.*, v.name AS venue_name, v.address AS venue_address, v.area AS venue_area,
         p.display_name AS host_display_name
  INTO v_session
  FROM public.sessions s
  LEFT JOIN public.venues v ON s.venue_id = v.id
  LEFT JOIN public.profiles p ON s.host_user_id = p.id
  WHERE s.id = p_session_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;

  IF v_actor IS NOT NULL THEN
    v_is_host := (v_session.host_user_id = v_actor);
    v_can_manage := v_is_host OR public.has_session_management_access(p_session_id, v_actor);
    v_can_view_finance := v_is_host OR public.has_session_finance_access(p_session_id, v_actor);
  END IF;

  -- draft hoặc private: phải có quyền (PD-01)
  IF v_session.visibility = 'private' OR v_session.lifecycle = 'draft' THEN
    IF v_actor IS NULL THEN
      RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem buổi chơi này' USING ERRCODE = '42501';
    END IF;
    IF NOT (
      v_can_manage OR v_can_view_finance OR
      (v_session.club_id IS NOT NULL AND public.is_club_member_active(v_session.club_id, v_actor)) OR
      public.is_session_participant(p_session_id, v_actor)
    ) THEN
      RAISE EXCEPTION 'FORBIDDEN: Không có quyền xem buổi chơi này' USING ERRCODE = '42501';
    END IF;
  END IF;

  IF v_actor IS NOT NULL THEN
    SELECT jsonb_build_object(
      'player_id', sp.id,
      'registration_status', sp.registration_status,
      'attendance_status', sp.attendance_status,
      'participant_type', sp.participant_type,
      'agreed_fee_vnd', sp.agreed_fee_vnd
    ) INTO v_registration
    FROM public.session_players sp
    WHERE sp.session_id = p_session_id AND sp.user_id = v_actor;
  END IF;

  RETURN jsonb_build_object(
    'id', v_session.id,
    'club_id', v_session.club_id,
    'title', v_session.title,
    'description', v_session.description,
    'starts_at', v_session.starts_at,
    'ends_at', v_session.ends_at,
    'capacity', v_session.capacity,
    'court_count', v_session.court_count,
    'level_requirement', v_session.level_requirement,
    'visibility', v_session.visibility,
    'lifecycle', v_session.lifecycle,
    'approval_mode', v_session.approval_mode,
    'fee_mode', v_session.fee_mode,
    'member_fee_vnd', v_session.member_fee_vnd,
    'guest_fee_vnd', v_session.guest_fee_vnd,
    'registration_deadline', v_session.registration_deadline,
    'cancellation_deadline', v_session.cancellation_deadline,
    'venue_id', v_session.venue_id,
    'venue_name', v_session.venue_name,
    'venue_address', v_session.venue_address,
    'venue_area', v_session.venue_area,
    'host_display_name', v_session.host_display_name,
    'version', v_session.version,
    'is_host', v_is_host,
    'can_manage', v_can_manage,
    'can_view_finance', v_can_view_finance,
    'confirmed_count', (
      SELECT count(*)::int FROM public.session_players
      WHERE session_id = p_session_id AND registration_status = 'confirmed'
    ),
    'my_registration', v_registration
  );
END;
$$;
GRANT EXECUTE ON FUNCTION public.get_session_public_detail(UUID) TO anon, authenticated;

-- ============================================================================
-- 2. Kiểm tra hợp lệ cấu hình buổi chơi (dùng chung create/update/duplicate)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.validate_session_config(
  p_venue_id UUID,
  p_starts_at TIMESTAMPTZ,
  p_ends_at TIMESTAMPTZ,
  p_capacity INT,
  p_court_count INT,
  p_visibility TEXT,
  p_approval_mode TEXT,
  p_fee_mode TEXT,
  p_member_fee_vnd BIGINT,
  p_guest_fee_vnd BIGINT,
  p_registration_deadline TIMESTAMPTZ,
  p_cancellation_deadline TIMESTAMPTZ
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  IF p_venue_id IS NULL OR NOT EXISTS (
    SELECT 1 FROM public.venues WHERE id = p_venue_id AND status = 'active'
  ) THEN
    RAISE EXCEPTION 'INVALID_INPUT: Sân không tồn tại hoặc đã ngừng hoạt động' USING ERRCODE = '22023';
  END IF;

  IF p_starts_at IS NULL OR p_ends_at IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: Thiếu thời gian bắt đầu/kết thúc' USING ERRCODE = '22023';
  END IF;
  IF p_ends_at <= p_starts_at THEN
    RAISE EXCEPTION 'INVALID_INPUT: Thời gian kết thúc phải sau thời gian bắt đầu' USING ERRCODE = '22023';
  END IF;

  IF p_capacity IS NULL OR p_capacity < 1 OR p_capacity > 200 THEN
    RAISE EXCEPTION 'INVALID_INPUT: Sức chứa phải trong khoảng 1..200' USING ERRCODE = '22023';
  END IF;
  IF p_court_count IS NULL OR p_court_count < 1 OR p_court_count > 50 THEN
    RAISE EXCEPTION 'INVALID_INPUT: Số sân phải trong khoảng 1..50' USING ERRCODE = '22023';
  END IF;

  IF p_visibility NOT IN ('private', 'unlisted', 'public') THEN
    RAISE EXCEPTION 'INVALID_INPUT: visibility không hợp lệ' USING ERRCODE = '22023';
  END IF;
  IF p_approval_mode NOT IN ('host_approval', 'auto_confirm') THEN
    RAISE EXCEPTION 'INVALID_INPUT: approval_mode không hợp lệ' USING ERRCODE = '22023';
  END IF;
  IF p_fee_mode NOT IN ('fixed', 'split_actual') THEN
    RAISE EXCEPTION 'INVALID_INPUT: fee_mode không hợp lệ' USING ERRCODE = '22023';
  END IF;

  IF p_member_fee_vnd IS NOT NULL AND (p_member_fee_vnd < 0 OR p_member_fee_vnd > 1000000000) THEN
    RAISE EXCEPTION 'INVALID_INPUT: member_fee_vnd ngoài miền cho phép' USING ERRCODE = '22023';
  END IF;
  IF p_guest_fee_vnd IS NOT NULL AND (p_guest_fee_vnd < 0 OR p_guest_fee_vnd > 1000000000) THEN
    RAISE EXCEPTION 'INVALID_INPUT: guest_fee_vnd ngoài miền cho phép' USING ERRCODE = '22023';
  END IF;

  IF p_fee_mode = 'fixed' AND (p_member_fee_vnd IS NULL OR p_guest_fee_vnd IS NULL) THEN
    RAISE EXCEPTION 'INVALID_INPUT: fee_mode=fixed cần member_fee_vnd và guest_fee_vnd' USING ERRCODE = '22023';
  END IF;

  IF p_registration_deadline IS NOT NULL AND p_registration_deadline > p_ends_at THEN
    RAISE EXCEPTION 'INVALID_INPUT: Hạn đăng ký phải trước khi buổi kết thúc' USING ERRCODE = '22023';
  END IF;
  IF p_cancellation_deadline IS NOT NULL AND p_cancellation_deadline > p_starts_at THEN
    RAISE EXCEPTION 'INVALID_INPUT: Hạn huỷ phải trước khi buổi bắt đầu' USING ERRCODE = '22023';
  END IF;
END;
$$;
REVOKE EXECUTE ON FUNCTION public.validate_session_config(UUID, TIMESTAMPTZ, TIMESTAMPTZ, INT, INT, TEXT, TEXT, TEXT, BIGINT, BIGINT, TIMESTAMPTZ, TIMESTAMPTZ) FROM PUBLIC, anon, authenticated;

-- ============================================================================
-- 3. Tạo buổi chơi (draft)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.create_session(
  p_venue_id UUID,
  p_title TEXT,
  p_starts_at TIMESTAMPTZ,
  p_ends_at TIMESTAMPTZ,
  p_capacity INT,
  p_court_count INT,
  p_club_id UUID DEFAULT NULL,
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
  v_session_id UUID;
  v_view JSONB;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để tạo buổi chơi' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  p_title := NULLIF(trim(COALESCE(p_title, '')), '');
  IF p_title IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: Tiêu đề buổi chơi không được để trống' USING ERRCODE = '22023';
  END IF;

  -- CLB (nếu gắn): actor phải là owner/host của CLB active
  IF p_club_id IS NOT NULL THEN
    IF NOT EXISTS (SELECT 1 FROM public.clubs WHERE id = p_club_id AND status = 'active') THEN
      RAISE EXCEPTION 'INVALID_INPUT: CLB không tồn tại hoặc đã ngừng hoạt động' USING ERRCODE = '22023';
    END IF;
    IF NOT (public.is_club_owner(p_club_id, v_actor) OR public.has_club_role(p_club_id, v_actor, ARRAY['owner', 'host'])) THEN
      RAISE EXCEPTION 'FORBIDDEN: Chỉ chủ nhiệm/quản lý CLB mới tạo được buổi cho CLB' USING ERRCODE = '42501';
    END IF;
  END IF;

  PERFORM public.validate_session_config(
    p_venue_id, p_starts_at, p_ends_at, p_capacity, p_court_count, p_visibility,
    p_approval_mode, p_fee_mode, p_member_fee_vnd, p_guest_fee_vnd,
    p_registration_deadline, p_cancellation_deadline);

  IF p_starts_at <= now() THEN
    RAISE EXCEPTION 'INVALID_INPUT: Thời gian bắt đầu phải ở tương lai' USING ERRCODE = '22023';
  END IF;

  v_payload_hash := md5(jsonb_build_array(
    p_venue_id, p_title, p_starts_at, p_ends_at, p_capacity, p_court_count, p_club_id,
    p_description, p_level_requirement, p_visibility, p_approval_mode, p_fee_mode,
    p_member_fee_vnd, p_guest_fee_vnd, p_registration_deadline, p_cancellation_deadline)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('create_session', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  -- Đảm bảo profile host tồn tại (tận dụng bản ghi cũ nếu có)
  INSERT INTO public.profiles (id, display_name)
  VALUES (v_actor, 'Chủ buổi')
  ON CONFLICT (id) DO NOTHING;

  INSERT INTO public.sessions (
    club_id, host_user_id, venue_id, title, description, starts_at, ends_at,
    capacity, court_count, level_requirement, visibility, lifecycle, approval_mode,
    fee_mode, member_fee_vnd, guest_fee_vnd, registration_deadline, cancellation_deadline
  ) VALUES (
    p_club_id, v_actor, p_venue_id, p_title, NULLIF(trim(COALESCE(p_description, '')), ''), p_starts_at, p_ends_at,
    p_capacity, p_court_count, NULLIF(trim(COALESCE(p_level_requirement, '')), ''), p_visibility, 'draft', p_approval_mode,
    p_fee_mode, p_member_fee_vnd, p_guest_fee_vnd, p_registration_deadline, p_cancellation_deadline
  ) RETURNING id INTO v_session_id;

  PERFORM public.log_audit_event(
    p_club_id, v_session_id, 'session', v_session_id, 'CREATE_SESSION',
    NULL, jsonb_build_object('title', p_title, 'starts_at', p_starts_at, 'visibility', p_visibility),
    'Tạo buổi chơi', p_request_id);

  v_view := public.get_session_public_detail(v_session_id);

  PERFORM public.record_idempotency('create_session', p_request_id, v_payload_hash, v_view);
  RETURN v_view;
END;
$$;
REVOKE ALL ON FUNCTION public.create_session(UUID, TEXT, TIMESTAMPTZ, TIMESTAMPTZ, INT, INT, UUID, TEXT, TEXT, TEXT, TEXT, TEXT, BIGINT, BIGINT, TIMESTAMPTZ, TIMESTAMPTZ, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.create_session(UUID, TEXT, TIMESTAMPTZ, TIMESTAMPTZ, INT, INT, UUID, TEXT, TEXT, TEXT, TEXT, TEXT, BIGINT, BIGINT, TIMESTAMPTZ, TIMESTAMPTZ, UUID) TO authenticated;

-- ============================================================================
-- 4. Cập nhật buổi chơi (optimistic version)
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
-- 5. Đổi vòng đời: publish / cancel
-- ============================================================================
CREATE OR REPLACE FUNCTION public.set_session_lifecycle(
  p_session_id UUID,
  p_action TEXT,
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
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để đổi trạng thái buổi chơi' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;
  IF p_action NOT IN ('publish', 'cancel') THEN
    RAISE EXCEPTION 'INVALID_INPUT: Hành động không hợp lệ' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_management_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Không có quyền đổi trạng thái buổi chơi' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_session_id, p_action, v_session.version)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('set_session_lifecycle', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  IF p_action = 'publish' THEN
    IF v_session.lifecycle <> 'draft' THEN
      RAISE EXCEPTION 'INVALID_STATE: Chỉ công bố được buổi đang ở bản nháp' USING ERRCODE = '22023';
    END IF;
    IF v_session.starts_at <= now() THEN
      RAISE EXCEPTION 'INVALID_STATE: Không công bố buổi đã qua thời gian bắt đầu' USING ERRCODE = '22023';
    END IF;
    IF v_session.fee_mode = 'fixed' AND (v_session.member_fee_vnd IS NULL OR v_session.guest_fee_vnd IS NULL) THEN
      RAISE EXCEPTION 'INVALID_STATE: Buổi thu phí cố định thiếu mức phí' USING ERRCODE = '22023';
    END IF;
  ELSE
    IF v_session.lifecycle NOT IN ('draft', 'published', 'in_progress') THEN
      RAISE EXCEPTION 'INVALID_STATE: Không huỷ được buổi ở trạng thái này' USING ERRCODE = '22023';
    END IF;
  END IF;

  UPDATE public.sessions SET
    lifecycle = CASE WHEN p_action = 'publish' THEN 'published' ELSE 'cancelled' END,
    version = version + 1,
    updated_at = now()
  WHERE id = p_session_id;

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'session', p_session_id,
    CASE WHEN p_action = 'publish' THEN 'PUBLISH_SESSION' ELSE 'CANCEL_SESSION' END,
    jsonb_build_object('lifecycle', v_session.lifecycle),
    jsonb_build_object('lifecycle', CASE WHEN p_action = 'publish' THEN 'published' ELSE 'cancelled' END),
    'Đổi trạng thái buổi chơi', p_request_id);

  v_res := public.get_session_public_detail(p_session_id);
  PERFORM public.record_idempotency('set_session_lifecycle', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.set_session_lifecycle(UUID, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.set_session_lifecycle(UUID, TEXT, UUID) TO authenticated;

-- ============================================================================
-- 6. Nhân bản buổi chơi — KHÔNG sao chép người chơi/tiền
-- ============================================================================
CREATE OR REPLACE FUNCTION public.duplicate_session(
  p_session_id UUID,
  p_starts_at TIMESTAMPTZ,
  p_ends_at TIMESTAMPTZ,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_src RECORD;
  v_new_id UUID;
  v_view JSONB;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để nhân bản buổi chơi' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_src FROM public.sessions WHERE id = p_session_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_management_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Không có quyền nhân bản buổi chơi' USING ERRCODE = '42501';
  END IF;

  PERFORM public.validate_session_config(
    v_src.venue_id, p_starts_at, p_ends_at, v_src.capacity, v_src.court_count, v_src.visibility,
    v_src.approval_mode, v_src.fee_mode, v_src.member_fee_vnd, v_src.guest_fee_vnd,
    NULL, NULL);

  IF p_starts_at <= now() THEN
    RAISE EXCEPTION 'INVALID_INPUT: Thời gian bắt đầu phải ở tương lai' USING ERRCODE = '22023';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_session_id, p_starts_at, p_ends_at)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('duplicate_session', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  INSERT INTO public.sessions (
    club_id, host_user_id, venue_id, title, description, starts_at, ends_at,
    capacity, court_count, level_requirement, visibility, lifecycle, approval_mode,
    fee_mode, member_fee_vnd, guest_fee_vnd, registration_deadline, cancellation_deadline
  ) VALUES (
    v_src.club_id, v_actor, v_src.venue_id, v_src.title, v_src.description, p_starts_at, p_ends_at,
    v_src.capacity, v_src.court_count, v_src.level_requirement, v_src.visibility, 'draft', v_src.approval_mode,
    v_src.fee_mode, v_src.member_fee_vnd, v_src.guest_fee_vnd, NULL, NULL
  ) RETURNING id INTO v_new_id;

  PERFORM public.log_audit_event(
    v_src.club_id, v_new_id, 'session', v_new_id, 'DUPLICATE_SESSION',
    jsonb_build_object('source_session_id', p_session_id),
    jsonb_build_object('title', v_src.title, 'starts_at', p_starts_at),
    'Nhân bản buổi chơi (không sao chép người/tiền)', p_request_id);

  v_view := public.get_session_public_detail(v_new_id);
  PERFORM public.record_idempotency('duplicate_session', p_request_id, v_payload_hash, v_view);
  RETURN v_view;
END;
$$;
REVOKE ALL ON FUNCTION public.duplicate_session(UUID, TIMESTAMPTZ, TIMESTAMPTZ, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.duplicate_session(UUID, TIMESTAMPTZ, TIMESTAMPTZ, UUID) TO authenticated;

-- ============================================================================
-- 7. Danh sách buổi tôi quản lý (host/management/finance) — phân trang trước agg
-- ============================================================================
CREATE OR REPLACE FUNCTION public.list_my_sessions(
  p_limit INT DEFAULT 50,
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
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem danh sách buổi chơi' USING ERRCODE = '42501';
  END IF;

  SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'id', t.id,
      'club_id', t.club_id,
      'club_name', t.club_name,
      'title', t.title,
      'starts_at', t.starts_at,
      'ends_at', t.ends_at,
      'capacity', t.capacity,
      'court_count', t.court_count,
      'visibility', t.visibility,
      'lifecycle', t.lifecycle,
      'fee_mode', t.fee_mode,
      'member_fee_vnd', t.member_fee_vnd,
      'guest_fee_vnd', t.guest_fee_vnd,
      'venue_name', t.venue_name,
      'venue_area', t.venue_area,
      'confirmed_count', t.confirmed_count,
      'version', t.version
    ) ORDER BY t.starts_at ASC, t.id ASC), '[]'::jsonb)
  INTO v_res
  FROM (
    SELECT s.id, s.club_id, c.name AS club_name, s.title, s.starts_at, s.ends_at,
           s.capacity, s.court_count, s.visibility, s.lifecycle, s.fee_mode,
           s.member_fee_vnd, s.guest_fee_vnd, s.version,
           v.name AS venue_name, v.area AS venue_area,
           COALESCE((
             SELECT count(*)::int FROM public.session_players sp
             WHERE sp.session_id = s.id AND sp.registration_status = 'confirmed'
           ), 0) AS confirmed_count
    FROM public.sessions s
    LEFT JOIN public.clubs c ON c.id = s.club_id
    LEFT JOIN public.venues v ON v.id = s.venue_id
    WHERE s.host_user_id = v_actor
       OR public.has_session_management_access(s.id, v_actor)
       OR public.has_session_finance_access(s.id, v_actor)
    ORDER BY s.starts_at ASC, s.id ASC
    LIMIT LEAST(GREATEST(COALESCE(p_limit, 50), 1), 100)
    OFFSET GREATEST(COALESCE(p_offset, 0), 0)
  ) t;

  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.list_my_sessions(INT, INT) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.list_my_sessions(INT, INT) TO authenticated;

-- ============================================================================
-- 8. Khám phá buổi công khai (PD-02) — whitelist, anon đọc được
-- ============================================================================
CREATE OR REPLACE FUNCTION public.list_public_sessions(
  p_area TEXT DEFAULT NULL,
  p_from TIMESTAMPTZ DEFAULT NULL,
  p_to TIMESTAMPTZ DEFAULT NULL,
  p_fee_mode TEXT DEFAULT NULL,
  p_only_available BOOLEAN DEFAULT FALSE,
  p_limit INT DEFAULT 50,
  p_offset INT DEFAULT 0
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_res JSONB;
BEGIN
  IF p_fee_mode IS NOT NULL AND p_fee_mode NOT IN ('fixed', 'split_actual') THEN
    RAISE EXCEPTION 'INVALID_INPUT: fee_mode không hợp lệ' USING ERRCODE = '22023';
  END IF;

  SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'id', t.id,
      'club_id', t.club_id,
      'title', t.title,
      'starts_at', t.starts_at,
      'ends_at', t.ends_at,
      'capacity', t.capacity,
      'court_count', t.court_count,
      'level_requirement', t.level_requirement,
      'visibility', t.visibility,
      'lifecycle', t.lifecycle,
      'fee_mode', t.fee_mode,
      'member_fee_vnd', t.member_fee_vnd,
      'guest_fee_vnd', t.guest_fee_vnd,
      'registration_deadline', t.registration_deadline,
      'venue_name', t.venue_name,
      'venue_area', t.venue_area,
      'host_display_name', t.host_display_name,
      'confirmed_count', t.confirmed_player_count
    ) ORDER BY t.starts_at ASC, t.id ASC), '[]'::jsonb)
  INTO v_res
  FROM (
    SELECT id, club_id, title, starts_at, ends_at, capacity, court_count, level_requirement,
           visibility, lifecycle, fee_mode, member_fee_vnd, guest_fee_vnd, registration_deadline,
           venue_name, venue_area, host_display_name, confirmed_player_count
    FROM public.public_session_summary
    WHERE (p_area IS NULL OR venue_area = p_area)
      AND (p_from IS NULL OR starts_at >= p_from)
      AND (p_to IS NULL OR starts_at <= p_to)
      AND (p_fee_mode IS NULL OR fee_mode = p_fee_mode)
      AND (p_only_available IS NOT TRUE OR confirmed_player_count < capacity)
    ORDER BY starts_at ASC, id ASC
    LIMIT LEAST(GREATEST(COALESCE(p_limit, 50), 1), 100)
    OFFSET GREATEST(COALESCE(p_offset, 0), 0)
  ) t;

  RETURN v_res;
END;
$$;
GRANT EXECUTE ON FUNCTION public.list_public_sessions(TEXT, TIMESTAMPTZ, TIMESTAMPTZ, TEXT, BOOLEAN, INT, INT) TO anon, authenticated;

-- ============================================================================
-- 9. Danh sách người đăng ký (management) — finance KHÔNG đọc (F7)
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
      'phone_number', t.phone_number
    ) ORDER BY t.requested_at ASC, t.id ASC), '[]'::jsonb)
  INTO v_res
  FROM (
    SELECT sp.id, sp.user_id, sp.display_name, sp.participant_type, sp.registration_status,
           sp.attendance_status, sp.fee_exempt, sp.agreed_fee_vnd, sp.requested_at, sp.confirmed_at,
           spc.phone_number
    FROM public.session_players sp
    LEFT JOIN public.session_player_contacts spc ON spc.player_id = sp.id
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
