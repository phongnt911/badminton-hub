-- BH-06A — thanh toan (submit/confirm/reject/reverse/cash) va so quy CLB.
-- Forward-only. Dung helper trang thai chot phi tu 20261016110000.
-- submitted KHONG phai da tra; chi confirmed moi tinh vao outstanding/ledger.
-- Dao/reject/history van duoc phep khi stale theo quyen (khong phai thu moi).

-- ============================================================================
-- 1. submit_payment — nguoi choi tu gui y dinh chuyen khoan (chua tinh la da tra)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.submit_payment(
  p_player_id UUID,
  p_amount_vnd BIGINT,
  p_method TEXT DEFAULT 'bank_transfer',
  p_reference TEXT DEFAULT NULL,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_player RECORD;
  v_session_id UUID;
  v_session RECORD;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved JSONB;
  v_rev UUID;
  v_due BIGINT;
  v_paid BIGINT;
  v_outstanding BIGINT;
  v_ref TEXT;
  v_payment_id UUID;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để gửi thanh toán' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  SELECT session_id INTO v_session_id FROM public.session_players WHERE id = p_player_id;
  IF v_session_id IS NULL THEN
    RAISE EXCEPTION 'NOT_FOUND: Đăng ký không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  SELECT * INTO v_session FROM public.sessions WHERE id = v_session_id FOR UPDATE;
  SELECT * INTO v_player FROM public.session_players WHERE id = p_player_id FOR UPDATE;

  IF v_player.user_id IS DISTINCT FROM v_actor THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ người chơi tự gửi thanh toán cho mình' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_player_id, p_amount_vnd, p_method, NULLIF(btrim(COALESCE(p_reference, '')), ''))::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved
  FROM public.check_idempotency('submit_payment', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved;
  END IF;

  IF v_player.registration_status <> 'confirmed' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ người đã confirmed mới gửi thanh toán' USING ERRCODE = '22023';
  END IF;
  IF p_amount_vnd IS NULL OR p_amount_vnd <= 0 OR p_amount_vnd > 1000000000 THEN
    RAISE EXCEPTION 'INVALID_INPUT: Số tiền phải là số nguyên dương VNĐ' USING ERRCODE = '22023';
  END IF;
  IF p_method IS NULL OR p_method <> 'bank_transfer' THEN
    RAISE EXCEPTION 'INVALID_INPUT: Chỉ nhận bank_transfer; tiền mặt dùng record_cash_payment' USING ERRCODE = '22023';
  END IF;

  v_rev := public.assert_billing_current(v_session.id);

  SELECT COALESCE(SUM(amount_due_vnd), 0) INTO v_due
  FROM public.session_charges WHERE revision_id = v_rev AND session_player_id = p_player_id;
  SELECT COALESCE(SUM(amount_vnd), 0) INTO v_paid
  FROM public.payments WHERE session_player_id = p_player_id AND status = 'confirmed';
  v_outstanding := GREATEST(0, v_due - v_paid);
  IF p_amount_vnd > v_outstanding THEN
    RAISE EXCEPTION 'PAYMENT_EXCEEDS_OUTSTANDING: Số tiền vượt quá khoản còn phải thu (%)', v_outstanding USING ERRCODE = '22023';
  END IF;

  v_ref := COALESCE(NULLIF(btrim(COALESCE(p_reference, '')), ''), 'PAY-' || replace(gen_random_uuid()::text, '-', ''));
  BEGIN
    INSERT INTO public.payments (
      session_player_id, amount_vnd, method, status, reference, submitted_by
    ) VALUES (
      p_player_id, p_amount_vnd, 'bank_transfer', 'submitted', v_ref, v_actor
    ) RETURNING id INTO v_payment_id;
  EXCEPTION WHEN unique_violation THEN
    RAISE EXCEPTION 'INVALID_INPUT: Mã tham chiếu đã tồn tại' USING ERRCODE = '22023';
  END;

  PERFORM public.log_audit_event(
    v_session.club_id, v_session.id, 'payment', v_payment_id, 'PAYMENT_SUBMITTED',
    NULL, jsonb_build_object('amount_vnd', p_amount_vnd, 'method', 'bank_transfer', 'reference', v_ref),
    'Người chơi gửi thanh toán', p_request_id);

  v_res := jsonb_build_object(
    'payment_id', v_payment_id,
    'player_id', p_player_id,
    'session_id', v_session.id,
    'amount_vnd', p_amount_vnd,
    'method', 'bank_transfer',
    'status', 'submitted',
    'reference', v_ref,
    'amount_due_vnd', v_due,
    'total_paid_vnd', v_paid,
    'outstanding_vnd', v_outstanding,
    'billing_state', 'current'
  );
  PERFORM public.record_idempotency('submit_payment', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.submit_payment(UUID, BIGINT, TEXT, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.submit_payment(UUID, BIGINT, TEXT, TEXT, UUID) TO authenticated;

-- ============================================================================
-- 2. confirm_payment — finance xác nhận thủ công, không thu dư active due
-- ============================================================================
CREATE OR REPLACE FUNCTION public.confirm_payment(
  p_payment_id UUID,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_payment RECORD;
  v_player RECORD;
  v_session_id UUID;
  v_session RECORD;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved JSONB;
  v_rev UUID;
  v_due BIGINT;
  v_paid BIGINT;
  v_ledger_id UUID;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xác nhận thanh toán' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_payment FROM public.payments WHERE id = p_payment_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Thanh toán không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  SELECT session_id INTO v_session_id FROM public.session_players WHERE id = v_payment.session_player_id;
  SELECT * INTO v_session FROM public.sessions WHERE id = v_session_id FOR UPDATE;
  SELECT * INTO v_player FROM public.session_players WHERE id = v_payment.session_player_id FOR UPDATE;
  SELECT * INTO v_payment FROM public.payments WHERE id = p_payment_id FOR UPDATE;

  IF NOT public.has_session_finance_access(v_session.id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để xác nhận thanh toán' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_payment_id)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved
  FROM public.check_idempotency('confirm_payment', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved;
  END IF;

  -- Đã confirmed: trả kết quả hiện tại, KHÔNG kiểm stale và KHÔNG ghi ledger lần hai.
  IF v_payment.status = 'confirmed' THEN
    SELECT COALESCE(SUM(amount_vnd), 0) INTO v_paid
    FROM public.payments WHERE session_player_id = v_payment.session_player_id AND status = 'confirmed';
    v_res := jsonb_build_object(
      'payment_id', p_payment_id, 'player_id', v_payment.session_player_id, 'session_id', v_session.id,
      'amount_vnd', v_payment.amount_vnd, 'method', v_payment.method, 'status', 'confirmed',
      'already_confirmed', true, 'total_paid_vnd', v_paid,
      'billing_state', public.session_billing_state(v_session.id)
    );
    PERFORM public.record_idempotency('confirm_payment', p_request_id, v_payload_hash, v_res);
    RETURN v_res;
  END IF;

  IF v_payment.status <> 'submitted' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ xác nhận được thanh toán đang submitted' USING ERRCODE = '22023';
  END IF;

  v_rev := public.assert_billing_current(v_session.id);

  SELECT COALESCE(SUM(amount_due_vnd), 0) INTO v_due
  FROM public.session_charges WHERE revision_id = v_rev AND session_player_id = v_payment.session_player_id;
  SELECT COALESCE(SUM(amount_vnd), 0) INTO v_paid
  FROM public.payments WHERE session_player_id = v_payment.session_player_id AND status = 'confirmed';
  IF v_paid + v_payment.amount_vnd > v_due THEN
    RAISE EXCEPTION 'PAYMENT_EXCEEDS_OUTSTANDING: Tổng đã xác nhận vượt khoản phải thu (%)', v_due USING ERRCODE = '22023';
  END IF;

  UPDATE public.payments
  SET status = 'confirmed', confirmed_by = v_actor, confirmed_at = now(), updated_at = now()
  WHERE id = p_payment_id;

  v_ledger_id := NULL;
  IF v_session.club_id IS NOT NULL THEN
    INSERT INTO public.club_transactions (
      club_id, direction, amount_vnd, title, source_type, source_payment_id, created_by
    ) VALUES (
      v_session.club_id, 'income', v_payment.amount_vnd,
      'Thu tiền buổi ' || COALESCE(v_session.title, ''), 'payment', p_payment_id, v_actor
    ) RETURNING id INTO v_ledger_id;
  END IF;

  PERFORM public.log_audit_event(
    v_session.club_id, v_session.id, 'payment', p_payment_id, 'PAYMENT_CONFIRMED',
    jsonb_build_object('status', 'submitted'), jsonb_build_object('status', 'confirmed', 'ledger_id', v_ledger_id),
    'Xác nhận thanh toán', p_request_id);

  v_res := jsonb_build_object(
    'payment_id', p_payment_id,
    'player_id', v_payment.session_player_id,
    'session_id', v_session.id,
    'amount_vnd', v_payment.amount_vnd,
    'method', v_payment.method,
    'status', 'confirmed',
    'ledger_id', v_ledger_id,
    'total_paid_vnd', v_paid + v_payment.amount_vnd,
    'outstanding_vnd', GREATEST(0, v_due - (v_paid + v_payment.amount_vnd)),
    'billing_state', 'current'
  );
  PERFORM public.record_idempotency('confirm_payment', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.confirm_payment(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.confirm_payment(UUID, UUID) TO authenticated;

-- ============================================================================
-- 3. reject_payment — finance từ chối submitted (cần lý do, không ledger)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.reject_payment(
  p_payment_id UUID,
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
  v_payment RECORD;
  v_session_id UUID;
  v_session RECORD;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved JSONB;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để từ chối thanh toán' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;
  IF p_reason IS NULL OR btrim(p_reason) = '' THEN
    RAISE EXCEPTION 'INVALID_INPUT: Cần lý do khi từ chối thanh toán' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_payment FROM public.payments WHERE id = p_payment_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Thanh toán không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  SELECT session_id INTO v_session_id FROM public.session_players WHERE id = v_payment.session_player_id;
  SELECT * INTO v_session FROM public.sessions WHERE id = v_session_id FOR UPDATE;
  SELECT * INTO v_payment FROM public.payments WHERE id = p_payment_id FOR UPDATE;

  IF NOT public.has_session_finance_access(v_session.id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để từ chối thanh toán' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_payment_id, btrim(p_reason))::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved
  FROM public.check_idempotency('reject_payment', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved;
  END IF;

  -- Đã rejected: trả kết quả hiện tại, không ghi thêm (cho phép cả khi stale).
  IF v_payment.status <> 'submitted' AND v_payment.status <> 'rejected' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ từ chối được thanh toán đang submitted' USING ERRCODE = '22023';
  END IF;

  IF v_payment.status = 'submitted' THEN
    UPDATE public.payments
    SET status = 'rejected', reason = btrim(p_reason), updated_at = now()
    WHERE id = p_payment_id;

    PERFORM public.log_audit_event(
      v_session.club_id, v_session.id, 'payment', p_payment_id, 'PAYMENT_REJECTED',
      jsonb_build_object('status', 'submitted'), jsonb_build_object('status', 'rejected'),
      btrim(p_reason), p_request_id);
  END IF;

  v_res := jsonb_build_object(
    'payment_id', p_payment_id, 'player_id', v_payment.session_player_id, 'session_id', v_session.id,
    'amount_vnd', v_payment.amount_vnd, 'method', v_payment.method, 'status', 'rejected',
    'billing_state', public.session_billing_state(v_session.id)
  );
  PERFORM public.record_idempotency('reject_payment', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.reject_payment(UUID, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.reject_payment(UUID, TEXT, UUID) TO authenticated;

-- ============================================================================
-- 4. reverse_payment — finance đảo confirmed (giữ payment, ledger đảo duy nhất)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.reverse_payment(
  p_payment_id UUID,
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
  v_payment RECORD;
  v_session_id UUID;
  v_session RECORD;
  v_ledger RECORD;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved JSONB;
  v_reversal_id UUID;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để đảo thanh toán' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;
  IF p_reason IS NULL OR btrim(p_reason) = '' THEN
    RAISE EXCEPTION 'INVALID_INPUT: Cần lý do khi đảo thanh toán' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_payment FROM public.payments WHERE id = p_payment_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Thanh toán không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  SELECT session_id INTO v_session_id FROM public.session_players WHERE id = v_payment.session_player_id;
  SELECT * INTO v_session FROM public.sessions WHERE id = v_session_id FOR UPDATE;
  SELECT * INTO v_payment FROM public.payments WHERE id = p_payment_id FOR UPDATE;

  IF NOT public.has_session_finance_access(v_session.id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để đảo thanh toán' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_payment_id, btrim(p_reason))::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved
  FROM public.check_idempotency('reverse_payment', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved;
  END IF;

  IF v_payment.status <> 'confirmed' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ đảo được thanh toán đã confirmed' USING ERRCODE = '22023';
  END IF;

  UPDATE public.payments
  SET status = 'reversed', reversed_by = v_actor, reversed_at = now(),
      reversal_reason = btrim(p_reason), updated_at = now()
  WHERE id = p_payment_id;

  v_reversal_id := NULL;
  IF v_session.club_id IS NOT NULL THEN
    SELECT * INTO v_ledger FROM public.club_transactions
    WHERE source_payment_id = p_payment_id AND source_type = 'payment';
    IF NOT FOUND THEN
      RAISE EXCEPTION 'INVALID_STATE: Thiếu bút toán quỹ nguồn để đảo' USING ERRCODE = '22023';
    END IF;
    INSERT INTO public.club_transactions (
      club_id, direction, amount_vnd, title, source_type, reversal_of, created_by
    ) VALUES (
      v_ledger.club_id, CASE WHEN v_ledger.direction = 'income' THEN 'expense' ELSE 'income' END,
      v_ledger.amount_vnd, v_ledger.title, 'reversal', v_ledger.id, v_actor
    ) RETURNING id INTO v_reversal_id;
  END IF;

  PERFORM public.log_audit_event(
    v_session.club_id, v_session.id, 'payment', p_payment_id, 'PAYMENT_REVERSED',
    jsonb_build_object('status', 'confirmed'),
    jsonb_build_object('status', 'reversed', 'reversal_ledger_id', v_reversal_id),
    btrim(p_reason), p_request_id);

  v_res := jsonb_build_object(
    'payment_id', p_payment_id, 'player_id', v_payment.session_player_id, 'session_id', v_session.id,
    'amount_vnd', v_payment.amount_vnd, 'status', 'reversed', 'reversal_ledger_id', v_reversal_id,
    'billing_state', public.session_billing_state(v_session.id)
  );
  PERFORM public.record_idempotency('reverse_payment', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.reverse_payment(UUID, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.reverse_payment(UUID, TEXT, UUID) TO authenticated;

-- ============================================================================
-- 5. record_cash_payment — finance tạo + xác nhận tiền mặt nguyên tử
-- ============================================================================
CREATE OR REPLACE FUNCTION public.record_cash_payment(
  p_player_id UUID,
  p_amount_vnd BIGINT,
  p_reference TEXT DEFAULT NULL,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_player RECORD;
  v_session_id UUID;
  v_session RECORD;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved JSONB;
  v_rev UUID;
  v_due BIGINT;
  v_paid BIGINT;
  v_outstanding BIGINT;
  v_ref TEXT;
  v_payment_id UUID;
  v_ledger_id UUID;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để ghi tiền mặt' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  SELECT session_id INTO v_session_id FROM public.session_players WHERE id = p_player_id;
  IF v_session_id IS NULL THEN
    RAISE EXCEPTION 'NOT_FOUND: Đăng ký không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  SELECT * INTO v_session FROM public.sessions WHERE id = v_session_id FOR UPDATE;
  SELECT * INTO v_player FROM public.session_players WHERE id = p_player_id FOR UPDATE;

  IF NOT public.has_session_finance_access(v_session.id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Cần quyền tài chính để ghi tiền mặt' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_player_id, p_amount_vnd, NULLIF(btrim(COALESCE(p_reference, '')), ''))::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved
  FROM public.check_idempotency('record_cash_payment', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved;
  END IF;

  IF v_player.registration_status <> 'confirmed' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ ghi tiền mặt cho người đã confirmed' USING ERRCODE = '22023';
  END IF;
  IF p_amount_vnd IS NULL OR p_amount_vnd <= 0 OR p_amount_vnd > 1000000000 THEN
    RAISE EXCEPTION 'INVALID_INPUT: Số tiền phải là số nguyên dương VNĐ' USING ERRCODE = '22023';
  END IF;

  v_rev := public.assert_billing_current(v_session.id);

  SELECT COALESCE(SUM(amount_due_vnd), 0) INTO v_due
  FROM public.session_charges WHERE revision_id = v_rev AND session_player_id = p_player_id;
  SELECT COALESCE(SUM(amount_vnd), 0) INTO v_paid
  FROM public.payments WHERE session_player_id = p_player_id AND status = 'confirmed';
  v_outstanding := GREATEST(0, v_due - v_paid);
  IF p_amount_vnd > v_outstanding THEN
    RAISE EXCEPTION 'PAYMENT_EXCEEDS_OUTSTANDING: Số tiền vượt quá khoản còn phải thu (%)', v_outstanding USING ERRCODE = '22023';
  END IF;

  v_ref := COALESCE(NULLIF(btrim(COALESCE(p_reference, '')), ''), 'CASH-' || replace(gen_random_uuid()::text, '-', ''));
  BEGIN
    INSERT INTO public.payments (
      session_player_id, amount_vnd, method, status, reference, submitted_by, confirmed_by, confirmed_at
    ) VALUES (
      p_player_id, p_amount_vnd, 'cash', 'confirmed', v_ref, v_actor, v_actor, now()
    ) RETURNING id INTO v_payment_id;
  EXCEPTION WHEN unique_violation THEN
    RAISE EXCEPTION 'INVALID_INPUT: Mã tham chiếu đã tồn tại' USING ERRCODE = '22023';
  END;

  v_ledger_id := NULL;
  IF v_session.club_id IS NOT NULL THEN
    INSERT INTO public.club_transactions (
      club_id, direction, amount_vnd, title, source_type, source_payment_id, created_by
    ) VALUES (
      v_session.club_id, 'income', p_amount_vnd,
      'Thu tiền mặt buổi ' || COALESCE(v_session.title, ''), 'payment', v_payment_id, v_actor
    ) RETURNING id INTO v_ledger_id;
  END IF;

  PERFORM public.log_audit_event(
    v_session.club_id, v_session.id, 'payment', v_payment_id, 'CASH_PAYMENT_RECORDED',
    NULL, jsonb_build_object('amount_vnd', p_amount_vnd, 'ledger_id', v_ledger_id),
    'Ghi nhận tiền mặt', p_request_id);

  v_res := jsonb_build_object(
    'payment_id', v_payment_id, 'player_id', p_player_id, 'session_id', v_session.id,
    'amount_vnd', p_amount_vnd, 'method', 'cash', 'status', 'confirmed', 'reference', v_ref,
    'ledger_id', v_ledger_id, 'total_paid_vnd', v_paid + p_amount_vnd,
    'outstanding_vnd', GREATEST(0, v_due - (v_paid + p_amount_vnd)),
    'billing_state', 'current'
  );
  PERFORM public.record_idempotency('record_cash_payment', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.record_cash_payment(UUID, BIGINT, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.record_cash_payment(UUID, BIGINT, TEXT, UUID) TO authenticated;

-- ============================================================================
-- 6. post_manual_club_transaction — owner/treasurer, không nhận source từ UI
-- ============================================================================
CREATE OR REPLACE FUNCTION public.post_manual_club_transaction(
  p_club_id UUID,
  p_direction TEXT,
  p_amount_vnd BIGINT,
  p_title TEXT,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_exists BOOLEAN;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved JSONB;
  v_tx_id UUID;
  v_balance BIGINT;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để ghi quỹ' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;

  PERFORM 1 FROM public.clubs WHERE id = p_club_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: CLB không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  IF NOT (public.is_club_owner(p_club_id, v_actor) OR public.has_club_role(p_club_id, v_actor, ARRAY['treasurer'])) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ owner/treasurer CLB ghi quỹ thủ công' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_club_id, p_direction, p_amount_vnd, p_title)::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved
  FROM public.check_idempotency('post_manual_club_transaction', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved;
  END IF;

  IF p_direction IS NULL OR p_direction NOT IN ('income', 'expense') THEN
    RAISE EXCEPTION 'INVALID_INPUT: Chiều giao dịch không hợp lệ' USING ERRCODE = '22023';
  END IF;
  IF p_amount_vnd IS NULL OR p_amount_vnd <= 0 OR p_amount_vnd > 1000000000 THEN
    RAISE EXCEPTION 'INVALID_INPUT: Số tiền phải là số nguyên dương VNĐ' USING ERRCODE = '22023';
  END IF;
  IF p_title IS NULL OR btrim(p_title) = '' THEN
    RAISE EXCEPTION 'INVALID_INPUT: Thiếu nội dung giao dịch' USING ERRCODE = '22023';
  END IF;

  INSERT INTO public.club_transactions (club_id, direction, amount_vnd, title, source_type, created_by)
  VALUES (p_club_id, p_direction, p_amount_vnd, btrim(p_title), 'manual', v_actor)
  RETURNING id INTO v_tx_id;

  PERFORM public.log_audit_event(
    p_club_id, NULL, 'club_transaction', v_tx_id, 'CLUB_TX_MANUAL',
    NULL, jsonb_build_object('direction', p_direction, 'amount_vnd', p_amount_vnd, 'title', btrim(p_title)),
    'Ghi quỹ thủ công', p_request_id);

  SELECT COALESCE(SUM(CASE WHEN direction = 'income' THEN amount_vnd ELSE -amount_vnd END), 0) INTO v_balance
  FROM public.club_transactions WHERE club_id = p_club_id;

  v_res := jsonb_build_object(
    'transaction_id', v_tx_id, 'club_id', p_club_id, 'direction', p_direction,
    'amount_vnd', p_amount_vnd, 'balance_vnd', v_balance, 'source_type', 'manual'
  );
  PERFORM public.record_idempotency('post_manual_club_transaction', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.post_manual_club_transaction(UUID, TEXT, BIGINT, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.post_manual_club_transaction(UUID, TEXT, BIGINT, TEXT, UUID) TO authenticated;

-- ============================================================================
-- 7. reverse_club_transaction — chỉ entry manual, entry đảo duy nhất
-- ============================================================================
CREATE OR REPLACE FUNCTION public.reverse_club_transaction(
  p_transaction_id UUID,
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
  v_tx RECORD;
  v_club_id UUID;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved JSONB;
  v_reversal_id UUID;
  v_balance BIGINT;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để đảo quỹ' USING ERRCODE = '42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE = '22023';
  END IF;
  IF p_reason IS NULL OR btrim(p_reason) = '' THEN
    RAISE EXCEPTION 'INVALID_INPUT: Cần lý do khi đảo quỹ' USING ERRCODE = '22023';
  END IF;

  SELECT club_id INTO v_club_id FROM public.club_transactions WHERE id = p_transaction_id;
  IF v_club_id IS NULL THEN
    RAISE EXCEPTION 'NOT_FOUND: Giao dịch không tồn tại' USING ERRCODE = 'P0002';
  END IF;
  PERFORM 1 FROM public.clubs WHERE id = v_club_id FOR UPDATE;
  SELECT * INTO v_tx FROM public.club_transactions WHERE id = p_transaction_id FOR UPDATE;

  IF NOT (public.is_club_owner(v_tx.club_id, v_actor) OR public.has_club_role(v_tx.club_id, v_actor, ARRAY['treasurer'])) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ owner/treasurer CLB đảo quỹ' USING ERRCODE = '42501';
  END IF;

  v_payload_hash := md5(jsonb_build_array(p_transaction_id, btrim(p_reason))::text);
  SELECT is_replay, saved_result INTO v_is_replay, v_saved
  FROM public.check_idempotency('reverse_club_transaction', p_request_id, v_payload_hash);
  IF v_is_replay THEN
    RETURN v_saved;
  END IF;

  IF v_tx.source_type <> 'manual' THEN
    RAISE EXCEPTION 'INVALID_STATE: Chỉ đảo entry manual; entry tự sinh đảo qua thao tác nguồn' USING ERRCODE = '22023';
  END IF;
  IF EXISTS (SELECT 1 FROM public.club_transactions WHERE reversal_of = p_transaction_id) THEN
    RAISE EXCEPTION 'INVALID_STATE: Giao dịch đã được đảo trước đó' USING ERRCODE = '22023';
  END IF;

  INSERT INTO public.club_transactions (
    club_id, direction, amount_vnd, title, source_type, reversal_of, created_by
  ) VALUES (
    v_tx.club_id, CASE WHEN v_tx.direction = 'income' THEN 'expense' ELSE 'income' END,
    v_tx.amount_vnd, v_tx.title, 'reversal', p_transaction_id, v_actor
  ) RETURNING id INTO v_reversal_id;

  PERFORM public.log_audit_event(
    v_tx.club_id, NULL, 'club_transaction', p_transaction_id, 'CLUB_TX_REVERSED',
    jsonb_build_object('direction', v_tx.direction),
    jsonb_build_object('reversal_id', v_reversal_id), btrim(p_reason), p_request_id);

  SELECT COALESCE(SUM(CASE WHEN direction = 'income' THEN amount_vnd ELSE -amount_vnd END), 0) INTO v_balance
  FROM public.club_transactions WHERE club_id = v_tx.club_id;

  v_res := jsonb_build_object(
    'transaction_id', p_transaction_id, 'reversal_id', v_reversal_id, 'club_id', v_tx.club_id,
    'balance_vnd', v_balance
  );
  PERFORM public.record_idempotency('reverse_club_transaction', p_request_id, v_payload_hash, v_res);
  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.reverse_club_transaction(UUID, TEXT, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.reverse_club_transaction(UUID, TEXT, UUID) TO authenticated;
