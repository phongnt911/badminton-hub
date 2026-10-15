-- Generated with CLI; reordered after existing future-dated BH04 migration.
-- Stable request hash: database version is not request input.
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

  v_payload_hash := md5(jsonb_build_array(p_session_id, p_action)::text);
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
