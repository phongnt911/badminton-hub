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

print(f"Tao DB {DB} tren container {CONTAINER} ...")
must(f'DROP DATABASE IF EXISTS {DB};', 'drop db', db='postgres')
must(f'CREATE DATABASE {DB};', 'create db', db='postgres')
must(setup_auth, 'auth stub')

for path in sorted((REPO_ROOT / 'supabase/migrations').glob('*.sql')):
    must(path.read_text(encoding='utf-8'), f'migration {path.name}')

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
def t_host_receiver_on_publish():
    must_user(2, "SELECT public.set_host_bank_account('MB', '2222333344', 'HOST TWO', "
                 f"'{newreq()}');", 'host2 bank')
    sid = create_session(2, 'HostReceiver')
    assert snapshot(sid) is None, 'draft khong duoc chot snapshot'
    publish(sid, actor=2)
    snap = snapshot(sid)
    assert snap is not None, 'publish phai chot receiver_snapshot tu host bank'
    assert snap['bank_code'] == 'MB' and snap['account_number'] == '2222333344', snap
    row = must(f"SELECT receiver_host_bank_account_id IS NOT NULL FROM public.sessions "
               f"WHERE id='{sid}';", 'host fk')
    assert row == 't', 'phai tro receiver_host_bank_account_id'


def t_club_receiver_preferred():
    sid = create_session(1, 'ClubReceiver', club_link=CLUB)
    publish(sid)
    snap = snapshot(sid)
    assert snap is not None, 'publish phai chot receiver_snapshot'
    assert snap['bank_code'] == 'TCB' and snap['account_number'] == '9999888877', snap
    row = must(f"SELECT receiver_club_bank_account_id IS NOT NULL FROM public.sessions "
               f"WHERE id='{sid}';", 'club fk')
    assert row == 't', 'buoi CLB phai uu tien tai khoan CLB'


def t_bank_after_publish():
    # Host 2 da co bank tu test truoc; tao host 3 khong co bank.
    sid = create_session(3, 'LateBank')
    publish(sid, actor=3)
    assert snapshot(sid) is None, 'chua cau hinh bank thi snapshot null'
    must_user(3, "SELECT public.set_host_bank_account('ACB', '3333444455', 'HOST THREE', "
                 f"'{newreq()}');", 'host3 bank')
    snap = snapshot(sid)
    assert snap is not None, 'cau hinh bank sau publish phai mo duoc huong dan/QR'
    assert snap['bank_code'] == 'ACB' and snap['account_number'] == '3333444455', snap


def t_draft_not_snapshotted():
    sid = create_session(1, 'DraftNoSnapshot')
    assert snapshot(sid) is None, 'draft khong duoc chot snapshot'


def t_session_version_refresh():
    sid = create_session(1, 'VersionRefresh', club_link=CLUB)
    publish(sid)
    guest = add_guest(1, sid, 'Guest Version')['player_id']
    before = finance(1, sid)
    db_version = int(must(
        f"SELECT version FROM public.sessions WHERE id='{sid}';", 'session version'))
    assert before['session_version'] == db_version, (before['session_version'], db_version)

    # Manager khac bat dau buoi: sessions.version tang, billing input khong doi.
    start(sid)
    attend(1, sid, guest)
    post_expense(1, sid, 'court', 'san version', 100000)
    refreshed = finance(1, sid)
    assert refreshed['session_version'] > before['session_version'], refreshed
    assert refreshed['billing_input_version'] >= before['billing_input_version'], refreshed

    # Gui version cu phai bi RPC chan; version moi tu DTO phai chot duoc.
    billing = refreshed['billing_input_version']
    r = user_exec(1, "SELECT public.finalize_session_charges("
                     f"'{sid}'::uuid, {before['session_version']}::bigint, "
                     f"{billing}::bigint, NULL, '{newreq()}');")
    assert expect_error(r, 'VERSION_CONFLICT'), f"version cu phai bi chan: {r.stderr}"
    final = load(must_user(1, "SELECT public.finalize_session_charges("
                              f"'{sid}'::uuid, {refreshed['session_version']}::bigint, "
                              f"{billing}::bigint, NULL, '{newreq()}');", 'finalize new version'))
    assert final['billing_state'] == 'current', final


# ------------------------------------------------------ full chain ----------
SHARED = {}


