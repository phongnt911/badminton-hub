import subprocess, json, datetime, sys, os
from pathlib import Path

# Đảm bảo mã hóa đầu ra utf-8 trên Windows
sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
CONTAINER = os.environ.get('BH02_TEST_CONTAINER', 'bh02-test-postgres')

stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
CLEAN = 'bh03_clean_' + stamp
LEGACY = 'bh03_legacy_' + stamp

def sql(db, query):
    return subprocess.run(
        ['docker', 'exec', '-i', CONTAINER, 'psql', '-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-v', 'VERBOSITY=verbose', '-U', 'postgres', '-d', db],
        input=query, text=True, encoding='utf-8', capture_output=True
    )

def must(db, query, label):
    r = sql(db, query)
    if r.returncode != 0:
        raise RuntimeError(f"{label}: {r.stderr.strip()}")
    return r.stdout.strip()

def uid(n):
    return '00000000-0000-0000-0000-' + f'{n:012d}'

def q(n):
    return "'" + uid(n) + "'"

def as_user_sql(actor_uid, query, role='authenticated', commit=True):
    action = 'COMMIT;' if commit else 'ROLLBACK;'
    sub = uid(actor_uid) if isinstance(actor_uid, int) else (actor_uid or '')
    return f"""BEGIN;
SET LOCAL ROLE {role};
DO $$ BEGIN PERFORM set_config('request.jwt.claim.sub', '{sub}', true); END $$;
{query}
{action}
"""

def user_exec(db, actor_uid, query, role='authenticated', commit=True):
    full_sql = as_user_sql(actor_uid, query, role=role, commit=commit)
    return sql(db, full_sql)

def must_user(db, actor_uid, query, label, role='authenticated', commit=True):
    r = user_exec(db, actor_uid, query, role=role, commit=commit)
    if r.returncode != 0:
        raise RuntimeError(f"{label}: {r.stderr.strip()}")
    # Lọc bỏ dòng trống
    lines = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else ''

print(f"Khởi tạo cơ sở dữ liệu kiểm thử BH-03: {CLEAN} và {LEGACY}...")

# 1. Setup Auth stub
setup_auth = """
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users(id uuid primary key, email text, raw_user_meta_data jsonb);
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$ 
  SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid 
$$;
GRANT USAGE ON SCHEMA auth TO anon, authenticated;
GRANT EXECUTE ON FUNCTION auth.uid() TO anon, authenticated;
"""

# 2. Schema v1.1 và BH-03 migration
migration_v1_1 = (REPO_ROOT / 'supabase/migrations/20261015051808_init_schema_v1_1.sql').read_text(encoding='utf-8')
migration_bh03 = (REPO_ROOT / 'supabase/migrations/20261015133247_bh03_clubs_and_members.sql').read_text(encoding='utf-8')

legacy_schema = """
CREATE TABLE public.venues(id uuid primary key default gen_random_uuid(), name text not null, address text not null, area text not null, phone_number text, court_count int default 4, price_range text, image_url text, map_url text, created_at timestamptz default now());
CREATE TABLE public.sessions(id uuid primary key default gen_random_uuid(), venue_name text not null, play_date date not null, start_time time not null, end_time time not null, max_slots int default 6, joined_count int default 1, estimated_cost int default 40000, level_requirement text, contact_phone text, status text default 'open', created_at timestamptz default now());
CREATE TABLE public.session_players(id uuid primary key default gen_random_uuid(), session_id uuid references public.sessions(id) on delete cascade, player_name text not null, phone_number text, has_arrived bool default false, has_paid bool default false, created_at timestamptz default now());
"""

for db in [CLEAN, LEGACY]:
    must('postgres', f'CREATE DATABASE {db};', f'Tạo DB {db}')
    must(db, setup_auth, 'Setup auth stub')

must(LEGACY, legacy_schema, 'Tạo legacy schema cho LEGACY DB')
must(LEGACY, f"INSERT INTO auth.users(id, email) VALUES ({q(90)}, 'preexisting@example.invalid');", 'Tài khoản Auth tồn tại từ trước')

