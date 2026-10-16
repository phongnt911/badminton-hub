-- BH-06A — duong doc tai chinh/QR va so quy (projection whitelist, gate current).
-- Khong lo contact/bank qua projection public. Khong thay the get_session_payment_instructions
-- cu cua BH-02 (chi tra receiver_snapshot, khong co so tien/ma tham chieu nen khong the
-- dung de thu tien sai khi stale); RPC moi get_payment_instructions moi gate current va tra
-- outstanding/source_version/ma tham chieu.

-- ============================================================================
-- 1. get_payment_instructions — nguoi choi confirmed hoac finance; chi khi current
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

  v_authorized := public.has_session_finance_access(p_session_id, v_actor)
    OR (v_player.user_id = v_actor AND v_player.registration_status = 'confirmed');
  IF NOT v_authorized THEN
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
-- 2. get_session_finance — projection tài chính buổi cho finance
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

  SELECT s.id, s.title, s.club_id, s.lifecycle, s.fee_mode, s.billing_input_version
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

-- ============================================================================
-- 3. get_club_ledger — owner/treasurer, phân trang, số dư từ SUM DB
-- ============================================================================
CREATE OR REPLACE FUNCTION public.get_club_ledger(
  p_club_id UUID,
  p_limit INT DEFAULT 20,
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
  v_limit INT;
  v_offset INT;
  v_balance BIGINT;
  v_entries JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem sổ quỹ' USING ERRCODE = '42501';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.clubs WHERE id = p_club_id) THEN
    RAISE EXCEPTION 'NOT_FOUND: CLB không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT (public.is_club_owner(p_club_id, v_actor) OR public.has_club_role(p_club_id, v_actor, ARRAY['treasurer'])) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ owner/treasurer CLB xem sổ quỹ' USING ERRCODE = '42501';
  END IF;

  v_limit := LEAST(GREATEST(COALESCE(p_limit, 20), 1), 100);
  v_offset := GREATEST(COALESCE(p_offset, 0), 0);

  SELECT COALESCE(SUM(CASE WHEN direction = 'income' THEN amount_vnd ELSE -amount_vnd END), 0) INTO v_balance
  FROM public.club_transactions WHERE club_id = p_club_id;

  SELECT COALESCE(jsonb_agg(jsonb_build_object(
    'transaction_id', t.id, 'direction', t.direction, 'amount_vnd', t.amount_vnd, 'title', t.title,
    'source_type', t.source_type, 'source_payment_id', t.source_payment_id,
    'source_expense_id', t.source_expense_id, 'reversal_of', t.reversal_of,
    'created_at', t.created_at) ORDER BY t.created_at DESC, t.id DESC), '[]'::jsonb)
  INTO v_entries
  FROM (
    SELECT * FROM public.club_transactions WHERE club_id = p_club_id
    ORDER BY created_at DESC, id DESC LIMIT v_limit OFFSET v_offset
  ) t;

  RETURN jsonb_build_object(
    'club_id', p_club_id,
    'balance_vnd', v_balance,
    'limit', v_limit,
    'offset', v_offset,
    'entries', v_entries
  );
END;
$$;
REVOKE ALL ON FUNCTION public.get_club_ledger(UUID, INT, INT) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_club_ledger(UUID, INT, INT) TO authenticated;
