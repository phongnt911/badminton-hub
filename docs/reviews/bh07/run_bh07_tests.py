"""BH-07A DB runner: complete -> history/summary -> debt/payment after complete.

Pham vi:
- Complete chi in_progress + billing current; khong doi hoi thu du tien.
- Retry/idempotency/version conflict/audit cho complete.
- Lich su/detail sau complete, phan trang va ACL.
- Summary tong hop server-side cho management/finance, khong lo contact/bank/player.
- Cong no va cac thao tac tai chinh duoc phep sau complete (submit/confirm/cash/
  reject/reverse/refinalize), khong lap ledger/payment, khong thu du.
- Upgrade DB tu BH-06 (khong co migration BH-07) sang BH-07: du lieu cu van doc
  duoc bang history/summary, khong bi ghi de.

Khong phai HTTP/PostgREST/JWT/Auth that. Chi PostgreSQL local + Auth stub, giong
runner BH-02..06. Script tu tao DB `bh07_clean_*` va `bh07_upgrade_*`, khong xoa
DB khac.
"""

import datetime
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
CONTAINER = os.environ.get('BH02_TEST_CONTAINER', 'bh02-test-postgres')
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
CLEAN = 'bh07_clean_' + STAMP
UPGRADE = 'bh07_upgrade_' + STAMP
MIGRATIONS = REPO_ROOT / 'supabase/migrations'
BH07_MIGRATION = '20261020180000_bh07_reads.sql'

DB = None
VENUE = None
CLUB1 = None
CLUB2 = None


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


def iso(days=0, hours=0, minutes=0):
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


def load(raw):
    return json.loads(raw)


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
    return [p.communicate() + (p.returncode,) for p in procs]


# ---------------------------------------------------------------------------
# Setup DB / migration chain
# ---------------------------------------------------------------------------
setup_auth = """
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users(id uuid primary key, email text, raw_user_meta_data jsonb);
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;
GRANT USAGE ON SCHEMA auth TO anon, authenticated;
GRANT EXECUTE ON FUNCTION auth.uid() TO anon, authenticated;
"""


def apply_migration(db, path):
    must(db, path.read_text(encoding='utf-8'), 'migration ' + path.name)


def create_db(name, label):
    must('postgres', f'DROP DATABASE IF EXISTS {name};', f'drop {label}')
    must('postgres', f'CREATE DATABASE {name};', f'create {label}')
    must(name, setup_auth, f'auth stub {label}')


def seed_base(db, label):
    stmts = []
    for n in range(1, 13):
        stmts.append(
            f"INSERT INTO auth.users(id, email, raw_user_meta_data) VALUES ({q(n)}, "
            f"'{label}{n}@example.invalid', jsonb_build_object('display_name', 'BH07 {label} {n}')) "
            "ON CONFLICT (id) DO NOTHING;"
        )
    must(db, '\n'.join(stmts), 'seed auth users')

    venue = must(db, f"""
      INSERT INTO public.venues(name, address, area, phone_number, court_count, status)
      VALUES ('Sân BH07 {label}', '1 Nguyễn Trãi', 'Nha Trang', '0900000700', 8, 'active')
      RETURNING id;
    """, 'seed venue')

    club1 = must(db, f"""
      INSERT INTO public.clubs(owner_user_id, name, visibility, status)
      VALUES ({q(1)}, 'CLB BH07 {label}', 'public', 'active') RETURNING id;
    """, 'seed club1')
    club2 = must(db, f"""
      INSERT INTO public.clubs(owner_user_id, name, visibility, status)
      VALUES ({q(8)}, 'CLB BH07 Khác {label}', 'public', 'active') RETURNING id;
    """, 'seed club2')

    must(db, f"""
      INSERT INTO public.club_members(club_id, user_id, display_name, role, status, joined_at) VALUES
        ('{club1}', {q(1)}, 'Owner', 'owner', 'active', now()),
        ('{club1}', {q(2)}, 'HostTwo', 'host', 'active', now()),
        ('{club1}', {q(3)}, 'Treasurer', 'treasurer', 'active', now()),
        ('{club1}', {q(4)}, 'MemberFour', 'member', 'active', now()),
        ('{club1}', {q(5)}, 'PlayerFive', 'member', 'active', now()),
        ('{club1}', {q(6)}, 'PlayerSix', 'member', 'active', now()),
        ('{club2}', {q(8)}, 'OwnerOther', 'owner', 'active', now()),
        ('{club2}', {q(9)}, 'MemberOther', 'member', 'active', now());
    """, 'seed club members')

    must_user(db, 1, "SELECT public.set_host_bank_account('VCB', '1111222233', 'HOST ONE', "
                     f"'{newreq()}');", 'host1 bank')
    must_user(db, 1, f"SELECT public.set_club_bank_account('{club1}'::uuid, 'TCB', '9999888877', "
                     f"'CLB BH07', '{newreq()}');", 'club1 bank')
    return venue, club1, club2


# ---------------------------------------------------------------------------
# Fixture helpers (dung DB/VENUE/CLUB global sau khi run_suite bat dau)
# ---------------------------------------------------------------------------
def create_session(actor, title, *, club=None, visibility='unlisted',
                   fee_mode='split_actual', member_fee=None, guest_fee=None,
                   capacity=10, start_days=1, start_hours=0):
    club_sql = f"'{club}'::uuid" if club else 'NULL'
    mf = str(member_fee) if member_fee is not None else 'NULL'
    gf = str(guest_fee) if guest_fee is not None else 'NULL'
    stmt = (
        f"SELECT public.create_session(p_venue_id=>'{VENUE}'::uuid, p_title=>'{title}', "
        f"p_starts_at=>'{iso(start_days, start_hours)}', "
        f"p_ends_at=>'{iso(start_days, start_hours + 2)}', p_capacity=>{capacity}, "
        f"p_court_count=>2, p_club_id=>{club_sql}, p_visibility=>'{visibility}', "
        f"p_approval_mode=>'auto_confirm', p_fee_mode=>'{fee_mode}', "
        f"p_member_fee_vnd=>{mf}, p_guest_fee_vnd=>{gf}, p_request_id=>'{newreq()}');"
    )
    return load(must_user(DB, actor, stmt, f'create {title}'))['id']