for db in [CLEAN, LEGACY]:
    must(db, migration_v1_1, f'Chạy migration 20261015051808_init_schema_v1_1 trên {db}')
    must(db, migration_bh03, f'Chạy migration 20261015133247_bh03_clubs_and_members trên {db}')

print("Chuỗi migrations đã áp dụng thành công trên cả CLEAN và LEGACY.")

# Định nghĩa các Test Case
results = []

def run_test(name, fn):
    try:
        fn()
        results.append({'name': name, 'status': 'PASS'})
        print(f"PASS: {name}")
    except Exception as e:
        results.append({'name': name, 'status': 'FAIL', 'error': str(e)})
        print(f"FAIL: {name} -> {e}")

# Seed người dùng test
def seed_users(db):
    stmts = []
    for n in range(1, 10):
        stmts.append(f"INSERT INTO auth.users(id, email, raw_user_meta_data) VALUES ({q(n)}, 'user{n}@test.invalid', '{{\"display_name\": \"User {n}\"}}') ON CONFLICT (id) DO NOTHING;")
        stmts.append(f"INSERT INTO public.profiles(id, display_name) VALUES ({q(n)}, 'User {n}') ON CONFLICT (id) DO NOTHING;")
    must(db, "\n".join(stmts), "Seed users")

for db in [CLEAN, LEGACY]:
    seed_users(db)

TARGET_DB = CLEAN

# Lưu trữ ID CLB dùng chung trong test suite
SHARED = {'club_id': None}

# ============================================================================
# NHÓM 1: ATOMIC & IDEMPOTENT (create_club)
# ============================================================================
def test_create_club_atomic():
    req_id = '11111111-0000-0000-0000-000000000001'
    query = f"SELECT public.create_club('CLB Thần Tốc', 'CLB thể thao', 'private', '{req_id}'::uuid);"
    raw_res = must_user(TARGET_DB, 1, query, "create_club call")
    res = json.loads(raw_res)
    SHARED['club_id'] = res['id']
    club_id = SHARED['club_id']
    
    # Kiểm tra club
    chk_club = must(TARGET_DB, f"SELECT owner_user_id FROM public.clubs WHERE id = '{club_id}';", "chk_club")
    assert chk_club == uid(1), f"Owner must be {uid(1)}, got {chk_club}"
    
    # Kiểm tra club_members có đúng 1 owner
    chk_member = must(TARGET_DB, f"SELECT role FROM public.club_members WHERE club_id = '{club_id}' AND user_id = '{uid(1)}';", "chk_member")
    assert chk_member == 'owner', f"Role must be owner, got {chk_member}"
    
    # Kiểm tra audit event
    chk_audit = must(TARGET_DB, f"SELECT count(*) FROM public.audit_events WHERE club_id = '{club_id}' AND action = 'CREATE_CLUB';", "chk_audit")
    assert int(chk_audit) == 1, f"Audit event must be logged, count={chk_audit}"

run_test("Tạo CLB và Owner nguyên tử (create_club)", test_create_club_atomic)

def test_create_club_idempotency_replay():
    req_id = '11111111-0000-0000-0000-000000000001'
    query = f"SELECT public.create_club('CLB Thần Tốc', 'CLB thể thao', 'private', '{req_id}'::uuid);"
    raw_res = must_user(TARGET_DB, 1, query, "create_club replay")
    res = json.loads(raw_res)
    assert res['id'] == SHARED['club_id']
    
    # Kiểm tra số lượng CLB tên này vẫn chỉ là 1
    chk_count = must(TARGET_DB, f"SELECT count(*) FROM public.clubs WHERE name = 'CLB Thần Tốc';", "chk_count")
    assert int(chk_count) == 1, f"Count must still be 1, got {chk_count}"

run_test("Idempotency replay không tạo CLB kép", test_create_club_idempotency_replay)

def test_create_club_idempotency_conflict():
    req_id = '11111111-0000-0000-0000-000000000001'
    query = f"SELECT public.create_club('Tên Khác Khác', 'CLB thể thao', 'private', '{req_id}'::uuid);"
    r = user_exec(TARGET_DB, 1, query)
    assert r.returncode != 0 and 'IDEMPOTENCY_CONFLICT' in r.stderr, f"Must fail with conflict, got {r.stderr}"

