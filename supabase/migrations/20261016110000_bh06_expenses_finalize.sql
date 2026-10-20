-- BH-06A — tai chinh buoi: chi phi, chot phi (charge revision) va cong hoan thanh.
-- Forward-only, khong sua migration da chia se (BH-02..BH-05). Chi CREATE OR REPLACE
-- cho helper/RPC cua ticket nay va GRANT/REVOKE lai.
--
-- Nguyen tac theo docs/08 §1, §4, §7 va ADR-08:
--   * Moi mutation: SECURITY DEFINER, search_path co dinh, actor tu auth.uid(),
--     bat buoc p_request_id, idempotency theo actor/operation/request + hash canonical,
--     audit cung transaction, REVOKE PUBLIC/anon + GRANT authenticated.
--   * "billing_state" la suy dien, khong phai cot: active charge_revision.source_version
--     so voi sessions.billing_input_version. Khong revision -> not_finalized; lech -> stale.
--   * Moi nguon thay input tinh phi (chi phi, roster confirmed, diem danh, mien phi) da
--     tang billing_input_version o BH-05 (bump_billing_input_version) hoac tai day.
--     update_session chi chay o draft/published (truoc khi co revision) nen khong lam
--     revision da chot tro nen stale.
--   * Helper noi bo bi REVOKE khoi moi role client.

-- ============================================================================
-- 1. Helper trạng thái chốt phí
-- ============================================================================

-- Trả id revision đang active của buổi (tối đa 1 theo unique index), hoặc NULL.
CREATE OR REPLACE FUNCTION public.active_charge_revision_id(p_session_id UUID)
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT id FROM public.charge_revisions
  WHERE session_id = p_session_id AND status = 'active'
  LIMIT 1;
$$;
REVOKE EXECUTE ON FUNCTION public.active_charge_revision_id(UUID) FROM PUBLIC, anon, authenticated;

