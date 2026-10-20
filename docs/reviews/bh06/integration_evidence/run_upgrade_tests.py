"""Probe nâng cấp BH-06: backfill receiver_snapshot cho dữ liệu có trước migration.

Kịch bản (theo review tích hợp I1):
- Dựng DB bằng toàn bộ migration trước bản tích hợp receiver.
- Cấu hình bank active, tạo/publish/start/điểm danh/ghi chi phí/chốt phí.
- Dựng thêm một buổi không có bank và một buổi đã có snapshot cũ.
- Chỉ sau đó apply các migration tích hợp receiver (và backfill nếu có).
- Đọc hướng dẫn thanh toán bằng role người chơi/finance:
  * buổi đủ điều kiện phải được điền receiver,
  * buổi không có bank vẫn NULL,
  * snapshot cũ phải bất biến.

Không phải HTTP/PostgREST/JWT thật; chỉ PostgreSQL 17 + Auth stub, giống runner
BH-02..06. Script tạo DB `bh06_upgrade_<ts>` và không xóa DB khác.
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
DB = 'bh06_upgrade_' + STAMP
RECEIVER_MIGRATION = '20261020100000_bh06_integration_receiver.sql'
MIGRATIONS = REPO_ROOT / 'supabase/migrations'


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


def must_user(actor_uid, query, label, role='authenticated'):
    r = sql(as_user_sql(actor_uid, query, role=role))
    if r.returncode != 0:
        raise RuntimeError(f"{label}: {r.stderr.strip()}")
    lines = [line.strip() for line in r.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else ''


def load(raw):
    return json.loads(raw)


results = []


def run_test(name, fn):
    try:
        fn()
        results.append({'name': name, 'status': 'PASS'})
        print(f"PASS: {name}")
    except Exception as exc:  # noqa: BLE001 - ghi lại lỗi test
        results.append({'name': name, 'status': 'FAIL', 'error': str(exc)})
        print(f"FAIL: {name} -> {exc}")


def snapshot(sid):
    raw = must(f"SELECT receiver_snapshot::text FROM public.sessions "
               f"WHERE id='{sid}';", 'snapshot')
    return None if raw in ('', 'NULL') else json.loads(raw)


def receiver_fks(sid):
    raw = must(
        "SELECT COALESCE(receiver_club_bank_account_id::text, '') || '|' || "
        "COALESCE(receiver_host_bank_account_id::text, '') "
        f"FROM public.sessions WHERE id='{sid}';", 'receiver fks')
    club, host = raw.split('|')
    return club or None, host or None


def must_apply(path):
    must(path.read_text(encoding='utf-8'), 'migration ' + path.name)


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

must(f'CREATE DATABASE {DB}', 'create upgrade db', db='postgres')
must(setup_auth, 'auth')

all_paths = sorted(MIGRATIONS.glob('*.sql'))
baseline = [p for p in all_paths if p.name < RECEIVER_MIGRATION]
upgrade = [p for p in all_paths if p.name >= RECEIVER_MIGRATION]
for path in baseline:
    must_apply(path)
print('BASELINE:', ', '.join(p.name for p in baseline[-3:]))
print('UPGRADE :', ', '.join(p.name for p in upgrade))

for n in range(1, 8):
    must(
        "INSERT INTO auth.users(id, email, raw_user_meta_data) VALUES "
        f"({q(n)}, 'up{n}@example.invalid', jsonb_build_object('display_name', 'UP {n}')) "
        "ON CONFLICT (id) DO NOTHING;",
        'seed auth users')

VENUE = must("""
  INSERT INTO public.venues(name, address, area, phone_number, court_count, status)
  VALUES ('San Upgrade', '1 Nguyen Trai', 'Nha Trang', '0900000010', 6, 'active')
  RETURNING id;
""", 'seed venue')

CLUB = must(f"""
  INSERT INTO public.clubs(owner_user_id, name, visibility, status)
  VALUES ({q(1)}, 'CLB Upgrade', 'public', 'active') RETURNING id;
""", 'seed club')

must(f"""
  INSERT INTO public.club_members(club_id, user_id, display_name, role, status, joined_at) VALUES
    ('{CLUB}', {q(1)}, 'Owner', 'owner', 'active', now()),
    ('{CLUB}', {q(2)}, 'Host2', 'host', 'active', now()),
    ('{CLUB}', {q(3)}, 'Player3', 'member', 'active', now()),
    ('{CLUB}', {q(6)}, 'NoBankHost', 'host', 'active', now());