def publish(sid, actor):
    must_user(DB, actor, f"SELECT public.set_session_lifecycle('{sid}'::uuid, 'publish', '{newreq()}');",
              'publish')


def join(actor, sid, contact=None):
    contact_sql = f"'{contact}'" if contact else 'NULL'
    return load(must_user(DB, actor,
        f"SELECT public.request_join_session('{sid}'::uuid, {contact_sql}, '{newreq()}');", 'join'))


def add_guest(actor, sid, name, exempt=False, contact=None):
    contact_sql = f"'{contact}'" if contact else 'NULL'
    return load(must_user(DB, actor,
        f"SELECT public.add_session_player('{sid}'::uuid, NULL, '{name}', {contact_sql}, "
        f"{'TRUE' if exempt else 'FALSE'}, FALSE, '{newreq()}');", 'add guest'))


def start(sid, actor):
    must_user(DB, actor, f"SELECT public.start_session('{sid}'::uuid, '{newreq()}');", 'start')


def attend(sid, player_id, actor, status='present'):
    return load(must_user(DB, actor,
        f"SELECT public.record_attendance('{sid}'::uuid, '{player_id}'::uuid, '{status}', "
        f"'{newreq()}');", 'attend'))


def post_expense(sid, amount, actor=1, category='court', title='Tiền sân'):
    return load(must_user(DB, actor,
        f"SELECT public.post_session_expense('{sid}'::uuid, '{category}', '{title}', {amount}, "
        f"'{newreq()}');", 'expense'))


def session_version(sid):
    return int(must(DB, f"SELECT version FROM public.sessions WHERE id='{sid}';", 'version'))


def billing_version(sid):
    return int(must(DB, f"SELECT billing_input_version FROM public.sessions WHERE id='{sid}';", 'billing version'))


def billing_state(sid):
    return must(DB, f"SELECT public.session_billing_state('{sid}');", 'billing state')


def lifecycle(sid):
    return must(DB, f"SELECT lifecycle FROM public.sessions WHERE id='{sid}';", 'lifecycle')


def finalize(sid, actor=1, reason=None, expected_version=None, expected_biv=None):
    v = session_version(sid) if expected_version is None else expected_version
    b = billing_version(sid) if expected_biv is None else expected_biv
    reason_sql = f"'{reason}'" if reason else 'NULL'
    return load(must_user(DB, actor,
        f"SELECT public.finalize_session_charges('{sid}'::uuid, {v}::bigint, {b}::bigint, "
        f"{reason_sql}, '{newreq()}');", 'finalize'))


def cash(player_id, amount, actor=1, reference=None, req=None):
    ref = f"'{reference}'" if reference else 'NULL'
    return load(must_user(DB, actor,
        f"SELECT public.record_cash_payment('{player_id}'::uuid, {amount}, {ref}, "
        f"'{req or newreq()}');", 'cash'))


def complete(sid, actor=1, version=None, req=None):
    v = session_version(sid) if version is None else version
    return user_exec(DB, actor,
        f"SELECT public.complete_session('{sid}'::uuid, {v}::bigint, '{req or newreq()}');")


def complete_ok(sid, actor=1, version=None, req=None):
    r = complete(sid, actor=actor, version=version, req=req)
    if r.returncode != 0:
        raise RuntimeError('complete: ' + r.stderr.strip())
    lines = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    return load(lines[-1])


def finance(sid, actor=1, limit=50, offset=0):
    return load(must_user(DB, actor,
        f"SELECT public.get_session_finance('{sid}'::uuid, {limit}, {offset});", 'finance'))


def summary(sid, actor=1):
    return load(must_user(DB, actor,
        f"SELECT public.get_session_summary('{sid}'::uuid);", 'summary'))


def summary_result(sid, actor=1):
    return user_exec(DB, actor, f"SELECT public.get_session_summary('{sid}'::uuid);")


def history(actor, limit=20, offset=0, club_id=None, from_=None, to=None):
    club_sql = f"'{club_id}'::uuid" if club_id else 'NULL'
    from_sql = f"'{from_}'" if from_ else 'NULL'
    to_sql = f"'{to}'" if to else 'NULL'
    raw = must_user(DB, actor,
        "SELECT public.list_my_session_history("
        f"p_limit=>{limit}, p_offset=>{offset}, p_club_id=>{club_sql}, "
        f"p_from=>{from_sql}, p_to=>{to_sql});", 'history')
    return load(raw)


def list_my(actor, limit=50, offset=0):
    return load(must_user(DB, actor,
        f"SELECT public.list_my_sessions({limit}, {offset});", 'list my sessions'))


def detail(sid, actor=1):
    return load(must_user(DB, actor,
        f"SELECT public.get_session_public_detail('{sid}'::uuid);", 'detail'))


def payment_instructions(sid, player_id, actor):
    return load(must_user(DB, actor,
        f"SELECT public.get_payment_instructions('{sid}'::uuid, '{player_id}'::uuid);",
        'payment instructions'))


def submit_payment(player_id, amount, actor, req=None, reference=None):
    ref = f"'{reference}'" if reference else 'NULL'
    r = user_exec(DB, actor,
        f"SELECT public.submit_payment('{player_id}'::uuid, {amount}, 'bank_transfer', {ref}, "
        f"'{req or newreq()}');")
    if r.returncode != 0:
        raise RuntimeError('submit payment: ' + r.stderr.strip())
    lines = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    return load(lines[-1])


def confirm_payment(payment_id, actor=1, req=None):
    return load(must_user(DB, actor,
        f"SELECT public.confirm_payment('{payment_id}'::uuid, '{req or newreq()}');", 'confirm payment'))


def reject_payment(payment_id, actor=1, reason='Sai chứng từ', req=None):
    return load(must_user(DB, actor,
        f"SELECT public.reject_payment('{payment_id}'::uuid, '{reason}', '{req or newreq()}');",
        'reject payment'))


