"""Run after run_bh03_tests.py against the same isolated test container."""
import concurrent.futures
import json
import os
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTAINER = os.environ.get('BH02_TEST_CONTAINER', 'bh02-review-postgres')
if not CONTAINER.startswith('bh02-'):
    raise SystemExit('Only bh02- isolated test containers are supported')
latest = sorted(ROOT.glob('bh03_test_results_*.json'))[-1]
meta = json.loads(latest.read_text(encoding='utf-8'))
stamp = meta['timestamp']
results = []

def q(n):
    return "'00000000-0000-0000-0000-" + f'{n:012d}' + "'"

def sql(db, query):
    return subprocess.run(['docker','exec','-i',CONTAINER,'psql','-X','-q','-t','-A','-v','ON_ERROR_STOP=1','-U','postgres','-d',db],input=query,text=True,capture_output=True)

def must(db, query):
    result = sql(db, query)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()

def actor(query, n=1):
    return f"SET ROLE authenticated; SELECT set_config('request.jwt.claim.sub',{q(n)},false); {query}"

def record(name, passed, actual):
    results.append(dict(name=name, passed=passed, actual=actual))
    print(('PASS ' if passed else 'FAIL ') + name, flush=True)

for prefix in ['bh03_clean_', 'bh03_legacy_']:
    db = prefix + stamp
    club = must(db, 'SELECT id FROM clubs ORDER BY created_at LIMIT 1;')
    for label, call, error in [
        ('consent required', f"SELECT add_club_member('{club}','Unaccepted',NULL,NULL,{q(9)},'{uuid.uuid4()}');", 'FORBIDDEN'),
        ('request id required', "SELECT create_club('Missing key');", 'INVALID_INPUT'),
    ]:
        outcome = sql(db, 'BEGIN; ' + actor(call) + ' ROLLBACK;')
        record(db + ': ' + label, outcome.returncode != 0 and error in outcome.stderr, outcome.stderr)
    key = str(uuid.uuid4())
    calls = f"SELECT add_club_member('{club}','Notes',NULL,'Before',NULL,'{key}'); SELECT add_club_member('{club}','Notes',NULL,'After',NULL,'{key}');"
    outcome = sql(db, 'BEGIN; ' + actor(calls) + ' ROLLBACK;')
    record(db + ': changed contact note conflicts', outcome.returncode != 0 and 'IDEMPOTENCY_CONFLICT' in outcome.stderr, outcome.stderr)
    key = str(uuid.uuid4())
    calls = f"SELECT set_club_bank_account('{club}','TEST','00123','Before','{key}'); SELECT set_club_bank_account('{club}','TEST','00123','After','{key}');"
    outcome = sql(db, 'BEGIN; ' + actor(calls) + ' ROLLBACK;')
    record(db + ': changed bank name conflicts', outcome.returncode != 0 and 'IDEMPOTENCY_CONFLICT' in outcome.stderr, outcome.stderr)
    # ':' in input cannot erase payload field boundaries.
    key = str(uuid.uuid4())
    calls = f"SELECT create_club('A:B','C','private','{key}'); SELECT create_club('A','B:C','private','{key}');"
    outcome = sql(db, 'BEGIN; ' + actor(calls, 9) + ' ROLLBACK;')
    record(db + ': field boundaries cannot collide', outcome.returncode != 0 and 'IDEMPOTENCY_CONFLICT' in outcome.stderr, outcome.stderr)
    # Test-only delay forces both transactions past their initial request entry point.
    must(db, "CREATE FUNCTION public.review_delay_club() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.name LIKE 'Retry race %' THEN PERFORM pg_sleep(0.3); END IF; RETURN NEW; END $$; CREATE TRIGGER review_delay_club BEFORE INSERT ON clubs FOR EACH ROW EXECUTE FUNCTION public.review_delay_club();")
    try:
        key = str(uuid.uuid4())
        name = 'Retry race ' + key
        query = actor(f"SELECT create_club('{name}',NULL,'private','{key}')->>'id';", 9)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda s: sql(db, s), [query, query]))
        ids = [o.stdout.strip().splitlines()[-1] if o.returncode == 0 else o.stderr for o in outcomes]
        count = must(db, f"SELECT count(*) FROM clubs WHERE name='{name}';")
        record(db + ': concurrent replay returns one club', all(o.returncode == 0 for o in outcomes) and len(set(ids)) == 1 and count == '1', dict(ids=ids, count=count))
        key = str(uuid.uuid4())
        name = 'Retry race ' + key
        queries = [actor(f"SELECT create_club('{name}','{desc}','private','{key}');",9) for desc in ['Before','After']]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda s: sql(db,s),queries))
        count = must(db, f"SELECT count(*) FROM clubs WHERE name='{name}';")
        record(db + ': concurrent changed payload conflicts', sum(o.returncode == 0 for o in outcomes) == 1 and any('IDEMPOTENCY_CONFLICT' in o.stderr for o in outcomes) and count == '1', dict(count=count, errors=[o.stderr for o in outcomes]))
    finally:
        must(db, 'DROP TRIGGER review_delay_club ON clubs; DROP FUNCTION public.review_delay_club();')
report = {'tested_commit':meta.get('tested_commit'),'worktree_dirty':meta.get('worktree_dirty'),'migration_sha256':meta.get('migration_sha256'),'tests':results,'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results)}
path = ROOT / f'bh03_retry_results_{stamp}.json'
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(f"TOTAL {len(results)} PASS {report['passed']} FAIL {report['failed']}")
raise SystemExit(bool(report['failed']))
