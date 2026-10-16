-- BH-06A — sửa theo review độc lập vòng 1 (R1, R2). Forward-only.
-- KHÔNG sửa ba migration BH-06A đã chia sẻ (20261016110000/120000/130000); file này chỉ
-- CREATE OR REPLACE hai hàm đọc để đóng hai phát hiện P1 và cấp lại GRANT/REVOKE.
--
-- R1 — get_payment_instructions kiểm quyền null-safe:
--   Khách offline (session_players.user_id = NULL) confirmed + actor không finance cho trước đây
--   v_authorized = false OR (NULL AND true) = NULL, nên `IF NOT v_authorized` không chặn; outsider
--   biết UUID đọc được tên khách, receiver_snapshot, amount_due/outstanding và reference. Nay dùng
--   `v_player.user_id IS NOT DISTINCT FROM v_actor` (actor đã non-NULL) và `IF v_authorized IS NOT TRUE`.
--   Quyền finance đọc khách đúng scope vẫn giữ.
--
-- R2 — get_session_payment_instructions (BH-02, chỉ trả receiver_snapshot) gate current:
--   Trước đây RPC cũ trả bank snapshot mà không kiểm revision, nên caller lấy được bank khi chưa
--   chốt/stale rồi ghép số tiền đã cache -> lọt gate §7 ("get_payment_instructions ... phải kiểm
--   tra current ở server"). Nay gate bằng assert_billing_current: chưa chốt -> BILLING_NOT_FINALIZED,
--   lệch phiên bản -> BILLING_STALE. Giữ quyền tương thích (host/management/finance/confirmed player)
--   và chỉ trả session_id + receiver_snapshot như cũ; không dùng làm API history.

-- ============================================================================
-- R1 — get_payment_instructions: kiểm quyền null-safe, gate current
-- ============================================================================
CREATE OR REPLACE FUNCTION public.get_payment_instructions(
  p_session_id UUID,
  p_player_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_player RECORD;
  v_session RECORD;
  v_rev UUID;
  v_due BIGINT;
  v_paid BIGINT;
  v_outstanding BIGINT;
  v_authorized BOOLEAN;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem hướng dẫn thanh toán' USING ERRCODE = '42501';
  END IF;

  IF p_player_id IS NULL THEN
    SELECT * INTO v_player FROM public.session_players
    WHERE session_id = p_session_id AND user_id = v_actor AND registration_status = 'confirmed';
  ELSE
    SELECT * INTO v_player FROM public.session_players
    WHERE id = p_player_id AND session_id = p_session_id;
  END IF;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Không có đăng ký confirmed phù hợp trong buổi' USING ERRCODE = 'P0002';
  END IF;

  SELECT s.id, s.title, s.club_id, s.receiver_snapshot, s.billing_input_version
  INTO v_session FROM public.sessions s WHERE s.id = p_session_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;

  -- R1: null-safe. v_actor đã non-NULL; khách offline user_id NULL không thể khớp actor.
  v_authorized := public.has_session_finance_access(p_session_id, v_actor)
    OR (v_player.user_id IS NOT DISTINCT FROM v_actor AND v_player.registration_status = 'confirmed');
  IF v_authorized IS NOT TRUE THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ người chơi đã confirmed hoặc finance xem được hướng dẫn thanh toán' USING ERRCODE = '42501';
  END IF;

  v_rev := public.assert_billing_current(p_session_id);

  SELECT COALESCE(SUM(amount_due_vnd), 0) INTO v_due
  FROM public.session_charges WHERE revision_id = v_rev AND session_player_id = v_player.id;
  SELECT COALESCE(SUM(amount_vnd), 0) INTO v_paid
  FROM public.payments WHERE session_player_id = v_player.id AND status = 'confirmed';
  v_outstanding := GREATEST(0, v_due - v_paid);

  RETURN jsonb_build_object(
    'session_id', p_session_id,
    'player_id', v_player.id,
    'display_name', v_player.display_name,
    'billing_state', 'current',
    'active_revision_id', v_rev,
    'source_version', (SELECT source_version FROM public.charge_revisions WHERE id = v_rev),
    'amount_due_vnd', v_due,
    'total_paid_vnd', v_paid,
    'outstanding_vnd', v_outstanding,
    'reference', 'BH-' || upper(substr(md5(v_player.id::text), 1, 10)),
    'receiver_snapshot', v_session.receiver_snapshot,
    'has_receiver', v_session.receiver_snapshot IS NOT NULL,
    'can_pay', v_outstanding > 0
  );
END;
$$;
REVOKE ALL ON FUNCTION public.get_payment_instructions(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_payment_instructions(UUID, UUID) TO authenticated;

-- ============================================================================
-- R2 — get_session_payment_instructions (BH-02): gate current, giữ quyền tương thích
-- ============================================================================
CREATE OR REPLACE FUNCTION public.get_session_payment_instructions(p_session_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_session RECORD;
  v_authorized BOOLEAN := FALSE;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem thông tin thanh toán' USING ERRCODE = '42501';
  END IF;

  SELECT s.id, s.host_user_id, s.receiver_snapshot
  INTO v_session
  FROM public.sessions s
  WHERE s.id = p_session_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;

  IF v_session.host_user_id = v_actor OR
     public.has_session_management_access(p_session_id, v_actor) OR
     public.has_session_finance_access(p_session_id, v_actor) THEN
    v_authorized := TRUE;
  ELSE
    SELECT EXISTS (
      SELECT 1 FROM public.session_players
      WHERE session_id = p_session_id
        AND user_id = v_actor
        AND registration_status = 'confirmed'
    ) INTO v_authorized;
  END IF;

  IF NOT v_authorized THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ người chơi đã được xác nhận (confirmed) mới có thể xem thông tin thanh toán' USING ERRCODE = '42501';
  END IF;

  -- R2: chỉ phát bank snapshot khi bản chốt phí đang current.
  PERFORM public.assert_billing_current(p_session_id);

  RETURN jsonb_build_object(
    'session_id', v_session.id,
    'receiver_snapshot', v_session.receiver_snapshot
  );
END;
$$;
REVOKE ALL ON FUNCTION public.get_session_payment_instructions(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_session_payment_instructions(UUID) TO authenticated;