def reverse_payment(payment_id, actor=1, reason='Hoàn tiền', req=None):
    return load(must_user(DB, actor,
        f"SELECT public.reverse_payment('{payment_id}'::uuid, '{reason}', '{req or newreq()}');",
        'reverse payment'))


def reverse_expense(expense_id, sid, actor=1, reason='Đảo chi phí'):
    return load(must_user(DB, actor,
        f"SELECT public.reverse_session_expense('{sid}'::uuid, '{expense_id}'::uuid, '{reason}', "
        f"'{newreq()}');", 'reverse expense'))


def audit_count(sid, action):
    return int(must(DB,
        f"SELECT count(*) FROM public.audit_events WHERE session_id='{sid}' AND action='{action}';",
        'audit count'))


def op_count(request_id, operation='complete_session'):
    return int(must(DB,
        f"SELECT count(*) FROM public.operation_requests WHERE request_id='{request_id}' "
        f"AND operation='{operation}';", 'operation count'))


def ledger_payment_count(sid, source_type='payment'):
    return int(must(DB, f"""
      SELECT count(*) FROM public.club_transactions ct
      JOIN public.payments p ON p.id=ct.source_payment_id
      JOIN public.session_players sp ON sp.id=p.session_player_id
      WHERE sp.session_id='{sid}' AND ct.source_type='{source_type}';
    """, 'ledger payment count'))


def ledger_reversal_count(sid):
    return int(must(DB, f"""
      SELECT count(*) FROM public.club_transactions ct
      JOIN public.club_transactions orig ON orig.id=ct.reversal_of
      JOIN public.payments p ON p.id=orig.source_payment_id
      JOIN public.session_players sp ON sp.id=p.session_player_id
      WHERE sp.session_id='{sid}' AND ct.source_type='reversal';
    """, 'ledger reversal count'))


def payment_status(payment_id):
    return must(DB, f"SELECT status FROM public.payments WHERE id='{payment_id}';", 'payment status')


def expense_id(sid, order='created_at ASC, id ASC'):
    return must(DB, f"SELECT id FROM public.session_expenses WHERE session_id='{sid}' ORDER BY {order} LIMIT 1;",
                'expense id')


def make_in_progress(title, *, host=1, club=CLUB1, user_players=(5,), guest_names=(),
                     present=None, no_show=(), expense=100000, expense_count=1,
                     start_days=1, visibility='unlisted', cash_before=None):
    """Tao session published -> start -> diem danh -> chot phi (current)."""
    sid = create_session(host, title, club=club, visibility=visibility, start_days=start_days)
    publish(sid, host)
    players = {}
    for actor in user_players:
        players[actor] = join(actor, sid)['player_id']
    guests = {}
    for idx, name in enumerate(guest_names):
        guests[name] = add_guest(host, sid, name, exempt=False)['player_id']
    start(sid, host)
    if present is None:
        present = list(players.values()) + list(guests.values())
    for pid in present:
        attend(sid, pid, host, 'present')
    for pid in no_show:
        attend(sid, pid, host, 'no_show')
    if expense and expense > 0:
        for _ in range(expense_count):
            post_expense(sid, expense, actor=host)
    finalize(sid, actor=host)
    if cash_before:
        for actor, amount in cash_before.items():
            pid = players.get(actor) or guests.get(actor)
            if pid is None:
                raise RuntimeError(f'cash_before actor {actor} không có player')
            cash(pid, amount, actor=host)
    return sid, players, guests


def make_completed(title, **kwargs):
    sid, players, guests = make_in_progress(title, **kwargs)
    complete_ok(sid, actor=kwargs.get('host', 1))
    return sid, players, guests


results = []


def run_test(name, fn):
    try:
        fn()
        results.append({'name': name, 'status': 'PASS'})
        print(f"PASS: {name}")
    except Exception as exc:  # noqa: BLE001 - runner ghi lại lỗi
        results.append({'name': name, 'status': 'FAIL', 'error': str(exc)})
        print(f"FAIL: {name} -> {exc}")


