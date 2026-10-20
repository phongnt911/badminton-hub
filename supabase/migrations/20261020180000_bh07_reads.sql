-- BH-07A — projection đọc cho lịch sử và tổng kết sau complete.
--
-- Phạm vi:
--   * `list_my_session_history`: danh sách buổi đã kết thúc/đã hủy của host,
--     management hoặc finance; lọc CLB/khoảng ngày, phân trang trước aggregate,
--     sắp xếp mới nhất trước. Không đọc toàn bộ bảng sessions từ client.
--   * `get_session_summary`: aggregate server-side cho tab Tổng kết. Không trả
--     contact, tài khoản ngân hàng, danh sách người chơi, charges/payments thô.
--     Management thấy count; finance thấy thêm tiền. Participant/outsider không
--     có quyền.
--
-- Đây là migration forward mới; không sửa migration đã chia sẻ. Không thay đổi
-- schema, không backfill, không nới gate complete hay quyền tài chính hiện hành.
-- Các RPC chỉ đọc, SECURITY DEFINER + search_path cố định, REVOKE PUBLIC/anon.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_session_summary(p_session_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_session RECORD;
  v_can_manage BOOLEAN := FALSE;
  v_can_finance BOOLEAN := FALSE;
  v_rev UUID;
  v_present_count INT := 0;
  v_no_show_count INT := 0;
  v_confirmed_count INT := 0;
  v_expenses_total BIGINT := 0;
  v_due_total BIGINT := 0;
  v_paid_total BIGINT := 0;
  v_outstanding_total BIGINT := 0;
  v_revision_no INT := NULL;
  v_source_version BIGINT := NULL;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem tổng kết buổi' USING ERRCODE = '42501';
  END IF;

  SELECT s.id, s.title, s.club_id, c.name AS club_name,
         s.starts_at, s.ends_at, s.lifecycle, s.fee_mode,
         s.version, s.billing_input_version,
         v.name AS venue_name
  INTO v_session
  FROM public.sessions s
  LEFT JOIN public.clubs c ON c.id = s.club_id
  LEFT JOIN public.venues v ON v.id = s.venue_id
  WHERE s.id = p_session_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;

  v_can_manage := public.has_session_management_access(p_session_id, v_actor);
  v_can_finance := public.has_session_finance_access(p_session_id, v_actor);
  IF NOT (v_can_manage OR v_can_finance) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ host/quản lý hoặc finance xem được tổng kết buổi' USING ERRCODE = '42501';
  END IF;

  SELECT
    count(*) FILTER (WHERE registration_status = 'confirmed' AND attendance_status = 'present'),
    count(*) FILTER (WHERE registration_status = 'confirmed' AND attendance_status = 'no_show'),
    count(*) FILTER (WHERE registration_status = 'confirmed')
  INTO v_present_count, v_no_show_count, v_confirmed_count
  FROM public.session_players
  WHERE session_id = p_session_id;

  IF v_can_finance THEN
    v_rev := public.active_charge_revision_id(p_session_id);

    SELECT COALESCE(SUM(amount_vnd), 0) INTO v_expenses_total
    FROM public.session_expenses
    WHERE session_id = p_session_id AND status = 'posted';

    IF v_rev IS NOT NULL THEN
      SELECT cr.revision_no, cr.source_version, COALESCE(cr.allocation_total_vnd, 0)
      INTO v_revision_no, v_source_version, v_due_total
      FROM public.charge_revisions cr
      WHERE cr.id = v_rev;

      SELECT COALESCE(SUM(GREATEST(0, sc.amount_due_vnd - COALESCE(pay.total, 0))), 0)
      INTO v_outstanding_total
      FROM public.session_charges sc
      LEFT JOIN (
        SELECT session_player_id, SUM(amount_vnd) AS total
        FROM public.payments
        WHERE status = 'confirmed'
        GROUP BY session_player_id
      ) pay ON pay.session_player_id = sc.session_player_id
      WHERE sc.revision_id = v_rev;
    END IF;

    SELECT COALESCE(SUM(p.amount_vnd), 0) INTO v_paid_total
    FROM public.payments p
    JOIN public.session_players sp ON sp.id = p.session_player_id
    WHERE sp.session_id = p_session_id AND p.status = 'confirmed';
  END IF;

  RETURN jsonb_build_object(
    'session_id', p_session_id,
    'title', v_session.title,
    'club_id', v_session.club_id,
    'club_name', v_session.club_name,
    'venue_name', v_session.venue_name,
    'starts_at', v_session.starts_at,
    'ends_at', v_session.ends_at,
    'lifecycle', v_session.lifecycle,
    'fee_mode', v_session.fee_mode,
    'session_version', v_session.version,
    'can_manage', v_can_manage,
    'can_view_finance', v_can_finance,
    'present_count', v_present_count,
    'no_show_count', v_no_show_count,
    'confirmed_count', v_confirmed_count,
    'billing_state', CASE WHEN v_can_finance THEN public.session_billing_state(p_session_id) END,
    'active_revision_id', CASE WHEN v_can_finance THEN v_rev END,
    'revision_no', CASE WHEN v_can_finance THEN v_revision_no END,
    'source_version', CASE WHEN v_can_finance THEN v_source_version END,
    'expenses_total_vnd', CASE WHEN v_can_finance THEN v_expenses_total END,
    'amount_due_total_vnd', CASE WHEN v_can_finance THEN v_due_total END,
    'total_paid_vnd', CASE WHEN v_can_finance THEN v_paid_total END,
    'outstanding_total_vnd', CASE WHEN v_can_finance THEN v_outstanding_total END
  );
END;
$$;
REVOKE ALL ON FUNCTION public.get_session_summary(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_session_summary(UUID) TO authenticated;

-- ============================================================================
-- Lịch sử buổi của actor: chỉ completed/cancelled, mới nhất trước, có filter
-- CLB/khoảng ngày và phân trang trước khi tính confirmed_count.
-- ============================================================================
CREATE OR REPLACE FUNCTION public.list_my_session_history(
  p_limit INT DEFAULT 20,
  p_offset INT DEFAULT 0,
  p_club_id UUID DEFAULT NULL,
  p_from TIMESTAMPTZ DEFAULT NULL,
  p_to TIMESTAMPTZ DEFAULT NULL
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
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem lịch sử buổi' USING ERRCODE = '42501';
  END IF;
  IF p_from IS NOT NULL AND p_to IS NOT NULL AND p_to < p_from THEN
    RAISE EXCEPTION 'INVALID_INPUT: Khoảng ngày không hợp lệ' USING ERRCODE = '22023';
  END IF;

  v_limit := LEAST(GREATEST(COALESCE(p_limit, 20), 1), 100);
  v_offset := GREATEST(COALESCE(p_offset, 0), 0);

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
    ) ORDER BY t.starts_at DESC, t.id DESC), '[]'::jsonb)
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
    WHERE s.lifecycle IN ('completed', 'cancelled')
      AND (
        s.host_user_id = v_actor
        OR public.has_session_management_access(s.id, v_actor)
        OR public.has_session_finance_access(s.id, v_actor)
      )
      AND (p_club_id IS NULL OR s.club_id = p_club_id)
      AND (p_from IS NULL OR s.starts_at >= p_from)
      AND (p_to IS NULL OR s.starts_at <= p_to)
    ORDER BY s.starts_at DESC, s.id DESC
    LIMIT v_limit
    OFFSET v_offset
  ) t;

  RETURN v_res;
END;
$$;
REVOKE ALL ON FUNCTION public.list_my_session_history(INT, INT, UUID, TIMESTAMPTZ, TIMESTAMPTZ) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.list_my_session_history(INT, INT, UUID, TIMESTAMPTZ, TIMESTAMPTZ) TO authenticated;