run_test("Idempotency khác payload bị chặn (IDEMPOTENCY_CONFLICT)", test_create_club_idempotency_conflict)

def test_create_club_unauthenticated():
    query = f"SELECT public.create_club('CLB Anon', 'desc', 'private', gen_random_uuid());"
    r = user_exec(TARGET_DB, None, query, role='anon')
    assert r.returncode != 0 and 'UNAUTHENTICATED' in r.stderr, f"Anon must fail, got: {r.stderr}"

run_test("Anon bị chặn tạo CLB (UNAUTHENTICATED)", test_create_club_unauthenticated)

# ============================================================================
# NHÓM 2: CẬP NHẬT CLB (update_club)
# ============================================================================
def test_update_club_owner_only():
    club_id = SHARED['club_id']
    query = f"SELECT public.update_club('{club_id}'::uuid, 'CLB Thần Tốc Đổi Tên', 'Mô tả mới', 'public');"
    raw_res = must_user(TARGET_DB, 1, query, "update_club call")
    res = json.loads(raw_res)
    assert res['name'] == 'CLB Thần Tốc Đổi Tên'
    assert res['visibility'] == 'public'

run_test("Owner cập nhật thông tin CLB thành công", test_update_club_owner_only)

def test_update_club_outsider_forbidden():
    club_id = SHARED['club_id']
    # User 3 là người ngoài
    query = f"SELECT public.update_club('{club_id}'::uuid, 'Hack Name', 'Hack Desc', 'private');"
    r = user_exec(TARGET_DB, 3, query)
    assert r.returncode != 0 and 'FORBIDDEN' in r.stderr, f"Outsider must be forbidden, got: {r.stderr}"

run_test("Người ngoài bị chặn sửa CLB (FORBIDDEN)", test_update_club_outsider_forbidden)

# ============================================================================
# NHÓM 3: THÊM THÀNH VIÊN VÀ OFFLINE IDENTITY (add_club_member)
# ============================================================================
def test_add_offline_member():
    club_id = SHARED['club_id']
    req_id = '22222222-0000-0000-0000-000000000001'
    query = f"""
    SELECT public.add_club_member(
      '{club_id}'::uuid, 
      'Chú Bảy Offline', 
      '0912345678', 
      'Khách đánh vãng lai', 
      NULL, 
      '{req_id}'::uuid
    );
    """
    raw_res = must_user(TARGET_DB, 1, query, "add offline member")
    res = json.loads(raw_res)
    SHARED['offline_member_id'] = res['id']
    assert res['user_id'] is None, "Offline member must have user_id = NULL"
    assert res['role'] == 'member', "Default role must be member"
    
    # Kiểm tra contact lưu vào member_contacts
    contact = must(TARGET_DB, f"SELECT phone_number FROM public.member_contacts WHERE member_id = '{res['id']}';", "chk contact")
    assert contact == '0912345678', f"Phone must be 0912345678, got {contact}"

run_test("Thêm thành viên offline không tài khoản với liên hệ riêng tư", test_add_offline_member)

def test_add_member_fake_user_rejected():
    club_id = SHARED['club_id']
    fake_uid = '99999999-9999-9999-9999-999999999999'
    query = f"SELECT public.add_club_member('{club_id}'::uuid, 'Fake User', NULL, NULL, '{fake_uid}'::uuid);"
    r = user_exec(TARGET_DB, 1, query)
    assert r.returncode != 0 and 'NOT_FOUND' in r.stderr, f"Must reject nonexistent user_id, got: {r.stderr}"

run_test("Từ chối thêm thành viên với user_id không tồn tại", test_add_member_fake_user_rejected)

def test_add_member_by_host():
    club_id = SHARED['club_id']
    # Gán User 5 làm host
    must(TARGET_DB, f"""
    INSERT INTO public.club_members(club_id, user_id, display_name, role, status)
    VALUES ('{club_id}', '{uid(5)}', 'Host Club', 'host', 'active')
    ON CONFLICT DO NOTHING;
    """, "seed host member")
    
    # User 5 thêm thành viên mới
    query = f"SELECT public.add_club_member('{club_id}'::uuid, 'Thành viên do host thêm', '0988776655', NULL, NULL);"
    raw_res = must_user(TARGET_DB, 5, query, "host adds member")
    res = json.loads(raw_res)
    assert res['role'] == 'member'