# ---------------------------------------------------------------------------
# Suite tren DB sach
# ---------------------------------------------------------------------------
def run_suite(db):
    global DB, VENUE, CLUB1, CLUB2
    DB = db
    VENUE, CLUB1, CLUB2 = seed_base(db, 'S')
    print(f"Suite DB {db}: venue={VENUE}, club1={CLUB1}, club2={CLUB2}")

    # ------------------------------------------------------------- complete
    def t_complete_not_finalized():
        sid = create_session(1, 'CompleteNoFinalize', club=CLUB1)
        publish(sid, 1)
        p = join(5, sid)['player_id']
        start(sid, 1)
        attend(sid, p, 1)
        v = session_version(sid)
        req = newreq()
        r = user_exec(DB, 1,
            f"SELECT public.complete_session('{sid}'::uuid, {v}::bigint, '{req}');")
        assert expect_error(r, 'BILLING_NOT_FINALIZED'), r.stderr
        assert lifecycle(sid) == 'in_progress'
        assert session_version(sid) == v
        assert audit_count(sid, 'SESSION_COMPLETED') == 0
        assert op_count(req) == 0
    run_test('Complete: chưa chốt phí bị BILLING_NOT_FINALIZED, không đổi lifecycle/version/audit', t_complete_not_finalized)

    def t_complete_stale():
        sid = create_session(1, 'CompleteStale', club=CLUB1)
        publish(sid, 1)
        p = join(5, sid)['player_id']
        start(sid, 1)
        attend(sid, p, 1)
        post_expense(sid, 100000)
        finalize(sid)
        post_expense(sid, 50000)
        assert billing_state(sid) == 'stale'
        v = session_version(sid)
        req = newreq()
        r = user_exec(DB, 1,
            f"SELECT public.complete_session('{sid}'::uuid, {v}::bigint, '{req}');")
        assert expect_error(r, 'BILLING_STALE'), r.stderr
        assert lifecycle(sid) == 'in_progress'
        assert session_version(sid) == v
        assert audit_count(sid, 'SESSION_COMPLETED') == 0
        assert op_count(req) == 0
    run_test('Complete: revision stale bị BILLING_STALE, không đổi lifecycle/version/audit', t_complete_stale)

    def t_complete_version_conflict():
        sid, players, _ = make_in_progress('CompleteVersion', club=CLUB1)
        v = session_version(sid)
        r = complete(sid, version=v + 1)
        assert expect_error(r, 'VERSION_CONFLICT'), r.stderr
        assert lifecycle(sid) == 'in_progress'
        assert session_version(sid) == v
        assert audit_count(sid, 'SESSION_COMPLETED') == 0
    run_test('Complete: version cũ trả VERSION_CONFLICT, không đổi dữ liệu', t_complete_version_conflict)

    def t_complete_acl():
        sid, players, _ = make_in_progress('CompleteAcl', club=CLUB1)
        v = session_version(sid)
        for actor, label in [(5, 'player'), (3, 'treasurer finance-only'),
                             (8, 'owner CLB khác'), (10, 'outsider')]:
            r = complete(sid, actor=actor, version=v)
            assert expect_error(r, 'FORBIDDEN'), f'{label} phải bị FORBIDDEN: {r.stderr}'
        r = anon_exec(DB, f"SELECT public.complete_session('{sid}'::uuid, {v}::bigint, '{newreq()}');")
        assert expect_error(r, 'permission denied'), f'anon phải bị ACL: {r.stderr}'
        assert lifecycle(sid) == 'in_progress'
        assert audit_count(sid, 'SESSION_COMPLETED') == 0

        # cohost duoc complete
        must(DB, f"INSERT INTO public.session_staff(session_id, user_id, role, status) "
                 f"VALUES ('{sid}', {q(2)}, 'cohost', 'active');", 'add cohost')
        complete_ok(sid, actor=2, version=v)
        assert lifecycle(sid) == 'completed'
        assert audit_count(sid, 'SESSION_COMPLETED') == 1
    run_test('Complete ACL: participant/finance-only/outsider/cross-club/anon bị chặn; cohost được phép', t_complete_acl)

    def t_complete_club_owner():
        # User 2 (club host) tạo buổi; owner CLB 1 (không phải host_user_id) complete.
        sid = create_session(2, 'CompleteClubOwner', club=CLUB1)
        publish(sid, 2)
        p = join(5, sid)['player_id']
        start(sid, 2)
        attend(sid, p, 2)
        finalize(sid, actor=2)
        v = session_version(sid)
        complete_ok(sid, actor=1, version=v)
        assert lifecycle(sid) == 'completed'
        assert audit_count(sid, 'SESSION_COMPLETED') == 1
    run_test('Complete: owner CLB quản lý được buổi của host khác trong CLB', t_complete_club_owner)

    def t_complete_free_session():
        sid, players, _ = make_completed('FreeSession', club=CLUB1, expense=0)
        assert lifecycle(sid) == 'completed'
        charges = must(DB, f"""
          SELECT count(*) || '|' || COALESCE(SUM(sc.amount_due_vnd), 0)
          FROM public.session_charges sc
          JOIN public.charge_revisions cr ON cr.id=sc.revision_id
          WHERE cr.session_id='{sid}' AND cr.status='active';
        """, 'free charges')
        assert charges == '1|0', charges
        s = summary(sid)
        assert s['billing_state'] == 'current'
        assert s['amount_due_total_vnd'] == 0
        assert s['total_paid_vnd'] == 0
        assert s['outstanding_total_vnd'] == 0
    run_test('Complete: buổi miễn phí vẫn cần revision current charges 0 và complete được', t_complete_free_session)

    def t_complete_debt_survives():
        sid, players, _ = make_completed('CompleteDebt', club=CLUB1, user_players=(5, 6),
                                         expense=100000)
        f = finance(sid)
        assert f['outstanding_total_vnd'] == 100000, f
        assert f['billing_state'] == 'current', f
        s = summary(sid)
        assert s['amount_due_total_vnd'] == 100000, s
        assert s['total_paid_vnd'] == 0, s
        assert s['outstanding_total_vnd'] == 100000, s
        pi = payment_instructions(sid, players[5], 5)
        assert pi['outstanding_vnd'] == 50000, pi
        d = detail(sid)
        assert d['lifecycle'] == 'completed', d
        assert d['confirmed_count'] == 2, d
    run_test('Complete + công nợ: còn nợ vẫn complete; finance/summary/payment giữ đúng công nợ', t_complete_debt_survives)

    def t_complete_replay_and_conflict():
        sid, players, _ = make_in_progress('CompleteReplay', club=CLUB1)
        v = session_version(sid)
        req = newreq()
        r1 = complete_ok(sid, actor=1, version=v, req=req)
        v2 = session_version(sid)
        assert lifecycle(sid) == 'completed'
        assert audit_count(sid, 'SESSION_COMPLETED') == 1
        assert op_count(req) == 1
        r2 = complete_ok(sid, actor=1, version=v, req=req)
        assert r2 == r1, (r1, r2)
        assert session_version(sid) == v2
        assert audit_count(sid, 'SESSION_COMPLETED') == 1
        assert op_count(req) == 1

        r3 = complete(sid, actor=1, version=v + 1, req=req)
        assert expect_error(r3, 'IDEMPOTENCY_CONFLICT'), r3.stderr
        assert audit_count(sid, 'SESSION_COMPLETED') == 1
        assert op_count(req) == 1
    run_test('Complete: replay cùng request trả cùng kết quả, không lặp audit; payload khác conflict', t_complete_replay_and_conflict)

    def t_complete_completed_new_request():
        sid, players, _ = make_completed('CompleteAgain', club=CLUB1)
        v = session_version(sid)
        r = complete(sid, actor=1, version=v, req=newreq())
        assert expect_error(r, 'INVALID_STATE'), r.stderr
        assert lifecycle(sid) == 'completed'
        assert session_version(sid) == v
        assert audit_count(sid, 'SESSION_COMPLETED') == 1
    run_test('Complete: buổi đã completed với request mới bị INVALID_STATE, không lặp audit', t_complete_completed_new_request)

    # -------------------------------------------------------------- history
    def t_history_completed_visible():
        sid, players, _ = make_completed('HistoryVisible', club=CLUB1, user_players=(5, 6),
                                         expense=100000)
        mine = list_my(1)
        assert any(x['id'] == sid and x['lifecycle'] == 'completed' for x in mine), 'host phải thấy buổi completed'
        as_finance = list_my(3)
        assert any(x['id'] == sid for x in as_finance), 'treasurer phải thấy buổi completed'
        as_player = list_my(5)
        assert all(x['id'] != sid for x in as_player), 'player không quản lý không được thấy trong list_my'
        as_outsider = list_my(10)
        assert all(x['id'] != sid for x in as_outsider), 'outsider không được thấy'
        d = detail(sid)
        assert d['lifecycle'] == 'completed'
        d_anon = load(anon_exec(DB,
            f"SELECT public.get_session_public_detail('{sid}'::uuid);").stdout.strip().splitlines()[-1])
        assert d_anon['lifecycle'] == 'completed'
        raw = json.dumps(d_anon)
        assert 'receiver' not in raw and 'phone_number' not in raw, raw
    run_test('History/detail: buổi completed vẫn đọc được đúng quyền; player/outsider không thấy trong list_my', t_history_completed_visible)

    def t_history_pagination_and_scope():
        host = 11
        made = []
        for idx, days in enumerate((1, 2, 3), start=1):
            sid, players, _ = make_completed(
                f'HistoryPaging{idx}', host=host, club=None, user_players=(5,),
                expense=50000, start_days=days)
            made.append(sid)
        # finance staff chỉ trên buổi mới nhất
        must(DB, f"INSERT INTO public.session_staff(session_id, user_id, role, status) "
                 f"VALUES ('{made[2]}', {q(7)}, 'finance', 'active');", 'finance staff history')
        page0 = history(host, limit=1, offset=0)
        page1 = history(host, limit=1, offset=1)
        page2 = history(host, limit=1, offset=2)
        page3 = history(host, limit=1, offset=3)
        assert [x['id'] for x in page0] == [made[2]], page0
        assert [x['id'] for x in page1] == [made[1]], page1
        assert [x['id'] for x in page2] == [made[0]], page2
        assert page3 == [], page3
        assert all(x['lifecycle'] == 'completed' for x in page0 + page1 + page2)

        by_finance = history(7)
        assert any(x['id'] == made[2] for x in by_finance), by_finance
        assert all(x['id'] != made[0] for x in by_finance), by_finance
        assert history(5) == [], 'participant không quản lý không có history'
        assert history(10) == [], 'outsider không có history'

        # filter ngày: H2/H3 nằm sau mốc 1.5 ngày, H1 trước mốc
        later = history(host, from_=iso(1, hours=12))
        assert {x['id'] for x in later} == {made[1], made[2]}, later
        earlier = history(host, to=iso(1, hours=12))
        assert {x['id'] for x in earlier} == {made[0]}, earlier
        # filter CLB: session host 11 không thuộc CLB1
        assert history(host, club_id=CLUB1) == [], 'filter CLB phải loại buổi độc lập'
        club_history = history(1, club_id=CLUB1)
        assert all(x['club_id'] == CLUB1 for x in club_history), club_history
    run_test('History: list_my_session_history phân trang desc, empty, finance staff, participant/outsider và filter ngày/CLB', t_history_pagination_and_scope)

    # -------------------------------------------------------------- summary
    def t_summary_aggregates_and_privacy():
        sid, players, guests = make_completed(
            'SummaryMoney', club=CLUB1, user_players=(5, 6),
            guest_names=('Sensitive Guest',),
            present=None, no_show=(),
            expense=120000, cash_before={5: 30000})
        # present mặc định gồm user 5,6 + guest; đánh dấu user 6 no_show riêng
        # (make_in_progress đã attend tất cả present; sửa 6 thành no_show là không được
        # sau finalize, nên tạo fixture riêng bên dưới thay vì dựa vào đây.)
        # Fixture này chỉ dùng để kiểm tra tổng tiền; counts được kiểm ở fixture sau.
        s = summary(sid)
        assert s['lifecycle'] == 'completed', s
        assert s['billing_state'] == 'current', s
        assert s['can_manage'] is True and s['can_view_finance'] is True, s
        assert s['present_count'] == 3, s
        assert s['confirmed_count'] == 3, s
        assert s['expenses_total_vnd'] == 120000, s
        assert s['amount_due_total_vnd'] == 120000, s
        assert s['total_paid_vnd'] == 30000, s
        assert s['outstanding_total_vnd'] == 90000, s
        raw = json.dumps(s, ensure_ascii=False)
        for forbidden in ('phone_number', 'receiver', 'account_number', 'bank_code',
                          'display_name', 'Sensitive Guest', 'charges', 'payments', 'players'):
            assert forbidden not in raw, f'summary lộ {forbidden}: {raw}'

        # ACL: cohost management-only thấy counts nhưng không thấy tiền
        must(DB, f"INSERT INTO public.session_staff(session_id, user_id, role, status) "
                 f"VALUES ('{sid}', {q(2)}, 'cohost', 'active');", 'summary cohost')
        cohost = summary(sid, actor=2)
        assert cohost['can_manage'] is True and cohost['can_view_finance'] is False, cohost
        assert cohost['present_count'] == 3 and cohost['confirmed_count'] == 3, cohost
        assert cohost['billing_state'] is None, cohost
        assert cohost['expenses_total_vnd'] is None, cohost
        assert cohost['amount_due_total_vnd'] is None and cohost['total_paid_vnd'] is None, cohost
        assert cohost['outstanding_total_vnd'] is None, cohost

        # finance-only: treasurer CLB và staff finance thấy tiền
        for actor in (3, 7):
            if actor == 7:
                must(DB, f"INSERT INTO public.session_staff(session_id, user_id, role, status) "
                         f"VALUES ('{sid}', {q(7)}, 'finance', 'active');", 'summary finance')
            fin = summary(sid, actor=actor)
            assert fin['can_view_finance'] is True, fin
            assert fin['amount_due_total_vnd'] == 120000, fin
            assert fin['total_paid_vnd'] == 30000, fin
            assert fin['outstanding_total_vnd'] == 90000, fin

        for actor, label in ((5, 'participant'), (10, 'outsider'), (8, 'cross-club')):
            r = summary_result(sid, actor)
            assert expect_error(r, 'FORBIDDEN'), f'{label} phải bị FORBIDDEN: {r.stderr}'
        r = anon_exec(DB, f"SELECT public.get_session_summary('{sid}'::uuid);")
        assert expect_error(r, 'permission denied'), f'anon phải bị ACL: {r.stderr}'
    run_test('Summary: aggregate server-side sau complete, privacy, cohost không tiền, finance/treasurer thấy tiền, ACL', t_summary_aggregates_and_privacy)

    def t_summary_counts_no_show():
        # Fixture riêng: 2 present (1 user + 1 guest), 1 no_show
        sid = create_session(1, 'SummaryCounts', club=CLUB1)
        publish(sid, 1)
        p5 = join(5, sid)['player_id']
        p6 = join(6, sid)['player_id']
        g = add_guest(1, sid, 'Guest Count')['player_id']
        start(sid, 1)
        attend(sid, p5, 1, 'present')
        attend(sid, g, 1, 'present')
        attend(sid, p6, 1, 'no_show')
        post_expense(sid, 120000)
        finalize(sid)
        complete_ok(sid)
        s = summary(sid)
        assert s['present_count'] == 2, s
        assert s['no_show_count'] == 1, s
        assert s['confirmed_count'] == 3, s
        assert s['expenses_total_vnd'] == 120000, s
        assert s['amount_due_total_vnd'] == 120000, s
        assert s['total_paid_vnd'] == 0, s
        assert s['outstanding_total_vnd'] == 120000, s
    run_test('Summary: present/no_show/confirmed và tổng tiền đúng sau complete', t_summary_counts_no_show)

    def t_summary_not_finalized_and_stale():
        sid = create_session(1, 'SummaryStates', club=CLUB1)
        publish(sid, 1)
        p = join(5, sid)['player_id']
        start(sid, 1)
        attend(sid, p, 1)
        s0 = summary(sid)
        assert s0['billing_state'] == 'not_finalized', s0
        assert s0['present_count'] == 1, s0
        assert s0['amount_due_total_vnd'] == 0 and s0['outstanding_total_vnd'] == 0, s0
        post_expense(sid, 100000)
        finalize(sid)
        s1 = summary(sid)
        assert s1['billing_state'] == 'current' and s1['amount_due_total_vnd'] == 100000, s1
        post_expense(sid, 50000)
        s2 = summary(sid)
        assert s2['billing_state'] == 'stale', s2
        assert s2['amount_due_total_vnd'] == 100000, 'summary phải trả revision cũ khi stale'
        assert s2['expenses_total_vnd'] == 150000, s2
        r = summary_result(sid, None)  # role authenticated nhưng auth.uid() NULL
        assert expect_error(r, 'UNAUTHENTICATED'), r.stderr
    run_test('Summary: not_finalized/stale có nhãn đúng, không giả current; anonymous bị chặn', t_summary_not_finalized_and_stale)

    # ------------------------------------------------------- post-complete
    def t_post_complete_submit_confirm():
        sid, players, _ = make_completed('PostSubmit', club=CLUB1, user_players=(5, 6),
                                         expense=100000)
        pay = submit_payment(players[5], 30000, actor=5)
        assert pay['status'] == 'submitted', pay
        assert summary(sid)['total_paid_vnd'] == 0, 'submitted chưa tính là đã thu'
        req = newreq()
        c1 = confirm_payment(pay['payment_id'], actor=1, req=req)
        assert c1['status'] == 'confirmed', c1
        assert ledger_payment_count(sid) == 1
        s = summary(sid)
        assert s['total_paid_vnd'] == 30000 and s['outstanding_total_vnd'] == 70000, s
        pi = payment_instructions(sid, players[5], 5)
        assert pi['outstanding_vnd'] == 20000, pi
        # replay cùng request và confirm lại payment đã confirmed: không ghi ledger lần hai
        c2 = confirm_payment(pay['payment_id'], actor=1, req=req)
        assert c2 == c1, (c1, c2)
        c3 = confirm_payment(pay['payment_id'], actor=1)
        assert c3.get('already_confirmed') is True, c3
        assert ledger_payment_count(sid) == 1
        assert summary(sid)['total_paid_vnd'] == 30000
        assert audit_count(sid, 'PAYMENT_CONFIRMED') == 1
    run_test('Sau complete: submit/confirm hoạt động, replay không lặp ledger, công nợ giảm đúng', t_post_complete_submit_confirm)

    def t_post_complete_cash_and_retry():
        sid, players, _ = make_completed('PostCash', club=CLUB1, user_players=(5, 6),
                                         expense=100000)
        req = newreq()
        c1 = cash(players[5], 20000, actor=1, req=req)
        assert c1['status'] == 'confirmed' and c1['ledger_id'], c1
        assert ledger_payment_count(sid) == 1
        c2 = cash(players[5], 20000, actor=1, req=req)
        assert c2 == c1, (c1, c2)
        assert ledger_payment_count(sid) == 1
        cash(players[6], 50000, actor=1)
        assert ledger_payment_count(sid) == 2
        s = summary(sid)
        assert s['total_paid_vnd'] == 70000 and s['outstanding_total_vnd'] == 30000, s
        r = user_exec(DB, 1,
            f"SELECT public.record_cash_payment('{players[6]}'::uuid, 60000, NULL, '{newreq()}');")
        assert expect_error(r, 'PAYMENT_EXCEEDS_OUTSTANDING'), r.stderr
        assert ledger_payment_count(sid) == 2
    run_test('Sau complete: cash tạo+confirm, retry cùng request không lặp ledger, không thu dư', t_post_complete_cash_and_retry)

    def t_post_complete_reject_reverse():
        sid, players, _ = make_completed('PostRejectReverse', club=CLUB1, user_players=(5, 6),
                                         expense=100000)
        p5 = submit_payment(players[5], 20000, actor=5)
        rej = reject_payment(p5['payment_id'], actor=1)
        assert rej['status'] == 'rejected', rej
        assert payment_status(p5['payment_id']) == 'rejected'
        assert ledger_payment_count(sid) == 0
        assert summary(sid)['total_paid_vnd'] == 0

        p6 = submit_payment(players[6], 30000, actor=6)
        c = confirm_payment(p6['payment_id'], actor=1)
        assert c['status'] == 'confirmed' and c['ledger_id'], c
        assert ledger_payment_count(sid) == 1
        rev = reverse_payment(p6['payment_id'], actor=1)
        assert rev['status'] == 'reversed', rev
        assert payment_status(p6['payment_id']) == 'reversed'
        assert ledger_reversal_count(sid) == 1
        s = summary(sid)
        assert s['total_paid_vnd'] == 0 and s['outstanding_total_vnd'] == 100000, s
        # giữ payment + ledger gốc, chỉ thêm entry đảo
        assert must(DB, f"SELECT count(*) FROM public.payments WHERE id='{p6['payment_id']}';", 'payment kept') == '1'
        r = user_exec(DB, 1,
            f"SELECT public.reverse_payment('{p6['payment_id']}'::uuid, 'Đảo lần 2', '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), r.stderr
        assert ledger_reversal_count(sid) == 1
    run_test('Sau complete: reject giữ payment không ledger; reverse một lần, giữ lịch sử/ledger đảo', t_post_complete_reject_reverse)

    def t_post_complete_refinalize_keeps_payment():
        sid, players, _ = make_completed('PostRefin', club=CLUB1, user_players=(5, 6),
                                         expense=100000, cash_before={5: 10000})
        before = summary(sid)
        r = finalize(sid, reason='Chốt lại sau complete')
        assert r['revision_no'] == 2 and r['billing_state'] == 'current', r
        after = summary(sid)
        assert after['amount_due_total_vnd'] == before['amount_due_total_vnd'] == 100000, (before, after)
        assert after['total_paid_vnd'] == 10000 and after['outstanding_total_vnd'] == 90000, after
        assert lifecycle(sid) == 'completed'
        assert must(DB, f"SELECT count(*) FROM public.payments p JOIN public.session_players sp ON sp.id=p.session_player_id WHERE sp.session_id='{sid}' AND p.status='confirmed';", 'payments kept') == '1'
    run_test('Sau complete: refinalize có lý do tạo revision mới current, giữ payment/công nợ', t_post_complete_refinalize_keeps_payment)

    def t_post_complete_refinalize_below_paid():
        sid = create_session(1, 'PostRefinBelowPaid', club=CLUB1)
        publish(sid, 1)
        p5 = join(5, sid)['player_id']
        p6 = join(6, sid)['player_id']
        start(sid, 1)
        attend(sid, p5, 1)
        attend(sid, p6, 1)
        post_expense(sid, 50000)
        post_expense(sid, 50000)
        finalize(sid)
        cash(p5, 40000, actor=1)
        complete_ok(sid)
        # đảo một chi phí sau complete: được phép, làm stale, nhưng không được giảm due dưới paid
        eid = expense_id(sid)
        rev = reverse_expense(eid, sid)
        assert rev['status'] == 'reversed', rev
        assert billing_state(sid) == 'stale'
        r = user_exec(DB, 1,
            f"SELECT public.finalize_session_charges('{sid}'::uuid, {session_version(sid)}::bigint, "
            f"{billing_version(sid)}::bigint, 'Giảm chi phí', '{newreq()}');")
        assert expect_error(r, 'INVALID_STATE'), r.stderr
        assert payment_status(must(DB, f"SELECT p.id FROM public.payments p JOIN public.session_players sp ON sp.id=p.session_player_id WHERE sp.session_id='{sid}' LIMIT 1;", 'payment id')) == 'confirmed'
        s = summary(sid)
        assert s['billing_state'] == 'stale'
        assert s['total_paid_vnd'] == 40000
        assert lifecycle(sid) == 'completed'
        # chi phí thường sau complete vẫn bị chặn
        r2 = user_exec(DB, 1,
            f"SELECT public.post_session_expense('{sid}'::uuid, 'court', 'x', 10000, '{newreq()}');")
        assert expect_error(r2, 'INVALID_STATE'), r2.stderr
    run_test('Sau complete: refinalize không được giảm due dưới paid; post expense thường bị chặn', t_post_complete_refinalize_below_paid)

    def t_complete_concurrency():
        sid, players, _ = make_in_progress('CompleteRace', club=CLUB1)
        v = session_version(sid)
        scripts = [
            tx_script(1, f"SELECT public.complete_session('{sid}'::uuid, {v}::bigint, '{newreq()}');"),
            tx_script(1, f"SELECT public.complete_session('{sid}'::uuid, {v}::bigint, '{newreq()}');"),
        ]
        out = run_concurrent(DB, scripts)
        successes = sum(1 for _, _, code in out if code == 0)
        errors = '\n'.join(err for _, err, _ in out)
        assert successes == 1, out
        assert 'INVALID_STATE' in errors or 'VERSION_CONFLICT' in errors, errors
        assert lifecycle(sid) == 'completed'
        assert audit_count(sid, 'SESSION_COMPLETED') == 1
        assert session_version(sid) == v + 1
    run_test('Đồng thời: 2 complete cùng version khác request chỉ một thành công, audit một lần', t_complete_concurrency)

    def t_acl_helpers():
        sid, players, _ = make_completed('AclSurface', club=CLUB1)
        v = session_version(sid)
        for call in [
            f"SELECT public.complete_session('{sid}'::uuid, {v}::bigint, '{newreq()}');",
            f"SELECT public.get_session_summary('{sid}'::uuid);",
            "SELECT public.list_my_session_history();",
            f"SELECT public.get_session_finance('{sid}'::uuid);",
        ]:
            r = anon_exec(DB, call)
            assert r.returncode != 0 and 'permission denied' in r.stderr, f'anon phải bị ACL: {call} -> {r.stderr}'
        # helper nội bộ vẫn không lộ cho authenticated
        for helper in [
            f"SELECT public.active_charge_revision_id('{sid}'::uuid);",
            f"SELECT public.session_billing_state('{sid}'::uuid);",
            f"SELECT public.assert_billing_current('{sid}'::uuid);",
        ]:
            r = user_exec(DB, 1, helper)
            assert expect_error(r, 'permission denied'), f'helper phải bị chặn: {helper}'
    run_test('ACL: anon không gọi complete/summary/history/finance; helper nội bộ vẫn bị chặn', t_acl_helpers)


# ---------------------------------------------------------------------------
# Upgrade DB: BH-06 -> BH-07 (du lieu completed cu van doc duoc)
# ---------------------------------------------------------------------------
def run_upgrade_suite():
    global DB, VENUE, CLUB1, CLUB2
    DB = UPGRADE
    VENUE, CLUB1, CLUB2 = seed_base(DB, 'U')
    # seed_base chạy sau khi chuỗi migration BH-06 đã áp dụng; tạo dữ liệu cũ.
    sid, players, _ = make_completed('UpgradeCompleted', club=CLUB1, user_players=(5, 6),
                                     expense=100000, cash_before={5: 30000})
    v_before = session_version(sid)
    lifecycle_before = lifecycle(sid)
    finance_before = finance(sid)
    payment_count_before = int(must(DB, f"SELECT count(*) FROM public.payments p JOIN public.session_players sp ON sp.id=p.session_player_id WHERE sp.session_id='{sid}';", 'pay count'))
    ledger_before = ledger_payment_count(sid)
    audit_before = audit_count(sid, 'SESSION_COMPLETED')

    # Áp migration BH-07 (nếu có) trên dữ liệu đã có.
    upgrade_paths = sorted(p for p in MIGRATIONS.glob('*.sql') if p.name >= BH07_MIGRATION)
    if not upgrade_paths:
        name = 'Upgrade: summary/history đọc được buổi completed cũ sau migration BH-07'
        results.append({'name': name, 'status': 'FAIL',
                        'error': f'không tìm thấy migration BH-07 >= {BH07_MIGRATION}'})
        print(f'FAIL: {name} -> không tìm thấy migration BH-07')
        return
    for p in upgrade_paths:
        apply_migration(DB, p)

    def check_old_data_unchanged():
        assert lifecycle(sid) == lifecycle_before == 'completed'
        assert session_version(sid) == v_before
        assert finance(sid)['outstanding_total_vnd'] == finance_before['outstanding_total_vnd'] == 70000
        assert int(must(DB, f"SELECT count(*) FROM public.payments p JOIN public.session_players sp ON sp.id=p.session_player_id WHERE sp.session_id='{sid}';", 'pay count after')) == payment_count_before
        assert ledger_payment_count(sid) == ledger_before
        assert audit_count(sid, 'SESSION_COMPLETED') == audit_before

    def check_summary_history_old_data():
        s = summary(sid)
        assert s['lifecycle'] == 'completed' and s['billing_state'] == 'current', s
        assert s['present_count'] == 2 and s['confirmed_count'] == 2, s
        assert s['expenses_total_vnd'] == 100000, s
        assert s['amount_due_total_vnd'] == 100000, s
        assert s['total_paid_vnd'] == 30000, s
        assert s['outstanding_total_vnd'] == 70000, s
        h = history(1, club_id=CLUB1)
        assert any(x['id'] == sid for x in h), h
        assert detail(sid)['lifecycle'] == 'completed'

    run_test('Upgrade: dữ liệu completed trước BH-07 không bị đổi lifecycle/version/payment/ledger/audit', check_old_data_unchanged)
    run_test('Upgrade: summary/history đọc được buổi completed cũ sau migration BH-07', check_summary_history_old_data)


def main():
    print(f'Khởi tạo DB BH-07: {CLEAN} và {UPGRADE}...')
    create_db(CLEAN, 'clean')
    create_db(UPGRADE, 'upgrade')

    all_paths = sorted(MIGRATIONS.glob('*.sql'))
    bh07_paths = [p for p in all_paths if p.name >= BH07_MIGRATION]
    pre_bh07 = [p for p in all_paths if p.name < BH07_MIGRATION]
    if not bh07_paths:
        print(f'CẢNH BÁO: chưa có migration BH-07 >= {BH07_MIGRATION}; prefix sẽ FAIL phần summary/history/upgrade.')

    # CLEAN: full chain (nếu BH-07 tồn tại).
    for p in all_paths:
        apply_migration(CLEAN, p)
    # UPGRADE: dừng trước BH-07, seed dữ liệu cũ, rồi apply BH-07 trong run_upgrade_suite.
    for p in pre_bh07:
        apply_migration(UPGRADE, p)
    print('CLEAN migrations:', ', '.join(p.name for p in all_paths[-3:]))
    print('UPGRADE baseline:', ', '.join(p.name for p in pre_bh07[-3:]))

    run_suite(CLEAN)
    run_upgrade_suite()

    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    print('\n==========================================')
    print(f'KẾT QUẢ KIỂM THỬ BH-07: TỔNG {len(results)} | PASS {passed} | FAIL {failed}')
    print('==========================================')

    out = ROOT / f'bh07_test_results_{STAMP}.json'
    out.write_text(json.dumps({
        'timestamp': STAMP,
        'base_sha': subprocess.check_output(['git', '-C', str(REPO_ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        'worktree_dirty': bool(subprocess.check_output(['git', '-C', str(REPO_ROOT), 'status', '--porcelain'], text=True).strip()),
        'container': CONTAINER,
        'clean_db': CLEAN,
        'upgrade_db': UPGRADE,
        'bh07_migration': BH07_MIGRATION,
        'migration_sha256': {p.name: hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                             for p in all_paths},
        'total': len(results),
        'passed': passed,
        'failed': failed,
        'tests': results,
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Results file: {out}')
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
