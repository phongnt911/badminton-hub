-- Forward fix BH-03: consent, request identity, canonical payloads.
-- Không sửa migration BH-03 đã chia sẻ hoặc tạo account linking giả.
CREATE OR REPLACE FUNCTION public.check_idempotency(
  p_operation TEXT, p_request_id UUID, p_payload_hash TEXT,
  OUT is_replay BOOLEAN, OUT saved_result JSONB
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_rec RECORD;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION 'UNAUTHENTICATED' USING ERRCODE='42501';
  END IF;
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE='22023';
  END IF;
  -- Khóa theo actor/operation/request trước mọi side effect. Hash collision chỉ serialize thêm.
  PERFORM pg_advisory_xact_lock(hashtextextended(
    jsonb_build_array(v_actor,p_operation,p_request_id)::text, 0));
  SELECT payload_hash,result INTO v_rec FROM public.operation_requests
  WHERE actor_user_id=v_actor AND operation=p_operation AND request_id=p_request_id;
  is_replay := FOUND;
  saved_result := NULL;
  IF is_replay THEN
    IF v_rec.payload_hash IS DISTINCT FROM p_payload_hash THEN
      RAISE EXCEPTION 'IDEMPOTENCY_CONFLICT: request_id reused with different payload' USING ERRCODE='23505';
    END IF;
    saved_result := v_rec.result;
  END IF;
END;
$$;
REVOKE EXECUTE ON FUNCTION public.check_idempotency(TEXT,UUID,TEXT) FROM PUBLIC,anon,authenticated;


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
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE='22023';
  END IF;
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
    v_payload_hash := md5(jsonb_build_array(p_name, p_description, p_visibility)::text);
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
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE='22023';
  END IF;
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
    v_payload_hash := md5(jsonb_build_array(p_club_id, p_name, p_description, p_visibility)::text);
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
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE='22023';
  END IF;
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
    v_payload_hash := md5(jsonb_build_array(p_club_id, p_display_name, p_phone_number, p_contact_note, p_user_id)::text);
    SELECT is_replay, saved_result INTO v_is_replay, v_saved_result
    FROM public.check_idempotency('add_club_member', p_request_id, v_payload_hash);
    IF v_is_replay THEN
      RETURN v_saved_result;
    END IF;
  END IF;

  -- Linking chưa có acceptance: chỉ tạo thành viên chưa liên kết account.
  IF p_user_id IS NOT NULL THEN
    RAISE EXCEPTION 'FORBIDDEN: Account linking requires verified acceptance' USING ERRCODE='42501';
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
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE='22023';
  END IF;
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
    v_payload_hash := md5(jsonb_build_array(p_club_id, p_member_id, p_role)::text);
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
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE='22023';
  END IF;
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
    v_payload_hash := md5(jsonb_build_array(p_club_id, p_bank_code, p_account_number, p_account_name)::text);
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
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE='22023';
  END IF;
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
    v_payload_hash := md5(jsonb_build_array(p_bank_code, p_account_number, p_account_name)::text);
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
  IF p_request_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_INPUT: request_id is required' USING ERRCODE='22023';
  END IF;
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
    v_payload_hash := md5(jsonb_build_array(p_club_id, p_member_id, p_display_name, p_phone_number, p_contact_note)::text);
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

REVOKE EXECUTE ON FUNCTION public.create_club(TEXT,TEXT,TEXT,UUID) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.create_club(TEXT,TEXT,TEXT,UUID) TO authenticated;

REVOKE EXECUTE ON FUNCTION public.update_club(UUID,TEXT,TEXT,TEXT,UUID) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.update_club(UUID,TEXT,TEXT,TEXT,UUID) TO authenticated;

REVOKE EXECUTE ON FUNCTION public.add_club_member(UUID,TEXT,TEXT,TEXT,UUID,UUID) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.add_club_member(UUID,TEXT,TEXT,TEXT,UUID,UUID) TO authenticated;

REVOKE EXECUTE ON FUNCTION public.set_club_member_role(UUID,UUID,TEXT,UUID) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.set_club_member_role(UUID,UUID,TEXT,UUID) TO authenticated;

REVOKE EXECUTE ON FUNCTION public.set_club_bank_account(UUID,TEXT,TEXT,TEXT,UUID) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.set_club_bank_account(UUID,TEXT,TEXT,TEXT,UUID) TO authenticated;

REVOKE EXECUTE ON FUNCTION public.set_host_bank_account(TEXT,TEXT,TEXT,UUID) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.set_host_bank_account(TEXT,TEXT,TEXT,UUID) TO authenticated;

REVOKE EXECUTE ON FUNCTION public.update_club_member_contact(UUID,UUID,TEXT,TEXT,TEXT,UUID) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.update_club_member_contact(UUID,UUID,TEXT,TEXT,TEXT,UUID) TO authenticated;
