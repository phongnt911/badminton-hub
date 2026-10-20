-- ============================================================================
-- BH-06 integration review I1 - backfill receiver snapshot cho du lieu cu
-- ============================================================================
--
-- Migration 20261020100000 da cai resolver/trigger/helper nhung chi tac dong
-- cho lan ghi sessions/bank sau do. DB da co tai khoan active va buoi
-- published/in_progress/completed da chot phi truoc khi nang cap van con
-- receiver_snapshot NULL, nen get_payment_instructions tra has_receiver=false
-- va UI chan QR/gui chuyen khoan cho den khi co mot mutation khong lien quan.
--
-- Migration nay chay backfill co gioi han, dung lai fill_session_receiver_snapshot
-- (cung quy tac resolver: bank active cua CLB truoc, host fallback):
-- 1. Chi xet buoi published/in_progress/completed con snapshot NULL.
-- 2. Khong ghi de snapshot/receiver FK da chot (helper kiem tra NULL va UPDATE
--    co dieu kien receiver_snapshot IS NULL).
-- 3. Khong tao bank, khong ghi so du, khong doi nghiep vu chia phi/thanh toan.
-- 4. Buoi khong co bank active van giu NULL de UI bao thieu tai khoan nhan tien.
--
-- Chay sau 20261020100000; idempotent voi DB khong con hang thieu snapshot.
-- ============================================================================

DO $$
DECLARE
  v_session_id UUID;
BEGIN
  FOR v_session_id IN
    SELECT s.id
    FROM public.sessions s
    WHERE s.receiver_snapshot IS NULL
      AND s.lifecycle IN ('published', 'in_progress', 'completed')
    ORDER BY s.id
  LOOP
    PERFORM public.fill_session_receiver_snapshot(v_session_id);
  END LOOP;
END;
$$;