run_test("Host của CLB thêm thành viên thành công", test_add_member_by_host)

def test_add_member_by_regular_member_forbidden():
    club_id = SHARED['club_id']
    # Gán User 2 làm member thường
    must(TARGET_DB, f"""
    INSERT INTO public.club_members(club_id, user_id, display_name, role, status)
    VALUES ('{club_id}', '{uid(2)}', 'Member Regular', 'member', 'active')
    ON CONFLICT DO NOTHING;
    """, "seed regular member")
    
    query = f"SELECT public.add_club_member('{club_id}'::uuid, 'Người Bạn', NULL, NULL, NULL);"
    r = user_exec(TARGET_DB, 2, query)
    assert r.returncode != 0 and 'FORBIDDEN' in r.stderr, f"Regular member must be forbidden, got: {r.stderr}"

run_test("Thành viên thường bị chặn thêm người (FORBIDDEN)", test_add_member_by_regular_member_forbidden)

# ============================================================================
# NHÓM 4: SỬA LIÊN HỆ THÀNH VIÊN (update_club_member_contact)
# ============================================================================
def test_update_member_contact_by_host():
    club_id = SHARED['club_id']
    member_id = SHARED['offline_member_id']
    
    query = f"""
    SELECT public.update_club_member_contact(
      '{club_id}'::uuid, 
      '{member_id}'::uuid, 
      'Chú Bảy (Sửa Tên)', 
      '0999999999', 
      'Ghi chú cập nhật'
    );
    """
    raw_res = must_user(TARGET_DB, 5, query, "update contact by host")
    res = json.loads(raw_res)
    assert res['display_name'] == 'Chú Bảy (Sửa Tên)'
    assert res['phone_number'] == '0999999999'

run_test("Host cập nhật SĐT và ghi chú của thành viên thành công", test_update_member_contact_by_host)

def test_update_member_contact_by_treasurer_forbidden():
    club_id = SHARED['club_id']
    member_id = SHARED['offline_member_id']
    # User 4 là Treasurer
    must(TARGET_DB, f"""
    INSERT INTO public.club_members(club_id, user_id, display_name, role, status)
    VALUES ('{club_id}', '{uid(4)}', 'Thủ Quỹ', 'treasurer', 'active')
    ON CONFLICT DO NOTHING;
    """, "seed treasurer")
    
    query = f"SELECT public.update_club_member_contact('{club_id}'::uuid, '{member_id}'::uuid, 'Hack Name', NULL, NULL);"
    r = user_exec(TARGET_DB, 4, query)
    assert r.returncode != 0 and 'FORBIDDEN' in r.stderr, f"Treasurer must be forbidden to update contact, got: {r.stderr}"

run_test("Thủ quỹ bị chặn cập nhật liên hệ thành viên (FORBIDDEN)", test_update_member_contact_by_treasurer_forbidden)

# ============================================================================
# NHÓM 5: PHÂN QUYỀN VÀ BẢO VỆ ROLE (set_club_member_role)
# ============================================================================
def test_set_role_for_offline_member_blocked():
    club_id = SHARED['club_id']
    offline_id = SHARED['offline_member_id']
    
    # Owner cố gán role host cho offline member
    query = f"SELECT public.set_club_member_role('{club_id}'::uuid, '{offline_id}'::uuid, 'host');"
    r = user_exec(TARGET_DB, 1, query)
    assert r.returncode != 0 and 'INVALID_ARGUMENT' in r.stderr, f"Must reject granting management role to offline member, got: {r.stderr}"

run_test("Chặn cấp vai trò quản lý (host/treasurer) cho người chưa có tài khoản", test_set_role_for_offline_member_blocked)

def test_set_role_for_linked_member_success():
    club_id = SHARED['club_id']
    member_id = must(TARGET_DB, f"SELECT id FROM public.club_members WHERE club_id = '{club_id}' AND user_id = '{uid(2)}';", "get_member")
    
    query = f"SELECT public.set_club_member_role('{club_id}'::uuid, '{member_id}'::uuid, 'treasurer');"
    raw_res = must_user(TARGET_DB, 1, query, "set role treasurer")
    res = json.loads(raw_res)
    assert res['role'] == 'treasurer'

