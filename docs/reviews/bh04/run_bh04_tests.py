import subprocess, json, datetime, sys, os, uuid, hashlib
from pathlib import Path

# Đảm bảo mã hóa đầu ra utf-8 trên Windows
sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
CONTAINER = os.environ.get('BH02_TEST_CONTAINER', 'bh02-review-postgres')

stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
CLEAN = 'bh04_clean_' + stamp
LEGACY = 'bh04_legacy_' + stamp


def sql(db, query, role_env=None):
    return subprocess.run(
        ['docker', 'exec', '-i', CONTAINER, 'psql', '-X', '-q', '-A', '-t',
         '-v', 'ON_ERROR_STOP=1', '-U', 'postgres', '-d', db],
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


def iso(days=1, hours=0):
    return (datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=days, hours=hours)).isoformat()


def newreq():
    return str(uuid.uuid4())


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
    return sql(db, as_user_sql(actor_uid, query, role=role, commit=commit))


def anon_exec(db, query):
    return user_exec(db, None, query, role='anon')


def must_user(db, actor_uid, query, label, role='authenticated', commit=True):
    r = user_exec(db, actor_uid, query, role=role, commit=commit)
    if r.returncode != 0:
        raise RuntimeError(f"{label}: {r.stderr.strip()}")
    lines = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else ''


def expect_error(result, *needles):
    return result.returncode != 0 and any(n in result.stderr for n in needles)


print(f"Khởi tạo cơ sở dữ liệu kiểm thử BH-04: {CLEAN} và {LEGACY}...")

setup_auth = """
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users(id uuid primary key, email text, raw_user_meta_data jsonb);
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;
GRANT USAGE ON SCHEMA auth TO anon, authenticated;
GRANT EXECUTE ON FUNCTION auth.uid() TO anon, authenticated;
"""

migration_v1_1 = (REPO_ROOT / 'supabase/migrations/20261015051808_init_schema_v1_1.sql').read_text(encoding='utf-8')
migration_after = '\n'.join(
    p.read_text(encoding='utf-8')
    for p in sorted((REPO_ROOT / 'supabase/migrations').glob('*.sql'))
    if p.name > '20261015051808_init_schema_v1_1.sql'
)

legacy_schema = """
CREATE TABLE public.venues(id uuid primary key default gen_random_uuid(), name text not null, address text not null, area text not null, phone_number text, court_count int default 4, price_range text, image_url text, map_url text, created_at timestamptz default now());
CREATE TABLE public.sessions(id uuid primary key default gen_random_uuid(), venue_name text not null, play_date date not null, start_time time not null, end_time time not null, max_slots int default 6, joined_count int default 1, estimated_cost int default 40000, level_requirement text, contact_phone text, status text default 'open', created_at timestamptz default now());
CREATE TABLE public.session_players(id uuid primary key default gen_random_uuid(), session_id uuid references public.sessions(id) on delete cascade, player_name text not null, phone_number text, has_arrived bool default false, has_paid bool default false, created_at timestamptz default now());
"""

for db in [CLEAN, LEGACY]:
    must('postgres', f'CREATE DATABASE {db};', f'Tạo DB {db}')
    must(db, setup_auth, 'Setup auth stub')

must(LEGACY, legacy_schema, 'Tạo legacy schema cho LEGACY DB')

for db in [CLEAN, LEGACY]:
    must(db, migration_v1_1, 'Chạy migration init v1.1')
    must(db, migration_after, 'Chạy các migration forward (BH-03, pre-BH04, BH-04)')

print("Chuỗi migrations đã áp dụng thành công trên cả CLEAN và LEGACY.")

results = []


def run_test(name, fn):
    try:
        fn()
        results.append({'name': name, 'status': 'PASS'})
        print(f"PASS: {name}")
    except Exception as e:
        results.append({'name': name, 'status': 'FAIL', 'error': str(e)})
        print(f"FAIL: {name} -> {e}")


SHARED = {}


