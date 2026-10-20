import subprocess, json, datetime, sys, os, uuid, hashlib
from pathlib import Path

# Đảm bảo mã hóa đầu ra utf-8 trên Windows
sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
CONTAINER = os.environ.get('BH02_TEST_CONTAINER', 'bh02-test-postgres')

stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
CLEAN = 'bh06_clean_' + stamp
LEGACY = 'bh06_legacy_' + stamp


def sql(db, query):
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


print(f"Khởi tạo cơ sở dữ liệu kiểm thử BH-06: {CLEAN} và {LEGACY}...")

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
    must('postgres', f'DROP DATABASE IF EXISTS {db};', f'Xoá DB cũ {db}')
    must('postgres', f'CREATE DATABASE {db};', f'Tạo DB {db}')
    must(db, setup_auth, 'Setup auth stub')

must(LEGACY, legacy_schema, 'Tạo legacy schema cho LEGACY DB')

for db in [CLEAN, LEGACY]:
    must(db, migration_v1_1, 'Chạy migration init v1.1')
    must(db, migration_after, 'Chạy các migration forward (BH-03..BH-06)')

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

    stmts = []
    for n in range(1, 13):
        stmts.append(
            f"INSERT INTO auth.users(id, email, raw_user_meta_data) VALUES ({q(n)}, 'u{n}@example.invalid', "
            f"jsonb_build_object('display_name', 'User {n}')) ON CONFLICT (id) DO NOTHING;"
        )
    must(db, '\n'.join(stmts), 'Seed auth users')

    venue = must(db, """
      INSERT INTO public.venues(name, address, area, phone_number, court_count, status)
      VALUES ('Sân BH06 A', '12 Trần Phú', 'Nha Trang', '0900000001', 6, 'active')
      RETURNING id;
    """, 'Seed venue')
    SHARED['venue'] = venue

    club = must(db, f"""
      INSERT INTO public.clubs(owner_user_id, name, visibility, status)
      VALUES ({q(1)}, 'CLB BH06', 'public', 'active') RETURNING id;
    """, 'Seed club')
    must(db, f"""
      INSERT INTO public.club_members(club_id, user_id, display_name, role, status, joined_at) VALUES
        ('{club}', {q(1)}, 'Owner', 'owner', 'active', now()),
        ('{club}', {q(2)}, 'HostOnly', 'host', 'active', now()),
        ('{club}', {q(3)}, 'Treasurer', 'treasurer', 'active', now()),
        ('{club}', {q(4)}, 'Member', 'member', 'active', now());
    """, 'Seed club members')
    SHARED['club'] = club

    # ------------------------------------------------------------------ helpers
    def create_and_publish(actor, title, *, capacity=12, courts=2, vis='unlisted',
                           approval='auto_confirm', fee_mode='split_actual',
                           member_fee=None, guest_fee=None, club_link=None, start_days=1):
        v = SHARED['venue']
        club_sql = f"'{club_link}'::uuid" if club_link else 'NULL'
        mf = str(member_fee) if member_fee is not None else 'NULL'
        gf = str(guest_fee) if guest_fee is not None else 'NULL'
        stmt = (f"SELECT public.create_session(p_venue_id=>'{v}'::uuid, p_title=>'{title}', "
                f"p_starts_at=>'{iso(start_days)}', p_ends_at=>'{iso(start_days, 2)}', "
                f"p_capacity=>{capacity}, p_court_count=>{courts}, p_club_id=>{club_sql}, "
                f"p_visibility=>'{vis}', p_approval_mode=>'{approval}', p_fee_mode=>'{fee_mode}', "
                f"p_member_fee_vnd=>{mf}, p_guest_fee_vnd=>{gf}, p_request_id=>'{newreq()}');")
        sid = json.loads(must_user(db, actor, stmt, f'create {title}'))['id']
        must_user(db, actor, f"SELECT public.set_session_lifecycle('{sid}'::uuid, 'publish', '{newreq()}');", f'publish {title}')
        return sid

    def join(actor, sid, contact=None, req=None):
        contact_sql = f"'{contact}'" if contact else 'NULL'
        key = req or newreq()
        return json.loads(must_user(db, actor,
            f"SELECT public.request_join_session('{sid}'::uuid, {contact_sql}, '{key}');", 'join'))

    def add_player(actor, sid, guest_name, exempt=False, contact=None):
        contact_sql = f"'{contact}'" if contact else 'NULL'
        return json.loads(must_user(db, actor,
            f"SELECT public.add_session_player('{sid}'::uuid, NULL, '{guest_name}', {contact_sql}, "
            f"{'TRUE' if exempt else 'FALSE'}, FALSE, '{newreq()}');", 'add player'))

    def start(sid, actor=1):
        must_user(db, actor, f"SELECT public.start_session('{sid}'::uuid, '{newreq()}');", 'start')

    def attend(sid, player, att='present', actor=1):
        return json.loads(must_user(db, actor,
            f"SELECT public.record_attendance('{sid}'::uuid, '{player}'::uuid, '{att}', '{newreq()}');", 'attend'))

    def post_expense(sid, amount, actor=1, category='court', title='Tiền sân'):
        return json.loads(must_user(db, actor,
            f"SELECT public.post_session_expense('{sid}'::uuid, '{category}', '{title}', {amount}, '{newreq()}');", 'expense'))

    def finalize(sid, actor=1, reason=None, expect_version=None, expect_biv=None):
        v = expect_version if expect_version is not None else must(db, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'v')
        b = expect_biv if expect_biv is not None else must(db, f"SELECT billing_input_version FROM public.sessions WHERE id='{sid}';", 'b')
        reason_sql = f"'{reason}'" if reason else 'NULL'
        return json.loads(must_user(db, actor,
            f"SELECT public.finalize_session_charges('{sid}'::uuid, {v}::bigint, {b}::bigint, {reason_sql}, '{newreq()}');", 'finalize'))

    def submit(player, amount, actor=None, method='bank_transfer', reference=None, req=None):
        # actor None -> dùng chính user của player (self); truyền actor cụ thể để test sai quyền
        owner = actor
        if owner is None:
            owner = int(must(db, f"SELECT u.email FROM public.session_players sp JOIN auth.users u ON u.id = sp.user_id WHERE sp.id='{player}';", 'owner').replace('u', '').replace('@example.invalid', ''))
        ref_sql = f"'{reference}'" if reference else 'NULL'
        return user_exec(db, owner,
            f"SELECT public.submit_payment('{player}'::uuid, {amount}, '{method}', {ref_sql}, '{req or newreq()}');")

    def submit_ok(player, amount, actor=None, reference=None, req=None):
        r = submit(player, amount, actor=actor, reference=reference, req=req)
        if r.returncode != 0:
            raise RuntimeError(f"submit: {r.stderr.strip()}")
        return json.loads([line.strip() for line in r.stdout.splitlines() if line.strip()][-1])

    def cash(player, amount, actor=1, reference=None):
        ref_sql = f"'{reference}'" if reference else 'NULL'
        return json.loads(must_user(db, actor,
            f"SELECT public.record_cash_payment('{player}'::uuid, {amount}, {ref_sql}, '{newreq()}');", 'cash'))

    def confirm(payment_id, actor=1):
        return json.loads(must_user(db, actor,
            f"SELECT public.confirm_payment('{payment_id}'::uuid, '{newreq()}');", 'confirm'))

    def billing_state(sid):
        return must(db, f"SELECT public.session_billing_state('{sid}');", 'billing state')

    def charges(sid):
        return [line.split('|') for line in must(db, f"""
          SELECT sc.session_player_id, sc.amount_due_vnd FROM public.session_charges sc
          JOIN public.charge_revisions cr ON cr.id = sc.revision_id
          WHERE cr.session_id='{sid}' AND cr.status='active' ORDER BY sc.session_player_id;
        """, 'charges').splitlines() if line.strip()]

    # ================================================================ ACL / quyền
    def t_anon_acl():
        sid = create_and_publish(1, 'AnonACL')
        for call in [
            f"SELECT public.post_session_expense('{sid}'::uuid, 'court', 'x', 1000, '{newreq()}');",
            f"SELECT public.finalize_session_charges('{sid}'::uuid, 1, 1, NULL, '{newreq()}');",
            f"SELECT public.record_cash_payment('{uid(2)}'::uuid, 1000, NULL, '{newreq()}');",
            f"SELECT public.post_manual_club_transaction('{SHARED['club']}'::uuid, 'income', 1000, 'x', '{newreq()}');",
            f"SELECT public.get_club_ledger('{SHARED['club']}'::uuid);",
        ]:
            r = anon_exec(db, call)
            assert expect_error(r, 'permission denied'), f"anon phải bị chặn ACL: {r.stderr}"
    run_test("ACL: anon không gọi được RPC tài chính/quỹ", t_anon_acl)

    def t_direct_write_and_helper_acl():
        sid = create_and_publish(1, 'DirectAcl', capacity=4)
        p = join(5, sid)['player_id']
        # authenticated không ghi trực tiếp được bảng tài chính (RLS bật + không có grant ghi)
        r = user_exec(db, 1, f"INSERT INTO public.session_expenses(session_id, category, title, amount_vnd, status, created_by) VALUES ('{sid}'::uuid, 'court', 'x', 1000, 'posted', {q(1)});")
        assert expect_error(r, 'permission denied'), f"không được ghi trực tiếp session_expenses: {r.stderr}"
        r = user_exec(db, 1, "UPDATE public.payments SET amount_vnd = 0;")
        assert expect_error(r, 'permission denied'), f"không được sửa trực tiếp payments: {r.stderr}"
        r = user_exec(db, 1, f"INSERT INTO public.club_transactions(club_id, direction, amount_vnd, title, source_type, created_by) VALUES ('{SHARED['club']}'::uuid, 'income', 1000, 'x', 'manual', {q(1)});")
        assert expect_error(r, 'permission denied'), f"không được ghi trực tiếp club_transactions: {r.stderr}"
        r = user_exec(db, 1, f"INSERT INTO public.charge_revisions(session_id, revision_no, source_version, status, allocation_total_vnd, fee_mode, finalized_by) VALUES ('{sid}'::uuid, 1, 1, 'active', 0, 'split_actual', {q(1)});")
        assert expect_error(r, 'permission denied'), f"không được ghi trực tiếp charge_revisions: {r.stderr}"
        # helper nội bộ bị REVOKE khỏi authenticated
        for helper in [
            f"SELECT public.active_charge_revision_id('{sid}'::uuid);",
            f"SELECT public.session_billing_state('{sid}'::uuid);",
            f"SELECT public.assert_billing_current('{sid}'::uuid);",
            f"SELECT public.player_charge_snapshot('{p}'::uuid);",
        ]:
            r = user_exec(db, 1, helper)
            assert expect_error(r, 'permission denied'), f"helper phải bị chặn: {helper} -> {r.stderr}"
    run_test("ACL: chặn ghi trực tiếp bảng tài chính và helper nội bộ", t_direct_write_and_helper_acl)

    def t_outsider_post_expense():
        sid = create_and_publish(1, 'OutsiderExp')
        r = user_exec(db, 10, f"SELECT public.post_session_expense('{sid}'::uuid, 'court', 'x', 1000, '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"người ngoài không được ghi chi phí: {r.stderr}"
    run_test("Quyền: outsider không ghi được chi phí (FORBIDDEN)", t_outsider_post_expense)

    def t_staff_finance_scope():
        sid = create_and_publish(1, 'StaffScope', club_link=SHARED['club'])
        must(db, f"INSERT INTO public.session_staff(session_id, user_id, role, status) VALUES ('{sid}', {q(2)}, 'cohost', 'active');", 'cohost')
        must(db, f"INSERT INTO public.session_staff(session_id, user_id, role, status) VALUES ('{sid}', {q(7)}, 'finance', 'active');", 'finance staff')
        r = user_exec(db, 2, f"SELECT public.post_session_expense('{sid}'::uuid, 'court', 'x', 1000, '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"cohost không finance phải bị chặn: {r.stderr}"
        # club treasurer (3) có quyền finance theo CLB
        must_user(db, 3, f"SELECT public.post_session_expense('{sid}'::uuid, 'court', 'ok treasurer', 1000, '{newreq()}');", 'treasurer expense')
        # session staff finance (7) cũng có quyền
        must_user(db, 7, f"SELECT public.post_session_expense('{sid}'::uuid, 'shuttle', 'ok staff', 2000, '{newreq()}');", 'staff finance expense')
    run_test("Quyền: cohost không finance bị chặn, treasurer/staff finance được ghi chi phí", t_staff_finance_scope)

    def t_player_cannot_confirm():
        sid = create_and_publish(1, 'NoSelfConfirm', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 50000)
        finalize(sid)
        pay = submit_ok(p, 1000)
        r = user_exec(db, 5, f"SELECT public.confirm_payment('{pay['payment_id']}'::uuid, '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"player không tự confirm được: {r.stderr}"
    run_test("Quyền: player không tự xác nhận thanh toán", t_player_cannot_confirm)

    def t_player_cannot_submit_for_other():
        sid = create_and_publish(1, 'SubmitOther', capacity=4)
        p5 = join(5, sid)['player_id']
        p6 = join(6, sid)['player_id']
        start(sid)
        attend(sid, p5)
        attend(sid, p6)
        finalize(sid)
        r = user_exec(db, 5, f"SELECT public.submit_payment('{p6}'::uuid, 1000, 'bank_transfer', NULL, '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"không gửi thanh toán cho người khác: {r.stderr}"
    run_test("Quyền: player không gửi thanh toán thay người khác", t_player_cannot_submit_for_other)

    def t_ledger_read_scope():
        r = user_exec(db, 2, f"SELECT public.get_club_ledger('{SHARED['club']}'::uuid);")
        assert expect_error(r, 'FORBIDDEN'), f"club host (không owner/treasurer) không đọc sổ quỹ: {r.stderr}"
        ok = json.loads(must_user(db, 1, f"SELECT public.get_club_ledger('{SHARED['club']}'::uuid);", 'owner ledger'))
        assert 'balance_vnd' in ok and 'entries' in ok, ok
    run_test("Quyền: chỉ owner/treasurer đọc sổ quỹ CLB", t_ledger_read_scope)

    def t_payment_instructions_scope():
        sid = create_and_publish(1, 'PayInfo', capacity=4, approval='host_approval', club_link=SHARED['club'])
        p = join(5, sid)  # pending
        r = user_exec(db, 5, f"SELECT public.get_payment_instructions('{sid}'::uuid);")
        assert expect_error(r, 'NOT_FOUND'), f"pending không có hướng dẫn thanh toán: {r.stderr}"
        must_user(db, 1, f"SELECT public.decide_registration('{sid}'::uuid, '{p['player_id']}'::uuid, 'confirmed', NULL, '{newreq()}');", 'confirm player')
        start(sid)
        attend(sid, p['player_id'])
        finalize(sid)
        mine = json.loads(must_user(db, 5, f"SELECT public.get_payment_instructions('{sid}'::uuid);", 'self payinfo'))
        assert mine['player_id'] == p['player_id'], mine
        assert mine['billing_state'] == 'current', mine
        as_finance = json.loads(must_user(db, 1, f"SELECT public.get_payment_instructions('{sid}'::uuid, '{p['player_id']}'::uuid);", 'finance payinfo'))
        assert as_finance['outstanding_vnd'] == mine['outstanding_vnd'], (as_finance, mine)
        # finance đọc được cả khi chưa confirmed (đọc cho người khác)
        as_finance2 = json.loads(must_user(db, 3, f"SELECT public.get_payment_instructions('{sid}'::uuid, '{p['player_id']}'::uuid);", 'treasurer payinfo'))
        assert as_finance2['player_id'] == p['player_id'], as_finance2
    run_test("Quyền: get_payment_instructions đúng người/finance, chặn pending", t_payment_instructions_scope)

    def t_payinfo_guest_null_forbidden():
        # R1 (review vòng 1): khách offline user_id=NULL confirmed phải không lộ công nợ/ngân hàng
        sid = create_and_publish(1, 'GuestScope', capacity=6, club_link=SHARED['club'])
        g = add_player(1, sid, 'Khách Offline')['player_id']  # user_id NULL, confirmed
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, g)
        attend(sid, p)
        post_expense(sid, 100000)
        finalize(sid)
        assert billing_state(sid) == 'current'
        # outsider không vai trò đọc công nợ khách offline -> FORBIDDEN (trước sửa bị NULL cho qua)
        r = user_exec(db, 10, f"SELECT public.get_payment_instructions('{sid}'::uuid, '{g}'::uuid);")
        assert expect_error(r, 'FORBIDDEN'), f"outsider đọc công nợ khách offline phải bị chặn: {r.stderr}"
        # cohost không finance đọc khách offline -> FORBIDDEN (management không phải finance)
        must(db, f"INSERT INTO public.session_staff(session_id, user_id, role, status) VALUES ('{sid}', {q(2)}, 'cohost', 'active');", 'cohost')
        r = user_exec(db, 2, f"SELECT public.get_payment_instructions('{sid}'::uuid, '{g}'::uuid);")
        assert expect_error(r, 'FORBIDDEN'), f"cohost không finance đọc khách offline phải bị chặn: {r.stderr}"
        # negative control: outsider đọc khách đã liên kết user vẫn FORBIDDEN
        r = user_exec(db, 10, f"SELECT public.get_payment_instructions('{sid}'::uuid, '{p}'::uuid);")
        assert expect_error(r, 'FORBIDDEN'), f"outsider đọc người khác phải bị chặn: {r.stderr}"
        # finance vẫn đọc được khách offline đúng scope
        ok = json.loads(must_user(db, 1, f"SELECT public.get_payment_instructions('{sid}'::uuid, '{g}'::uuid);", 'finance guest'))
        assert ok['player_id'] == g and ok['billing_state'] == 'current' and ok['outstanding_vnd'] == 50000, ok
    run_test("Quyền: outsider/cohost không đọc công nợ khách offline user_id NULL (R1)", t_payinfo_guest_null_forbidden)

    def t_payinfo_gate_legacy_and_new():
        # R2 (review vòng 1): RPC bank cũ (BH-02) và RPC mới đều phải gate current
        sid = create_and_publish(1, 'LegacyGate', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        # chưa chốt: cả đường cũ và mới -> BILLING_NOT_FINALIZED
        r = user_exec(db, 5, f"SELECT public.get_session_payment_instructions('{sid}'::uuid);")
        assert expect_error(r, 'BILLING_NOT_FINALIZED'), f"RPC cũ chưa chốt phải bị chặn: {r.stderr}"
        r = user_exec(db, 5, f"SELECT public.get_payment_instructions('{sid}'::uuid);")
        assert expect_error(r, 'BILLING_NOT_FINALIZED'), f"RPC mới chưa chốt phải bị chặn: {r.stderr}"
        finalize(sid)
        legacy = json.loads(must_user(db, 5, f"SELECT public.get_session_payment_instructions('{sid}'::uuid);", 'legacy current'))
        assert 'receiver_snapshot' in legacy and legacy['session_id'] == sid, legacy
        post_expense(sid, 10000)  # stale
        assert billing_state(sid) == 'stale'
        # stale: cả đường cũ và mới -> BILLING_STALE
        r = user_exec(db, 5, f"SELECT public.get_session_payment_instructions('{sid}'::uuid);")
        assert expect_error(r, 'BILLING_STALE'), f"RPC cũ stale phải bị chặn: {r.stderr}"
        r = user_exec(db, 5, f"SELECT public.get_payment_instructions('{sid}'::uuid);")
        assert expect_error(r, 'BILLING_STALE'), f"RPC mới stale phải bị chặn: {r.stderr}"
    run_test("Gate: RPC bank cũ và mới đều chặn not_finalized/stale (R2)", t_payinfo_gate_legacy_and_new)

    def t_public_detail_no_bank():
        sid = create_and_publish(1, 'NoBankLeak', vis='public')
        raw = anon_exec(db, f"SELECT public.get_session_public_detail('{sid}'::uuid);").stdout
        assert 'receiver_snapshot' not in raw, f"projection public không được lộ ngân hàng: {raw[:200]}"
        assert 'receiver_' not in raw, f"projection public không được lộ trường receiver: {raw[:200]}"
    run_test("Privacy: projection public không lộ ngân hàng", t_public_detail_no_bank)

    def t_finance_read_scope():
        sid = create_and_publish(1, 'FinRead', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        finalize(sid)
        r = user_exec(db, 5, f"SELECT public.get_session_finance('{sid}'::uuid);")
        assert expect_error(r, 'FORBIDDEN'), f"player không đọc tài chính buổi: {r.stderr}"
        ok = json.loads(must_user(db, 1, f"SELECT public.get_session_finance('{sid}'::uuid);", 'finance read'))
        assert ok['active_revision'] is not None and ok['billing_state'] == 'current', ok
    run_test("Quyền: get_session_finance chỉ finance", t_finance_read_scope)

    # ============================================================== chia tiền
    def t_split_450k_7():
        sid = create_and_publish(1, 'Split7', capacity=10)
        players = [join(u, sid)['player_id'] for u in range(4, 11)]  # 7 người
        start(sid)
        for p in players:
            attend(sid, p)
        post_expense(sid, 450000)
        res = finalize(sid)
        assert res['allocation_total_vnd'] == 450000, res
        rows = charges(sid)
        assert len(rows) == 7, rows
        amounts = sorted(int(r[1]) for r in rows)
        assert sum(amounts) == 450000, f"tổng charges phải = 450000: {amounts}"
        assert amounts.count(64286) == 5 and amounts.count(64285) == 2, f"chia dư sai: {amounts}"
    run_test("Chia tiền: split 450.000/7 tổng chính xác, chia dư ổn định", t_split_450k_7)

    def t_split_no_show_and_exempt():
        sid = create_and_publish(1, 'SplitExempt', capacity=10)
        players = [join(u, sid)['player_id'] for u in range(4, 9)]  # 5 present
        absent = join(9, sid)['player_id']
        exempt = add_player(1, sid, 'VIP', exempt=True)
        exempt_id = exempt['player_id']
        start(sid)
        for p in players:
            attend(sid, p)
        attend(sid, absent, 'no_show')
        attend(sid, exempt_id)
        post_expense(sid, 400000)
        res = finalize(sid)
        assert res['allocation_total_vnd'] == 400000, res
        rows = {r[0]: int(r[1]) for r in charges(sid)}
        assert rows.get(exempt_id) == 0, f"người miễn phí phải 0: {rows}"
        assert absent not in rows, f"no_show không có charge: {rows}"
        assert sum(rows.values()) == 400000, rows
        # 5 người present không exempt: 400000/5 = 80000 mỗi người; exempt 0
        assert sorted(rows.values()) == [0, 80000, 80000, 80000, 80000, 80000], rows
    run_test("Chia tiền: exemption 0, no_show không tính, phần còn lại chia đều", t_split_no_show_and_exempt)

    def t_no_billable_players():
        sid = create_and_publish(1, 'NoBillable', capacity=4)
        exempt = add_player(1, sid, 'VIP', exempt=True)
        start(sid)
        attend(sid, exempt['player_id'])
        post_expense(sid, 100000)
        b = must(db, f"SELECT billing_input_version FROM public.sessions WHERE id='{sid}';", 'biv')
        v = must(db, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'v')
        r = user_exec(db, 1, f"SELECT public.finalize_session_charges('{sid}'::uuid, {v}::bigint, {b}::bigint, NULL, '{newreq()}');")
        assert expect_error(r, 'NO_BILLABLE_PLAYERS'), f"phải báo NO_BILLABLE_PLAYERS: {r.stderr}"
        revs = must(db, f"SELECT count(*) FROM public.charge_revisions WHERE session_id='{sid}';", 'revs')
        assert revs == '0', f"không được tạo revision khi lỗi: {revs}"
    run_test("Chia tiền: có chi phí nhưng không người chịu phí -> NO_BILLABLE_PLAYERS, rollback", t_no_billable_players)

    def t_zero_total_free():
        sid = create_and_publish(1, 'FreeZero', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        res = finalize(sid)  # không có expense -> total 0
        assert res['allocation_total_vnd'] == 0, res
        rows = charges(sid)
        assert len(rows) == 1 and int(rows[0][1]) == 0, rows
        assert billing_state(sid) == 'current'
    run_test("Chia tiền: total 0 vẫn có revision current, charges 0", t_zero_total_free)

    def t_fixed_differs_from_expense():
        sid = create_and_publish(1, 'Fixed', capacity=4, club_link=SHARED['club'],
                                 fee_mode='fixed', member_fee=50000, guest_fee=60000)
        pm = join(4, sid)['player_id']  # thành viên CLB -> member fee
        pg = join(6, sid)['player_id']  # không phải thành viên -> guest fee
        start(sid)
        attend(sid, pm)
        attend(sid, pg)
        post_expense(sid, 100000)  # chi phí thực khác tổng phí cố định
        res = finalize(sid)
        assert res['allocation_total_vnd'] == 110000, res
        rows = {r[0]: int(r[1]) for r in charges(sid)}
        assert rows[pm] == 50000 and rows[pg] == 60000, rows
    run_test("Chia tiền: fixed khác tổng expense (thu theo agreed fee)", t_fixed_differs_from_expense)

    # ========================================================== revision/stale
    def t_expense_after_finalize_stale():
        sid = create_and_publish(1, 'StaleExp', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        finalize(sid)
        assert billing_state(sid) == 'current'
        post_expense(sid, 50000)
        assert billing_state(sid) == 'stale', 'chi phí sau chốt phải làm stale'
        for call, label in [
            (f"SELECT public.get_payment_instructions('{sid}'::uuid, '{p}'::uuid);", 'payinfo'),
            (f"SELECT public.record_cash_payment('{p}'::uuid, 10000, NULL, '{newreq()}');", 'cash'),
        ]:
            r = user_exec(db, 1, call)
            assert expect_error(r, 'BILLING_STALE'), f"{label} phải bị BILLING_STALE khi stale: {r.stderr}"
        r = user_exec(db, 5, f"SELECT public.submit_payment('{p}'::uuid, 10000, 'bank_transfer', NULL, '{newreq()}');")
        assert expect_error(r, 'BILLING_STALE'), f"submit khi stale phải bị chặn: {r.stderr}"
        v = must(db, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'v')
        r = user_exec(db, 1, f"SELECT public.complete_session('{sid}'::uuid, {v}::bigint, '{newreq()}');")
        assert expect_error(r, 'BILLING_STALE'), f"complete khi stale phải bị chặn: {r.stderr}"
    run_test("Stale: chi phí sau chốt làm stale, chặn QR/submit/cash/complete", t_expense_after_finalize_stale)

    def t_refinalize_ok():
        sid = create_and_publish(1, 'Refin', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 100000)
        r1 = finalize(sid)
        post_expense(sid, 200000)  # tổng 300000 -> stale
        assert billing_state(sid) == 'stale'
        r2 = finalize(sid, reason='bổ sung chi phí')
        assert r2['revision_no'] == 2 and r2['allocation_total_vnd'] == 300000, r2
        assert billing_state(sid) == 'current'
        superseded = must(db, f"SELECT count(*) FROM public.charge_revisions WHERE session_id='{sid}' AND status='superseded';", 'superseded')
        assert superseded == '1', superseded
        assert must(db, f"SELECT id FROM public.charge_revisions WHERE session_id='{sid}' AND status='active';", 'active') == r2['revision_id']
    run_test("Revision: refinalize supersede nguyên tử, revision_no 2, current trở lại", t_refinalize_ok)

    def t_refinalize_version_conflicts():
        sid = create_and_publish(1, 'RefinVer', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        finalize(sid)
        b = must(db, f"SELECT billing_input_version FROM public.sessions WHERE id='{sid}';", 'b')
        v = must(db, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'v')
        r = user_exec(db, 1, f"SELECT public.finalize_session_charges('{sid}'::uuid, {int(v)+5}::bigint, {b}::bigint, 'x', '{newreq()}');")
        assert expect_error(r, 'VERSION_CONFLICT'), f"version cũ phải conflict: {r.stderr}"
        r = user_exec(db, 1, f"SELECT public.finalize_session_charges('{sid}'::uuid, {v}::bigint, {int(b)+5}::bigint, 'x', '{newreq()}');")
        assert expect_error(r, 'BILLING_STALE'), f"billing version cũ phải stale: {r.stderr}"
    run_test("Revision: expected version/billing version sai -> VERSION_CONFLICT/BILLING_STALE", t_refinalize_version_conflicts)

    def t_refinalize_needs_reason():
        sid = create_and_publish(1, 'RefinReason', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        finalize(sid)
        post_expense(sid, 10000)
        b = must(db, f"SELECT billing_input_version FROM public.sessions WHERE id='{sid}';", 'b')
        v = must(db, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'v')
        r = user_exec(db, 1, f"SELECT public.finalize_session_charges('{sid}'::uuid, {v}::bigint, {b}::bigint, NULL, '{newreq()}');")
        assert expect_error(r, 'INVALID_INPUT'), f"chốt lại phải cần lý do: {r.stderr}"
    run_test("Revision: chốt lại lần 2 thiếu lý do -> INVALID_INPUT", t_refinalize_needs_reason)

    def t_attendance_after_finalize_stale():
        sid = create_and_publish(1, 'StaleAtt', capacity=4)
        p1 = join(5, sid)['player_id']
        p2 = join(6, sid)['player_id']
        start(sid)
        attend(sid, p1)
        attend(sid, p2)
        finalize(sid)
        attend(sid, p2, 'no_show')  # đổi điểm danh sau chốt
        assert billing_state(sid) == 'stale', 'đổi điểm danh sau chốt phải stale'
    run_test("Stale: đổi điểm danh sau chốt làm stale", t_attendance_after_finalize_stale)

    def t_roster_after_finalize_stale():
        sid = create_and_publish(1, 'StaleRoster', capacity=4)
        p1 = join(5, sid)['player_id']
        p2 = join(6, sid)['player_id']
        start(sid)
        attend(sid, p1)
        attend(sid, p2)
        finalize(sid)
        must_user(db, 1, f"SELECT public.cancel_registration('{sid}'::uuid, '{p2}'::uuid, 'đổi roster', '{newreq()}');", 'cancel after finalize')
        assert billing_state(sid) == 'stale', 'hủy confirmed sau chốt phải stale'
    run_test("Stale: đổi roster confirmed sau chốt làm stale", t_roster_after_finalize_stale)

    def t_not_finalized_gate():
        sid = create_and_publish(1, 'NotFin', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        r = user_exec(db, 5, f"SELECT public.submit_payment('{p}'::uuid, 10000, 'bank_transfer', NULL, '{newreq()}');")
        assert expect_error(r, 'BILLING_NOT_FINALIZED'), f"chưa chốt phí phải bị chặn: {r.stderr}"
        r = user_exec(db, 1, f"SELECT public.record_cash_payment('{p}'::uuid, 10000, NULL, '{newreq()}');")
        assert expect_error(r, 'BILLING_NOT_FINALIZED'), f"cash khi chưa chốt phải bị chặn: {r.stderr}"
        v = must(db, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'v')
        r = user_exec(db, 1, f"SELECT public.complete_session('{sid}'::uuid, {v}::bigint, '{newreq()}');")
        assert expect_error(r, 'BILLING_NOT_FINALIZED'), f"complete khi chưa chốt phải bị chặn: {r.stderr}"
    run_test("Gate: chưa chốt phí -> BILLING_NOT_FINALIZED cho submit/cash/complete", t_not_finalized_gate)

    # ======================================================== tiền đã thu
    def t_refinalize_not_below_paid():
        sid = create_and_publish(1, 'PaidGuard', capacity=4)
        p = join(5, sid)['player_id']
        other = join(6, sid)['player_id']
        start(sid)
        attend(sid, p)
        attend(sid, other)
        post_expense(sid, 100000)  # p và other mỗi người 50.000
        finalize(sid)
        pay = submit_ok(p, 50000)
        confirm(pay['payment_id'])
        # p bị loại khỏi tập billable (no_show) -> due mới 0 < paid 50000 -> chặn chốt lại
        attend(sid, p, 'no_show')
        b = must(db, f"SELECT billing_input_version FROM public.sessions WHERE id='{sid}';", 'b')
        v = must(db, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'v')
        r = user_exec(db, 1, f"SELECT public.finalize_session_charges('{sid}'::uuid, {v}::bigint, {b}::bigint, 'no_show', '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), f"refinalize không được giảm due dưới paid: {r.stderr}"
        # payment vẫn còn nguyên
        st = must(db, f"SELECT status FROM public.payments WHERE id='{pay['payment_id']}';", 'pay status')
        assert st == 'confirmed', st
    run_test("Tiền đã thu: refinalize không giảm due dưới paid (kể cả người bị loại khỏi billable)", t_refinalize_not_below_paid)

    def t_refinalize_keeps_payment_and_ledger_once():
        sid = create_and_publish(1, 'NoDouble', capacity=4, club_link=SHARED['club'])
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 100000)
        finalize(sid)
        pay = submit_ok(p, 100000)
        confirm(pay['payment_id'])
        incomes = must(db, f"SELECT count(*) FROM public.club_transactions WHERE source_payment_id='{pay['payment_id']}';", 'income count')
        assert incomes == '1', incomes
        # refinalize cao hơn (thêm chi phí) -> due tăng, không tạo ledger thu lặp
        post_expense(sid, 200000)
        finalize(sid, reason='tăng chi phí')
        incomes2 = must(db, f"SELECT count(*) FROM public.club_transactions WHERE source_payment_id='{pay['payment_id']}';", 'income count 2')
        assert incomes2 == '1', f"refinalize không được ghi ledger thu lặp: {incomes2}"
        st = must(db, f"SELECT status FROM public.payments WHERE id='{pay['payment_id']}';", 'pay status')
        assert st == 'confirmed', st
    run_test("Tiền đã thu: refinalize giữ payment, không ghi ledger thu lặp", t_refinalize_keeps_payment_and_ledger_once)

    # ======================================================= thanh toán/idempotency
    def t_submit_replay_and_conflict():
        sid = create_and_publish(1, 'SubmitReplay', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 100000)
        finalize(sid)
        req = newreq()
        a = submit_ok(p, 40000, req=req)
        b = submit_ok(p, 40000, req=req)
        assert a['payment_id'] == b['payment_id'], 'replay phải trả cùng payment'
        n = must(db, f"SELECT count(*) FROM public.payments WHERE session_player_id='{p}';", 'pay count')
        assert n == '1', n
        r = user_exec(db, 5, f"SELECT public.submit_payment('{p}'::uuid, 50000, 'bank_transfer', NULL, '{req}');")
        assert expect_error(r, 'IDEMPOTENCY_CONFLICT'), f"cùng key khác payload phải conflict: {r.stderr}"
    run_test("Idempotency: submit replay cùng key, khác payload -> IDEMPOTENCY_CONFLICT", t_submit_replay_and_conflict)

    def t_confirm_exceeds_outstanding():
        sid = create_and_publish(1, 'ConfirmCap', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 50000)
        finalize(sid)
        a = submit_ok(p, 30000)
        b = submit_ok(p, 30000)
        confirm(a['payment_id'])
        r = user_exec(db, 1, f"SELECT public.confirm_payment('{b['payment_id']}'::uuid, '{newreq()}');")
        assert expect_error(r, 'PAYMENT_EXCEEDS_OUTSTANDING'), f"xác nhận vượt due phải bị chặn: {r.stderr}"
        total = must(db, f"SELECT COALESCE(SUM(amount_vnd),0) FROM public.payments WHERE session_player_id='{p}' AND status='confirmed';", 'confirmed total')
        assert int(total) == 30000, total
    run_test("Thanh toán: tổng confirmed không vượt active due", t_confirm_exceeds_outstanding)

    def t_confirm_race():
        sid = create_and_publish(1, 'ConfirmRace', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 50000)
        finalize(sid)
        a = submit_ok(p, 30000)
        b = submit_ok(p, 30000)
        s1 = tx_script(1, f"SELECT public.confirm_payment('{a['payment_id']}'::uuid, '{newreq()}');\nSELECT pg_sleep(1.0);")
        s2 = tx_script(1, f"SELECT pg_sleep(0.2);\nSELECT public.confirm_payment('{b['payment_id']}'::uuid, '{newreq()}');")
        run_concurrent(db, [s1, s2])
        total = int(must(db, f"SELECT COALESCE(SUM(amount_vnd),0) FROM public.payments WHERE session_player_id='{p}' AND status='confirmed';", 'confirmed total'))
        assert total <= 50000, f"hai confirm tranh nhau không được thu dư: {total}"
        assert total == 30000, f"chỉ một confirm thành công: {total}"
    run_test("Đồng thời: 2 confirm tranh outstanding không thu dư", t_confirm_race)

    def t_cash_race():
        sid = create_and_publish(1, 'CashRace', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 50000)
        finalize(sid)
        s1 = tx_script(1, f"SELECT public.record_cash_payment('{p}'::uuid, 30000, NULL, '{newreq()}');\nSELECT pg_sleep(1.0);")
        s2 = tx_script(1, f"SELECT pg_sleep(0.2);\nSELECT public.record_cash_payment('{p}'::uuid, 30000, NULL, '{newreq()}');")
        run_concurrent(db, [s1, s2])
        total = int(must(db, f"SELECT COALESCE(SUM(amount_vnd),0) FROM public.payments WHERE session_player_id='{p}' AND status='confirmed';", 'cash total'))
        assert total == 30000, f"hai cash tranh nhau chỉ một thành công: {total}"
    run_test("Đồng thời: 2 ghi tiền mặt tranh outstanding không thu dư", t_cash_race)

    def t_cash_exceeds():
        sid = create_and_publish(1, 'CashCap', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 50000)
        finalize(sid)
        cash(p, 30000)
        r = user_exec(db, 1, f"SELECT public.record_cash_payment('{p}'::uuid, 30000, NULL, '{newreq()}');")
        assert expect_error(r, 'PAYMENT_EXCEEDS_OUTSTANDING'), f"cash vượt outstanding phải bị chặn: {r.stderr}"
    run_test("Thanh toán: cash không thu dư outstanding", t_cash_exceeds)

    def t_cash_atomic_and_ledger():
        sid = create_and_publish(1, 'CashLed', capacity=4, club_link=SHARED['club'])
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 50000)
        finalize(sid)
        res = cash(p, 50000, actor=3)  # treasurer
        assert res['status'] == 'confirmed' and res['method'] == 'cash', res
        led = must(db, f"SELECT count(*) FROM public.club_transactions WHERE source_payment_id='{res['payment_id']}';", 'cash ledger')
        assert led == '1', led
    run_test("Thanh toán: cash tạo+confirm nguyên tử và đúng một entry quỹ", t_cash_atomic_and_ledger)

    def t_reverse_payment_once():
        sid = create_and_publish(1, 'RevPay', capacity=4, club_link=SHARED['club'])
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 100000)
        finalize(sid)
        pay = submit_ok(p, 100000)
        confirm(pay['payment_id'])
        must_user(db, 1, f"SELECT public.reverse_payment('{pay['payment_id']}'::uuid, 'khách chuyển nhầm', '{newreq()}');", 'reverse')
        r = user_exec(db, 1, f"SELECT public.reverse_payment('{pay['payment_id']}'::uuid, 'lần hai', '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), f"đảo hai lần phải bị chặn: {r.stderr}"
        rev = must(db, f"SELECT count(*) FROM public.club_transactions ct WHERE ct.reversal_of IN (SELECT id FROM public.club_transactions WHERE source_payment_id='{pay['payment_id']}');", 'reversal count')
        assert rev == '1', f"chỉ một entry đảo: {rev}"
        st = must(db, f"SELECT status FROM public.payments WHERE id='{pay['payment_id']}';", 'pay status')
        assert st == 'reversed', st
    run_test("Thanh toán: đảo một lần, giữ payment, entry đảo duy nhất", t_reverse_payment_once)

    def t_reject_stale_allowed():
        sid = create_and_publish(1, 'RejectStale', capacity=4, club_link=SHARED['club'])
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 50000)
        finalize(sid)
        pay = submit_ok(p, 50000)
        post_expense(sid, 10000)  # stale
        assert billing_state(sid) == 'stale'
        res = json.loads(must_user(db, 1, f"SELECT public.reject_payment('{pay['payment_id']}'::uuid, 'sai số tiền', '{newreq()}');", 'reject while stale'))
        assert res['status'] == 'rejected', res
        led = must(db, f"SELECT count(*) FROM public.club_transactions WHERE source_payment_id='{pay['payment_id']}';", 'no ledger on reject')
        assert led == '0', led
    run_test("Replay/history: reject vẫn được khi stale, không ghi ledger", t_reject_stale_allowed)

    def t_confirm_already_and_replay_after_stale():
        sid = create_and_publish(1, 'ReplayStale', capacity=4, club_link=SHARED['club'])
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 100000)
        finalize(sid)
        pay = submit_ok(p, 100000)
        confirm(pay['payment_id'])
        post_expense(sid, 10000)  # stale
        # confirm lại payment đã confirmed: trả kết quả hiện tại, không cần current
        again = confirm(pay['payment_id'])
        assert again['status'] == 'confirmed' and again.get('already_confirmed') is True, again
        led = must(db, f"SELECT count(*) FROM public.club_transactions WHERE source_payment_id='{pay['payment_id']}';", 'ledger once')
        assert led == '1', led
    run_test("Replay/history: confirm đã confirmed trả kết quả hiện tại, không ghi ledger lặp dù stale", t_confirm_already_and_replay_after_stale)

    # ============================================================== ledger/quỹ
    def t_expense_ledger_scope():
        sid_club = create_and_publish(1, 'ExpClub', capacity=4, club_link=SHARED['club'])
        res = post_expense(sid_club, 70000)
        led = must(db, f"SELECT count(*) FROM public.club_transactions WHERE source_expense_id='{res['expense_id']}' AND source_type='session_expense';", 'club expense ledger')
        assert led == '1', led
        sid_alone = create_and_publish(1, 'ExpAlone', capacity=4)
        res2 = post_expense(sid_alone, 70000)
        led2 = must(db, f"SELECT count(*) FROM public.club_transactions WHERE source_expense_id='{res2['expense_id']}';", 'standalone ledger')
        assert led2 == '0', f"buổi độc lập không tạo ledger CLB: {led2}"
        assert res2['club_ledger_entry'] is False, res2
    run_test("Ledger: chi phí buổi CLB sinh một entry, buổi độc lập không", t_expense_ledger_scope)

    def t_reverse_expense_once():
        sid = create_and_publish(1, 'RevExp', capacity=4, club_link=SHARED['club'])
        res = post_expense(sid, 80000)
        must_user(db, 1, f"SELECT public.reverse_session_expense('{sid}'::uuid, '{res['expense_id']}'::uuid, 'huỷ sân', '{newreq()}');", 'reverse expense')
        r = user_exec(db, 1, f"SELECT public.reverse_session_expense('{sid}'::uuid, '{res['expense_id']}'::uuid, 'lần hai', '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), f"đảo chi phí hai lần phải bị chặn: {r.stderr}"
        rev = must(db, f"SELECT count(*) FROM public.club_transactions ct WHERE ct.reversal_of IN (SELECT id FROM public.club_transactions WHERE source_expense_id='{res['expense_id']}');", 'reversal count')
        assert rev == '1', rev
        st = must(db, f"SELECT status FROM public.session_expenses WHERE id='{res['expense_id']}';", 'expense status')
        assert st == 'reversed', st
    run_test("Ledger: đảo chi phí một lần, giữ nguồn và entry đảo duy nhất", t_reverse_expense_once)

    def t_manual_tx_and_reverse():
        sid_actor = 1
        res = json.loads(must_user(db, sid_actor, f"SELECT public.post_manual_club_transaction('{SHARED['club']}'::uuid, 'income', 100000, 'đóng quỹ', '{newreq()}');", 'manual income'))
        assert isinstance(res['balance_vnd'], int) and res['source_type'] == 'manual', res
        r = user_exec(db, 2, f"SELECT public.post_manual_club_transaction('{SHARED['club']}'::uuid, 'expense', 1000, 'x', '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"club host không ghi quỹ thủ công: {r.stderr}"
        # đảo entry payment (tự sinh) phải bị chặn
        sid = create_and_publish(1, 'ManualRev', capacity=4, club_link=SHARED['club'])
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        post_expense(sid, 10000)
        finalize(sid)
        pay = submit_ok(p, 10000)
        confirm(pay['payment_id'])
        auto_tx = must(db, f"SELECT id FROM public.club_transactions WHERE source_payment_id='{pay['payment_id']}';", 'auto tx')
        r = user_exec(db, 1, f"SELECT public.reverse_club_transaction('{auto_tx}'::uuid, 'x', '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), f"không đảo entry tự sinh qua hàm manual: {r.stderr}"
        rev = json.loads(must_user(db, 1, f"SELECT public.reverse_club_transaction('{res['transaction_id']}'::uuid, 'hoàn quỹ', '{newreq()}');", 'reverse manual'))
        assert 'balance_vnd' in rev, rev
        r = user_exec(db, 1, f"SELECT public.reverse_club_transaction('{res['transaction_id']}'::uuid, 'lần hai', '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), f"đảo quỹ hai lần phải bị chặn: {r.stderr}"
    run_test("Ledger: quỹ manual chỉ owner/treasurer, đảo một lần, không đảo entry tự sinh", t_manual_tx_and_reverse)

    def t_ledger_balance_sum():
        ledger = json.loads(must_user(db, 3, f"SELECT public.get_club_ledger('{SHARED['club']}'::uuid, 100, 0);", 'treasurer ledger'))
        expected = int(must(db, f"SELECT COALESCE(SUM(CASE WHEN direction='income' THEN amount_vnd ELSE -amount_vnd END),0) FROM public.club_transactions WHERE club_id='{SHARED['club']}';", 'sum'))
        assert ledger['balance_vnd'] == expected, (ledger['balance_vnd'], expected)
    run_test("Ledger: số dư trả từ SUM DB khớp ledger", t_ledger_balance_sum)

    # ============================================================== complete
    def t_complete_requires_current_and_state():
        # published -> INVALID_STATE
        sid = create_and_publish(1, 'CompletePub', capacity=4)
        v = must(db, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'v')
        r = user_exec(db, 1, f"SELECT public.complete_session('{sid}'::uuid, {v}::bigint, '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), f"complete khi chưa in_progress phải bị chặn: {r.stderr}"
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        finalize(sid)  # free, revision current charges 0
        v = must(db, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'v2')
        sc = must(db, f"SELECT count(*) FROM public.session_charges sc JOIN public.charge_revisions cr ON cr.id=sc.revision_id WHERE cr.session_id='{sid}' AND cr.status='active' AND sc.amount_due_vnd=0;", 'zero charges')
        assert int(sc) >= 1, sc
        res = json.loads(must_user(db, 1, f"SELECT public.complete_session('{sid}'::uuid, {v}::bigint, '{newreq()}');", 'complete'))
        assert res['lifecycle'] == 'completed', res
        assert must(db, f"SELECT lifecycle FROM public.sessions WHERE id='{sid}';", 'lc') == 'completed'
    run_test("Complete: chỉ in_progress và cần revision current (buổi miễn phí charges 0)", t_complete_requires_current_and_state)

    def t_complete_requires_management():
        sid = create_and_publish(1, 'CompletePerm', capacity=4)
        p = join(5, sid)['player_id']
        start(sid)
        attend(sid, p)
        finalize(sid)
        v = must(db, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'v')
        r = user_exec(db, 5, f"SELECT public.complete_session('{sid}'::uuid, {v}::bigint, '{newreq()}');")
        assert expect_error(r, 'FORBIDDEN'), f"player không kết thúc buổi: {r.stderr}"
    run_test("Complete: chỉ host/quản lý", t_complete_requires_management)

    def t_invalid_input_rollback():
        sid = create_and_publish(1, 'InvalidExp', capacity=4, club_link=SHARED['club'])
        biv0 = must(db, f"SELECT billing_input_version FROM public.sessions WHERE id='{sid}';", 'biv0')
        r = user_exec(db, 1, f"SELECT public.post_session_expense('{sid}'::uuid, 'court', 'âm', -5, '{newreq()}');")
        assert expect_error(r, 'INVALID_INPUT'), f"amount âm phải bị chặn: {r.stderr}"
        assert must(db, f"SELECT count(*) FROM public.session_expenses WHERE session_id='{sid}';", 'exp count') == '0'
        assert must(db, f"SELECT billing_input_version FROM public.sessions WHERE id='{sid}';", 'biv') == biv0, 'biv không đổi khi lỗi'
        assert must(db, f"SELECT count(*) FROM public.club_transactions ct JOIN public.session_expenses e ON e.id=ct.source_expense_id WHERE e.session_id='{sid}';", 'tx count') == '0'
    run_test("Rollback: input sai không tạo expense/ledger và không tăng billing_input_version", t_invalid_input_rollback)


run_suite(CLEAN)
run_suite(LEGACY)

passed = sum(1 for r in results if r['status'] == 'PASS')
failed = sum(1 for r in results if r['status'] == 'FAIL')
print("\n==========================================")
print(f"KẾT QUẢ KIỂM THỬ BH-06: TỔNG {len(results)} | PASS {passed} | FAIL {failed}")
print("==========================================")

report_file = ROOT / f"bh06_test_results_{stamp}.json"
report_file.write_text(json.dumps({
    'timestamp': stamp,
    'tested_commit': subprocess.check_output(['git', '-C', str(REPO_ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
    'worktree_dirty': bool(subprocess.check_output(['git', '-C', str(REPO_ROOT), 'status', '--porcelain'], text=True).strip()),
    'migration_sha256': {p.name: hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in sorted((REPO_ROOT / 'supabase/migrations').glob('*.sql'))},
    'total': len(results),
    'passed': passed,
    'failed': failed,
    'tests': results,
}, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Results file: {report_file}")

if failed > 0:
    sys.exit(1)
