-- ============================================================================
-- BH-06 integration - chot receiver_snapshot cho huong dan thanh toan/QR
-- ============================================================================
--
-- Lo hong tich hop: schema docs/03 va RPC docs/08 (get_payment_instructions,
-- get_session_payment_instructions) dua vao sessions.receiver_snapshot, nhung
-- khong co migration/RPC nao ghi snapshot hay receiver_*_bank_account_id.
-- Vi vay sau khi chot phi, `has_receiver` luon false va UI BH-06C luon hien
-- "Chua co tai khoan nhan tien", khong tao duoc QR/khong gui duoc chuyen khoan.
--
-- Migration nay:
-- 1. resolve_session_receiver: chon tai khoan active cua CLB (neu buoi gan CLB)
--    hoac cua host (fallback), tra kind/id/snapshot JSON.
-- 2. Trigger BEFORE INSERT/UPDATE tren sessions: chot snapshot khi buoi o
--    published/in_progress/completed va snapshot con NULL. Khong ghi de
--    snapshot da chot (giu lich su/doi soat).
-- 3. Trigger AFTER INSERT/UPDATE tren club_bank_accounts/host_bank_accounts:
--    dien snapshot cho cac buoi dang mo chua co snapshot, de host cau hinh
--    ngan hang sau khi publish/start van mo duoc huong dan/QR.
--
-- Khong doi nghiep vu chia phi/thanh toan; khong ghi so du; khong dung secret.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Chon tai khoan nhan tien theo scope CLB/host
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.resolve_session_receiver(
  p_club_id UUID,
  p_host_user_id UUID
)
RETURNS TABLE(account_kind TEXT, account_id UUID, snapshot JSONB)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_account RECORD;
BEGIN
  -- Buoi gan CLB: uu tien tai khoan active cua CLB.
  IF p_club_id IS NOT NULL THEN
    SELECT cba.id, cba.bank_code, cba.account_number, cba.account_name
    INTO v_account
    FROM public.club_bank_accounts cba
    WHERE cba.club_id = p_club_id AND cba.status = 'active'
    ORDER BY cba.updated_at DESC, cba.id DESC
    LIMIT 1;

    IF FOUND THEN
      RETURN QUERY SELECT
        'club'::TEXT,
        v_account.id,
        jsonb_build_object(
          'bank_code', v_account.bank_code,
          'account_number', v_account.account_number,
          'account_name', v_account.account_name);
      RETURN;
    END IF;
  END IF;

  -- Fallback (hoac buoi khong gan CLB): tai khoan active cua host.
  SELECT hba.id, hba.bank_code, hba.account_number, hba.account_name
  INTO v_account
  FROM public.host_bank_accounts hba
  WHERE hba.user_id = p_host_user_id AND hba.status = 'active'
  ORDER BY hba.updated_at DESC, hba.id DESC
  LIMIT 1;

  IF FOUND THEN
    RETURN QUERY SELECT
      'host'::TEXT,
      v_account.id,
      jsonb_build_object(
        'bank_code', v_account.bank_code,
        'account_number', v_account.account_number,
        'account_name', v_account.account_name);
  END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.resolve_session_receiver(UUID, UUID) FROM PUBLIC, anon, authenticated;

-- ----------------------------------------------------------------------------
-- 2. Chot snapshot tren sessions (BEFORE trigger, khong ghi de snapshot cu)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.bh06_sessions_receiver_snapshot()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_receiver RECORD;
BEGIN
  IF NEW.receiver_snapshot IS NOT NULL THEN
    RETURN NEW;
  END IF;
  IF NEW.lifecycle NOT IN ('published', 'in_progress', 'completed') THEN
    RETURN NEW;
  END IF;

  SELECT * INTO v_receiver
  FROM public.resolve_session_receiver(NEW.club_id, NEW.host_user_id);

  IF NOT FOUND OR v_receiver.account_id IS NULL THEN
    RETURN NEW;
  END IF;

  IF v_receiver.account_kind = 'club' THEN
    NEW.receiver_club_bank_account_id := v_receiver.account_id;
    NEW.receiver_host_bank_account_id := NULL;
  ELSE
    NEW.receiver_host_bank_account_id := v_receiver.account_id;
    NEW.receiver_club_bank_account_id := NULL;
  END IF;
  NEW.receiver_snapshot := v_receiver.snapshot;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS bh06_sessions_receiver_snapshot ON public.sessions;
