import io
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

root = next(p for p in Path(__file__).resolve().parents if (p / '.git').exists())
sys.path.insert(0, str(root))
from scripts.bh07_backup import run_v4_concurrent_rehearsal as runner

# Synthetic lifecycle failure; no child process or Docker is started.
proc = Mock()
proc.poll.return_value = None
proc.stdin = io.BytesIO()
proc.stdout = io.BytesIO()
proc.stderr = io.BytesIO()
proc.wait.side_effect = subprocess.TimeoutExpired('fake-owned-observer', 1)
proc.kill.side_effect = PermissionError('synthetic kill denial')
observer = runner.PersistentDumpObserver('fake-container')
observer.process = proc
try:
    observer.close()
    outcome = 'returned_without_error'
except Exception as err:
    outcome = type(err).__name__
print(json.dumps({'kind': 'synthetic process lifecycle only; no actual process created',
                  'close_outcome': outcome, 'process_still_alive': proc.poll() is None,
                  'wait_calls': proc.wait.call_count, 'kill_calls': proc.kill.call_count}, indent=2))
