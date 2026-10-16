-- BH-05 tich hop — review c7ed6d5 I1 (P1).
-- Lo hong: app tao draft -> publish nhung KHONG co duong hop le dua buoi sang
-- 'in_progress', nen diem danh (record_attendance chi cho in_progress) khong the
-- chay tu app; runner cu phai UPDATE sessions tay. Bo sung RPC start_session:
-- published -> in_progress co kiem actor/management, khoa session, request_id,
-- idempotency/hash/replay, audit va ACL. KHONG mo direct UPDATE tren sessions va
-- KHONG noi long guard in_progress cua record_attendance.
--
-- Khong sua migration da chia se (BH-04 va cac file BH-05 truoc); day la file moi,
-- forward-only. Giu nguyen mau SECURITY DEFINER + search_path + thu tu khoa
-- session FOR UPDATE nhu set_session_lifecycle.

CREATE OR REPLACE FUNCTION public.start_session(
  p_session_id UUID,
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
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để bắt đầu buổi chơi' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_management_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Không có quyền bắt đầu buổi chơi' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_session_id)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
  FROM public.check_idempotency('start_session', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved_result;
  END IF;

  IF v_session.lifecycle <> 'published' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ bắt đầu được buổi đang công bố' USING ERRCODE = '22023';
  END IF;

  UPDATE public.sessions SET
    lifecycle = 'in_progress',
    version = version + 1,
    updated_at = now()
  WHERE id = p_session_id;

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'session', p_session_id,
    'START_SESSION',
    jsonb_build_object('lifecycle', v_session.lifecycle),
    jsonb_build_object('lifecycle', 'in_progress'),
    'Bắt đầu buổi chơi', p_request_id);

  v_res := public.get_session_public_detail(p_session_id);
  PERFORM public.record_idempotency('start_session', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.start_session(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.start_session(UUID, UUID) TO authenticated;
