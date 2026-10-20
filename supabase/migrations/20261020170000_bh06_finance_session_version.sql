-- ============================================================================
-- BH-06 integration review I2 - session_version trong DTO tai chinh
-- ============================================================================
--
-- SessionFinanceScreen truoc day luon gui expectedVersion lay tu Session nhan
-- luc mo route. Refresh chi tai lai get_session_finance, khong cap nhat version
-- do, nen sau VERSION_CONFLICT moi lan chot lai van gui version cu va nguoi
-- dung phai dong/mo lai man hinh.
--
-- Migration nay bo sung `session_version` (sessions.version hien hanh) vao cung
-- DTO `get_session_finance`. UI dung gia tri nay cho optimistic concurrency;
-- refresh DTO sau conflict se lay duoc version moi. Khong bo expectedVersion,
-- khong tu tang version o client, khong doi quyen/doc nghiep vu.
--
-- Chi thay doi projection doc; giu nguyen chu ky ham, AC L va phan trang.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_session_finance(
  p_session_id UUID,
  p_limit INT DEFAULT 50,
  p_offset INT DEFAULT 0
)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_session RECORD;
  v_rev UUID;
  v_limit INT;
  v_offset INT;
  v_outstanding_total BIGINT;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem tài chính buổi' USING ERRCODE = '42501';
  END IF;

  SELECT s.id, s.title, s.club_id, s.lifecycle, s.fee_mode, s.billing_input_version, s.version
  INTO v_session FROM public.sessions s WHERE s.id = p_session_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_finance_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để xem tài chính buổi' USING ERRCODE = '42501';
  END IF;

  v_limit := LEAST(GREATEST(COALESCE(p_limit, 50), 1), 100);
  v_offset := GREATEST(COALESCE(p_offset, 0), 0);
  v_rev := public.active_charge_revision_id(p_session_id);

  SELECT COALESCE(SUM(GREATEST(0, sc.amount_due_vnd - COALESCE(pay.total, 0))), 0) INTO v_outstanding_total
  FROM public.session_charges sc
  LEFT JOIN (
    SELECT session_player_id, SUM(amount_vnd) AS total
    FROM public.payments WHERE status = 'confirmed' GROUP BY session_player_id
  ) pay ON pay.session_player_id = sc.session_player_id
  WHERE sc.revision_id = v_rev;

  RETURN jsonb_build_object(
    'session_id', p_session_id,
    'title', v_session.title,
    'club_id', v_session.club_id,
    'lifecycle', v_session.lifecycle,
    'fee_mode', v_session.fee_mode,
    'billing_input_version', v_session.billing_input_version,
    'session_version', v_session.version,
    'billing_state', public.session_billing_state(p_session_id),
    'active_revision', CASE WHEN v_rev IS NULL THEN NULL ELSE (
      SELECT jsonb_build_object(
        'revision_id', cr.id, 'revision_no', cr.revision_no, 'source_version', cr.source_version,
        'allocation_total_vnd', cr.allocation_total_vnd, 'fee_mode', cr.fee_mode,
        'reason', cr.reason, 'finalized_at', cr.finalized_at)
      FROM public.charge_revisions cr WHERE cr.id = v_rev
    ) END,
    'expenses_total_vnd', (
      SELECT COALESCE(SUM(amount_vnd), 0) FROM public.session_expenses
      WHERE session_id = p_session_id AND status = 'posted'
    ),
    'outstanding_total_vnd', COALESCE(v_outstanding_total, 0),
    'expenses', (
      SELECT COALESCE(jsonb_agg(jsonb_build_object(
        'expense_id', e.id, 'category', e.category, 'title', e.title, 'amount_vnd', e.amount_vnd,
        'status', e.status, 'reversal_reason', e.reversal_reason, 'posted_at', e.posted_at) ORDER BY e.created_at DESC, e.id DESC), '[]'::jsonb)
      FROM (
        SELECT * FROM public.session_expenses WHERE session_id = p_session_id
        ORDER BY created_at DESC, id DESC LIMIT v_limit OFFSET v_offset
      ) e
    ),
    'charges', (
      SELECT COALESCE(jsonb_agg(jsonb_build_object(
        'player_id', sc.session_player_id, 'display_name', sp.display_name,
        'amount_due_vnd', sc.amount_due_vnd) ORDER BY sp.id), '[]'::jsonb)
      FROM public.session_charges sc
      JOIN public.session_players sp ON sp.id = sc.session_player_id
      WHERE sc.revision_id = v_rev
    ),
    'payments', (
      SELECT COALESCE(jsonb_agg(jsonb_build_object(
        'payment_id', p.id, 'player_id', p.session_player_id, 'amount_vnd', p.amount_vnd,
        'method', p.method, 'status', p.status, 'reference', p.reference,
        'confirmed_at', p.confirmed_at, 'created_at', p.created_at) ORDER BY p.created_at DESC, p.id DESC), '[]'::jsonb)
      FROM (
        SELECT p.* FROM public.payments p
        JOIN public.session_players sp ON sp.id = p.session_player_id
        WHERE sp.session_id = p_session_id
        ORDER BY p.created_at DESC, p.id DESC LIMIT v_limit OFFSET v_offset
      ) p
    ),
    'limit', v_limit,
    'offset', v_offset
  );
END;
$$;
REVOKE ALL ON FUNCTION public.get_session_finance(UUID, INT, INT) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_session_finance(UUID, INT, INT) TO authenticated;
