-- Migration: 20261015133247_bh03_clubs_and_members.sql
-- Mô tả: Cung cấp đầy đủ RPCs và logic nghiệp vụ cho BH-03 (CLB, Thành viên, Ngân hàng)
-- Tuân thủ: docs/03_DATABASE.md, docs/08_DOMAIN_CONTRACTS.md, docs/15_BH03_IMPLEMENTATION_HANDOFF.md

-- ============================================================================
-- 1. BACKFILL PROFILES CHO TÀI KHOẢN AUTH CŨ (NẾU CÓ)
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'auth' AND table_name = 'users') THEN
    INSERT INTO public.profiles (id, display_name)
    SELECT 
      u.id, 
      COALESCE(NULLIF(u.raw_user_meta_data->>'display_name', ''), split_part(COALESCE(u.email, 'User'), '@', 1))
    FROM auth.users u
    ON CONFLICT (id) DO NOTHING;
  END IF;
END $$;

-- ============================================================================
-- 2. RPC TẠO CLB VÀ GÁN OWNER NGUYÊN TỬ (ATOMIC CREATE_CLUB)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.create_club(
  p_name TEXT,
  p_description TEXT DEFAULT NULL,
  p_visibility TEXT DEFAULT 'private',
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_club_id UUID;
  v_member_id UUID;
  v_display_name TEXT;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
BEGIN
  -- 1. Kiểm tra xác thực
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để tạo CLB' USING ERRCODE = '42501';
  END IF;

  -- 2. Validate dữ liệu đầu vào
  p_name := trim(p_name);
  IF p_name IS NULL OR length(p_name) = 0 THEN
    RAISE EXCEPTION 'INVALID_ARGUMENT: Tên CLB không được để trống' USING ERRCODE = '22023';
  END IF;

  IF p_visibility NOT IN ('private', 'public') THEN
    RAISE EXCEPTION 'INVALID_ARGUMENT: Quyền riêng tư phải là private hoặc public' USING ERRCODE = '22023';
  END IF;

  -- 3. Kiểm tra Idempotency
  IF p_request_id IS NOT NULL THEN
    v_payload_hash := md5(p_name || ':' || COALESCE(p_description, '') || ':' || p_visibility);
    SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
    FROM public.check_idempotency('create_club', p_request_id, v_payload_hash);
    IF v_is_replay THEN
      RETURN v_saved_result;
    END IF;
  END IF;

  -- 4. Đảm bảo profile người tạo tồn tại
  SELECT display_name INTO v_display_name FROM public.profiles WHERE id = v_actor;
  IF v_display_name IS NULL THEN
    v_display_name := 'Chủ nhiệm';
    INSERT INTO public.profiles (id, display_name)
    VALUES (v_actor, v_display_name)
    ON CONFLICT (id) DO UPDATE SET updated_at = now()
    RETURNING display_name INTO v_display_name;
  END IF;

  -- 5. Tạo CLB
  INSERT INTO public.clubs (owner_user_id, name, description, visibility, status)
  VALUES (v_actor, p_name, NULLIF(trim(p_description), ''), p_visibility, 'active')
  RETURNING id INTO v_club_id;

  -- 6. Tạo thành viên Owner nguyên tử
  INSERT INTO public.club_members (club_id, user_id, display_name, role, status, joined_at)
  VALUES (v_club_id, v_actor, v_display_name, 'owner', 'active', now())
  RETURNING id INTO v_member_id;

  -- 7. Ghi audit event
  PERFORM public.log_audit_event(
    v_club_id, NULL, 'club', v_club_id, 'CREATE_CLUB',
    NULL, jsonb_build_object('name', p_name, 'visibility', p_visibility),
    'Tạo mới câu lạc bộ kèm chủ nhiệm', p_request_id
  );

  v_res := jsonb_build_object(
    'id', v_club_id,
    'owner_user_id', v_actor,
    'name', p_name,
    'description', p_description,
    'visibility', p_visibility,
    'status', 'active',
    'my_role', 'owner',
    'created_at', now()
  );

  -- 8. Lưu kết quả Idempotency
  IF p_request_id IS NOT NULL THEN
    PERFORM public.record_idempotency('create_club', p_request_id, v_payload_hash, v_res);
  END IF;

  RETURN v_res;
END;
$$;

-- ============================================================================
-- 3. RPC CẬP NHẬT THÔNG TIN CLB (UPDATE_CLUB)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.update_club(
  p_club_id UUID,
  p_name TEXT DEFAULT NULL,
  p_description TEXT DEFAULT NULL,
  p_visibility TEXT DEFAULT NULL,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_club RECORD;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để cập nhật CLB' USING ERRCODE = '42501';
  END IF;

  -- Khóa CLB và kiểm tra quyền Owner
  SELECT * INTO v_club FROM public.clubs WHERE id = p_club_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: CLB không tồn tại' USING ERRCODE = 'P0002';
  END IF;

  IF v_club.owner_user_id != v_actor THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ chủ nhiệm mới có quyền sửa thông tin CLB' USING ERRCODE = '42501';
  END IF;

  -- Idempotency
  IF p_request_id IS NOT NULL THEN
    v_payload_hash := md5(COALESCE(p_name, '') || ':' || COALESCE(p_description, '') || ':' || COALESCE(p_visibility, ''));
    SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
    FROM public.check_idempotency('update_club', p_request_id, v_payload_hash);
    IF v_is_replay THEN
      RETURN v_saved_result;
    END IF;
  END IF;

  IF p_name IS NOT NULL AND length(trim(p_name)) = 0 THEN
    RAISE EXCEPTION 'INVALID_ARGUMENT: Tên CLB không được rỗng' USING ERRCODE = '22023';
  END IF;

  IF p_visibility IS NOT NULL AND p_visibility NOT IN ('private', 'public') THEN
    RAISE EXCEPTION 'INVALID_ARGUMENT: Quyền riêng tư không hợp lệ' USING ERRCODE = '22023';
  END IF;

  UPDATE public.clubs
  SET
    name = COALESCE(NULLIF(trim(p_name), ''), name),
    description = CASE WHEN p_description IS NOT NULL THEN trim(p_description) ELSE description END,
    visibility = COALESCE(p_visibility, visibility),
    updated_at = now()
  WHERE id = p_club_id
  RETURNING * INTO v_club;

  PERFORM public.log_audit_event(
    p_club_id, NULL, 'club', p_club_id, 'UPDATE_CLUB',
    jsonb_build_object('name', v_club.name),
    jsonb_build_object('name', p_name, 'visibility', p_visibility),
    'Cập nhật thông tin CLB', p_request_id
  );

  v_res := jsonb_build_object(
    'id', v_club.id,
    'owner_user_id', v_club.owner_user_id,
    'name', v_club.name,
    'description', v_club.description,
    'visibility', v_club.visibility,
    'status', v_club.status,
    'updated_at', v_club.updated_at
  );

  IF p_request_id IS NOT NULL THEN
    PERFORM public.record_idempotency('update_club', p_request_id, v_payload_hash, v_res);
  END IF;

  RETURN v_res;
END;
$$;

-- ============================================================================
-- 4. RPC THÊM THÀNH VIÊN VÀO CLB (ADD_CLUB_MEMBER)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.add_club_member(
  p_club_id UUID,
  p_display_name TEXT,
  p_phone_number TEXT DEFAULT NULL,
  p_contact_note TEXT DEFAULT NULL,
  p_user_id UUID DEFAULT NULL,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_club RECORD;
  v_member_id UUID;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để thêm thành viên' USING ERRCODE = '42501';
  END IF;

  -- 1. Kiểm tra quyền của actor: Owner hoặc Host active
  IF NOT (public.is_club_owner(p_club_id, v_actor) OR public.has_club_role(p_club_id, v_actor, ARRAY['owner', 'host'])) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ chủ nhiệm hoặc quản lý mới có quyền thêm thành viên' USING ERRCODE = '42501';
  END IF;

  -- 2. Kiểm tra CLB active
  SELECT * INTO v_club FROM public.clubs WHERE id = p_club_id;
  IF NOT FOUND OR v_club.status != 'active' THEN
    RAISE EXCEPTION 'INVALID_ARGUMENT: Câu lạc bộ không tồn tại hoặc đã ngừng hoạt động' USING ERRCODE = '22023';
  END IF;

  p_display_name := trim(p_display_name);
  IF p_display_name IS NULL OR length(p_display_name) = 0 THEN
    RAISE EXCEPTION 'INVALID_ARGUMENT: Tên thành viên không được để trống' USING ERRCODE = '22023';
  END IF;

  -- 3. Idempotency
  IF p_request_id IS NOT NULL THEN
    v_payload_hash := md5(p_club_id::text || ':' || p_display_name || ':' || COALESCE(p_phone_number, '') || ':' || COALESCE(p_user_id::text, ''));
    SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
    FROM public.check_idempotency('add_club_member', p_request_id, v_payload_hash);
    IF v_is_replay THEN
      RETURN v_saved_result;
    END IF;
  END IF;

  -- 4. Kiểm tra user_id nếu có
  IF p_user_id IS NOT NULL THEN
    IF NOT EXISTS (SELECT 1 FROM public.profiles WHERE id = p_user_id) THEN
      RAISE EXCEPTION 'NOT_FOUND: Tài khoản liên kết không tồn tại' USING ERRCODE = 'P0002';
    END IF;
    IF EXISTS (SELECT 1 FROM public.club_members WHERE club_id = p_club_id AND user_id = p_user_id) THEN
      RAISE EXCEPTION 'CONFLICT: Thành viên với tài khoản này đã có trong CLB' USING ERRCODE = '23505';
    END IF;
  END IF;

  -- 5. Tạo thành viên với vai trò mặc định 'member'
  INSERT INTO public.club_members (club_id, user_id, display_name, role, status, joined_at)
  VALUES (p_club_id, p_user_id, p_display_name, 'member', 'active', now())
  RETURNING id INTO v_member_id;

  -- 6. Lưu thông tin liên hệ riêng tư (nếu có cung cấp)
  p_phone_number := NULLIF(trim(p_phone_number), '');
  p_contact_note := NULLIF(trim(p_contact_note), '');
  IF p_phone_number IS NOT NULL OR p_contact_note IS NOT NULL THEN
    INSERT INTO public.member_contacts (member_id, phone_number, contact_note)
    VALUES (v_member_id, p_phone_number, p_contact_note);
  END IF;

  PERFORM public.log_audit_event(
    p_club_id, NULL, 'club_member', v_member_id, 'ADD_MEMBER',
    NULL, jsonb_build_object('display_name', p_display_name, 'has_user', p_user_id IS NOT NULL),
    'Thêm thành viên mới vào CLB', p_request_id
  );

  v_res := jsonb_build_object(
    'id', v_member_id,
    'club_id', p_club_id,
    'user_id', p_user_id,
    'display_name', p_display_name,
    'role', 'member',
    'status', 'active',
    'has_contact', (p_phone_number IS NOT NULL),
    'created_at', now()
  );

  IF p_request_id IS NOT NULL THEN
    PERFORM public.record_idempotency('add_club_member', p_request_id, v_payload_hash, v_res);
  END IF;

  RETURN v_res;
END;
$$;

-- ============================================================================
-- 5. RPC PHÂN QUYỀN THÀNH VIÊN CLB (SET_CLUB_MEMBER_ROLE)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.set_club_member_role(
  p_club_id UUID,
  p_member_id UUID,
  p_role TEXT,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_member RECORD;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để phân quyền' USING ERRCODE = '42501';
  END IF;

  -- 1. CHỈ Owner của CLB mới có quyền cấp vai trò
  IF NOT public.is_club_owner(p_club_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ chủ nhiệm CLB mới có quyền thay đổi vai trò' USING ERRCODE = '42501';
  END IF;

  -- 2. Kiểm tra vai trò hợp lệ (không đổi owner qua endpoint này)
  IF p_role NOT IN ('host', 'treasurer', 'member') THEN
    RAISE EXCEPTION 'INVALID_ARGUMENT: Vai trò không hợp lệ (chỉ chấp nhận host, treasurer, member)' USING ERRCODE = '22023';
  END IF;

  -- 3. Idempotency
  IF p_request_id IS NOT NULL THEN
    v_payload_hash := md5(p_club_id::text || ':' || p_member_id::text || ':' || p_role);
    SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
    FROM public.check_idempotency('set_club_member_role', p_request_id, v_payload_hash);
    IF v_is_replay THEN
      RETURN v_saved_result;
    END IF;
  END IF;

  -- 4. Kiểm tra target member
  SELECT * INTO v_member FROM public.club_members WHERE id = p_member_id AND club_id = p_club_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Thành viên không tồn tại trong CLB này' USING ERRCODE = 'P0002';
  END IF;

  -- Không được sửa vai trò của Owner
  IF v_member.role = 'owner' THEN
    RAISE EXCEPTION 'FORBIDDEN: Không thể thay đổi vai trò của Chủ nhiệm qua chức năng này' USING ERRCODE = '42501';
  END IF;

  -- Không cấp vai trò quản lý (host/treasurer) cho thành viên chưa liên kết tài khoản
  IF v_member.user_id IS NULL AND p_role IN ('host', 'treasurer') THEN
    RAISE EXCEPTION 'INVALID_ARGUMENT: Thành viên chưa liên kết tài khoản app không thể nhận vai trò quản trị' USING ERRCODE = '22023';
  END IF;

  UPDATE public.club_members
  SET role = p_role, updated_at = now()
  WHERE id = p_member_id;

  PERFORM public.log_audit_event(
    p_club_id, NULL, 'club_member', p_member_id, 'SET_MEMBER_ROLE',
    jsonb_build_object('old_role', v_member.role),
    jsonb_build_object('new_role', p_role),
    'Thay đổi vai trò thành viên CLB', p_request_id
  );

  v_res := jsonb_build_object(
    'id', p_member_id,
    'club_id', p_club_id,
    'user_id', v_member.user_id,
    'display_name', v_member.display_name,
    'role', p_role,
    'status', v_member.status
  );

  IF p_request_id IS NOT NULL THEN
    PERFORM public.record_idempotency('set_club_member_role', p_request_id, v_payload_hash, v_res);
  END IF;

  RETURN v_res;
END;
$$;

-- ============================================================================
-- 6. RPC CẤU HÌNH TÀI KHOẢN NGÂN HÀNG CLB (SET_CLUB_BANK_ACCOUNT)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.set_club_bank_account(
  p_club_id UUID,
  p_bank_code TEXT,
  p_account_number TEXT,
  p_account_name TEXT,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_account_id UUID;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để cấu hình ngân hàng' USING ERRCODE = '42501';
  END IF;

  -- CHỈ Owner mới được cấu hình tài khoản CLB
  IF NOT public.is_club_owner(p_club_id, v_actor) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ chủ nhiệm mới có quyền cấu hình tài khoản ngân hàng CLB' USING ERRCODE = '42501';
  END IF;

  p_bank_code := trim(p_bank_code);
  p_account_number := trim(p_account_number);
  p_account_name := trim(p_account_name);

  IF length(COALESCE(p_bank_code, '')) = 0 OR length(COALESCE(p_account_number, '')) = 0 OR length(COALESCE(p_account_name, '')) = 0 THEN
    RAISE EXCEPTION 'INVALID_ARGUMENT: Thông tin ngân hàng không được để trống' USING ERRCODE = '22023';
  END IF;

  IF p_request_id IS NOT NULL THEN
    v_payload_hash := md5(p_club_id::text || ':' || p_bank_code || ':' || p_account_number);
    SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
    FROM public.check_idempotency('set_club_bank_account', p_request_id, v_payload_hash);
    IF v_is_replay THEN
      RETURN v_saved_result;
    END IF;
  END IF;

  -- Khóa CLB để tránh concurrent updates tạo 2 active accounts
  PERFORM 1 FROM public.clubs WHERE id = p_club_id FOR UPDATE;

  -- Ngừng active tài khoản cũ
  UPDATE public.club_bank_accounts
  SET status = 'inactive', updated_at = now()
  WHERE club_id = p_club_id AND status = 'active';

  -- Tạo tài khoản active mới (giữ leading zeros với kiểu TEXT)
  INSERT INTO public.club_bank_accounts (club_id, bank_code, account_number, account_name, status)
  VALUES (p_club_id, p_bank_code, p_account_number, p_account_name, 'active')
  RETURNING id INTO v_account_id;

  PERFORM public.log_audit_event(
    p_club_id, NULL, 'club_bank_account', v_account_id, 'SET_BANK_ACCOUNT',
    NULL, jsonb_build_object('bank_code', p_bank_code, 'account_name', p_account_name),
    'Cập nhật tài khoản ngân hàng nhận tiền CLB', p_request_id
  );

  v_res := jsonb_build_object(
    'id', v_account_id,
    'club_id', p_club_id,
    'bank_code', p_bank_code,
    'account_number', p_account_number,
    'account_name', p_account_name,
    'status', 'active'
  );

  IF p_request_id IS NOT NULL THEN
    PERFORM public.record_idempotency('set_club_bank_account', p_request_id, v_payload_hash, v_res);
  END IF;

  RETURN v_res;
END;
$$;

-- ============================================================================
-- 7. RPC CẤU HÌNH TÀI KHOẢN NGÂN HÀNG CÁ NHÂN CỦA HOST (SET_HOST_BANK_ACCOUNT)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.set_host_bank_account(
  p_bank_code TEXT,
  p_account_number TEXT,
  p_account_name TEXT,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_account_id UUID;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để cấu hình tài khoản cá nhân' USING ERRCODE = '42501';
  END IF;

  p_bank_code := trim(p_bank_code);
  p_account_number := trim(p_account_number);
  p_account_name := trim(p_account_name);

  IF length(COALESCE(p_bank_code, '')) = 0 OR length(COALESCE(p_account_number, '')) = 0 OR length(COALESCE(p_account_name, '')) = 0 THEN
    RAISE EXCEPTION 'INVALID_ARGUMENT: Thông tin ngân hàng không được để trống' USING ERRCODE = '22023';
  END IF;

  IF p_request_id IS NOT NULL THEN
    v_payload_hash := md5(v_actor::text || ':' || p_bank_code || ':' || p_account_number);
    SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
    FROM public.check_idempotency('set_host_bank_account', p_request_id, v_payload_hash);
    IF v_is_replay THEN
      RETURN v_saved_result;
    END IF;
  END IF;

  PERFORM 1 FROM public.profiles WHERE id = v_actor FOR UPDATE;

  UPDATE public.host_bank_accounts
  SET status = 'inactive', updated_at = now()
  WHERE user_id = v_actor AND status = 'active';

  INSERT INTO public.host_bank_accounts (user_id, bank_code, account_number, account_name, status)
  VALUES (v_actor, p_bank_code, p_account_number, p_account_name, 'active')
  RETURNING id INTO v_account_id;

  v_res := jsonb_build_object(
    'id', v_account_id,
    'user_id', v_actor,
    'bank_code', p_bank_code,
    'account_number', p_account_number,
    'account_name', p_account_name,
    'status', 'active'
  );

  IF p_request_id IS NOT NULL THEN
    PERFORM public.record_idempotency('set_host_bank_account', p_request_id, v_payload_hash, v_res);
  END IF;

  RETURN v_res;
END;
$$;

-- ============================================================================
-- 8. RPC ĐỌC CHI TIẾT CLB THEO PHÂN QUYỀN (GET_CLUB_DETAIL)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.get_club_detail(p_club_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_club RECORD;
  v_my_role TEXT;
  v_balance BIGINT := NULL;
  v_member_count INT;
BEGIN
  SELECT * INTO v_club FROM public.clubs WHERE id = p_club_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: CLB không tồn tại' USING ERRCODE = 'P0002';
  END IF;

  -- Kiểm tra quyền xem CLB private
  IF v_club.visibility = 'private' THEN
    IF v_actor IS NULL THEN
      RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem CLB nội bộ' USING ERRCODE = '42501';
    END IF;
    IF NOT (v_club.owner_user_id = v_actor OR public.is_club_member_active(p_club_id, v_actor)) THEN
      RAISE EXCEPTION 'FORBIDDEN: Không có quyền truy cập CLB này' USING ERRCODE = '42501';
    END IF;
  END IF;

  -- Lấy role của actor
  IF v_actor IS NOT NULL THEN
    SELECT role INTO v_my_role FROM public.club_members WHERE club_id = p_club_id AND user_id = v_actor AND status = 'active';
    IF v_club.owner_user_id = v_actor THEN
      v_my_role := 'owner';
    END IF;
  END IF;

  -- Chỉ Owner hoặc Treasurer mới thấy số dư quỹ
  IF v_my_role IN ('owner', 'treasurer') THEN
    SELECT balance_vnd INTO v_balance FROM public.club_balance WHERE club_id = p_club_id;
    v_balance := COALESCE(v_balance, 0);
  END IF;

  SELECT count(*)::int INTO v_member_count
  FROM public.club_members
  WHERE club_id = p_club_id AND status = 'active';

  RETURN jsonb_build_object(
    'id', v_club.id,
    'owner_user_id', v_club.owner_user_id,
    'name', v_club.name,
    'description', v_club.description,
    'visibility', v_club.visibility,
    'status', v_club.status,
    'my_role', v_my_role,
    'balance_vnd', v_balance,
    'member_count', v_member_count,
    'created_at', v_club.created_at
  );
END;
$$;

-- ============================================================================
-- 9. RPC ĐỌC DANH SÁCH THÀNH VIÊN THEO QUYỀN (LIST_CLUB_MEMBERS)
-- ============================================================================
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
      cm.created_at ASC
  ), '[]'::jsonb)
  INTO v_members
  FROM public.club_members cm
  LEFT JOIN public.member_contacts mc ON mc.member_id = cm.id
  WHERE cm.club_id = p_club_id AND cm.status = 'active'
  LIMIT p_limit OFFSET p_offset;

  RETURN v_members;
END;
$$;

-- ============================================================================
-- 10. RPC ĐỌC TÀI KHOẢN NGÂN HÀNG CLB (GET_CLUB_BANK_ACCOUNT)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.get_club_bank_account(p_club_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_acc RECORD;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem thông tin ngân hàng' USING ERRCODE = '42501';
  END IF;

  -- Chỉ Owner và Treasurer được xem tài khoản ngân hàng CLB
  IF NOT (public.is_club_owner(p_club_id, v_actor) OR public.has_club_role(p_club_id, v_actor, ARRAY['treasurer'])) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ chủ nhiệm hoặc thủ quỹ mới có quyền xem tài khoản ngân hàng CLB' USING ERRCODE = '42501';
  END IF;

  SELECT * INTO v_acc
  FROM public.club_bank_accounts
  WHERE club_id = p_club_id AND status = 'active';

  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  RETURN jsonb_build_object(
    'id', v_acc.id,
    'club_id', v_acc.club_id,
    'bank_code', v_acc.bank_code,
    'account_number', v_acc.account_number,
    'account_name', v_acc.account_name,
    'status', v_acc.status
  );
END;
$$;

-- ============================================================================
-- 11. RPC CẬP NHẬT THÔNG TIN LIÊN HỆ THÀNH VIÊN (UPDATE_CLUB_MEMBER_CONTACT)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.update_club_member_contact(
  p_club_id UUID,
  p_member_id UUID,
  p_display_name TEXT DEFAULT NULL,
  p_phone_number TEXT DEFAULT NULL,
  p_contact_note TEXT DEFAULT NULL,
  p_request_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_member RECORD;
  v_payload_hash TEXT;
  v_is_replay BOOLEAN;
  v_saved_result JSONB;
  v_res JSONB;
  v_phone TEXT;
  v_note TEXT;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để cập nhật thông tin thành viên' USING ERRCODE = '42501';
  END IF;

  -- 1. Quyền: chỉ Owner hoặc Host active của CLB
  IF NOT (public.is_club_owner(p_club_id, v_actor) OR public.has_club_role(p_club_id, v_actor, ARRAY['owner', 'host'])) THEN
    RAISE EXCEPTION 'FORBIDDEN: Chỉ chủ nhiệm hoặc quản lý mới có quyền sửa thông tin liên hệ thành viên' USING ERRCODE = '42501';
  END IF;

  -- 2. Kiểm tra member tồn tại đúng trong CLB
  SELECT * INTO v_member FROM public.club_members WHERE id = p_member_id AND club_id = p_club_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Thành viên không tồn tại trong CLB này' USING ERRCODE = 'P0002';
  END IF;

  -- 3. Idempotency
  IF p_request_id IS NOT NULL THEN
    v_payload_hash := md5(p_club_id::text || ':' || p_member_id::text || ':' || COALESCE(p_display_name, '') || ':' || COALESCE(p_phone_number, '') || ':' || COALESCE(p_contact_note, ''));
    SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
    FROM public.check_idempotency('update_club_member_contact', p_request_id, v_payload_hash);
    IF v_is_replay THEN
      RETURN v_saved_result;
    END IF;
  END IF;

  -- 4. Cập nhật display_name nếu được cung cấp
  IF p_display_name IS NOT NULL THEN
    p_display_name := trim(p_display_name);
    IF length(p_display_name) = 0 THEN
      RAISE EXCEPTION 'INVALID_ARGUMENT: Tên hiển thị không được để rỗng' USING ERRCODE = '22023';
    END IF;
    UPDATE public.club_members
    SET display_name = p_display_name, updated_at = now()
    WHERE id = p_member_id
    RETURNING * INTO v_member;
  END IF;

  -- 5. Cập nhật member_contacts
  v_phone := NULLIF(trim(p_phone_number), '');
  v_note := NULLIF(trim(p_contact_note), '');

  INSERT INTO public.member_contacts (member_id, phone_number, contact_note, updated_at)
  VALUES (p_member_id, v_phone, v_note, now())
  ON CONFLICT (member_id) DO UPDATE
  SET
    phone_number = CASE WHEN p_phone_number IS NOT NULL THEN v_phone ELSE member_contacts.phone_number END,
    contact_note = CASE WHEN p_contact_note IS NOT NULL THEN v_note ELSE member_contacts.contact_note END,
    updated_at = now();

  PERFORM public.log_audit_event(
    p_club_id, NULL, 'club_member', p_member_id, 'UPDATE_MEMBER_CONTACT',
    NULL,
    jsonb_build_object('display_name', v_member.display_name, 'has_phone', v_phone IS NOT NULL),
    'Cập nhật thông tin liên hệ thành viên CLB', p_request_id
  );

  -- Đọc contact sau update
  SELECT phone_number, contact_note INTO v_phone, v_note FROM public.member_contacts WHERE member_id = p_member_id;

  v_res := jsonb_build_object(
    'id', v_member.id,
    'club_id', v_member.club_id,
    'user_id', v_member.user_id,
    'display_name', v_member.display_name,
    'role', v_member.role,
    'status', v_member.status,
    'phone_number', v_phone,
    'contact_note', v_note,
    'updated_at', now()
  );

  IF p_request_id IS NOT NULL THEN
    PERFORM public.record_idempotency('update_club_member_contact', p_request_id, v_payload_hash, v_res);
  END IF;

  RETURN v_res;
END;
$$;

-- ============================================================================
-- 12. RPC ĐỌC TÀI KHOẢN NGÂN HÀNG CỦA HOST (GET_HOST_BANK_ACCOUNT)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.get_host_bank_account()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_acc RECORD;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem tài khoản ngân hàng' USING ERRCODE = '42501';
  END IF;

  SELECT * INTO v_acc
  FROM public.host_bank_accounts
  WHERE user_id = v_actor AND status = 'active';

  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  RETURN jsonb_build_object(
    'id', v_acc.id,
    'user_id', v_acc.user_id,
    'bank_code', v_acc.bank_code,
    'account_number', v_acc.account_number,
    'account_name', v_acc.account_name,
    'status', v_acc.status
  );
END;
$$;

-- ============================================================================
-- 13. RPC ĐỌC DANH SÁCH CLB CỦA TÔI (LIST_MY_CLUBS)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.list_my_clubs()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_clubs JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RETURN '[]'::jsonb;
  END IF;

  SELECT COALESCE(jsonb_agg(
    jsonb_build_object(
      'id', c.id,
      'owner_user_id', c.owner_user_id,
      'name', c.name,
      'description', c.description,
      'visibility', c.visibility,
      'status', c.status,
      'my_role', CASE WHEN c.owner_user_id = v_actor THEN 'owner' ELSE cm.role END,
      'created_at', c.created_at
    ) ORDER BY c.created_at DESC
  ), '[]'::jsonb)
  INTO v_clubs
  FROM public.clubs c
  LEFT JOIN public.club_members cm ON cm.club_id = c.id AND cm.user_id = v_actor AND cm.status = 'active'
  WHERE c.status = 'active'
    AND (c.owner_user_id = v_actor OR cm.id IS NOT NULL);

  RETURN v_clubs;
END;
$$;

-- ============================================================================
-- 14. CẤP QUYỀN THỰC THI (GRANTS)
-- ============================================================================
GRANT EXECUTE ON FUNCTION public.create_club(TEXT, TEXT, TEXT, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.update_club(UUID, TEXT, TEXT, TEXT, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.add_club_member(UUID, TEXT, TEXT, TEXT, UUID, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.update_club_member_contact(UUID, UUID, TEXT, TEXT, TEXT, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.set_club_member_role(UUID, UUID, TEXT, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.set_club_bank_account(UUID, TEXT, TEXT, TEXT, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.set_host_bank_account(TEXT, TEXT, TEXT, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_club_detail(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.list_club_members(UUID, INT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_club_bank_account(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_host_bank_account() TO authenticated;
GRANT EXECUTE ON FUNCTION public.list_my_clubs() TO authenticated;