def t_full_chain():
    sid = create_session(1, 'FullChain', club_link=CLUB)
    publish(sid)
    players = {n: join(n, sid)['player_id'] for n in (4, 5, 6)}
    guest = add_guest(1, sid, 'Guest VIP', exempt=True)['player_id']

    start(sid)
    attend(1, sid, players[4], 'present')
    attend(1, sid, players[5], 'present')
    attend(1, sid, players[6], 'no_show')
    attend(1, sid, guest, 'present')

    post_expense(1, sid, 'court', 'Tien san', 400000)
    post_expense(1, sid, 'other', 'Nuoc', 50000)
    finalize(1, sid)

    due = active_charges(sid)
    assert due[players[4]] == 225000 and due[players[5]] == 225000, due
    assert due[guest] == 0, due

    fin = finance(3, sid)
    assert fin['billing_state'] == 'current', fin['billing_state']
    assert fin['expenses_total_vnd'] == 450000, fin
    assert fin['payments'] == [], fin['payments']
    assert fin['active_revision'] is not None, fin

    info = instructions(4, sid)
    assert info['outstanding_vnd'] == 225000 and info['has_receiver'] is True, info
    assert info['receiver_snapshot']['bank_code'] == 'TCB', info
    assert info['reference'].startswith('BH-'), info

    # Tra mot phan, manager xac nhan.
    p1 = submit_ok(4, players[4], 100000)
    confirm(3, p1['payment_id'])
    assert instructions(4, sid)['outstanding_vnd'] == 125000

    # Chi phi sau chot -> stale, chan thu moi.
    post_expense(3, sid, 'court', 'Them san', 100000)
    assert finance(3, sid)['billing_state'] == 'stale'
    r = submit(4, players[4], 1000)
    assert expect_error(r, 'BILLING_STALE'), f"phai chan submit khi stale: {r.stderr}"

    # Chot lai -> due tang, tra them phan con thieu.
    finalize(3, sid, reason='them chi phi san')
    assert finance(3, sid)['billing_state'] == 'current'
    info = instructions(4, sid)
    assert info['outstanding_vnd'] == 175000, info
    p2 = submit_ok(4, players[4], 175000)
    confirm(3, p2['payment_id'])
    assert instructions(4, sid)['outstanding_vnd'] == 0

    # Chong thu du.
    r = submit(4, players[4], 1)
    assert expect_error(r, 'PAYMENT_EXCEEDS_OUTSTANDING'), f"chan tra du submit: {r.stderr}"
    r = user_exec(3, "SELECT public.record_cash_payment("
                     f"'{players[5]}'::uuid, 999999, NULL, '{newreq()}');")
    assert expect_error(r, 'PAYMENT_EXCEEDS_OUTSTANDING'), f"chan thu du cash: {r.stderr}"

    # Diem danh doi (chi con player 4 billable) -> stale; chot lai hop le vi
    # due moi 550.000 >= da thu 275.000.
    attend(1, sid, players[5], 'no_show')
    assert finance(3, sid)['billing_state'] == 'stale'
    finalize(3, sid, reason='doi diem danh')
    due2 = active_charges(sid)
    assert due2.get(players[4]) == 550000, due2
    assert players[5] not in due2, due2
    info = instructions(4, sid)
    assert info['total_paid_vnd'] == 275000 and info['outstanding_vnd'] == 275000, info

    # Idempotency + quyen confirm + reject (khong ghi ledger).
    req = newreq()
    first = submit_ok(4, players[4], 1000, req=req)
    again = submit_ok(4, players[4], 1000, req=req)
    assert first['payment_id'] == again['payment_id'], (first, again)
    r = submit(4, players[4], 2000, req=req)
    assert expect_error(r, 'IDEMPOTENCY_CONFLICT'), f"doi payload cung key: {r.stderr}"
    r = user_exec(5, "SELECT public.confirm_payment("
                     f"'{first['payment_id']}'::uuid, '{newreq()}');")
    assert expect_error(r, 'FORBIDDEN'), f"player confirm: {r.stderr}"
    ledger_before_reject = ledger(3)['balance_vnd']
    must_user(3, "SELECT public.reject_payment("
                 f"'{first['payment_id']}'::uuid, 'sai noi dung', '{newreq()}');", 'reject')
    assert ledger(3)['balance_vnd'] == ledger_before_reject, 'reject khong duoc ghi ledger'

    # Tra not phan con lai.
    p3 = submit_ok(4, players[4], 275000)
    confirm(3, p3['payment_id'])
    assert instructions(4, sid)['outstanding_vnd'] == 0
    assert instructions(4, sid)['total_paid_vnd'] == 550000

    # Hoan tac thanh toan -> outstanding tang, ledger co but toan dao; tra lai.
    reverse_payment(3, p2['payment_id'], 'sai bank')
    assert instructions(4, sid)['outstanding_vnd'] == 175000
    p4 = submit_ok(4, players[4], 175000)
    confirm(3, p4['payment_id'])
    after = ledger(3)
    assert instructions(4, sid)['outstanding_vnd'] == 0
    sum_db = int(must(f"""
      SELECT COALESCE(SUM(CASE WHEN direction='income' THEN amount_vnd ELSE -amount_vnd END), 0)
      FROM public.club_transactions WHERE club_id='{CLUB}';
    """, 'balance sum'))
    assert after['balance_vnd'] == sum_db, (after['balance_vnd'], sum_db)
    assert any(e['reversal_of'] for e in after['entries']), 'ledger phai co entry dao'

    # Quy thu/chi thu cong + dao.
    inc = load(must_user(3, f"SELECT public.post_manual_club_transaction('{CLUB}'::uuid, "
                            f"'income', 50000, 'Thu quy', '{newreq()}');", 'manual income'))
    exp = load(must_user(3, f"SELECT public.post_manual_club_transaction('{CLUB}'::uuid, "
                            f"'expense', 20000, 'Chi quy', '{newreq()}');", 'manual expense'))
    must_user(3, "SELECT public.reverse_club_transaction("
                 f"'{exp['transaction_id']}'::uuid, 'nhap sai', '{newreq()}');", 'reverse manual')
    final = ledger(3)
    sum_db = int(must(f"""
      SELECT COALESCE(SUM(CASE WHEN direction='income' THEN amount_vnd ELSE -amount_vnd END), 0)
      FROM public.club_transactions WHERE club_id='{CLUB}';
    """, 'final balance'))
    assert final['balance_vnd'] == sum_db, (final['balance_vnd'], sum_db)
    assert any(e['reversal_of'] == exp['transaction_id'] for e in final['entries']), final

    # Privacy/role: player khong doc finance; anon khong doc quy.
    r = user_exec(4, f"SELECT public.get_session_finance('{sid}'::uuid, 50, 0);")
    assert expect_error(r, 'FORBIDDEN'), f"player doc finance: {r.stderr}"
    r = user_exec(None, f"SELECT public.get_club_ledger('{CLUB}'::uuid, 20, 0);", role='anon')
    assert expect_error(r, 'permission denied'), f"anon doc quy: {r.stderr}"

    # Complete gate + lifecycle.
    version = must(f"SELECT version FROM public.sessions WHERE id='{sid}';", 'v')
    complete = load(must_user(1, "SELECT public.complete_session("
                                 f"'{sid}'::uuid, {version}::bigint, "
                                 f"'{newreq()}');", 'complete'))
    assert complete['lifecycle'] == 'completed', complete
    SHARED['session'] = sid


