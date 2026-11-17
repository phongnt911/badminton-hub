"""Local-only two-connection probe of the actual generated cleanup SQL."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from scripts.bh07_appheap import disposable_instructions_fixture as fx

DB = fx.DockerPsqlClient('docker', 'bh07-android-db')
CMD = ['docker', 'exec', '-i', 'bh07-android-db', 'psql', '-X', '-U', 'postgres',
       '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-t', '-A']
OUT = ROOT / '.build/club-bank-root-20261117'
PRIVATE = Path(tempfile.mkdtemp(prefix='bh07-bank-lock-probe-'))
KEY = uuid.uuid4().int % 2_000_000_000 + 1
TAG = 'bh07_bank_probe_' + uuid.uuid4().hex[:10]
report = {'probe': 'cleanup_parent_lock_at_pre_parent_delete_boundary', 'checks': {}}
report['source_sha'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
report['git_dirty'] = bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip())
report['fixture_module_sha256'] = hashlib.sha256(Path(fx.__file__).read_bytes()).hexdigest()
report['probe_script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
before = DB.fingerprint()
fixtures = []
processes = []


def start(sql):
    p = subprocess.Popen(CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding='utf-8')
    p.stdin.write(sql)
    p.stdin.close()
    p.stdin = None
    processes.append(p)
    return p


def wait_query(sql):
    for _ in range(100):
        if DB.query_json(sql).get('ok') is True:
            return
        time.sleep(.1)
    raise RuntimeError('controlled probe boundary not reached')


class Capture:
    def __init__(self):
        self.sql = None

    def __getattr__(self, key):
        return getattr(DB, key)

    def exec_sql(self, sql, fixture=None):
        self.sql = sql
        raise RuntimeError('capture_only_no_write')


try:
    # Side fixture is created first so target baseline includes it.
    for name in ('side', 'target'):
        f = fx.DisposableInstructionsFixture(include_club_bank=True)
        state = PRIVATE / (name + '.json')
        fixtures.append((f, state))
        f.create(DB, state_path=state, capture_baseline=True)
    side, target = fixtures[0][0], fixtures[1][0]
    capture = Capture()
    target.cleanup(capture)
    sql = capture.sql
    assert sql and sql.count('DELETE FROM public.clubs WHERE') == 1
    report['generated_cleanup_sha256'] = hashlib.sha256(sql.encode()).hexdigest()
    gate = start(f"SET application_name='{TAG}_gate'; SELECT pg_advisory_lock({KEY}); SELECT pg_sleep(15);")
    wait_query(f"SELECT json_build_object('ok', EXISTS(SELECT 1 FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid WHERE a.application_name='{TAG}_gate' AND l.locktype='advisory' AND l.granted));")
    gated_sql = sql.replace('DELETE FROM public.clubs WHERE',
        f'SELECT pg_advisory_lock({KEY}); SELECT pg_advisory_unlock({KEY});\nDELETE FROM public.clubs WHERE', 1)
    cleanup = start(f"SET application_name='{TAG}_cleanup';\n" + gated_sql)
    wait_query(f"SELECT json_build_object('ok', EXISTS(SELECT 1 FROM pg_stat_activity WHERE application_name='{TAG}_cleanup' AND wait_event_type='Lock' AND wait_event='advisory')); ")
    report['checks']['reached_after_absence_before_parent_delete'] = True
    foreign_id = str(uuid.uuid4())
    attempts = {
        'foreign_insert_blocked': f"INSERT INTO public.club_bank_accounts(id,club_id,bank_code,account_number,account_name,status) VALUES ('{foreign_id}','{target.club_id}','VCB','9999000011112222','BH07 LOCK PROBE','active');",
        'foreign_reparent_blocked': f"UPDATE public.club_bank_accounts SET club_id='{target.club_id}' WHERE id='{side.club_bank_account_id}';",
    }
    for label, statement in attempts.items():
        result = subprocess.run(CMD, input="\\set VERBOSITY sqlstate\nSET lock_timeout='750ms';\n" + statement,
                                text=True, encoding='utf-8', capture_output=True, timeout=10)
        report['checks'][label] = result.returncode != 0 and '55P03' in result.stderr
        assert report['checks'][label], label
    _, _ = gate.communicate(timeout=20)
    _, _ = cleanup.communicate(timeout=20)
    assert gate.returncode == 0 and cleanup.returncode == 0
    report['checks']['target_cleanup_transaction_committed'] = True
    target.removed = True
    target.club_bank_removed = True
    preserved = DB.query_json(f"SELECT json_build_object('ok', EXISTS(SELECT 1 FROM public.club_bank_accounts WHERE id='{side.club_bank_account_id}' AND club_id='{side.club_id}') AND NOT EXISTS(SELECT 1 FROM public.club_bank_accounts WHERE id='{foreign_id}'));")
    report['checks']['foreign_side_row_preserved_and_insert_absent'] = preserved['ok'] is True
    assert report['checks']['foreign_side_row_preserved_and_insert_absent']
except Exception as exc:
    report['error_type'] = type(exc).__name__
finally:
    # Bounded gate naturally exits; allow the owned cleanup transaction to finish before recovery.
    for p in processes:
        if p.poll() is None:
            p.communicate(timeout=30)
    receipts = []
    for f, state in reversed(fixtures):
        receipt, code = fx.finalize_cli_cleanup(f, DB, state)
        receipts.append({'cleanup_ok': code == 0, 'bank_absent': receipt.get('disposable_instructions_club_bank_verified_absent')})
    report['fixture_cleanup'] = receipts
    report['root_db_comparison'] = fx.compare_fingerprints(before, DB.fingerprint())
    report['private_state_absent'] = not any(PRIVATE.glob('*.json'))
    report['empty_private_directory_retained'] = True
    report['ok'] = ('error_type' not in report and all(report['checks'].values())
                    and all(r['cleanup_ok'] for r in receipts)
                    and report['private_state_absent'] and report['root_db_comparison']['equal'])
    OUT.mkdir(exist_ok=True)
    (OUT/'lock-probe-receipt.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(report))
sys.exit(0 if report['ok'] else 1)