def run_suite(db):
    global SHARED
    SHARED = {'db': db}

    # --- Seed: users (trigger tạo profiles), venues, club + members ---
    user_ids = list(range(1, 13))
    stmts = []
    for n in user_ids:
        stmts.append(
            f"INSERT INTO auth.users(id, email, raw_user_meta_data) VALUES ({q(n)}, 'u{n}@example.invalid', "
            f"jsonb_build_object('display_name', 'User {n}')) ON CONFLICT (id) DO NOTHING;"
        )
    must(db, '\n'.join(stmts), 'Seed auth users')

    venue_area = must(db, """
      INSERT INTO public.venues(name, address, area, phone_number, court_count, status)
      VALUES ('Sân Nha Trang A', '12 Trần Phú', 'Nha Trang', '0900000001', 6, 'active')
      RETURNING id;
    """, 'Seed venue A')
    venue_far = must(db, """
      INSERT INTO public.venues(name, address, area, phone_number, court_count, status)
      VALUES ('Sân Cam Ranh', '1 Nguyễn Tất Thành', 'Cam Ranh', '0900000002', 4, 'active')
      RETURNING id;
    """, 'Seed venue B')
    SHARED['venue'] = venue_area
    SHARED['venue_far'] = venue_far

    club_id = must(db, f"""
      INSERT INTO public.clubs(owner_user_id, name, visibility, status)
      VALUES ({q(1)}, 'CLB Thần Tốc', 'public', 'active') RETURNING id;
    """, 'Seed club')
    must(db, f"""
      INSERT INTO public.club_members(club_id, user_id, display_name, role, status, joined_at) VALUES
        ('{club_id}', {q(1)}, 'Owner', 'owner', 'active', now()),
        ('{club_id}', {q(2)}, 'Host', 'host', 'active', now()),
        ('{club_id}', {q(3)}, 'Treasurer', 'treasurer', 'active', now()),
        ('{club_id}', {q(4)}, 'Member', 'member', 'active', now());
    """, 'Seed club members')
    SHARED['club'] = club_id

    venue = SHARED['venue']
    club = SHARED['club']

    # ------------------------------------------------------------------ #
    def t_anon_cannot_create():
        r = anon_exec(db, f"""SELECT public.create_session('{venue}'::uuid, 'Anon', '{iso(1)}', '{iso(1, 2)}',
          8, 2, NULL, NULL, NULL, 'unlisted', 'host_approval', 'split_actual', NULL, NULL, NULL, NULL, '{newreq()}');""")
        assert expect_error(r, 'permission denied', 'UNAUTHENTICATED'), f"anon phải bị chặn: {r.stderr}"
    run_test("anon không gọi được create_session (ACL)", t_anon_cannot_create)

    def t_requires_request_id():
        r = user_exec(db, 1, f"""SELECT public.create_session('{venue}'::uuid, 'NoKey', '{iso(1)}', '{iso(1, 2)}',
          8, 2, NULL, NULL, NULL, 'unlisted', 'host_approval', 'split_actual');""")
        assert expect_error(r, 'INVALID_INPUT'), f"thiếu request_id phải bị chặn: {r.stderr}"
    run_test("create_session bắt buộc request_id", t_requires_request_id)

    def t_reject_past():
        r = user_exec(db, 1, f"""SELECT public.create_session('{venue}'::uuid, 'Past', '{iso(-1)}', '{iso(-1, 2)}',
          8, 2, NULL, NULL, NULL, 'unlisted', 'host_approval', 'split_actual', NULL, NULL, NULL, NULL, '{newreq()}');""")
        assert expect_error(r, 'INVALID_INPUT'), f"buổi quá khứ phải bị chặn: {r.stderr}"
    run_test("create_session từ chối thời gian bắt đầu trong quá khứ", t_reject_past)

    def t_reject_bad_range():
        r = user_exec(db, 1, f"""SELECT public.create_session('{venue}'::uuid, 'Bad', '{iso(1, 3)}', '{iso(1, 2)}',
          8, 2, NULL, NULL, NULL, 'unlisted', 'host_approval', 'split_actual', NULL, NULL, NULL, NULL, '{newreq()}');""")
        assert expect_error(r, 'INVALID_INPUT'), f"ends<=starts phải bị chặn: {r.stderr}"
    run_test("create_session từ chối ends_at <= starts_at", t_reject_bad_range)

    def t_reject_fixed_missing_fee():
        r = user_exec(db, 1, f"""SELECT public.create_session('{venue}'::uuid, 'Fixed', '{iso(1)}', '{iso(1, 2)}',
          8, 2, NULL, NULL, NULL, 'unlisted', 'host_approval', 'fixed', NULL, NULL, NULL, NULL, '{newreq()}');""")
        assert expect_error(r, 'INVALID_INPUT'), f"fixed thiếu phí phải bị chặn: {r.stderr}"
    run_test("create_session fee_mode=fixed yêu cầu cả hai mức phí", t_reject_fixed_missing_fee)

    def t_club_requires_role():
        r = user_exec(db, 4, f"""SELECT public.create_session('{venue}'::uuid, 'MemberCreate', '{iso(1)}', '{iso(1, 2)}',
          8, 2, '{club}'::uuid, NULL, NULL, 'unlisted', 'host_approval', 'split_actual', NULL, NULL, NULL, NULL, '{newreq()}');""")
        assert expect_error(r, 'FORBIDDEN'), f"member thường phải bị chặn: {r.stderr}"
    run_test("create_session gắn CLB yêu cầu owner/host", t_club_requires_role)

    def t_create_ok_and_idempotent():
        req = newreq()
        sql_stmt = f"""SELECT public.create_session('{venue}'::uuid, 'Buổi nháp', '{iso(1)}', '{iso(1, 2)}',
          8, 2, '{club}'::uuid, 'Mô tả', 'Trung bình', 'unlisted', 'host_approval', 'split_actual', NULL, NULL, '{iso(1, -2)}', '{iso(1, -4)}', '{req}');"""
        first = json.loads(must_user(db, 1, sql_stmt, 'create session'))
        assert first['lifecycle'] == 'draft', first
        assert first['version'] == 1, first
        assert first['is_host'] is True and first['can_manage'] is True, first
        second = json.loads(must_user(db, 1, sql_stmt, 'create session replay'))
        assert second['id'] == first['id'], f"replay phải trả cùng id: {first['id']} vs {second['id']}"
        SHARED['draft_id'] = first['id']
    run_test("create_session tạo draft + replay cùng request_id trả cùng bản ghi", t_create_ok_and_idempotent)

    def t_idempotency_conflict():
        req = newreq()
        base = f"""SELECT public.create_session('{venue}'::uuid, 'X1', '{iso(2)}', '{iso(2, 2)}',
          8, 2, NULL, NULL, NULL, 'unlisted', 'host_approval', 'split_actual', NULL, NULL, NULL, NULL, '{req}');"""
        must_user(db, 1, base, 'create for conflict')
        changed = base.replace("'X1'", "'X2'")
        r = user_exec(db, 1, changed)
        assert expect_error(r, 'IDEMPOTENCY_CONFLICT'), f"payload khác cùng key phải conflict: {r.stderr}"
    run_test("create_session payload khác cùng request_id trả IDEMPOTENCY_CONFLICT", t_idempotency_conflict)

    def t_draft_hidden_from_anon():
        draft = SHARED['draft_id']
        r = anon_exec(db, f"SELECT public.get_session_public_detail('{draft}'::uuid);")
        assert expect_error(r, 'UNAUTHENTICATED', 'FORBIDDEN'), f"draft phải ẩn với anon: {r.stderr}"
    run_test("get_session_public_detail: draft ẩn với anon", t_draft_hidden_from_anon)

    def t_draft_visible_to_host():
        draft = SHARED['draft_id']
        res = json.loads(must_user(db, 1, f"SELECT public.get_session_public_detail('{draft}'::uuid);", 'host draft'))
        assert res['lifecycle'] == 'draft'
        assert res['can_manage'] is True
        assert 'receiver_snapshot' not in res and 'host_user_id' not in res, "whitelist không được lộ field nhạy cảm"
    run_test("get_session_public_detail: host đọc được draft, whitelist sạch", t_draft_visible_to_host)

    def t_publish():
        draft = SHARED['draft_id']
        key = newreq()
        call = f"SELECT public.set_session_lifecycle('{draft}'::uuid, 'publish', '{key}');"
        res = json.loads(must_user(db, 1, call, 'publish'))
        assert json.loads(must_user(db, 1, call, 'publish replay')) == res
        assert res['lifecycle'] == 'published', res
        assert res['version'] == 2, res
        r = user_exec(db, 1, f"SELECT public.set_session_lifecycle('{draft}'::uuid, 'publish', '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), f"publish lần hai phải bị chặn: {r.stderr}"
    run_test("set_session_lifecycle: draft->published, publish lại bị INVALID_STATE", t_publish)

    def t_public_visible_anon():
        draft = SHARED['draft_id']
        # Buổi này visibility 'unlisted' -> vẫn đọc theo link nhưng không xuất hiện trong list public.
        res = json.loads(must_user(db, None, f"SELECT public.get_session_public_detail('{draft}'::uuid);", 'anon unlisted', role='anon'))
        assert res['lifecycle'] == 'published'
        assert 'confirmed_count' in res
    run_test("get_session_public_detail: unlisted đã publish đọc được bằng link (anon)", t_public_visible_anon)

    def t_private_requires_membership():
        req = newreq()
        priv = json.loads(must_user(db, 1, f"""SELECT public.create_session('{venue}'::uuid, 'Buổi nội bộ', '{iso(2)}', '{iso(2, 2)}',
          8, 2, '{club}'::uuid, NULL, NULL, 'private', 'host_approval', 'split_actual', NULL, NULL, NULL, NULL, '{req}');""", 'private create'))
        pid = priv['id']
        must(db, f"UPDATE public.sessions SET lifecycle='published' WHERE id='{pid}';", 'force publish private')
        # user 4 là member CLB -> đọc được; user 10 không liên quan -> FORBIDDEN; anon -> UNAUTHENTICATED
        ok = json.loads(must_user(db, 4, f"SELECT public.get_session_public_detail('{pid}'::uuid);", 'member private'))
        assert ok['id'] == pid
        r_far = user_exec(db, 10, f"SELECT public.get_session_public_detail('{pid}'::uuid);")
        assert expect_error(r_far, 'FORBIDDEN'), f"người ngoài phải bị chặn: {r_far.stderr}"
        r_anon = anon_exec(db, f"SELECT public.get_session_public_detail('{pid}'::uuid);")
        assert expect_error(r_anon, 'UNAUTHENTICATED'), f"anon phải bị chặn: {r_anon.stderr}"
    run_test("get_session_public_detail: private chỉ thành viên/host đọc được", t_private_requires_membership)

    def t_update_version_conflict():
        draft = SHARED['draft_id']
        cur = json.loads(must_user(db, 1, f"SELECT public.get_session_public_detail('{draft}'::uuid);", 'get cur'))
        v = cur['version']
        upd = f"""SELECT public.update_session('{draft}'::uuid, {v}, '{venue}'::uuid, 'Buổi đổi tên', '{iso(1)}', '{iso(1, 2)}',
          10, 3, NULL, NULL, 'unlisted', 'host_approval', 'split_actual', NULL, NULL, NULL, NULL, '{newreq()}');"""
        res = json.loads(must_user(db, 1, upd, 'update ok'))
        assert res['version'] == v + 1, res
        assert res['capacity'] == 10, res
        # Dùng lại version cũ -> conflict
        r = user_exec(db, 1, upd.replace(f", {v},", f", {v},"))
        # new request_id: cùng payload nhưng version cũ
        again = upd.replace('{newreq()}', newreq()) if False else None
        r2 = user_exec(db, 1, f"""SELECT public.update_session('{draft}'::uuid, {v}, '{venue}'::uuid, 'Buổi đổi tên', '{iso(1)}', '{iso(1, 2)}',
          10, 3, NULL, NULL, 'unlisted', 'host_approval', 'split_actual', NULL, NULL, NULL, NULL, '{newreq()}');""")
        assert expect_error(r2, 'VERSION_CONFLICT'), f"version cũ phải conflict: {r2.stderr}"
    run_test("update_session: tăng version và từ chối version cũ (VERSION_CONFLICT)", t_update_version_conflict)

    def t_update_forbidden_for_non_manager():
        draft = SHARED['draft_id']
        r = user_exec(db, 10, f"""SELECT public.update_session('{draft}'::uuid, 99, '{venue}'::uuid, 'Hack', '{iso(1)}', '{iso(1, 2)}',
          10, 3, NULL, NULL, 'unlisted', 'host_approval', 'split_actual', NULL, NULL, NULL, NULL, '{newreq()}');""")
        assert expect_error(r, 'FORBIDDEN'), f"người ngoài phải bị chặn: {r.stderr}"
    run_test("update_session chặn người không có quyền quản lý", t_update_forbidden_for_non_manager)

    def t_update_blocked_when_in_progress():
        draft = SHARED['draft_id']
        must(db, f"UPDATE public.sessions SET lifecycle='in_progress' WHERE id='{draft}';", 'force in_progress')
        cur = json.loads(must_user(db, 1, f"SELECT public.get_session_public_detail('{draft}'::uuid);", 'get inprogress'))
        r = user_exec(db, 1, f"""SELECT public.update_session('{draft}'::uuid, {cur['version']}, '{venue}'::uuid, 'X', '{iso(1)}', '{iso(1, 2)}',
          10, 3, NULL, NULL, 'unlisted', 'host_approval', 'split_actual', NULL, NULL, NULL, NULL, '{newreq()}');""")
        assert expect_error(r, 'INVALID_STATE'), f"buổi đang chơi không sửa được: {r.stderr}"
        must(db, f"UPDATE public.sessions SET lifecycle='published' WHERE id='{draft}';", 'restore published')
    run_test("update_session chặn sửa khi buổi đang diễn ra (INVALID_STATE)", t_update_blocked_when_in_progress)

    def t_duplicate_does_not_copy_people_money():
        draft = SHARED['draft_id']
        must(db, f"""
          INSERT INTO public.session_players(session_id, user_id, display_name, registration_status, created_by, requested_at)
          VALUES ('{draft}', {q(5)}, 'Player 5', 'confirmed', {q(1)}, now());
        """, 'seed player on source')
        res = json.loads(must_user(db, 1, f"SELECT public.duplicate_session('{draft}'::uuid, '{iso(3)}', '{iso(3, 2)}', '{newreq()}');", 'duplicate'))
        new_id = res['id']
        assert new_id != draft
        assert res['lifecycle'] == 'draft'
        players = must(db, f"SELECT count(*) FROM public.session_players WHERE session_id='{new_id}';", 'count players')
        assert players == '0', f"bản sao không được chứa người chơi: {players}"
        charges = must(db, f"""SELECT count(*) FROM public.session_charges sc
          JOIN public.charge_revisions cr ON cr.id = sc.revision_id WHERE cr.session_id = '{new_id}';""", 'count charges')
        assert charges == '0', f"bản sao không được chứa khoản thu: {charges}"
        SHARED['dup_id'] = new_id
    run_test("duplicate_session sao chép cấu hình nhưng không sao chép người/tiền", t_duplicate_does_not_copy_people_money)

    def t_list_my_sessions_and_pagination():
        # Host riêng (user 11) với đúng 3 buổi để kiểm phân trang
        for i in range(3):
            must_user(db, 11, f"""SELECT public.create_session('{venue}'::uuid, 'P{i}', '{iso(1 + i)}', '{iso(1 + i, 2)}',
              6, 1, NULL, NULL, NULL, 'unlisted', 'host_approval', 'split_actual', NULL, NULL, NULL, NULL, '{newreq()}');""", f'seed paged {i}')
        page0 = json.loads(must_user(db, 11, "SELECT public.list_my_sessions(2, 0);", 'page0'))
        assert len(page0) == 2, f"limit phải được tôn trọng: {len(page0)}"
        page1 = json.loads(must_user(db, 11, "SELECT public.list_my_sessions(2, 2);", 'page1'))
        assert isinstance(page1, list) and len(page1) == 1, f"offset>0 phải trả phần còn lại, không NULL: {page1}"
        assert page0[0]['id'] != page1[0]['id']
        # user1 thấy buổi của CLB mình (không thấy buổi của user 11)
        mine = json.loads(must_user(db, 1, "SELECT public.list_my_sessions();", 'user1 list'))
        ids = {row['id'] for row in mine}
        assert SHARED['draft_id'] in ids
        assert not any(row['title'].startswith('P') for row in mine), "không được thấy buổi của người khác"
    run_test("list_my_sessions: đúng chủ sở hữu, phân trang offset>0 trả phần còn lại", t_list_my_sessions_and_pagination)

    def t_list_public_sessions_filters():
        # Sân Nha Trang: buổi public còn chỗ
        pub_id = json.loads(must_user(db, 1, f"""SELECT public.create_session('{venue}'::uuid, 'Public NT', '{iso(4)}', '{iso(4, 2)}',
          8, 2, NULL, NULL, NULL, 'public', 'auto_confirm', 'fixed', 50000, 70000, NULL, NULL, '{newreq()}');""", 'pub create'))['id']
        must_user(db, 1, f"SELECT public.set_session_lifecycle('{pub_id}'::uuid, 'publish', '{newreq()}');", 'pub publish')
        # Sân Cam Ranh: buổi public đã đầy (capacity 1, 1 confirmed)
        full_id = json.loads(must_user(db, 1, f"""SELECT public.create_session('{SHARED['venue_far']}'::uuid, 'Full CR', '{iso(5)}', '{iso(5, 2)}',
          1, 1, NULL, NULL, NULL, 'public', 'host_approval', 'split_actual', NULL, NULL, NULL, NULL, '{newreq()}');""", 'full create'))['id']
        must(db, f"INSERT INTO public.session_players(session_id, user_id, display_name, registration_status, created_by) VALUES ('{full_id}', {q(6)}, 'P6', 'confirmed', {q(1)});", 'seed full player')
        must_user(db, 1, f"SELECT public.set_session_lifecycle('{full_id}'::uuid, 'publish', '{newreq()}');", 'full publish')

        all_pub = json.loads(must_user(db, None, "SELECT public.list_public_sessions();", 'anon public', role='anon'))
        ids = {r['id'] for r in all_pub}
        assert pub_id in ids and full_id in ids
        assert SHARED['draft_id'] not in ids, "unlisted/không publish không được lọt vào list public"

        by_area = json.loads(must_user(db, None, "SELECT public.list_public_sessions('Nha Trang');", 'area filter', role='anon'))
        assert all(r['venue_area'] == 'Nha Trang' for r in by_area)
        assert all(r['id'] != full_id for r in by_area)

        avail = json.loads(must_user(db, None, "SELECT public.list_public_sessions(NULL, NULL, NULL, NULL, TRUE);", 'available filter', role='anon'))
        assert all(r['confirmed_count'] < r['capacity'] for r in avail)
        assert all(r['id'] != full_id for r in avail)
    run_test("list_public_sessions: whitelist công khai, lọc khu vực và còn chỗ", t_list_public_sessions_filters)

    def t_list_session_players_acl_and_pagination():
        draft = SHARED['draft_id']
        for i in range(3):
            must(db, f"INSERT INTO public.session_players(session_id, user_id, display_name, registration_status, created_by) VALUES ('{draft}', {q(7 + i)}, 'Reg {i}', 'pending', {q(1)});", f'seed reg {i}')
        # Host (user 1) đọc được toàn bộ
        all_rows = json.loads(must_user(db, 1, f"SELECT public.list_session_players('{draft}'::uuid, 100, 0);", 'host players'))
        assert len(all_rows) >= 4
        # Phân trang
        p0 = json.loads(must_user(db, 1, f"SELECT public.list_session_players('{draft}'::uuid, 2, 0);", 'page0'))
        p1 = json.loads(must_user(db, 1, f"SELECT public.list_session_players('{draft}'::uuid, 2, 2);", 'page1'))
        assert len(p0) == 2 and isinstance(p1, list) and len(p1) >= 1
        # Thủ quỹ CLB (user 3) không có quyền quản lý buổi -> FORBIDDEN (F7)
        r_fin = user_exec(db, 3, f"SELECT public.list_session_players('{draft}'::uuid);")
        assert expect_error(r_fin, 'FORBIDDEN'), f"thủ quỹ không được đọc danh sách: {r_fin.stderr}"
        # Thành viên thường (user 4) -> FORBIDDEN
        r_mem = user_exec(db, 4, f"SELECT public.list_session_players('{draft}'::uuid);")
        assert expect_error(r_mem, 'FORBIDDEN'), f"member không được đọc danh sách: {r_mem.stderr}"
    run_test("list_session_players: chỉ host/quản lý, phân trang, chặn thủ quỹ/member", t_list_session_players_acl_and_pagination)

    def t_cancel_replay():
        req = newreq()
        created = json.loads(must_user(db, 1, f"SELECT create_session('{venue}', 'Cancel replay', '{iso(3)}', '{iso(3,2)}',8,2,p_request_id => '{newreq()}');", 'create cancel fixture'))
        call = f"SELECT set_session_lifecycle('{created['id']}', 'cancel', '{req}');"
        first = json.loads(must_user(db, 1, call, 'cancel'))
        second = json.loads(must_user(db, 1, call, 'cancel replay'))
        assert first == second and second['lifecycle'] == 'cancelled'
    run_test("cancel retry replays same result", t_cancel_replay)

    def t_no_client_counter_write():
        # Bảng sessions không có cột joined_count trên DB clean (không còn bộ đếm do client ghi)
        r = sql(db, "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='sessions' AND column_name='joined_count';")
        count = r.stdout.strip()
        if db == CLEAN:
            assert count == '0', "DB clean không được có cột bộ đếm joined_count"
    run_test("DB clean không còn cột bộ đếm joined_count (không ghi bộ đếm từ client)", t_no_client_counter_write)


run_suite(CLEAN)
run_suite(LEGACY)

passed = sum(1 for r in results if r['status'] == 'PASS')
failed = sum(1 for r in results if r['status'] == 'FAIL')
print("\n==========================================")
print(f"KẾT QUẢ KIỂM THỬ BH-04: TỔNG {len(results)} | PASS {passed} | FAIL {failed}")
print("==========================================")

report_file = ROOT / f"bh04_test_results_{stamp}.json"
report_file.write_text(json.dumps({
    'timestamp': stamp,
    'tested_commit': subprocess.check_output(['git', '-C', str(REPO_ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
    'worktree_dirty': bool(subprocess.check_output(['git', '-C', str(REPO_ROOT), 'status', '--porcelain'], text=True).strip()),
    'migration_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((REPO_ROOT / 'supabase/migrations').glob('*.sql'))},
    'total': len(results),
    'passed': passed,
    'failed': failed,
    'tests': results,
}, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Results file: {report_file}")

if failed > 0:
    sys.exit(1)
