__file__='/workspace/badminton-hub/docs/reviews/bh06/integration_evidence/run_integration_tests.py'
"""Integration tests BH-06 A+B+C tren PostgreSQL local (Docker).

Muc tieu:
- Kiem tra chuoi DB -> DTO (get_* RPC) -> luong nghiep vu day du:
  chi phi, diem danh/mien phi, chot phi, huong dan/QR (receiver snapshot),
  gui/xac nhan/tu choi/hoan tac/ghi thu, so quy, stale/chot lai/tra them.
- Tai hien loi tich hop: receiver_snapshot khong duoc chot khi publish/start
  hoac khi cau hinh ngan hang, lam UI QR/huong dan thanh toan khong hoat dong.

Khong phai HTTP/PostgREST/JWT that; chi PostgreSQL 17 + Auth stub, giong runner
BH-02..06. Script tu tao DB `bh06_integration_<ts>` va khong xoa DB khac.
"""

import datetime
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[3]
CONTAINER = os.environ.get('BH02_TEST_CONTAINER', 'bh02-test-postgres')
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
DB = 'bh06_integration_' + STAMP


def sql(query, db=None):
    return subprocess.run(
        ['docker', 'exec', '-i', CONTAINER, 'psql', '-X', '-q', '-A', '-t',
         '-v', 'ON_ERROR_STOP=1', '-U', 'postgres', '-d', db or DB],
        input=query, text=True, encoding='utf-8', capture_output=True
    )


def must(query, label, db=None):
    r = sql(query, db=db)
    if r.returncode != 0:
        raise RuntimeError(f"{label}: {r.stderr.strip()}")
    lines = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else ''


def must_all(query, label, db=None):
    r = sql(query, db=db)
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


def as_user_sql(actor_uid, query, role='authenticated'):
    sub = uid(actor_uid) if isinstance(actor_uid, int) else (actor_uid or '')
    return f"""BEGIN;
SET LOCAL ROLE {role};
DO $$ BEGIN PERFORM set_config('request.jwt.claim.sub', '{sub}', true); END $$;
{query}
COMMIT;
"""


def user_exec(actor_uid, query, role='authenticated'):
    return sql(as_user_sql(actor_uid, query, role=role))


def must_user(actor_uid, query, label, role='authenticated'):
    r = user_exec(actor_uid, query, role=role)
    if r.returncode != 0:
        raise RuntimeError(f"{label}: {r.stderr.strip()}")
    lines = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else ''


def expect_error(result, *needles):
    return result.returncode != 0 and any(n in result.stderr for n in needles)


def load(raw):
    return json.loads(raw)


results = []


def run_test(name, fn):
    try:
        fn()
        results.append({'name': name, 'status': 'PASS'})
        print(f"PASS: {name}")
    except Exception as exc:  # noqa: BLE001 - ghi lai loi test
        results.append({'name': name, 'status': 'FAIL', 'error': str(exc)})
        print(f"FAIL: {name} -> {exc}")


# ---------------------------------------------------------------- setup -----
setup_auth = """
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users(id uuid primary key, email text, raw_user_meta_data jsonb);
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;
GRANT USAGE ON SCHEMA auth TO anon, authenticated;
GRANT EXECUTE ON FUNCTION auth.uid() TO anon, authenticated;
"""


DB='bh06_review_fix_upgrade_'+STAMP
must(f'CREATE DATABASE {DB}', 'create upgrade db', db='postgres')
must(setup_auth,'auth')
for path in sorted((REPO_ROOT/'supabase/migrations').glob('*.sql')):
 if path.name < '20261020100000_bh06_integration_receiver.sql':
  must(path.read_text(),'old migration '+path.name)
for n in range(1, 13):
    must(
        "INSERT INTO auth.users(id, email, raw_user_meta_data) VALUES "
        f"({q(n)}, 'it{n}@example.invalid', jsonb_build_object('display_name', 'IT {n}')) "
        "ON CONFLICT (id) DO NOTHING;",
        'seed auth users')