run_test("Owner phân quyền thành công cho thành viên đã liên kết tài khoản", test_set_role_for_linked_member_success)

def test_set_role_cannot_demote_owner():
    club_id = SHARED['club_id']
    owner_member_id = must(TARGET_DB, f"SELECT id FROM public.club_members WHERE club_id = '{club_id}' AND role = 'owner';", "get_owner_member")
    
    query = f"SELECT public.set_club_member_role('{club_id}'::uuid, '{owner_member_id}'::uuid, 'member');"
    r = user_exec(TARGET_DB, 1, query)
    assert r.returncode != 0 and 'FORBIDDEN' in r.stderr, f"Must forbid modifying owner role, got: {r.stderr}"

run_test("Chặn sửa hoặc hạ quyền Owner qua endpoint role thông thường", test_set_role_cannot_demote_owner)

def test_set_role_self_escalation_blocked():
    club_id = SHARED['club_id']
    member_id = must(TARGET_DB, f"SELECT id FROM public.club_members WHERE club_id = '{club_id}' AND user_id = '{uid(5)}';", "get_member")
    
    query = f"SELECT public.set_club_member_role('{club_id}'::uuid, '{member_id}'::uuid, 'owner');"
    r = user_exec(TARGET_DB, 5, query)
    assert r.returncode != 0, f"Host self escalation must fail, got: {r.stderr}"

run_test("Chặn thành viên tự nâng quyền hoặc sửa role người khác", test_set_role_self_escalation_blocked)

# ============================================================================
# NHÓM 6: QUẢN LÝ TÀI KHOẢN NGÂN HÀNG (set_club_bank_account)
# ============================================================================
def test_set_club_bank_account_owner_only():
    club_id = SHARED['club_id']
    
    query = f"SELECT public.set_club_bank_account('{club_id}'::uuid, 'VCB', '0071000123456', 'NGUYEN VAN CHU NHIEM');"
    raw_res = must_user(TARGET_DB, 1, query, "set club bank")
    res = json.loads(raw_res)
    assert res['account_number'] == '0071000123456', "Must preserve leading zeros"
    assert res['status'] == 'active'

run_test("Owner cấu hình ngân hàng CLB giữ nguyên số 0 ở đầu (TEXT)", test_set_club_bank_account_owner_only)

def test_set_club_bank_account_single_active():
    club_id = SHARED['club_id']
    
    # Cấu hình tài khoản thứ 2
    query = f"SELECT public.set_club_bank_account('{club_id}'::uuid, 'TCB', '190333444555', 'NGUYEN VAN CHU NHIEM');"
    must_user(TARGET_DB, 1, query, "set second club bank")
    
    # Kiểm tra chỉ có đúng 1 tài khoản active
    active_count = must(TARGET_DB, f"SELECT count(*) FROM public.club_bank_accounts WHERE club_id = '{club_id}' AND status = 'active';", "chk active bank")
    assert int(active_count) == 1, f"Must have exactly 1 active bank account, got {active_count}"
    
    total_count = must(TARGET_DB, f"SELECT count(*) FROM public.club_bank_accounts WHERE club_id = '{club_id}';", "chk total bank")
    assert int(total_count) == 2, f"Total accounts must be 2 (history preserved), got {total_count}"

run_test("Cập nhật bank vô hiệu hóa tài khoản cũ, giữ đúng 1 active", test_set_club_bank_account_single_active)

def test_set_club_bank_account_treasurer_forbidden():
    club_id = SHARED['club_id']
    
    # User 4 là Treasurer cố đổi tài khoản nhận tiền
    query = f"SELECT public.set_club_bank_account('{club_id}'::uuid, 'MB', '999999999', 'THU QUY TU Y');"
    r = user_exec(TARGET_DB, 4, query)
    assert r.returncode != 0 and 'FORBIDDEN' in r.stderr, f"Treasurer must be forbidden to set club bank, got: {r.stderr}"

