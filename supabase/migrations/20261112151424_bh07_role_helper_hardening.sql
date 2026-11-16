-- BH-07: restrict anonymous role-helper RPC access and pin legacy trigger search paths.
-- Target: Badminton Hub staging schema hardening
--
-- Scope:
-- 1. Revoke EXECUTE from PUBLIC, anon; grant EXECUTE to authenticated for 10 RLS role helper functions.
-- 2. Pin search_path = public, pg_temp on 2 legacy column synchronization trigger functions.
-- 3. Preserve view definitions and function bodies untouched (zero body edits, zero view edits).

-- ============================================================================
-- 1. TEN RLS ROLE HELPER FUNCTIONS: REVOKE PUBLIC, anon; GRANT authenticated
-- ============================================================================

-- 1. is_app_admin(UUID)
REVOKE ALL ON FUNCTION public.is_app_admin(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.is_app_admin(UUID) TO authenticated;

-- 2. is_club_owner(UUID, UUID)
REVOKE ALL ON FUNCTION public.is_club_owner(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.is_club_owner(UUID, UUID) TO authenticated;

-- 3. is_club_member_active(UUID, UUID)
REVOKE ALL ON FUNCTION public.is_club_member_active(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.is_club_member_active(UUID, UUID) TO authenticated;

-- 4. has_club_role(UUID, UUID, TEXT[])
REVOKE ALL ON FUNCTION public.has_club_role(UUID, UUID, TEXT[]) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.has_club_role(UUID, UUID, TEXT[]) TO authenticated;

-- 5. is_session_host(UUID, UUID)
REVOKE ALL ON FUNCTION public.is_session_host(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.is_session_host(UUID, UUID) TO authenticated;

-- 6. has_session_staff_role(UUID, UUID, TEXT[])
REVOKE ALL ON FUNCTION public.has_session_staff_role(UUID, UUID, TEXT[]) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.has_session_staff_role(UUID, UUID, TEXT[]) TO authenticated;

-- 7. has_session_management_access(UUID, UUID)
REVOKE ALL ON FUNCTION public.has_session_management_access(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.has_session_management_access(UUID, UUID) TO authenticated;

-- 8. has_session_finance_access(UUID, UUID)
REVOKE ALL ON FUNCTION public.has_session_finance_access(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.has_session_finance_access(UUID, UUID) TO authenticated;

-- 9. is_session_participant(UUID, UUID)
REVOKE ALL ON FUNCTION public.is_session_participant(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.is_session_participant(UUID, UUID) TO authenticated;

-- 10. has_session_player_finance_access(UUID, UUID)
REVOKE ALL ON FUNCTION public.has_session_player_finance_access(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.has_session_player_finance_access(UUID, UUID) TO authenticated;

-- ============================================================================
-- 2. TWO LEGACY COLUMN SYNC TRIGGER FUNCTIONS: SET search_path
-- ============================================================================

-- 1. sync_legacy_session_columns()
ALTER FUNCTION public.sync_legacy_session_columns() SET search_path = public, pg_temp;

-- 2. sync_legacy_session_player_columns()
ALTER FUNCTION public.sync_legacy_session_player_columns() SET search_path = public, pg_temp;