-- 'not_finalized' khi chưa có revision active; 'stale' khi source_version lệch
-- billing_input_version; ngược lại 'current'.
CREATE OR REPLACE FUNCTION public.session_billing_state(p_session_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_biv BIGINT;
  v_src BIGINT;
BEGIN
  SELECT billing_input_version INTO v_biv FROM public.sessions WHERE id = p_session_id;
  SELECT source_version INTO v_src FROM public.charge_revisions
    WHERE session_id = p_session_id AND status = 'active';
  IF v_src IS NULL THEN
    RETURN 'not_finalized';
  ELSIF v_src <> v_biv THEN
    RETURN 'stale';
  END IF;
  RETURN 'current';
END;
$$;
REVOKE EXECUTE ON FUNCTION public.session_billing_state(UUID) FROM PUBLIC, anon, authenticated;

-- Gate dùng chung cho QR/submit/confirm mới/cash/complete: trả revision active khi
-- billing current, nếu không thì ném BILLING_NOT_FINALIZED / BILLING_STALE.
CREATE OR REPLACE FUNCTION public.assert_billing_current(p_session_id UUID)
RETURNS UUID
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_rev UUID;
BEGIN
  v_rev := public.active_charge_revision_id(p_session_id);
  IF v_rev IS NULL THEN
    RAISE EXCEPTION 'BILLING_NOT_FINALIZED: Buổi chơi chưa chốt phí' USING ERRCODE = '22023';
  END IF;
  IF public.session_billing_state(p_session_id) <> 'current' THEN
    RAISE EXCEPTION 'BILLING_STALE: Bản chốt phí đã lỗi thời, cần chốt lại trước' USING ERRCODE = '22023';
  END IF;
  RETURN v_rev;
END;
$$;
REVOKE EXECUTE ON FUNCTION public.assert_billing_current(UUID) FROM PUBLIC, anon, authenticated;

-- Ảnh chụp công nợ một người chơi theo revision active (không gate current).
CREATE OR REPLACE FUNCTION public.player_charge_snapshot(p_player_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_session UUID;
  v_rev UUID;
  v_due BIGINT;
  v_paid BIGINT;
  v_src BIGINT;
BEGIN
  SELECT session_id INTO v_session FROM public.session_players WHERE id = p_player_id;
  IF v_session IS NULL THEN
    RAISE EXCEPTION 'NOT_FOUND: Đăng ký không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  v_rev := public.active_charge_revision_id(v_session);
  SELECT COALESCE(SUM(amount_due_vnd), 0) INTO v_due
  FROM public.session_charges WHERE revision_id = v_rev AND session_player_id = p_player_id;
  SELECT COALESCE(SUM(amount_vnd), 0) INTO v_paid
  FROM public.payments WHERE session_player_id = p_player_id AND status = 'confirmed';
  SELECT source_version INTO v_src FROM public.charge_revisions WHERE id = v_rev;
  RETURN jsonb_build_object(
    'session_id', v_session,
    'player_id', p_player_id,
    'billing_state', public.session_billing_state(v_session),
    'active_revision_id', v_rev,
    'source_version', v_src,
    'amount_due_vnd', v_due,
    'total_paid_vnd', v_paid,
    'outstanding_vnd', GREATEST(0, v_due - v_paid)
  );
END;
$$;
REVOKE EXECUTE ON FUNCTION public.player_charge_snapshot(UUID) FROM PUBLIC, anon, authenticated;

-- ============================================================================
-- 2. post_session_expense — ghi chi phí buổi (+ ledger CLB cùng transaction)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.post_session_expense(
  p_session_id UUID,
  p_category TEXT,
  p_title TEXT,
  p_amount_vnd BIGINT,
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
  v_saved JSONB;
  v_expense_id UUID;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để ghi chi phí' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_finance_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để ghi chi phí' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_session_id, p_category, p_title, p_amount_vnd)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved
  FROM public.check_idempotency('post_session_expense', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved;
  END IF;

  IF v_session.lifecycle IN ('completed', 'cancelled') THEN
    RAISE EXCEPTION 'INVALID_STATE: Buổi đã kết thúc/huỷ, chỉ điều chỉnh qua hành động tài chính' USING ERRCODE = '22023';
  END IF;
  IF p_category IS NULL OR p_category NOT IN ('court', 'shuttle', 'other') THEN
    RAISE EXCEPTION 'INVALID_INPUT: Loại chi phí không hợp lệ' USING ERRCODE = '22023';
  END IF;
  IF p_title IS NULL OR btrim(p_title) = '' THEN
    RAISE EXCEPTION 'INVALID_INPUT: Thiếu tên chi phí' USING ERRCODE = '22023';
  END IF;
  IF p_amount_vnd IS NULL OR p_amount_vnd <= 0 OR p_amount_vnd > 1000000000 THEN
    RAISE EXCEPTION 'INVALID_INPUT: Số tiền phải là số nguyên dương VNĐ (<= 1 tỷ)' USING ERRCODE = '22023';
  END IF;

  INSERT INTO public.session_expenses (session_id, category, title, amount_vnd, status, created_by)
  VALUES (p_session_id, p_category, btrim(p_title), p_amount_vnd, 'posted', v_actor)
  RETURNING id INTO v_expense_id;

  IF v_session.club_id IS NOT NULL THEN
    INSERT INTO public.club_transactions (
      club_id, direction, amount_vnd, title, source_type, source_expense_id, created_by
    ) VALUES (
      v_session.club_id, 'expense', p_amount_vnd, btrim(p_title), 'session_expense', v_expense_id, v_actor
    );
  END IF;

  PERFORM public.bump_billing_input_version(p_session_id);

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'session_expense', v_expense_id, 'EXPENSE_POSTED',
    NULL, jsonb_build_object('category', p_category, 'amount_vnd', p_amount_vnd, 'title', btrim(p_title)),
    'Ghi chi phí buổi', p_request_id);

  v_res := jsonb_build_object(
    'expense_id', v_expense_id,
    'session_id', p_session_id,
    'category', p_category,
    'amount_vnd', p_amount_vnd,
    'status', 'posted',
    'club_ledger_entry', v_session.club_id IS NOT NULL,
    'billing_state', public.session_billing_state(p_session_id)
  );
  PERFORM public.record_idempotency('post_session_expense', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.post_session_expense(UUID, TEXT, TEXT, BIGINT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.post_session_expense(UUID, TEXT, TEXT, BIGINT, UUID) TO authenticated;

-- ============================================================================
-- 3. reverse_session_expense — đảo chi phí, giữ nguồn và entry đảo duy nhất
-- ============================================================================
CREATE OR REPLACE FUNCTION public.reverse_session_expense(
  p_session_id UUID,
  p_expense_id UUID,
  p_reason TEXT,
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
  v_expense RECORD;
  v_ledger RECORD;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved JSONB;
  v_reversal_id UUID;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để đảo chi phí' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;
  IF p_reason IS NULL OR btrim(p_reason) = '' THEN
    RAISE EXCEPTION 'INVALID_INPUT: Cần lý do khi đảo chi phí' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_finance_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để đảo chi phí' USING ERRCODE = '42501';
  END IF;

  SELECT * INTO v_expense FROM public.session_expenses
  WHERE id = p_expense_id AND session_id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Chi phí không tồn tại trong buổi' USING ERRCODE = 'P0002';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_session_id, p_expense_id, btrim(p_reason))::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved
  FROM public.check_idempotency('reverse_session_expense', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved;
  END IF;

  IF v_expense.status <> 'posted' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chi phí đã được đảo trước đó' USING ERRCODE = '22023';
  END IF;

  UPDATE public.session_expenses
  SET status = 'reversed', reversal_reason = btrim(p_reason), updated_at = now()
  WHERE id = p_expense_id;

  IF v_session.club_id IS NOT NULL THEN
    SELECT * INTO v_ledger FROM public.club_transactions
    WHERE source_expense_id = p_expense_id AND source_type = 'session_expense';
    IF NOT FOUND THEN
      RAISE EXCEPTION 'INVALID_STATE: Thiếu bút toán quỹ nguồn để đảo' USING ERRCODE = '22023';
    END IF;
    INSERT INTO public.club_transactions (
      club_id, direction, amount_vnd, title, source_type, reversal_of, created_by
    ) VALUES (
      v_ledger.club_id, CASE WHEN v_ledger.direction = 'expense' THEN 'income' ELSE 'expense' END,
      v_ledger.amount_vnd, v_ledger.title, 'reversal', v_ledger.id, v_actor
    ) RETURNING id INTO v_reversal_id;
  END IF;

  PERFORM public.bump_billing_input_version(p_session_id);

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'session_expense', p_expense_id, 'EXPENSE_REVERSED',
    jsonb_build_object('status', 'posted'),
    jsonb_build_object('status', 'reversed', 'reversal_ledger_id', v_reversal_id),
    btrim(p_reason), p_request_id);

  v_res := jsonb_build_object(
    'expense_id', p_expense_id,
    'session_id', p_session_id,
    'status', 'reversed',
    'reversal_ledger_id', v_reversal_id,
    'billing_state', public.session_billing_state(p_session_id)
  );
  PERFORM public.record_idempotency('reverse_session_expense', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.reverse_session_expense(UUID, UUID, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.reverse_session_expense(UUID, UUID, TEXT, UUID) TO authenticated;

-- ============================================================================
-- 4. finalize_session_charges — chốt phí server-side, revision nguyên tử
-- ============================================================================
CREATE OR REPLACE FUNCTION public.finalize_session_charges(
  p_session_id UUID,
  p_expected_version BIGINT,
  p_expected_billing_input_version BIGINT,
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
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved JSONB;
  v_revision_no INT;
  v_expenses_total BIGINT;
  v_present_count INT;
  v_billable_count INT;
  v_allocation BIGINT;
  v_rev_id UUID;
  v_reason TEXT;
  v_row RECORD;
  v_due BIGINT;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để chốt phí' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_finance_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để chốt phí' USING ERRCODE = '42501';
  END IF;

  v_reason := NULLIF(btrim(COALESCE(p_reason, '')), '');
  v_payload_hash := md5(jsonb_build_array(p_session_id, p_expected_version, p_expected_billing_input_version, v_reason)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved
  FROM public.check_idempotency('finalize_session_charges', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved;
  END IF;

  IF p_expected_version IS NULL OR v_session.version <> p_expected_version THEN
    RAISE EXCEPTION 'VERSION_CONFLICT: Buổi chơi đã thay đổi, cần tải lại' USING ERRCODE = '22023';
  END IF;
  IF p_expected_billing_input_version IS NULL
     OR v_session.billing_input_version <> p_expected_billing_input_version THEN
    RAISE EXCEPTION 'BILLING_STALE: Dữ liệu tính phí đã thay đổi, cần tải lại' USING ERRCODE = '22023';
  END IF;
  IF v_session.lifecycle NOT IN ('in_progress', 'completed') THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ chốt phí khi buổi đang diễn ra hoặc đã kết thúc' USING ERRCODE = '22023';
  END IF;

  SELECT COALESCE(MAX(revision_no), 0) + 1 INTO v_revision_no
  FROM public.charge_revisions WHERE session_id = p_session_id;
  IF v_revision_no > 1 AND v_reason IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: Cần lý do khi chốt lại phí' USING ERRCODE = '22023';
  END IF;

  SELECT COALESCE(SUM(amount_vnd), 0) INTO v_expenses_total
  FROM public.session_expenses WHERE session_id = p_session_id AND status = 'posted';
  SELECT count(*) INTO v_present_count
  FROM public.session_players
  WHERE session_id = p_session_id AND registration_status = 'confirmed' AND attendance_status = 'present';
  SELECT count(*) INTO v_billable_count
  FROM public.session_players
  WHERE session_id = p_session_id AND registration_status = 'confirmed'
    AND attendance_status = 'present' AND fee_exempt = false;

  IF v_session.fee_mode = 'split_actual' AND v_expenses_total > 0 AND v_billable_count = 0 THEN
    RAISE EXCEPTION 'NO_BILLABLE_PLAYERS: Có chi phí nhưng không có người chịu phí' USING ERRCODE = '22023';
  END IF;
  IF v_expenses_total > 1000000000 THEN
    RAISE EXCEPTION 'INVALID_INPUT: Tổng chi phí vượt giới hạn 1 tỷ' USING ERRCODE = '22023';
  END IF;

  -- Bảng tạm: số phải thu mới của từng người present (chia dư theo thứ tự id ổn định).
  DROP TABLE IF EXISTS pg_temp._bh06_charges;
  CREATE TEMP TABLE _bh06_charges ON COMMIT DROP AS
  WITH present AS (
    SELECT sp.id AS player_id, sp.fee_exempt, COALESCE(sp.agreed_fee_vnd, 0) AS fee
    FROM public.session_players sp
    WHERE sp.session_id = p_session_id
      AND sp.registration_status = 'confirmed'
      AND sp.attendance_status = 'present'
  ),
  billable AS (
    SELECT player_id, row_number() OVER (ORDER BY player_id) AS brn
    FROM present WHERE fee_exempt = false
  )
  SELECT
    p.player_id,
    CASE
      WHEN v_session.fee_mode = 'fixed' THEN (CASE WHEN p.fee_exempt THEN 0 ELSE p.fee END)
      WHEN p.fee_exempt THEN 0
      WHEN v_billable_count = 0 THEN 0
      ELSE (v_expenses_total / v_billable_count)
           + (CASE WHEN b.brn <= (v_expenses_total % v_billable_count) THEN 1 ELSE 0 END)
    END AS amount_due_vnd
  FROM present p
  LEFT JOIN billable b ON b.player_id = p.player_id;

  SELECT COALESCE(SUM(amount_due_vnd), 0) INTO v_allocation FROM pg_temp._bh06_charges;
  IF v_allocation > 1000000000 THEN
    RAISE EXCEPTION 'INVALID_INPUT: Tổng phải thu vượt giới hạn 1 tỷ' USING ERRCODE = '22023';
  END IF;

  -- Đối chiếu tiền đã thu: mỗi người có confirmed payment phải có due mới >= đã thu,
  -- kể cả người bị loại khỏi tập billable (no_show/miễn phí/huỷ).
  FOR v_row IN
    SELECT sp.id AS player_id, COALESCE(paid.total, 0) AS paid
    FROM public.session_players sp
    LEFT JOIN (
      SELECT session_player_id, SUM(amount_vnd) AS total
      FROM public.payments WHERE status = 'confirmed' GROUP BY session_player_id
    ) paid ON paid.session_player_id = sp.id
    WHERE sp.session_id = p_session_id AND COALESCE(paid.total, 0) > 0
    ORDER BY sp.id
  LOOP
    SELECT COALESCE(amount_due_vnd, 0) INTO v_due FROM pg_temp._bh06_charges WHERE player_id = v_row.player_id;
    IF COALESCE(v_due, 0) < v_row.paid THEN
      RAISE EXCEPTION 'INVALID_STATE: Khoản phải thu mới (%) nhỏ hơn tiền đã xác nhận (%) — cần đảo/hoàn trước khi chốt lại',
        COALESCE(v_due, 0), v_row.paid USING ERRCODE = '22023';
    END IF;
  END LOOP;

  UPDATE public.charge_revisions
  SET status = 'superseded'
  WHERE session_id = p_session_id AND status = 'active';

  INSERT INTO public.charge_revisions (
    session_id, revision_no, source_version, status, allocation_total_vnd, fee_mode, reason, finalized_by
  ) VALUES (
    p_session_id, v_revision_no, v_session.billing_input_version, 'active', v_allocation,
    v_session.fee_mode, v_reason, v_actor
  ) RETURNING id INTO v_rev_id;

  INSERT INTO public.session_charges (revision_id, session_player_id, amount_due_vnd)
  SELECT v_rev_id, player_id, amount_due_vnd FROM pg_temp._bh06_charges;

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'charge_revision', v_rev_id, 'BILLING_FINALIZED',
    NULL, jsonb_build_object('revision_no', v_revision_no, 'allocation_total_vnd', v_allocation,
                             'source_version', v_session.billing_input_version, 'fee_mode', v_session.fee_mode),
    v_reason, p_request_id);

  v_res := jsonb_build_object(
    'revision_id', v_rev_id,
    'session_id', p_session_id,
    'revision_no', v_revision_no,
    'source_version', v_session.billing_input_version,
    'allocation_total_vnd', v_allocation,
    'fee_mode', v_session.fee_mode,
    'present_count', v_present_count,
    'charge_count', (SELECT count(*) FROM pg_temp._bh06_charges),
    'billing_state', 'current'
  );
  PERFORM public.record_idempotency('finalize_session_charges', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.finalize_session_charges(UUID, BIGINT, BIGINT, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.finalize_session_charges(UUID, BIGINT, BIGINT, TEXT, UUID) TO authenticated;

-- ============================================================================
-- 5. complete_session — bảo vệ hợp đồng complete ngay trong A (gate billing current)
--    Chỉ gate + đổi lifecycle; UI/history/pilot thuộc BH-07.
-- ============================================================================
CREATE OR REPLACE FUNCTION public.complete_session(
  p_session_id UUID,
  p_expected_version BIGINT,
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
  v_saved JSONB;
  v_rev UUID;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để kết thúc buổi' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_session FROM public.sessions WHERE id = p_session_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT public.has_session_management_access(p_session_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ host/quản lý buổi mới kết thúc buổi' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_session_id, p_expected_version)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved
  FROM public.check_idempotency('complete_session', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved;
  END IF;

  IF v_session.lifecycle <> 'in_progress' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ kết thúc buổi đang diễn ra' USING ERRCODE = '22023';
  END IF;
  IF p_expected_version IS NULL OR v_session.version <> p_expected_version THEN
    RAISE EXCEPTION 'VERSION_CONFLICT: Buổi chơi đã thay đổi, cần tải lại' USING ERRCODE = '22023';
  END IF;

  -- Không cho complete bỏ qua chốt phí: cần revision active và current
  -- (buổi miễn phí vẫn phải có revision current với charges 0).
  v_rev := public.assert_billing_current(p_session_id);

  UPDATE public.sessions
  SET lifecycle = 'completed', version = version + 1, updated_at = now()
  WHERE id = p_session_id;

  PERFORM public.log_audit_event(
    v_session.club_id, p_session_id, 'session', p_session_id, 'SESSION_COMPLETED',
    jsonb_build_object('lifecycle', 'in_progress'),
    jsonb_build_object('lifecycle', 'completed', 'revision_id', v_rev),
    'Kết thúc buổi', p_request_id);

  v_res := public.get_session_public_detail(p_session_id);
  PERFORM public.record_idempotency('complete_session', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.complete_session(UUID, BIGINT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.complete_session(UUID, BIGINT, UUID) TO authenticated;