run_test("Thủ quỹ bị chặn cấu hình tài khoản ngân hàng CLB (FORBIDDEN)", test_set_club_bank_account_treasurer_forbidden)

def test_set_host_bank_account_self():
    query = f"SELECT public.set_host_bank_account('ACB', '0123456789', 'HOST CA NHAN');"
    raw_res = must_user(TARGET_DB, 1, query, "set host bank")
    res = json.loads(raw_res)
    assert res['account_number'] == '0123456789'
    assert res['user_id'] == uid(1)

run_test("Host tự cấu hình tài khoản cá nhân của chính mình", test_set_host_bank_account_self)

# ============================================================================
# NHÓM 7: PRIVACY VÀ QUYỀN ĐỌC (get_club_detail, list_club_members, get_club_bank_account)
# ============================================================================
def test_get_club_detail_privacy():
    club_id = SHARED['club_id']
    # Seed quỹ 5,000,000 vào ledger đúng schema: direction, amount_vnd, title, source_type, created_by
    must(TARGET_DB, f"""
    INSERT INTO public.club_transactions(club_id, direction, amount_vnd, title, source_type, created_by)
    VALUES ('{club_id}', 'income', 5000000, 'Thu tiền quỹ', 'manual', '{uid(1)}')
    ON CONFLICT DO NOTHING;
    """, "seed ledger")
    
    # 1. Owner đọc -> Thấy balance
    res_owner = json.loads(must_user(TARGET_DB, 1, f"SELECT public.get_club_detail('{club_id}'::uuid);", "owner detail"))
    assert res_owner['balance_vnd'] == 5000000, f"Owner must see balance, got {res_owner['balance_vnd']}"
    
    # 2. Treasurer (User 4) đọc -> Thấy balance
    res_treasurer = json.loads(must_user(TARGET_DB, 4, f"SELECT public.get_club_detail('{club_id}'::uuid);", "treasurer detail"))
    assert res_treasurer['balance_vnd'] == 5000000, f"Treasurer must see balance, got {res_treasurer['balance_vnd']}"
    
    # 3. Regular member (User 7) -> KHÔNG thấy balance (balance_vnd IS NULL)
    must(TARGET_DB, f"""
    INSERT INTO public.club_members(club_id, user_id, display_name, role, status)
    VALUES ('{club_id}', '{uid(7)}', 'Member Khong Quy', 'member', 'active')
    ON CONFLICT DO NOTHING;
    """, "seed member 7")
    res_member = json.loads(must_user(TARGET_DB, 7, f"SELECT public.get_club_detail('{club_id}'::uuid);", "member detail"))
    assert res_member['balance_vnd'] is None, f"Regular member must NOT see balance, got {res_member['balance_vnd']}"

run_test("Số dư quỹ chỉ hiển thị cho Chủ nhiệm và Thủ quỹ, ẩn với thành viên", test_get_club_detail_privacy)

def test_list_club_members_contact_privacy():
    club_id = SHARED['club_id']
    m7_id = must(TARGET_DB, f"SELECT id FROM public.club_members WHERE club_id = '{club_id}' AND user_id = '{uid(7)}';", "get_m7")
    must(TARGET_DB, f"""
    INSERT INTO public.member_contacts(member_id, phone_number, contact_note)
    VALUES ('{m7_id}', '0977112233', 'Riêng tư của 7')
    ON CONFLICT (member_id) DO UPDATE SET phone_number = '0977112233';
    """, "seed contact 7")
    
    # 1. Host (User 5) đọc danh sách -> Thấy phone của User 7
    members_host = json.loads(must_user(TARGET_DB, 5, f"SELECT public.list_club_members('{club_id}'::uuid);", "host list members"))
    m7_in_host = next(m for m in members_host if m['id'] == m7_id)
    assert m7_in_host['phone_number'] == '0977112233', f"Host must see phone, got {m7_in_host['phone_number']}"
    
    # 2. Treasurer (User 4) đọc danh sách -> KHÔNG thấy phone của User 7
    members_treasurer = json.loads(must_user(TARGET_DB, 4, f"SELECT public.list_club_members('{club_id}'::uuid);", "treasurer list members"))
    m7_in_treasurer = next(m for m in members_treasurer if m['id'] == m7_id)
    assert m7_in_treasurer['phone_number'] is None, f"Treasurer must NOT see phone, got {m7_in_treasurer['phone_number']}"
    
    # 3. Thành viên khác (User 2) đọc danh sách -> KHÔNG thấy phone của User 7
    members_other = json.loads(must_user(TARGET_DB, 2, f"SELECT public.list_club_members('{club_id}'::uuid);", "other member list members"))
    m7_in_other = next(m for m in members_other if m['id'] == m7_id)
    assert m7_in_other['phone_number'] is None, f"Other member must NOT see phone, got {m7_in_other['phone_number']}"
    
    # 4. Chính User 7 đọc danh sách -> Thấy phone của CHÍNH MÌNH
    members_self = json.loads(must_user(TARGET_DB, 7, f"SELECT public.list_club_members('{club_id}'::uuid);", "self list members"))
    m7_in_self = next(m for m in members_self if m['id'] == m7_id)
    assert m7_in_self['phone_number'] == '0977112233', f"User must see own phone, got {m7_in_self['phone_number']}"