CREATE TRIGGER bh06_sessions_receiver_snapshot
BEFORE INSERT OR UPDATE ON public.sessions
FOR EACH ROW EXECUTE FUNCTION public.bh06_sessions_receiver_snapshot();

-- ----------------------------------------------------------------------------
-- 3. Dien snapshot cho cac buoi dang mo khi cau hinh ngan hang
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.fill_session_receiver_snapshot(p_session_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_session RECORD;
  v_receiver RECORD;
BEGIN
  SELECT id, club_id, host_user_id, lifecycle, receiver_snapshot
  INTO v_session
  FROM public.sessions
  WHERE id = p_session_id
  FOR UPDATE;

  IF NOT FOUND OR v_session.receiver_snapshot IS NOT NULL THEN
    RETURN;
  END IF;
  IF v_session.lifecycle NOT IN ('published', 'in_progress', 'completed') THEN
    RETURN;
  END IF;

  SELECT * INTO v_receiver
  FROM public.resolve_session_receiver(v_session.club_id, v_session.host_user_id);
  IF NOT FOUND OR v_receiver.account_id IS NULL THEN
    RETURN;
  END IF;

  UPDATE public.sessions SET
    receiver_club_bank_account_id = CASE
      WHEN v_receiver.account_kind = 'club' THEN v_receiver.account_id ELSE NULL END,
    receiver_host_bank_account_id = CASE
      WHEN v_receiver.account_kind = 'host' THEN v_receiver.account_id ELSE NULL END,
    receiver_snapshot = v_receiver.snapshot
  WHERE id = p_session_id AND receiver_snapshot IS NULL;
END;
$$;

REVOKE ALL ON FUNCTION public.fill_session_receiver_snapshot(UUID) FROM PUBLIC, anon, authenticated;

CREATE OR REPLACE FUNCTION public.bh06_bank_receiver_snapshot()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_session_id UUID;
BEGIN
  IF NEW.status <> 'active' THEN
    RETURN NEW;
  END IF;

  IF TG_TABLE_NAME = 'club_bank_accounts' THEN
    FOR v_session_id IN
      SELECT s.id FROM public.sessions s
      WHERE s.club_id = NEW.club_id
        AND s.lifecycle IN ('published', 'in_progress', 'completed')
        AND s.receiver_snapshot IS NULL
    LOOP
      PERFORM public.fill_session_receiver_snapshot(v_session_id);
    END LOOP;
  ELSE
    FOR v_session_id IN
      SELECT s.id FROM public.sessions s
      WHERE s.host_user_id = NEW.user_id
        AND s.lifecycle IN ('published', 'in_progress', 'completed')
        AND s.receiver_snapshot IS NULL
    LOOP
      PERFORM public.fill_session_receiver_snapshot(v_session_id);
    END LOOP;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS bh06_club_bank_receiver_snapshot ON public.club_bank_accounts;
CREATE TRIGGER bh06_club_bank_receiver_snapshot
AFTER INSERT OR UPDATE ON public.club_bank_accounts
FOR EACH ROW EXECUTE FUNCTION public.bh06_bank_receiver_snapshot();

DROP TRIGGER IF EXISTS bh06_host_bank_receiver_snapshot ON public.host_bank_accounts;
CREATE TRIGGER bh06_host_bank_receiver_snapshot
AFTER INSERT OR UPDATE ON public.host_bank_accounts
FOR EACH ROW EXECUTE FUNCTION public.bh06_bank_receiver_snapshot();