VENUE = must("""
  INSERT INTO public.venues(name, address, area, phone_number, court_count, status)
  VALUES ('San Integration', '1 Nguyen Trai', 'Nha Trang', '0900000009', 6, 'active')
  RETURNING id;
""", 'seed venue')

CLUB = must(f"""
  INSERT INTO public.clubs(owner_user_id, name, visibility, status)
  VALUES ({q(1)}, 'CLB Integration', 'public', 'active') RETURNING id;
""", 'seed club')

must(f"""
  INSERT INTO public.club_members(club_id, user_id, display_name, role, status, joined_at) VALUES
    ('{CLUB}', {q(1)}, 'Owner', 'owner', 'active', now()),
    ('{CLUB}', {q(2)}, 'Host2', 'host', 'active', now()),
    ('{CLUB}', {q(3)}, 'Treasurer', 'treasurer', 'active', now()),
    ('{CLUB}', {q(4)}, 'Player4', 'member', 'active', now()),
    ('{CLUB}', {q(5)}, 'Player5', 'member', 'active', now()),
    ('{CLUB}', {q(6)}, 'Player6', 'member', 'active', now());
""", 'seed club members')

# Host 1 co tai khoan ca nhan; CLB co tai khoan rieng.
must_user(1, "SELECT public.set_host_bank_account('VCB', '1111222233', 'HOST ONE', "
             f"'{newreq()}');", 'host1 bank')
must_user(1, f"SELECT public.set_club_bank_account('{CLUB}'::uuid, 'TCB', '9999888877', "
             f"'CLB INTEGRATION', '{newreq()}');", 'club bank')


def create_session(actor, title, club_link=None, visibility='unlisted'):
    club_sql = f"'{club_link}'::uuid" if club_link else 'NULL'
    stmt = (
        "SELECT public.create_session("
        f"p_venue_id=>'{VENUE}'::uuid, p_title=>'{title}', "
        f"p_starts_at=>'{iso(1)}', p_ends_at=>'{iso(1, 2)}', "
        "p_capacity=>8, p_court_count=>2, "
        f"p_club_id=>{club_sql}, p_visibility=>'{visibility}', "
        "p_approval_mode=>'auto_confirm', p_fee_mode=>'split_actual', "
        "p_member_fee_vnd=>NULL, p_guest_fee_vnd=>NULL, "
        f"p_request_id=>'{newreq()}');"
    )
    return load(must_user(actor, stmt, f'create {title}'))['id']


def publish(sid, actor=1):
    must_user(actor, "SELECT public.set_session_lifecycle("
                     f"'{sid}'::uuid, 'publish', '{newreq()}');", 'publish')


def snapshot(sid):
    raw = must(f"SELECT receiver_snapshot::text FROM public.sessions "
               f"WHERE id='{sid}';", 'snapshot')
    return None if raw in ('', 'NULL') else json.loads(raw)


def join(actor, sid):
    return load(must_user(actor, "SELECT public.request_join_session("
                                 f"'{sid}'::uuid, NULL, '{newreq()}');", 'join'))


def add_guest(actor, sid, name, exempt=False):
    return load(must_user(actor, "SELECT public.add_session_player("
                                 f"'{sid}'::uuid, NULL, '{name}', NULL, "
                                 f"{'TRUE' if exempt else 'FALSE'}, FALSE, "
                                 f"'{newreq()}');", 'add guest'))


def start(sid, actor=1):
    must_user(actor, "SELECT public.start_session("
                     f"'{sid}'::uuid, '{newreq()}');", 'start')


def attend(actor, sid, player, status='present'):
    return load(must_user(actor, "SELECT public.record_attendance("
                                 f"'{sid}'::uuid, '{player}'::uuid, '{status}', "
                                 f"'{newreq()}');", 'attend'))


def post_expense(actor, sid, category, title, amount):
    return load(must_user(actor, "SELECT public.post_session_expense("
                                 f"'{sid}'::uuid, '{category}', '{title}', {amount}, "
                                 f"'{newreq()}');", 'expense'))