run_test("SĐT thành viên chỉ hiển thị cho Owner/Host và chính chủ, ẩn với Thủ quỹ và member khác", test_list_club_members_contact_privacy)

def test_get_club_bank_account_privacy():
    club_id = SHARED['club_id']
    
    # 1. Owner đọc -> Thấy bank
    res_owner = json.loads(must_user(TARGET_DB, 1, f"SELECT public.get_club_bank_account('{club_id}'::uuid);", "owner get bank"))
    assert res_owner['bank_code'] == 'TCB'
    
    # 2. Treasurer đọc -> Thấy bank
    res_treasurer = json.loads(must_user(TARGET_DB, 4, f"SELECT public.get_club_bank_account('{club_id}'::uuid);", "treasurer get bank"))
    assert res_treasurer['bank_code'] == 'TCB'
    
    # 3. Regular member đọc -> Bị FORBIDDEN
    r = user_exec(TARGET_DB, 7, f"SELECT public.get_club_bank_account('{club_id}'::uuid);")
    assert r.returncode != 0 and 'FORBIDDEN' in r.stderr, f"Regular member must be forbidden, got: {r.stderr}"

run_test("Tài khoản ngân hàng CLB chỉ Chủ nhiệm và Thủ quỹ xem được", test_get_club_bank_account_privacy)

def test_list_my_clubs():
    # User 1 là owner của CLB Thần Tốc
    clubs1 = json.loads(must_user(TARGET_DB, 1, "SELECT public.list_my_clubs();", "list my clubs user 1"))
    assert len(clubs1) >= 1
    assert any(c['my_role'] == 'owner' for c in clubs1)
    
    # User 7 là member
    clubs7 = json.loads(must_user(TARGET_DB, 7, "SELECT public.list_my_clubs();", "list my clubs user 7"))
    assert len(clubs7) >= 1
    assert any(c['my_role'] == 'member' for c in clubs7)
    
    # User 9 chưa vào CLB nào
    clubs9 = json.loads(must_user(TARGET_DB, 9, "SELECT public.list_my_clubs();", "list my clubs user 9"))
    assert len(clubs9) == 0

run_test("Danh sách CLB của tôi (list_my_clubs) hiển thị đúng theo vai trò", test_list_my_clubs)

# ============================================================================
# TỔNG KẾT
# ============================================================================
passed = sum(1 for r in results if r['status'] == 'PASS')
failed = sum(1 for r in results if r['status'] == 'FAIL')
print(f"\n==========================================")
print(f"KẾT QUẢ KIỂM THỬ BH-03: TỔNG {len(results)} | PASS {passed} | FAIL {failed}")
print(f"==========================================")

report_file = ROOT / f"bh03_test_results_{stamp}.json"
report_file.write_text(json.dumps({
    'timestamp': stamp,
    'total': len(results),
    'passed': passed,
    'failed': failed,
    'tests': results
}, indent=2, ensure_ascii=False), encoding='utf-8')

if failed > 0:
    sys.exit(1)
