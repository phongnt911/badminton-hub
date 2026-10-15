import subprocess, json, datetime, sys, os, uuid, hashlib
from pathlib import Path

# Đảm bảo mã hóa đầu ra utf-8 trên Windows
sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
CONTAINER = os.environ.get('BH02_TEST_CONTAINER', 'bh02-test-postgres')

stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
CLEAN = 'bh05_clean_' + stamp
LEGACY = 'bh05_legacy_' + stamp


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


def iso(days=1, hours=0, minutes=0):
    return (datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=days, hours=hours, minutes=minutes)).isoformat()


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


def tx_script(actor_uid, body, role='authenticated'):
    sub = uid(actor_uid) if isinstance(actor_uid, int) else (actor_uid or '')
    return f"""BEGIN;
SET LOCAL ROLE {role};
SELECT set_config('request.jwt.claim.sub', '{sub}', true);
{body}
COMMIT;
"""


def run_concurrent(db, scripts):
    procs = [
        subprocess.Popen(
            ['docker', 'exec', CONTAINER, 'psql', '-X', '-q', '-A', '-t',
             '-v', 'ON_ERROR_STOP=1', '-U', 'postgres', '-d', db, '-c', s],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8')
        for s in scripts
    ]
    return [p.communicate() for p in procs]


print(f"Khởi tạo cơ sở dữ liệu kiểm thử BH-05: {CLEAN} và {LEGACY}...")

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
    must(db, migration_after, 'Chạy các migration forward (BH-03, pre-BH04, BH-04, BH-05)')

print("Chuỗi migrations đã áp dụng thành công trên cả CLEAN và LEGACY.")

results = []
SHARED = {}


def run_test(name, fn):
    try:
        fn()
        results.append({'name': name, 'status': 'PASS'})
        print(f"PASS: {name}")
    except Exception as e:
        results.append({'name': name, 'status': 'FAIL', 'error': str(e)})
        print(f"FAIL: {name} -> {e}")


def run_suite(db):
    global SHARED
    SHARED = {'db': db}

    # --- Seed: users (trigger tạo profiles), venue, club + members ---
    stmts = []
    for n in range(1, 13):
        stmts.append(
            f"INSERT INTO auth.users(id, email, raw_user_meta_data) VALUES ({q(n)}, 'u{n}@example.invalid', "
            f"jsonb_build_object('display_name', 'User {n}')) ON CONFLICT (id) DO NOTHING;"
        )
    must(db, '\n'.join(stmts), 'Seed auth users')

    venue = must(db, """
      INSERT INTO public.venues(name, address, area, phone_number, court_count, status)
      VALUES ('Sân Nha Trang A', '12 Trần Phú', 'Nha Trang', '0900000001', 6, 'active')
      RETURNING id;
    """, 'Seed venue')
    SHARED['venue'] = venue

    club = must(db, f"""
      INSERT INTO public.clubs(owner_user_id, name, visibility, status)
      VALUES ({q(1)}, 'CLB Thần Tốc', 'public', 'active') RETURNING id;
    """, 'Seed club')
    must(db, f"""
      INSERT INTO public.club_members(club_id, user_id, display_name, role, status, joined_at) VALUES
        ('{club}', {q(1)}, 'Owner', 'owner', 'active', now()),
        ('{club}', {q(2)}, 'Cohost', 'host', 'active', now()),
        ('{club}', {q(3)}, 'Treasurer', 'treasurer', 'active', now()),
        ('{club}', {q(4)}, 'Member', 'member', 'active', now());
    """, 'Seed club members')
    SHARED['club'] = club
    SHARED['member4_id'] = must(db, f"SELECT id FROM public.club_members WHERE club_id='{club}' AND user_id={q(4)};", 'member4 id')

    def create_and_publish(actor, title, *, capacity=8, courts=2, vis='unlisted',
                           approval='auto_confirm', fee_mode='split_actual',
                           member_fee=None, guest_fee=None, reg_deadline=None,
                           cancel_deadline=None, start_days=1, club_link=None):
        v = SHARED['venue']
        club_sql = f"'{club_link}'::uuid" if club_link else 'NULL'
        mf = str(member_fee) if member_fee is not None else 'NULL'
        gf = str(guest_fee) if guest_fee is not None else 'NULL'
        rd = f"'{reg_deadline}'" if reg_deadline else 'NULL'
        cd = f"'{cancel_deadline}'" if cancel_deadline else 'NULL'
        stmt = (f"SELECT public.create_session(p_venue_id=>'{v}'::uuid, p_title=>'{title}', "
                f"p_starts_at=>'{iso(start_days)}', p_ends_at=>'{iso(start_days, 2)}', "
                f"p_capacity=>{capacity}, p_court_count=>{courts}, p_club_id=>{club_sql}, "
                f"p_visibility=>'{vis}', p_approval_mode=>'{approval}', p_fee_mode=>'{fee_mode}', "
                f"p_member_fee_vnd=>{mf}, p_guest_fee_vnd=>{gf}, "
                f"p_registration_deadline=>{rd}, p_cancellation_deadline=>{cd}, p_request_id=>'{newreq()}');")
        sid = json.loads(must_user(db, actor, stmt, f'create {title}'))['id']
        must_user(db, actor, f"SELECT public.set_session_lifecycle('{sid}'::uuid, 'publish', '{newreq()}');", f'publish {title}')
        return sid

    def join(actor, sid, contact=None, req=None):
        contact_sql = f"'{contact}'" if contact else 'NULL'
        key = req or newreq()
        return json.loads(must_user(db, actor,
            f"SELECT public.request_join_session('{sid}'::uuid, {contact_sql}, '{key}');", 'join'))

    def finalize_billing(sid, actor=1):
        # Tạo revision 'active' (mô phỏng đã chốt phí) để kiểm gate quyền tài chính.
        must(db, f"""
          INSERT INTO public.charge_revisions(
            session_id, revision_no, source_version, status,
            allocation_total_vnd, fee_mode, finalized_by)
          SELECT '{sid}', 1, s.billing_input_version, 'active', 0, s.fee_mode, {q(actor)}
          FROM public.sessions s WHERE s.id = '{sid}';
        """, 'finalize billing')

    def confirmed_count(sid):
        return int(must(db, f"SELECT count(*) FROM public.session_players WHERE session_id='{sid}' AND registration_status='confirmed';", 'confirmed count'))

    def capacity_of(sid):
        return int(must(db, f"SELECT capacity FROM public.sessions WHERE id='{sid}';", 'capacity'))

    def update_session_sql(sid, version, capacity, title='Cap'):
        return (f"SELECT public.update_session(p_session_id=>'{sid}'::uuid, p_version=>{version}, "
                f"p_venue_id=>'{SHARED['venue']}'::uuid, p_title=>'{title}', "
                f"p_starts_at=>'{iso(1)}', p_ends_at=>'{iso(1, 2)}', p_capacity=>{capacity}, "
                f"p_court_count=>2, p_visibility=>'unlisted', p_approval_mode=>'auto_confirm', "
                f"p_fee_mode=>'split_actual', p_request_id=>'{newreq()}');")

    # ------------------------------------------------------------------ #
    def t_anon_cannot_join():
        sid = create_and_publish(1, 'AnonJoin')
        r = anon_exec(db, f"SELECT public.request_join_session('{sid}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r, 'permission denied', 'UNAUTHENTICATED'), f"anon phải bị chặn: {r.stderr}"
    run_test("anon không gọi được request_join_session (ACL)", t_anon_cannot_join)

    def t_requires_request_id():
        sid = create_and_publish(1, 'NoKey')
        r = user_exec(db, 5, f"SELECT public.request_join_session('{sid}'::uuid, NULL);")
        assert expect_error(r, 'INVALID_INPUT'), f"thiếu request_id phải bị chặn: {r.stderr}"
    run_test("request_join_session bắt buộc request_id", t_requires_request_id)

    def t_pending_no_slot_and_replay():
        sid = create_and_publish(1, 'HA', approval='host_approval', capacity=8)
        req = newreq()
        first = join(5, sid, contact='0900000005', req=req)
        assert first['registration_status'] == 'pending', first
        assert first['confirmed_count'] == 0, 'pending không được chiếm slot'
        replay = join(5, sid, contact='0900000005', req=req)
        assert replay['player_id'] == first['player_id'], 'replay phải trả cùng player_id'
        assert replay['confirmed_count'] == 0
        # contact không lộ qua projection công khai
        detail = json.loads(must_user(db, 5, f"SELECT public.get_session_public_detail('{sid}'::uuid);", 'detail'))
        assert 'phone_number' not in detail['my_registration'], 'projection không được lộ contact'
        assert detail['my_registration']['registration_status'] == 'pending'
        SHARED['ha_session'] = sid
        SHARED['ha_player'] = first['player_id']
    run_test("request_join_session host_approval: pending, không chiếm slot, replay cùng key", t_pending_no_slot_and_replay)

    def t_auto_confirm_and_fixed_fee():
        sid = create_and_publish(1, 'AC', approval='auto_confirm', capacity=2,
                                 fee_mode='fixed', member_fee=50000, guest_fee=70000)
        r = join(6, sid)
        assert r['registration_status'] == 'confirmed', r
        assert r['agreed_fee_vnd'] == 70000, f"guest fixed phải chốt 70000: {r}"
        assert r['confirmed_count'] == 1
        SHARED['ac_session'] = sid
    run_test("request_join_session auto_confirm: confirmed và chốt agreed_fee fixed", t_auto_confirm_and_fixed_fee)

    def t_auto_confirm_full_waitlist():
        sid = create_and_publish(1, 'Full', approval='auto_confirm', capacity=1)
        a = join(7, sid)
        b = join(8, sid)
        assert a['registration_status'] == 'confirmed', a
        assert b['registration_status'] == 'waitlisted', b
        assert b['confirmed_count'] == 1, 'waitlisted không được tăng confirmed'
        SHARED['wl_session'] = sid
        SHARED['wl_player'] = b['player_id']
        SHARED['wl_user'] = 8
    run_test("request_join_session auto_confirm hết chỗ: waitlisted, không vượt sức chứa", t_auto_confirm_full_waitlist)

    def t_duplicate_participant():
        sid = SHARED['ac_session']
        r = user_exec(db, 6, f"SELECT public.request_join_session('{sid}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r, 'DUPLICATE_PARTICIPANT'), f"đăng ký trùng phải bị chặn: {r.stderr}"
    run_test("request_join_session chặn đăng ký trùng (DUPLICATE_PARTICIPANT)", t_duplicate_participant)

    def t_idempotency_conflict():
        sid = create_and_publish(1, 'Conflict', capacity=8)
        req = newreq()
        join(9, sid, contact='0900000009', req=req)
        r = user_exec(db, 9, f"SELECT public.request_join_session('{sid}'::uuid, '0900000999', '{req}');")
        assert expect_error(r, 'IDEMPOTENCY_CONFLICT'), f"cùng key khác payload phải conflict: {r.stderr}"
    run_test("request_join_session cùng request_id khác payload trả IDEMPOTENCY_CONFLICT", t_idempotency_conflict)

    def t_rejoin_after_cancel_keeps_id():
        sid = create_and_publish(1, 'Rejoin', capacity=4)
        first = join(6, sid)
        assert first['registration_status'] == 'confirmed'
        cancel = json.loads(must_user(db, 6,
            f"SELECT public.cancel_registration('{sid}'::uuid, '{first['player_id']}'::uuid, NULL, '{newreq()}');", 'self cancel'))
        assert cancel['registration_status'] == 'cancelled', cancel
        again = join(6, sid)
        assert again['player_id'] == first['player_id'], 'đăng ký lại phải dùng lại ID, không thêm bản ghi'
        assert again['registration_status'] == 'confirmed'
    run_test("đăng ký lại sau cancelled dùng lại player_id (không thêm ID)", t_rejoin_after_cancel_keeps_id)

    def t_join_draft_invalid():
        # Tạo draft không publish rồi thử join
        v = SHARED['venue']
        sid = json.loads(must_user(db, 1,
            f"SELECT public.create_session(p_venue_id=>'{v}'::uuid, p_title=>'Draft', p_starts_at=>'{iso(1)}', "
            f"p_ends_at=>'{iso(1,2)}', p_capacity=>8, p_court_count=>2, p_approval_mode=>'auto_confirm', "
            f"p_request_id=>'{newreq()}');", 'draft'))['id']
        r = user_exec(db, 5, f"SELECT public.request_join_session('{sid}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), f"buổi nháp phải bị chặn: {r.stderr}"
    run_test("request_join_session chặn buổi chưa publish (INVALID_STATE)", t_join_draft_invalid)

    def t_join_deadline_passed():
        sid = create_and_publish(1, 'Deadline', capacity=8, reg_deadline=iso(-1))
        r = user_exec(db, 5, f"SELECT public.request_join_session('{sid}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r, 'DEADLINE_PASSED'), f"quá hạn đăng ký phải bị chặn: {r.stderr}"
    run_test("request_join_session chặn sau registration_deadline (DEADLINE_PASSED)", t_join_deadline_passed)

    def t_private_join_access():
        sid = create_and_publish(1, 'Private', capacity=8, vis='private', club_link=SHARED['club'])
        r_out = user_exec(db, 10, f"SELECT public.request_join_session('{sid}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r_out, 'FORBIDDEN'), f"người ngoài CLB phải bị chặn: {r_out.stderr}"
        ok = join(4, sid)
        assert ok['registration_status'] == 'confirmed', ok
    run_test("request_join_session buổi private: member CLB vào được, người ngoài FORBIDDEN", t_private_join_access)

    def t_decide_confirm_and_waitlisted_blocked():
        sid = SHARED['ha_session']
        player = SHARED['ha_player']
        res = json.loads(must_user(db, 1,
            f"SELECT public.decide_registration('{sid}'::uuid, '{player}'::uuid, 'confirmed', NULL, '{newreq()}');", 'decide'))
        assert res['registration_status'] == 'confirmed', res
        assert res['confirmed_count'] == 1
        # waitlisted không được duyệt thẳng -> confirmed
        wl_sid = SHARED['wl_session']
        r = user_exec(db, 1, f"SELECT public.decide_registration('{wl_sid}'::uuid, '{SHARED['wl_player']}'::uuid, 'confirmed', NULL, '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), f"waitlisted->confirmed phải bị chặn: {r.stderr}"
    run_test("decide_registration duyệt pending và chặn duyệt thẳng waitlisted", t_decide_confirm_and_waitlisted_blocked)

    def t_decide_capacity_full():
        sid = create_and_publish(1, 'DecideFull', approval='host_approval', capacity=1)
        join(5, sid)
        p = json.loads(must_user(db, 1, f"SELECT public.list_session_players('{sid}'::uuid);", 'players'))
        p5 = [x for x in p if x['registration_status'] == 'pending'][0]
        must_user(db, 1, f"SELECT public.decide_registration('{sid}'::uuid, '{p5['id']}'::uuid, 'confirmed', NULL, '{newreq()}');", 'confirm p5')
        join(6, sid)
        p = json.loads(must_user(db, 1, f"SELECT public.list_session_players('{sid}'::uuid);", 'players2'))
        p6 = [x for x in p if x['registration_status'] == 'pending'][0]
        r = user_exec(db, 1, f"SELECT public.decide_registration('{sid}'::uuid, '{p6['id']}'::uuid, 'confirmed', NULL, '{newreq()}');")
        assert expect_error(r, 'CAPACITY_FULL'), f"hết chỗ phải CAPACITY_FULL: {r.stderr}"
    run_test("decide_registration chặn khi hết chỗ (CAPACITY_FULL)", t_decide_capacity_full)

    def t_add_guest_and_member():
        sid = create_and_publish(1, 'AddP', capacity=8, club_link=SHARED['club'])
        guest = json.loads(must_user(db, 1,
            f"SELECT public.add_session_player('{sid}'::uuid, NULL, 'Khách Zalo', '0912000000', FALSE, FALSE, '{newreq()}');", 'add guest'))
        assert guest['registration_status'] == 'confirmed'
        assert guest['participant_type'] == 'guest'
        assert must(db, f"SELECT user_id IS NULL FROM public.session_players WHERE id='{guest['player_id']}';", 'guest user null') == 't'
        # contact riêng, không lộ ở customer list công khai
        contact = must(db, f"SELECT phone_number FROM public.session_player_contacts WHERE player_id='{guest['player_id']}';", 'guest contact')
        assert contact == '0912000000', contact
        member = json.loads(must_user(db, 1,
            f"SELECT public.add_session_player('{sid}'::uuid, '{SHARED['member4_id']}'::uuid, NULL, NULL, FALSE, FALSE, '{newreq()}');", 'add member'))
        assert member['participant_type'] == 'member', member
    run_test("add_session_player thêm guest và member CLB (guest user_id NULL, giữ contact riêng)", t_add_guest_and_member)

    def t_add_member_outside_club():
        sid = create_and_publish(1, 'AddOut', capacity=8, club_link=SHARED['club'])
        other_club = must(db, f"INSERT INTO public.clubs(owner_user_id, name, visibility, status) VALUES ({q(11)}, 'CLB Khác', 'private', 'active') RETURNING id;", 'other club')
        other_member = must(db, f"INSERT INTO public.club_members(club_id, user_id, display_name, role, status) VALUES ('{other_club}', {q(12)}, 'Ngoài', 'member', 'active') RETURNING id;", 'other member')
        r = user_exec(db, 1, f"SELECT public.add_session_player('{sid}'::uuid, '{other_member}'::uuid, NULL, NULL, FALSE, FALSE, '{newreq()}');")
        assert expect_error(r, 'INVALID_INPUT'), f"member ngoài CLB phải bị chặn: {r.stderr}"
    run_test("add_session_player chặn member ngoài CLB (INVALID_INPUT)", t_add_member_outside_club)

    def t_add_capacity_and_waitlist():
        sid = create_and_publish(1, 'AddFull', capacity=1)
        join(7, sid)
        r = user_exec(db, 1, f"SELECT public.add_session_player('{sid}'::uuid, NULL, 'Khách B', NULL, FALSE, FALSE, '{newreq()}');")
        assert expect_error(r, 'CAPACITY_FULL'), f"hết chỗ phải CAPACITY_FULL: {r.stderr}"
        wl = json.loads(must_user(db, 1,
            f"SELECT public.add_session_player('{sid}'::uuid, NULL, 'Khách B', NULL, FALSE, TRUE, '{newreq()}');", 'add waitlist'))
        assert wl['registration_status'] == 'waitlisted', wl
    run_test("add_session_player hết chỗ: CAPACITY_FULL hoặc waitlist khi host chọn", t_add_capacity_and_waitlist)

    def t_add_fee_exempt_requires_finance():
        sid = create_and_publish(1, 'Exempt', capacity=8)
        must(db, f"INSERT INTO public.session_staff(session_id, user_id, role, status) VALUES ('{sid}', {q(2)}, 'cohost', 'active');", 'seed cohost')
        r = user_exec(db, 2, f"SELECT public.add_session_player('{sid}'::uuid, NULL, 'Khách M', NULL, TRUE, FALSE, '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"cohost không finance không được miễn phí: {r.stderr}"
        ok = json.loads(must_user(db, 1,
            f"SELECT public.add_session_player('{sid}'::uuid, NULL, 'Khách M', NULL, TRUE, FALSE, '{newreq()}');", 'host exempt'))
        assert ok['fee_exempt'] is True, ok
    run_test("add_session_player fee_exempt cần quyền tài chính (cohost không finance bị chặn)", t_add_fee_exempt_requires_finance)

    def t_cancel_rules():
        sid = create_and_publish(1, 'Cancel', capacity=8, cancel_deadline=iso(0, 12))
        j = join(6, sid)
        # người khác không có quyền
        r = user_exec(db, 10, f"SELECT public.cancel_registration('{sid}'::uuid, '{j['player_id']}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"người khác phải bị chặn: {r.stderr}"
        # tự hủy trước hạn -> giải phóng slot
        c = json.loads(must_user(db, 6, f"SELECT public.cancel_registration('{sid}'::uuid, '{j['player_id']}'::uuid, NULL, '{newreq()}');", 'cancel'))
        assert c['registration_status'] == 'cancelled' and c['confirmed_count'] == 0, c
        # quá hạn hủy
        sid2 = create_and_publish(1, 'CancelLate', capacity=8, cancel_deadline=iso(-1))
        j2 = join(6, sid2)
        r2 = user_exec(db, 6, f"SELECT public.cancel_registration('{sid2}'::uuid, '{j2['player_id']}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r2, 'DEADLINE_PASSED'), f"quá hạn hủy phải bị chặn: {r2.stderr}"
    run_test("cancel_registration: tự hủy đúng hạn, chặn người khác và quá hạn", t_cancel_rules)

    def t_cancel_present_requires_finance():
        sid = create_and_publish(1, 'Present', capacity=8)
        must(db, f"INSERT INTO public.session_staff(session_id, user_id, role, status) VALUES ('{sid}', {q(2)}, 'cohost', 'active');", 'cohost')
        j = join(6, sid)
        must(db, f"UPDATE public.sessions SET lifecycle='in_progress' WHERE id='{sid}';", 'in_progress')
        must_user(db, 1, f"SELECT public.record_attendance('{sid}'::uuid, '{j['player_id']}'::uuid, 'present', '{newreq()}');", 'present')
        r = user_exec(db, 2, f"SELECT public.cancel_registration('{sid}'::uuid, '{j['player_id']}'::uuid, 'test', '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"hủy người present cần finance: {r.stderr}"
    run_test("cancel_registration người đã present cần quyền tài chính", t_cancel_present_requires_finance)

    def t_attendance_lifecycle_and_replay():
        sid = create_and_publish(1, 'Att', capacity=8)
        j = join(6, sid)
        r = user_exec(db, 1, f"SELECT public.record_attendance('{sid}'::uuid, '{j['player_id']}'::uuid, 'present', '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), f"published không điểm danh được: {r.stderr}"
        must(db, f"UPDATE public.sessions SET lifecycle='in_progress' WHERE id='{sid}';", 'in_progress')
        req = newreq()
        a = json.loads(must_user(db, 1, f"SELECT public.record_attendance('{sid}'::uuid, '{j['player_id']}'::uuid, 'present', '{req}');", 'present'))
        assert a['attendance_status'] == 'present', a
        b = json.loads(must_user(db, 1, f"SELECT public.record_attendance('{sid}'::uuid, '{j['player_id']}'::uuid, 'present', '{req}');", 'present replay'))
        assert b == a, 'replay điểm danh phải trả cùng kết quả'
        checked = must(db, f"SELECT checked_in_by = {q(1)} FROM public.session_players WHERE id='{j['player_id']}';", 'checked_by')
        assert checked == 't'
    run_test("record_attendance: chỉ in_progress, chỉ confirmed, replay cùng kết quả", t_attendance_lifecycle_and_replay)

    def t_invitation_issue_replay_and_non_waitlisted():
        sid = SHARED['wl_session']
        player = SHARED['wl_player']
        req = newreq()
        inv = json.loads(must_user(db, 1, f"SELECT public.invite_waitlisted_player('{sid}'::uuid, '{player}'::uuid, NULL, '{req}');", 'invite'))
        assert inv['status'] == 'pending' and inv['expires_at'], inv
        # không giữ slot
        assert must(db, f"SELECT count(*) FROM public.session_players WHERE session_id='{sid}' AND registration_status='confirmed';", 'count') == '1'
        replay = json.loads(must_user(db, 1, f"SELECT public.invite_waitlisted_player('{sid}'::uuid, '{player}'::uuid, NULL, '{req}');", 'invite replay'))
        assert replay['invitation_id'] == inv['invitation_id'], 'replay phải trả cùng invitation_id'
        SHARED['wl_invitation'] = inv['invitation_id']
        # non-waitlisted: người đã confirmed
        conf_id = must(db, f"SELECT id FROM public.session_players WHERE session_id='{sid}' AND registration_status='confirmed';", 'conf id')
        r = user_exec(db, 1, f"SELECT public.invite_waitlisted_player('{sid}'::uuid, '{conf_id}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), f"không mời người không waitlisted: {r.stderr}"
    run_test("invite_waitlisted_player: tạo lời mời không giữ slot, replay cùng key, chặn non-waitlisted", t_invitation_issue_replay_and_non_waitlisted)

    def t_invitation_expiry_bound():
        sid = create_and_publish(1, 'Bound', approval='auto_confirm', capacity=1)
        j = join(7, sid)
        w = join(8, sid)
        r = user_exec(db, 1, f"SELECT public.invite_waitlisted_player('{sid}'::uuid, '{w['player_id']}'::uuid, '{iso(3)}', '{newreq()}');")
        assert expect_error(r, 'INVALID_INPUT'), f"expiry vượt starts_at phải bị chặn: {r.stderr}"
        r2 = user_exec(db, 1, f"SELECT public.invite_waitlisted_player('{sid}'::uuid, '{w['player_id']}'::uuid, '{iso(-1)}', '{newreq()}');")
        assert expect_error(r2, 'INVALID_INPUT'), f"expiry quá khứ phải bị chặn: {r2.stderr}"
    run_test("invite_waitlisted_player chặn expiry ngoài biên (quá khứ/vượt starts_at)", t_invitation_expiry_bound)

    def t_accept_full_then_free_and_retry_no_extra_slot():
        sid = SHARED['wl_session']
        inv = SHARED['wl_invitation']
        # hết chỗ (capacity 1, 1 confirmed) -> CAPACITY_FULL, lời mời vẫn pending
        r = user_exec(db, SHARED['wl_user'], f"SELECT public.accept_waitlist_invitation('{sid}'::uuid, '{inv}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r, 'CAPACITY_FULL'), f"hết chỗ phải CAPACITY_FULL: {r.stderr}"
        assert must(db, f"SELECT status FROM public.waitlist_invitations WHERE id='{inv}';", 'still pending') == 'pending'
        # giải phóng chỗ bằng cancel người confirmed
        conf = must(db, f"SELECT id FROM public.session_players WHERE session_id='{sid}' AND registration_status='confirmed';", 'conf')
        conf_user = must(db, f"SELECT user_id FROM public.session_players WHERE id='{conf}';", 'conf user')
        # người confirmed là user 7 (join) -> tự hủy; dùng postgres cho chắc
        must(db, f"UPDATE public.session_players SET registration_status='cancelled', cancelled_at=now() WHERE id='{conf}';", 'free seat')
        req = newreq()
        a = json.loads(must_user(db, SHARED['wl_user'], f"SELECT public.accept_waitlist_invitation('{sid}'::uuid, '{inv}'::uuid, NULL, '{req}');", 'accept'))
        assert a['registration_status'] == 'confirmed' and a['invitation_status'] == 'accepted', a
        assert a['confirmed_count'] == 1
        # replay cùng key
        b = json.loads(must_user(db, SHARED['wl_user'], f"SELECT public.accept_waitlist_invitation('{sid}'::uuid, '{inv}'::uuid, NULL, '{req}');", 'accept replay'))
        assert b == a, 'replay accept phải trả cùng kết quả'
        # retry bằng key mới: đã accepted + confirmed -> không thêm slot
        c = json.loads(must_user(db, SHARED['wl_user'], f"SELECT public.accept_waitlist_invitation('{sid}'::uuid, '{inv}'::uuid, NULL, '{newreq()}');", 'accept again'))
        assert c['confirmed_count'] == 1, 'accept lặp không được lấy slot hai lần'
    run_test("accept_waitlist_invitation: hết chỗ CAPACITY_FULL, giải phóng chỗ thì confirmed, accept lặp không thêm slot", t_accept_full_then_free_and_retry_no_extra_slot)

    def t_accept_wrong_person():
        sid = create_and_publish(1, 'Wrong', approval='auto_confirm', capacity=1)
        join(7, sid)
        w = join(8, sid)
        inv = json.loads(must_user(db, 1, f"SELECT public.invite_waitlisted_player('{sid}'::uuid, '{w['player_id']}'::uuid, NULL, '{newreq()}');", 'invite'))
        r = user_exec(db, 10, f"SELECT public.accept_waitlist_invitation('{sid}'::uuid, '{inv['invitation_id']}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"sai người nhận phải FORBIDDEN: {r.stderr}"
    run_test("accept_waitlist_invitation sai người nhận trả FORBIDDEN", t_accept_wrong_person)

    def t_accept_revoked_and_expired():
        sid = create_and_publish(1, 'RevExp', approval='auto_confirm', capacity=1)
        join(7, sid)
        w = join(8, sid)
        inv = json.loads(must_user(db, 1, f"SELECT public.invite_waitlisted_player('{sid}'::uuid, '{w['player_id']}'::uuid, NULL, '{newreq()}');", 'invite'))
        must_user(db, 1, f"SELECT public.revoke_waitlist_invitation('{sid}'::uuid, '{inv['invitation_id']}'::uuid, 'test', '{newreq()}');", 'revoke')
        r = user_exec(db, 8, f"SELECT public.accept_waitlist_invitation('{sid}'::uuid, '{inv['invitation_id']}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r, 'INVITATION_REVOKED'), f"lời mời thu hồi phải INVITATION_REVOKED: {r.stderr}"
        # expired
        sid2 = create_and_publish(1, 'Exp', approval='auto_confirm', capacity=1)
        join(7, sid2)
        w2 = join(8, sid2)
        inv2 = json.loads(must_user(db, 1, f"SELECT public.invite_waitlisted_player('{sid2}'::uuid, '{w2['player_id']}'::uuid, NULL, '{newreq()}');", 'invite2'))
        must(db, f"UPDATE public.waitlist_invitations SET invited_at = now() - interval '10 minutes', expires_at = now() - interval '1 minute' WHERE id='{inv2['invitation_id']}';", 'expire invitation')
        r2 = user_exec(db, 8, f"SELECT public.accept_waitlist_invitation('{sid2}'::uuid, '{inv2['invitation_id']}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r2, 'INVITATION_EXPIRED'), f"lời mời hết hạn phải INVITATION_EXPIRED: {r2.stderr}"
    run_test("accept_waitlist_invitation: lời mời thu hồi/hết hạn trả đúng mã", t_accept_revoked_and_expired)

    def t_revoke_accepted_blocked():
        sid = create_and_publish(1, 'RevAcc', approval='auto_confirm', capacity=1)
        join(7, sid)
        w = join(8, sid)
        inv = json.loads(must_user(db, 1, f"SELECT public.invite_waitlisted_player('{sid}'::uuid, '{w['player_id']}'::uuid, NULL, '{newreq()}');", 'invite'))
        must(db, f"UPDATE public.session_players SET registration_status='cancelled', cancelled_at=now() WHERE session_id='{sid}' AND registration_status='confirmed';", 'free')
        must_user(db, 8, f"SELECT public.accept_waitlist_invitation('{sid}'::uuid, '{inv['invitation_id']}'::uuid, NULL, '{newreq()}');", 'accept')
        r = user_exec(db, 1, f"SELECT public.revoke_waitlist_invitation('{sid}'::uuid, '{inv['invitation_id']}'::uuid, 'test', '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), f"revoke lời mời đã accepted phải bị chặn: {r.stderr}"
    run_test("revoke_waitlist_invitation chặn lời mời đã accepted (dùng hủy đăng ký)", t_revoke_accepted_blocked)

    def t_host_recorded_consent():
        sid = create_and_publish(1, 'HostRec', capacity=1)
        join(7, sid)
        g = json.loads(must_user(db, 1, f"SELECT public.add_session_player('{sid}'::uuid, NULL, 'Khách C', NULL, FALSE, TRUE, '{newreq()}');", 'guest wl'))
        inv = json.loads(must_user(db, 1, f"SELECT public.invite_waitlisted_player('{sid}'::uuid, '{g['player_id']}'::uuid, NULL, '{newreq()}');", 'invite guest'))
        # consent rỗng -> FORBIDDEN
        r = user_exec(db, 1, f"SELECT public.accept_waitlist_invitation('{sid}'::uuid, '{inv['invitation_id']}'::uuid, '   ', '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"guest thiếu consent phải bị chặn: {r.stderr}"
        # account khác không tự accept guest
        r2 = user_exec(db, 10, f"SELECT public.accept_waitlist_invitation('{sid}'::uuid, '{inv['invitation_id']}'::uuid, 'x', '{newreq()}');")
        assert expect_error(r2, 'FORBIDDEN'), f"người khác không accept guest: {r2.stderr}"
        # giải phóng chỗ rồi host ghi nhận đồng ý
        must(db, f"UPDATE public.session_players SET registration_status='cancelled' WHERE session_id='{sid}' AND registration_status='confirmed';", 'free')
        a = json.loads(must_user(db, 1, f"SELECT public.accept_waitlist_invitation('{sid}'::uuid, '{inv['invitation_id']}'::uuid, 'Khách đồng ý qua Zalo', '{newreq()}');", 'host_rec'))
        assert a['registration_status'] == 'confirmed', a
        mode = must(db, f"SELECT acceptance_mode FROM public.waitlist_invitations WHERE id='{inv['invitation_id']}';", 'mode')
        assert mode == 'host_recorded', mode
    run_test("accept_waitlist_invitation host_recorded: cần consent, không cho account khác, ghi mode+consent", t_host_recorded_consent)

    def t_cancel_revokes_pending_invitation():
        sid = create_and_publish(1, 'CancelInv', approval='auto_confirm', capacity=1)
        join(7, sid)
        w = join(8, sid)
        inv = json.loads(must_user(db, 1, f"SELECT public.invite_waitlisted_player('{sid}'::uuid, '{w['player_id']}'::uuid, NULL, '{newreq()}');", 'invite'))
        must_user(db, 8, f"SELECT public.cancel_registration('{sid}'::uuid, '{w['player_id']}'::uuid, NULL, '{newreq()}');", 'cancel wl')
        assert must(db, f"SELECT status FROM public.waitlist_invitations WHERE id='{inv['invitation_id']}';", 'revoked on cancel') == 'revoked'
    run_test("cancel_registration thu hồi lời mời pending cùng transaction", t_cancel_revokes_pending_invitation)

    def t_get_my_invitation():
        sid = create_and_publish(1, 'MyInv', approval='auto_confirm', capacity=1)
        join(7, sid)
        w = join(8, sid)
        inv = json.loads(must_user(db, 1, f"SELECT public.invite_waitlisted_player('{sid}'::uuid, '{w['player_id']}'::uuid, NULL, '{newreq()}');", 'invite'))
        mine = json.loads(must_user(db, 8, f"SELECT public.get_my_waitlist_invitation('{sid}'::uuid);", 'my inv'))
        assert mine['invitation_id'] == inv['invitation_id'], mine
        none = must_user(db, 10, f"SELECT public.get_my_waitlist_invitation('{sid}'::uuid);", 'other inv')
        assert none in ('', 'NULL', 'null'), f"người không đăng ký phải nhận NULL: {none}"
    run_test("get_my_waitlist_invitation: đúng người nhận lời mời, người khác NULL", t_get_my_invitation)

    def t_outsider_cannot_manage_or_read_contacts():
        sid = create_and_publish(1, 'ACL', capacity=8)
        join(5, sid)
        p = json.loads(must_user(db, 1, f"SELECT public.list_session_players('{sid}'::uuid);", 'host players'))
        pid = p[0]['id']
        for actor, label in [(10, 'người ngoài'), (4, 'member CLB'), (3, 'thủ quỹ')]:
            r = user_exec(db, actor, f"SELECT public.list_session_players('{sid}'::uuid);")
            assert expect_error(r, 'FORBIDDEN'), f"{label} không được đọc danh sách: {r.stderr}"
            r2 = user_exec(db, actor, f"SELECT public.decide_registration('{sid}'::uuid, '{pid}'::uuid, 'confirmed', NULL, '{newreq()}');")
            assert expect_error(r2, 'FORBIDDEN'), f"{label} không được duyệt: {r2.stderr}"
    run_test("người ngoài/buổi không duyệt được và không đọc contact qua RPC", t_outsider_cannot_manage_or_read_contacts)

    def t_no_direct_writes():
        sid = create_and_publish(1, 'Direct', capacity=8)
        r1 = user_exec(db, 5, f"INSERT INTO public.session_players(session_id, user_id, display_name, created_by) VALUES ('{sid}', {q(5)}, 'X', {q(5)});")
        assert expect_error(r1, 'permission denied'), f"authenticated không được INSERT session_players: {r1.stderr}"
        r2 = user_exec(db, 5, "UPDATE public.session_players SET registration_status='confirmed';")
        assert expect_error(r2, 'permission denied'), f"authenticated không được UPDATE session_players: {r2.stderr}"
        r3 = user_exec(db, 5, f"INSERT INTO public.waitlist_invitations(session_player_id, invited_by, expires_at) VALUES ('{sid}', {q(5)}, now()+interval '1 hour');")
        assert expect_error(r3, 'permission denied'), f"authenticated không được INSERT waitlist_invitations: {r3.stderr}"
    run_test("không có direct write cho authenticated trên session_players/waitlist_invitations", t_no_direct_writes)

    def t_race_last_slot():
        sid = create_and_publish(1, 'Race', approval='auto_confirm', capacity=1)
        req1, req2 = newreq(), newreq()
        # T1 giữ lock (đã confirmed) rồi sleep trước commit; T2 chờ rồi phải thấy hết chỗ
        s1 = tx_script(5, f"SELECT public.request_join_session('{sid}'::uuid, NULL, '{req1}');\nSELECT pg_sleep(1.5);")
        s2 = tx_script(6, f"SELECT pg_sleep(0.2);\nSELECT public.request_join_session('{sid}'::uuid, NULL, '{req2}');")
        (o1, e1), (o2, e2) = run_concurrent(db, [s1, s2])
        conf = must(db, f"SELECT count(*) FROM public.session_players WHERE session_id='{sid}' AND registration_status='confirmed';", 'race confirmed')
        wl = must(db, f"SELECT count(*) FROM public.session_players WHERE session_id='{sid}' AND registration_status='waitlisted';", 'race waitlisted')
        assert conf == '1', f"slot cuối chỉ một confirmed: {conf}; T1={e1.strip()}; T2={e2.strip()}"
        assert wl == '1', f"người thua phải waitlisted: {wl}; T2={e2.strip()}"
    run_test("hai kết nối tranh slot cuối: chỉ một confirmed, người kia waitlisted", t_race_last_slot)

    def t_race_decide_capacity():
        sid = create_and_publish(1, 'RaceDecide', approval='host_approval', capacity=1)
        join(5, sid)
        join(6, sid)
        players = json.loads(must_user(db, 1, f"SELECT public.list_session_players('{sid}'::uuid);", 'players'))
        ids = {x['user_id']: x['id'] for x in players}
        # Host duyệt đồng thời hai pending -> chỉ một confirmed
        s1 = tx_script(1, f"SELECT public.decide_registration('{sid}'::uuid, '{ids[uid(5)]}'::uuid, 'confirmed', NULL, '{newreq()}');\nSELECT pg_sleep(1.5);")
        s2 = tx_script(1, f"SELECT pg_sleep(0.2);\nSELECT public.decide_registration('{sid}'::uuid, '{ids[uid(6)]}'::uuid, 'confirmed', NULL, '{newreq()}');")
        (o1, e1), (o2, e2) = run_concurrent(db, [s1, s2])
        conf = must(db, f"SELECT count(*) FROM public.session_players WHERE session_id='{sid}' AND registration_status='confirmed';", 'decide confirmed')
        assert conf == '1', f"duyệt cạnh tranh không vượt sức chứa: {conf}; T2={e2.strip()}"
        assert 'CAPACITY_FULL' in e2, f"người thua phải CAPACITY_FULL: {e2.strip()}"
    run_test("hai kết nối duyệt cạnh tranh: không vượt sức chứa (người thua CAPACITY_FULL)", t_race_decide_capacity)

    # --- Vòng sửa review 7fcbdee: A1 (gate finance) và A2 (capacity) ---------- #

    def t_a1_add_confirmed_requires_finance_after_finalize():
        sid = create_and_publish(1, 'FinAdd', capacity=8)
        must(db, f"INSERT INTO public.session_staff(session_id, user_id, role, status) VALUES "
                 f"('{sid}', {q(2)}, 'cohost', 'active'), "
                 f"('{sid}', {q(4)}, 'cohost', 'active'), ('{sid}', {q(4)}, 'finance', 'active');", 'staff')
        finalize_billing(sid)
        before = must(db, f"SELECT billing_input_version FROM public.sessions WHERE id='{sid}';", 'biv before')
        r = user_exec(db, 2, f"SELECT public.add_session_player('{sid}'::uuid, NULL, 'Khách F', NULL, FALSE, FALSE, '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"cohost không finance không được thêm confirmed sau chốt phí: {r.stderr}"
        ok = json.loads(must_user(db, 4, f"SELECT public.add_session_player('{sid}'::uuid, NULL, 'Khách F', NULL, FALSE, FALSE, '{newreq()}');", 'cohost+finance add'))
        assert ok['registration_status'] == 'confirmed', ok
        after = must(db, f"SELECT billing_input_version FROM public.sessions WHERE id='{sid}';", 'biv after')
        assert int(after) == int(before) + 1, f"thêm confirmed sau chốt phí phải tăng billing_input_version: {before}->{after}"
    run_test("A1 add_session_player: thêm confirmed sau chốt phí cần quyền tài chính (cohost FORBIDDEN, finance cho phép)", t_a1_add_confirmed_requires_finance_after_finalize)

    def t_a1_decide_confirmed_requires_finance_after_finalize():
        sid = create_and_publish(1, 'FinDecide', approval='host_approval', capacity=8)
        must(db, f"INSERT INTO public.session_staff(session_id, user_id, role, status) VALUES ('{sid}', {q(2)}, 'cohost', 'active');", 'cohost')
        j = join(5, sid)
        finalize_billing(sid)
        r = user_exec(db, 2, f"SELECT public.decide_registration('{sid}'::uuid, '{j['player_id']}'::uuid, 'confirmed', NULL, '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"cohost không finance không được duyệt confirmed sau chốt phí: {r.stderr}"
        ok = json.loads(must_user(db, 1, f"SELECT public.decide_registration('{sid}'::uuid, '{j['player_id']}'::uuid, 'confirmed', NULL, '{newreq()}');", 'host decide after finalize'))
        assert ok['registration_status'] == 'confirmed', ok
    run_test("A1 decide_registration: duyệt confirmed sau chốt phí cần quyền tài chính", t_a1_decide_confirmed_requires_finance_after_finalize)

    def t_a1_cancel_confirmed_requires_finance_after_finalize():
        sid = create_and_publish(1, 'FinCancel', approval='auto_confirm', capacity=8)
        must(db, f"INSERT INTO public.session_staff(session_id, user_id, role, status) VALUES ('{sid}', {q(2)}, 'cohost', 'active');", 'cohost')
        j = join(6, sid)
        assert j['registration_status'] == 'confirmed', j
        finalize_billing(sid)
        r = user_exec(db, 2, f"SELECT public.cancel_registration('{sid}'::uuid, '{j['player_id']}'::uuid, 'x', '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"cohost không finance không được hủy confirmed sau chốt phí: {r.stderr}"
        ok = json.loads(must_user(db, 1, f"SELECT public.cancel_registration('{sid}'::uuid, '{j['player_id']}'::uuid, 'y', '{newreq()}');", 'host cancel after finalize'))
        assert ok['registration_status'] == 'cancelled', ok
    run_test("A1 cancel_registration: hủy confirmed sau chốt phí cần quyền tài chính", t_a1_cancel_confirmed_requires_finance_after_finalize)

    def t_a1_accept_confirmed_requires_finance_after_finalize():
        sid = create_and_publish(1, 'FinAccept', approval='auto_confirm', capacity=2)
        must(db, f"INSERT INTO public.session_staff(session_id, user_id, role, status) VALUES ('{sid}', {q(2)}, 'cohost', 'active');", 'cohost')
        join(5, sid)
        j6 = join(6, sid)
        w = join(7, sid)
        assert w['registration_status'] == 'waitlisted', w
        inv = json.loads(must_user(db, 1, f"SELECT public.invite_waitlisted_player('{sid}'::uuid, '{w['player_id']}'::uuid, NULL, '{newreq()}');", 'invite'))
        must_user(db, 6, f"SELECT public.cancel_registration('{sid}'::uuid, '{j6['player_id']}'::uuid, NULL, '{newreq()}');", 'free slot')
        finalize_billing(sid)
        r = user_exec(db, 7, f"SELECT public.accept_waitlist_invitation('{sid}'::uuid, '{inv['invitation_id']}'::uuid, NULL, '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"nhận chỗ sau chốt phí cần quyền tài chính: {r.stderr}"
    run_test("A1 accept_waitlist_invitation: nhận chỗ sau chốt phí cần quyền tài chính", t_a1_accept_confirmed_requires_finance_after_finalize)

    def t_a2_update_capacity_below_confirmed():
        sid = create_and_publish(1, 'CapShrink', approval='auto_confirm', capacity=2)
        join(5, sid)
        join(6, sid)
        assert confirmed_count(sid) == 2
        v = must(db, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'version')
        r = user_exec(db, 1, update_session_sql(sid, v, 1, 'CapShrink'))
        assert expect_error(r, 'CAPACITY_FULL'), f"không được hạ capacity dưới confirmed: {r.stderr}"
        assert capacity_of(sid) == 2, 'capacity phải giữ nguyên khi bị từ chối'
    run_test("A2 update_session: từ chối hạ capacity dưới số đã confirmed", t_a2_update_capacity_below_confirmed)

    def t_a2_race_update_capacity_vs_join():
        sid = create_and_publish(1, 'CapRace', approval='auto_confirm', capacity=2)
        join(5, sid)
        join(6, sid)
        v = must(db, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'version')
        s1 = tx_script(1, update_session_sql(sid, v, 1, 'CapRace') + "\nSELECT pg_sleep(1.5);")
        s2 = tx_script(7, f"SELECT pg_sleep(0.2);\nSELECT public.request_join_session('{sid}'::uuid, NULL, '{newreq()}');")
        run_concurrent(db, [s1, s2])
        cap, conf = capacity_of(sid), confirmed_count(sid)
        assert conf <= cap, f"confirmed không được vượt capacity sau commit: confirmed={conf}, capacity={cap}"
        assert cap >= 2, f"capacity không được hạ xuống dưới confirmed: {cap}"
    run_test("A2 race: hạ capacity đấu với join — confirmed không vượt capacity", t_a2_race_update_capacity_vs_join)


run_suite(CLEAN)
run_suite(LEGACY)

passed = sum(1 for r in results if r['status'] == 'PASS')
failed = sum(1 for r in results if r['status'] == 'FAIL')
print("\n==========================================")
print(f"KẾT QUẢ KIỂM THỬ BH-05: TỔNG {len(results)} | PASS {passed} | FAIL {failed}")
print("==========================================")

report_file = ROOT / f"bh05_test_results_{stamp}.json"
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
