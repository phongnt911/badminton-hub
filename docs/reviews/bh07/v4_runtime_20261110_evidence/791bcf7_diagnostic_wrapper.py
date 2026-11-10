import hashlib
import json
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from scripts.bh07_backup import run_v4_concurrent_rehearsal as runner

original = runner.cmd
report_path = Path(__file__).with_name('v4-recovery-port-failure-metadata.json')

def audited_command(args, *positional, **kwargs):
    try:
        return original(args, *positional, **kwargs)
    except Exception:
        if args[:2] == ['docker', 'port'] and len(args) >= 4:
            match = re.fullmatch(r'bh07-v4-target-(auth|rest)-[0-9a-f]{8}', args[2])
            if match:
                record = {
                    'kind': 'read-only diagnostic wrapper; original command error re-raised',
                    'service': 'target_' + match.group(1),
                    'wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                }
                try:
                    inspection = original(['docker', 'inspect', '--format', '{{json .State}}', args[2]], accept_error=True)
                    record['inspect_exit'] = inspection.returncode
                    if inspection.returncode == 0:
                        state = json.loads(inspection.stdout)
                        record.update(status=state.get('Status'), exit_code=state.get('ExitCode'),
                                      running=state.get('Running'), oom_killed=state.get('OOMKilled'))
                    logs = original(['docker', 'logs', '--tail', '50', args[2]], accept_error=True)
                    text = (logs.stdout + logs.stderr).decode('utf-8', 'replace')
                    record['missing_configuration_keys'] = [
                        key for key in ('SITE_URL', 'API_EXTERNAL_URL', 'JWT_SECRET', 'DB_DATABASE_URL', 'DB_DRIVER')
                        if re.search(r'(?:required|missing|empty)[^\n]{0,100}' + key +
                                     '|' + key + r'[^\n]{0,100}(?:required|missing|empty)', text, re.I)]
                    record['database_authentication_failed'] = 'password authentication failed' in text.lower()
                    record['configuration_load_failed'] = 'failed to load configuration' in text.lower()
                    record['database_connection_failed'] = 'failed to connect to database' in text.lower()
                except Exception as diagnostic_error:
                    record['diagnostic_failure_type'] = type(diagnostic_error).__name__
                report_path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
                print(json.dumps(record), flush=True)
        raise

runner.cmd = audited_command
sys.argv = ['run_v4_concurrent_rehearsal.py', '--out', str(Path(__file__).with_name('bh07-v4-recovery-port-diagnosis'))]
raise SystemExit(runner.main())