def t_dto_shapes():
    # DTO tra ve du key cho model/repository; khong co key la (theo contract).
    sid = SHARED.get('session')
    assert sid, 'full chain phai chay truoc'
    fin = finance(3, sid)
    for key in ('session_id', 'title', 'club_id', 'lifecycle', 'fee_mode',
                'billing_input_version', 'session_version', 'billing_state',
                'active_revision', 'expenses_total_vnd', 'outstanding_total_vnd',
                'expenses', 'charges', 'payments', 'limit', 'offset'):
        assert key in fin, f'thieu key {key} trong get_session_finance'
    led = ledger(3)
    for key in ('club_id', 'balance_vnd', 'limit', 'offset', 'entries'):
        assert key in led, f'thieu key {key} trong get_club_ledger'
    info = instructions(4, sid)
    for key in ('session_id', 'player_id', 'display_name', 'billing_state',
                'active_revision_id', 'source_version', 'amount_due_vnd',
                'total_paid_vnd', 'outstanding_vnd', 'reference',
                'receiver_snapshot', 'has_receiver', 'can_pay'):
        assert key in info, f'thieu key {key} trong get_payment_instructions'


run_test("receiver: host bank duoc chot khi publish", t_host_receiver_on_publish)
run_test("receiver: buoi CLB uu tien tai khoan CLB", t_club_receiver_preferred)
run_test("receiver: cau hinh bank sau publish mo duoc huong dan", t_bank_after_publish)
run_test("receiver: draft khong chot snapshot", t_draft_not_snapshotted)
run_test("version: refresh DTO sau start + chan version cu, chot version moi", t_session_version_refresh)
run_test("luong day du: chi phi/diem danh/chot phi/thanh toan/stale/tra them/hoan tac/quy", t_full_chain)
run_test("contract DTO: get_session_finance/get_club_ledger/get_payment_instructions", t_dto_shapes)

passed = sum(1 for r in results if r['status'] == 'PASS')
failed = len(results) - passed
out = {
    'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'database': DB,
    'container': CONTAINER,
    'tested_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO_ROOT,
                                    capture_output=True, text=True).stdout.strip(),
    'total': len(results),
    'passed': passed,
    'failed': failed,
    'tests': results,
}
out_path = ROOT / f'integration_results_{STAMP}.json'
out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"TOTAL {len(results)} PASS {passed} FAIL {failed}")
print(f"Results file: {out_path}")
sys.exit(0 if failed == 0 else 1)