""", 'seed club members')

# Bank active có sẵn trước khi tạo/publish buổi (đường nâng cấp thật).
must_user(1, "SELECT public.set_host_bank_account('VCB', '1111222233', 'HOST ONE', "
             f"'{newreq()}');", 'host1 bank')
must_user(1, f"SELECT public.set_club_bank_account('{CLUB}'::uuid, 'TCB', '9999888877', "
             f"'CLB UPGRADE', '{newreq()}');", 'club bank')


def create_session(actor, title, club_link=True, visibility='unlisted'):
    club_sql = f"'{CLUB}'::uuid" if club_link else 'NULL'
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


def add_guest(actor, sid, name):
    return load(must_user(actor, "SELECT public.add_session_player("
                                 f"'{sid}'::uuid, NULL, '{name}', NULL, "
                                 f"FALSE, FALSE, '{newreq()}');", 'add guest'))


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


def finalize(actor, sid):
    v = must(f"SELECT version FROM public.sessions WHERE id='{sid}';", 'version')
    b = must(f"SELECT billing_input_version FROM public.sessions WHERE id='{sid}';",
             'billing')
    return load(must_user(actor, "SELECT public.finalize_session_charges("
                                f"'{sid}'::uuid, {v}::bigint, {b}::bigint, NULL, "
                                f"'{newreq()}');", 'finalize'))


def instructions(actor, sid, player):
    return load(must_user(actor, "SELECT public.get_payment_instructions("
                                f"'{sid}'::uuid, '{player}'::uuid);", 'instructions'))


# ------------------------------------------------------- fixture trước upgrade
# A. Buổi gắn CLB, CLB có bank active, đã chốt phí nhưng receiver NULL.
sid_a = create_session(1, 'Upgrade club finalized')
publish(sid_a)
guest_a = add_guest(1, sid_a, 'Guest A')['player_id']
start(sid_a)
attend(1, sid_a, guest_a)
post_expense(1, sid_a, 'court', 'san A', 100000)
finalize(1, sid_a)
assert snapshot(sid_a) is None, 'trước upgrade phải NULL (không có trigger legacy)'
assert receiver_fks(sid_a) == (None, None), 'trước upgrade FK receiver phải NULL'

# B. Buổi không gắn CLB, host không có bank, đã chốt phí: phải giữ NULL.
sid_b = create_session(6, 'Upgrade no bank', club_link=False)
publish(sid_b, actor=6)
guest_b = add_guest(6, sid_b, 'Guest B')['player_id']
start(sid_b, actor=6)
attend(6, sid_b, guest_b)
post_expense(6, sid_b, 'court', 'san B', 100000)
finalize(6, sid_b)
assert snapshot(sid_b) is None, 'buổi không bank phải NULL trước upgrade'

# C. Buổi đã có snapshot cũ: migration không được ghi đè hay đổi FK.
sid_c = create_session(1, 'Upgrade immutable snapshot')
publish(sid_c)
old_snapshot = {'bank_code': 'OLD', 'account_number': '0000000000',
                'account_name': 'OLD SNAPSHOT'}
must(f"UPDATE public.sessions SET receiver_snapshot = '{json.dumps(old_snapshot)}'::jsonb "
     f"WHERE id='{sid_c}';", 'seed old snapshot')
assert snapshot(sid_c) == old_snapshot, 'fixture snapshot cũ sai'

# ------------------------------------------------------------- apply upgrade
for path in upgrade:
    must_apply(path)

# ------------------------------------------------------------------ assert --
case_details = {}


def case_a():
    actual = instructions(1, sid_a, guest_a)
    case_details['a'] = actual
    assert actual['has_receiver'] is True, 'buổi đủ điều kiện phải được backfill receiver'
    assert actual['receiver_snapshot'] == {
        'bank_code': 'TCB', 'account_number': '9999888877',
        'account_name': 'CLB UPGRADE'}, actual['receiver_snapshot']
    assert actual['can_pay'] is True and actual['outstanding_vnd'] == 100000, actual
    fks = receiver_fks(sid_a)
    assert fks[0] is not None and fks[1] is None, f'phải chọn bank CLB: {fks}'


def case_b():
    assert snapshot(sid_b) is None, 'buổi không có bank phải giữ NULL'
    actual = instructions(6, sid_b, guest_b)
    case_details['b'] = actual
    assert actual['has_receiver'] is False, 'không được bịa receiver khi thiếu bank'
    assert receiver_fks(sid_b) == (None, None), 'không được ghi FK khi thiếu bank'


def case_c():
    assert snapshot(sid_c) == old_snapshot, 'snapshot cũ phải bất biến'
    assert receiver_fks(sid_c) == (None, None), 'FK cũ phải nguyên trạng'
    case_details['c'] = {'snapshot': snapshot(sid_c), 'fks': receiver_fks(sid_c)}


run_test('A. buổi đã chốt phí + bank active được backfill sau upgrade', case_a)
run_test('B. buổi không có bank giữ NULL sau upgrade', case_b)
run_test('C. snapshot cũ bất biến sau upgrade', case_c)

summary = {
    'db': DB,
    'baseline_last': baseline[-1].name if baseline else None,
    'upgrade_migrations': [p.name for p in upgrade],
    'results': results,
    'details': case_details,
}
out = ROOT / f'upgrade_results_{STAMP}.json'
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print('SUMMARY:', out)
exit(0 if all(r['status'] == 'PASS' for r in results) else 1)