def finalize(actor, sid, reason=None, version=None, billing=None):
    v = version if version is not None else must(
        f"SELECT version FROM public.sessions WHERE id='{sid}';", 'version')
    b = billing if billing is not None else must(
        f"SELECT billing_input_version FROM public.sessions WHERE id='{sid}';", 'billing')
    reason_sql = f"'{reason}'" if reason else 'NULL'
    return load(must_user(actor, "SELECT public.finalize_session_charges("
                                 f"'{sid}'::uuid, {v}::bigint, {b}::bigint, {reason_sql}, "
                                 f"'{newreq()}');", 'finalize'))


def finance(actor, sid):
    return load(must_user(actor, "SELECT public.get_session_finance("
                                 f"'{sid}'::uuid, 50, 0);", 'finance'))


def instructions(actor, sid, player=None):
    pid = f"'{player}'::uuid" if player else 'NULL'
    return load(must_user(actor, "SELECT public.get_payment_instructions("
                                 f"'{sid}'::uuid, {pid});", 'instructions'))


def submit(actor, player, amount, req=None):
    return user_exec(actor, "SELECT public.submit_payment("
                            f"'{player}'::uuid, {amount}, 'bank_transfer', NULL, "
                            f"'{req or newreq()}');")


def submit_ok(actor, player, amount, req=None):
    return load(must_user(actor, "SELECT public.submit_payment("
                                 f"'{player}'::uuid, {amount}, 'bank_transfer', NULL, "
                                 f"'{req or newreq()}');", 'submit'))


def confirm(actor, payment_id):
    return load(must_user(actor, "SELECT public.confirm_payment("
                                 f"'{payment_id}'::uuid, '{newreq()}');", 'confirm'))


def cash(actor, player, amount):
    return load(must_user(actor, "SELECT public.record_cash_payment("
                                 f"'{player}'::uuid, {amount}, NULL, '{newreq()}');", 'cash'))


def reverse_payment(actor, payment_id, reason='hoan tac'):
    return load(must_user(actor, "SELECT public.reverse_payment("
                                 f"'{payment_id}'::uuid, '{reason}', '{newreq()}');", 'reverse payment'))


def ledger(actor, limit=100):
    return load(must_user(actor, "SELECT public.get_club_ledger("
                                 f"'{CLUB}'::uuid, {limit}, 0);", 'ledger'))


def active_charges(sid):
    rows = must_all(f"""
      SELECT sc.session_player_id || '|' || sc.amount_due_vnd
      FROM public.session_charges sc
      JOIN public.charge_revisions cr ON cr.id = sc.revision_id
      WHERE cr.session_id='{sid}' AND cr.status='active';
    """, 'charges')
    return {row.split('|')[0]: int(row.split('|')[1])
            for row in rows.splitlines() if row.strip()}


# ------------------------------------------------- receiver snapshot --------

sid=create_session(1,'Reviewer preexisting finalized session')
publish(sid)
p=join(4,sid)['player_id']
start(sid);attend(1,sid,p);post_expense(1,sid,'court','fixture',100000);finalize(1,sid)
assert snapshot(sid) is None
for path in sorted((REPO_ROOT/'supabase/migrations').glob('*.sql')):
 if path.name >= '20261020100000_bh06_integration_receiver.sql':
  must(path.read_text(),'apply forward migration '+path.name)
actual=instructions(4,sid)
print(json.dumps({'case':'existing finalized session after upgrade','db':DB,'has_receiver':actual['has_receiver'],'receiver_snapshot':actual['receiver_snapshot'],'can_pay':actual['can_pay'],'outstanding':actual['outstanding_vnd']},ensure_ascii=False,indent=2))
assert actual['has_receiver'], 'Migration must backfill existing eligible sessions without an extra mutation'

assert actual['receiver_snapshot']['account_number']=='1111222233'
print('PASS: existing finalized host session backfilled without extra session/bank mutation')
