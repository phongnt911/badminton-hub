-- Forward-only: phân trang trước aggregate và ACL RPC đọc CLB.
CREATE OR REPLACE FUNCTION public.list_club_members(
  p_club_id UUID,
  p_limit INT DEFAULT 50,
  p_offset INT DEFAULT 0
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_can_manage_contacts BOOLEAN := FALSE;
  v_members JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem danh sách thành viên' USING ERRCODE = '42501';
  END IF;

  -- Kiểm tra quyền xem thành viên CLB
  IF NOT (public.is_club_owner(p_club_id, v_actor) OR public.is_club_member_active(p_club_id, v_actor)) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ thành viên của CLB mới có quyền xem danh sách' USING ERRCODE = '42501';
  END IF;

  -- Kiểm tra quyền đọc contact: Chỉ Owner hoặc Host
  v_can_manage_contacts := (public.is_club_owner(p_club_id, v_actor) OR public.has_club_role(p_club_id, v_actor, ARRAY['owner', 'host']));

  SELECT COALESCE(jsonb_agg(
    jsonb_build_object(
      'id', cm.id,
      'club_id', cm.club_id,
      'user_id', cm.user_id,
      'display_name', cm.display_name,
      'role', cm.role,
      'status', cm.status,
      'joined_at', cm.joined_at,
      'phone_number', CASE WHEN (v_can_manage_contacts OR cm.user_id = v_actor) THEN mc.phone_number ELSE NULL END,
      'contact_note', CASE WHEN (v_can_manage_contacts OR cm.user_id = v_actor) THEN mc.contact_note ELSE NULL END
    ) ORDER BY 
      CASE cm.role 
        WHEN 'owner' THEN 1 
        WHEN 'host' THEN 2 
        WHEN 'treasurer' THEN 3 
        ELSE 4 
      END,
      cm.created_at ASC, cm.id ASC
  ), '[]'::jsonb)
  INTO v_members
  FROM (
    SELECT * FROM public.club_members
    WHERE club_id = p_club_id AND status = 'active'
    ORDER BY CASE role WHEN 'owner' THEN 1 WHEN 'host' THEN 2 WHEN 'treasurer' THEN 3 ELSE 4 END,
      created_at ASC, id ASC
    LIMIT LEAST(GREATEST(COALESCE(p_limit, 50), 1), 100)
    OFFSET GREATEST(COALESCE(p_offset, 0), 0)
  ) cm
  LEFT JOIN public.member_contacts mc ON mc.member_id = cm.id
;

  RETURN v_members;
END;
$$;
REVOKE ALL ON FUNCTION public.list_my_clubs() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.list_my_clubs() TO authenticated;

REVOKE ALL ON FUNCTION public.get_club_detail(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_club_detail(UUID) TO authenticated;

REVOKE ALL ON FUNCTION public.list_club_members(UUID, INT, INT) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.list_club_members(UUID, INT, INT) TO authenticated;
