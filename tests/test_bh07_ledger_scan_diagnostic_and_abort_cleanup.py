"""Unit and TDD controls for LGR9 (scan diagnostic retention) and LGR10 (abort cleanup metadata).

Verifies:
1. LGR9 Structured Scan Failure Diagnostic:
   - extractScanDiagnostic captures exit status, error type, and safe detail on nonzero exit.
   - Handles exit 2 with JSON stdout (e.g. snapshot_too_small, snapshot_invalid_json).
   - Handles exit 1 with Python traceback in stderr (e.g. MemoryError, ValueError).
   - Handles spawn/execution errors (e.g. ENOENT).
   - Redacts private sentinels and secrets from detail and error_type using redactSentinels.
   - Never publishes raw stdout sentinel tables, credentials, or heap snapshot chunks.
2. LGR10 Abort Cleanup Metadata:
   - evaluateCleanupState populates dump_dir_outside_repo, raw_snapshots_remaining,
     dumps_dir_removed, and chrome_profile_dir_removed on abort.
   - Reflects verified filesystem state: ok=True when physical cleanup and DB absence succeed.
   - Fails closed (ok=False) when dumps directory remains.
   - Fails closed (ok=False) when raw snapshots remain on disk.
   - Fails closed (ok=False) when Chrome profile remains or shutdown failed.
   - Fails closed (ok=False) when dump dir is inside repo.
   - Fails closed (ok=False) when fixture absence fails or errors out.
3. Serialization & Redaction Integrity:
   - redactValue preserves boolean types (true/false) and numbers (integers) in structured summary.

Run: python -X utf8 -m unittest tests.test_bh07_ledger_scan_diagnostic_and_abort_cleanup -v
"""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = (ROOT / 'scripts/bh07_appheap/run_app_profile_heap.js').as_posix()


def run_node_eval(script_body: str, timeout_sec: float = 15.0) -> dict:
    """Execute a Node script that prints a JSON result line, returning the parsed dict."""
    cmd = ['node', '-e', script_body]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout_sec)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Node process exited with {proc.returncode}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"No output from node script. STDERR:\n{proc.stderr}")
    return json.loads(lines[-1])


class TestScanDiagnosticExtraction(unittest.TestCase):
    """LGR9: Diagnostic retention for nonzero oracle scan subprocess."""

    def test_scan_diagnostic_exit_2_json_stdout(self):
        """When oracle exits with code 2 and JSON payload, extract structured error."""
        script = f"""
        const {{ extractScanDiagnostic }} = require({json.dumps(RUNNER_PATH)});
        const err = {{
          status: 2,
          stdout: JSON.stringify({{
            ok: false,
            error: 'snapshot_too_small',
            size_bytes: 100,
            sha256_12: '1234567890ab',
            sentinels: {{ probe: {{ present: null }} }}
          }}),
          message: 'Command failed: python scan'
        }};
        const diag = extractScanDiagnostic(err);
        console.log(JSON.stringify(diag));
        """
        data = run_node_eval(script)
        self.assertEqual(data['exit_status'], 2)
        self.assertEqual(data['error_type'], 'snapshot_unusable')
        self.assertEqual(data['detail'], 'snapshot_too_small')

    def test_scan_diagnostic_exit_1_python_memory_error(self):
        """When oracle exits 1 with MemoryError in stderr, extract exception type and detail."""
        script = f"""
        const {{ extractScanDiagnostic }} = require({json.dumps(RUNNER_PATH)});
        const err = {{
          status: 1,
          stderr: 'Traceback (most recent call last):\\n  File "heap_oracle.py", line 550, in scan\\nMemoryError',
          message: 'Command failed: python scan'
        }};
        const diag = extractScanDiagnostic(err);
        console.log(JSON.stringify(diag));
        """
        data = run_node_eval(script)
        self.assertEqual(data['exit_status'], 1)
        self.assertEqual(data['error_type'], 'MemoryError')
        self.assertEqual(data['detail'], 'MemoryError')

    def test_scan_diagnostic_exit_1_python_value_error_with_detail(self):
        """When oracle exits 1 with ValueError: reason, extract exception type and reason."""
        script = f"""
        const {{ extractScanDiagnostic }} = require({json.dumps(RUNNER_PATH)});
        const err = {{
          status: 1,
          stderr: 'Traceback (most recent call last):\\n  File "heap_oracle.py", line 123\\nValueError: snapshot_layout_missing_fields',
          message: 'Command failed: python scan'
        }};
        const diag = extractScanDiagnostic(err);
        console.log(JSON.stringify(diag));
        """
        data = run_node_eval(script)
        self.assertEqual(data['exit_status'], 1)
        self.assertEqual(data['error_type'], 'ValueError')
        self.assertEqual(data['detail'], 'snapshot_layout_missing_fields')

    def test_scan_diagnostic_spawn_error(self):
        """When subprocess fails to spawn (e.g. ENOENT), preserve code and message."""
        script = f"""
        const {{ extractScanDiagnostic }} = require({json.dumps(RUNNER_PATH)});
        const err = {{
          code: 'ENOENT',
          message: 'spawn python ENOENT'
        }};
        const diag = extractScanDiagnostic(err);
        console.log(JSON.stringify(diag));
        """
        data = run_node_eval(script)
        self.assertEqual(data['exit_status'], 'ENOENT')
        self.assertIn('ENOENT', data['detail'])

    def test_scan_diagnostic_redacts_private_sentinels(self):
        """Private sentinel values in error detail or type must be sanitized."""
        sentinel_secret = 'SECRET_SENTINEL_TRANSACTION_999999'
        script = f"""
        const {{ extractScanDiagnostic }} = require({json.dumps(RUNNER_PATH)});
        const customValues = {{
          ledger_transaction_id: {json.dumps(sentinel_secret)}
        }};
        const err = {{
          status: 1,
          stderr: 'Error: Failed while processing ' + {json.dumps(sentinel_secret)},
          message: 'Command failed: ' + {json.dumps(sentinel_secret)}
        }};
        const diag = extractScanDiagnostic(err, customValues);
        console.log(JSON.stringify({{
          diag,
          leaked: diag.detail.includes({json.dumps(sentinel_secret)})
        }}));
        """
        data = run_node_eval(script)
        self.assertFalse(data['leaked'], "Detail must NOT contain the raw private sentinel")
        self.assertIn('<redacted>', data['diag']['detail'])

    def test_scan_diagnostic_never_retains_raw_stdout_sentinels_or_heap(self):
        """Raw stdout sentinel table and heap chunks must never be retained in diagnostic."""
        script = f"""
        const {{ extractScanDiagnostic }} = require({json.dumps(RUNNER_PATH)});
        const err = {{
          status: 2,
          stdout: JSON.stringify({{
            ok: false,
            error: 'corrupted_snapshot',
            nodes: [1, 2, 3, 4, 5],
            edges: [10, 20, 30],
            strings: ['confidential_actor_data'],
            sentinels: {{ bank: {{ present: false, occurrences: 0 }} }}
          }})
        }};
        const diag = extractScanDiagnostic(err);
        console.log(JSON.stringify({{
          diag,
          has_nodes: 'nodes' in diag,
          has_edges: 'edges' in diag,
          has_strings: 'strings' in diag,
          has_sentinels: 'sentinels' in diag,
          keys: Object.keys(diag).sort()
        }}));
        """
        data = run_node_eval(script)
        self.assertFalse(data['has_nodes'])
        self.assertFalse(data['has_edges'])
        self.assertFalse(data['has_strings'])
        self.assertFalse(data['has_sentinels'])
        self.assertEqual(data['keys'], ['detail', 'error_type', 'exit_status'])


class TestAbortCleanupMetadata(unittest.TestCase):
    """LGR10: Abort cleanup reporting reflects verified filesystem state and fails closed."""

    def test_abort_cleanup_verified_success(self):
        """When dump dir and profile are physically removed outside repo, ok=True."""
        with tempfile.TemporaryDirectory() as tmp_dumps, tempfile.TemporaryDirectory() as tmp_chrome:
            script = f"""
            const fs = require('node:fs');
            const {{ evaluateCleanupState }} = require({json.dumps(RUNNER_PATH)});

            // Simulate dumpsDir and chromeDir removed
            const dumpsDir = {json.dumps(tmp_dumps)} + '_removed';
            const chromeDir = {json.dumps(tmp_chrome)} + '_removed';

            const result = evaluateCleanupState({{
              dumpsDir,
              chromeDir,
              browserCleanupOk: true,
              fixture: {{ created: true, removed: true, verified_absent: true }},
              paymentFixture: {{ created: true, removed: true, verified_absent: true }},
              isBankCoverage: true,
              bankCleanupOk: true,
              isLedgerCoverage: true,
              ledgerCleanupOk: true,
            }});
            console.log(JSON.stringify(result));
            """
            data = run_node_eval(script)
            self.assertTrue(data['dump_dir_outside_repo'])
            self.assertEqual(data['raw_snapshots_remaining'], 0)
            self.assertTrue(data['dumps_dir_removed'])
            self.assertTrue(data['chrome_profile_dir_removed'])
            self.assertTrue(data['ok'])

    def test_abort_cleanup_fails_closed_when_dumps_dir_remains(self):
        """When dumpsDir remains on filesystem, dumps_dir_removed=False and ok=False."""
        with tempfile.TemporaryDirectory() as tmp_dumps, tempfile.TemporaryDirectory() as tmp_chrome:
            script = f"""
            const {{ evaluateCleanupState }} = require({json.dumps(RUNNER_PATH)});

            const dumpsDir = {json.dumps(tmp_dumps)}; // exists!
            const chromeDir = {json.dumps(tmp_chrome)} + '_removed';

            const result = evaluateCleanupState({{
              dumpsDir,
              chromeDir,
              browserCleanupOk: true,
              fixture: {{ created: true, removed: true, verified_absent: true }},
              paymentFixture: {{ created: true, removed: true, verified_absent: true }},
            }});
            console.log(JSON.stringify(result));
            """
            data = run_node_eval(script)
            self.assertFalse(data['dumps_dir_removed'])
            self.assertFalse(data['ok'])

    def test_abort_cleanup_fails_closed_when_raw_snapshots_remain(self):
        """When raw .heapsnapshot files remain, raw_snapshots_remaining > 0 and ok=False."""
        with tempfile.TemporaryDirectory() as tmp_dumps, tempfile.TemporaryDirectory() as tmp_chrome:
            dummy_snapshot = Path(tmp_dumps) / 'test.heapsnapshot'
            dummy_snapshot.write_text('{}')
            script = f"""
            const {{ evaluateCleanupState }} = require({json.dumps(RUNNER_PATH)});

            const dumpsDir = {json.dumps(tmp_dumps)};
            const chromeDir = {json.dumps(tmp_chrome)} + '_removed';

            const result = evaluateCleanupState({{
              dumpsDir,
              chromeDir,
              browserCleanupOk: true,
              fixture: {{ created: true, removed: true, verified_absent: true }},
              paymentFixture: {{ created: true, removed: true, verified_absent: true }},
            }});
            console.log(JSON.stringify(result));
            """
            data = run_node_eval(script)
            self.assertEqual(data['raw_snapshots_remaining'], 1)
            self.assertFalse(data['ok'])

    def test_abort_cleanup_fails_closed_when_chrome_profile_remains(self):
        """When Chrome profile directory remains, chrome_profile_dir_removed=False and ok=False."""
        with tempfile.TemporaryDirectory() as tmp_dumps, tempfile.TemporaryDirectory() as tmp_chrome:
            script = f"""
            const {{ evaluateCleanupState }} = require({json.dumps(RUNNER_PATH)});

            const dumpsDir = {json.dumps(tmp_dumps)} + '_removed';
            const chromeDir = {json.dumps(tmp_chrome)}; // exists!

            const result = evaluateCleanupState({{
              dumpsDir,
              chromeDir,
              browserCleanupOk: true,
              fixture: {{ created: true, removed: true, verified_absent: true }},
              paymentFixture: {{ created: true, removed: true, verified_absent: true }},
            }});
            console.log(JSON.stringify(result));
            """
            data = run_node_eval(script)
            self.assertFalse(data['chrome_profile_dir_removed'])
            self.assertFalse(data['ok'])

    def test_abort_cleanup_fails_closed_when_browser_cleanup_not_ok(self):
        """When browser shutdown fails (browserCleanupOk=False), chrome_profile_dir_removed=False and ok=False."""
        with tempfile.TemporaryDirectory() as tmp_dumps, tempfile.TemporaryDirectory() as tmp_chrome:
            script = f"""
            const {{ evaluateCleanupState }} = require({json.dumps(RUNNER_PATH)});

            const dumpsDir = {json.dumps(tmp_dumps)} + '_removed';
            const chromeDir = {json.dumps(tmp_chrome)} + '_removed';

            const result = evaluateCleanupState({{
              dumpsDir,
              chromeDir,
              browserCleanupOk: false, // failed shutdown!
              fixture: {{ created: true, removed: true, verified_absent: true }},
              paymentFixture: {{ created: true, removed: true, verified_absent: true }},
            }});
            console.log(JSON.stringify(result));
            """
            data = run_node_eval(script)
            self.assertFalse(data['chrome_profile_dir_removed'])
            self.assertFalse(data['ok'])

    def test_abort_cleanup_fails_closed_when_dump_dir_inside_repo(self):
        """When dumps directory is inside repository root, dump_dir_outside_repo=False and ok=False."""
        inside_dir = (ROOT / 'build' / 'test_dumps').as_posix()
        script = f"""
        const {{ evaluateCleanupState }} = require({json.dumps(RUNNER_PATH)});

        const result = evaluateCleanupState({{
          dumpsDir: {json.dumps(inside_dir)},
          rootDir: {json.dumps(ROOT.as_posix())},
          chromeDir: null,
          browserCleanupOk: true,
          fixture: {{ created: true, removed: true, verified_absent: true }},
          paymentFixture: {{ created: true, removed: true, verified_absent: true }},
        }});
        console.log(JSON.stringify(result));
        """
        data = run_node_eval(script)
        self.assertFalse(data['dump_dir_outside_repo'])
        self.assertFalse(data['ok'])

    def test_abort_cleanup_fails_closed_on_fixture_absence_failure(self):
        """When run-only fixture is not verified absent, ok=False."""
        with tempfile.TemporaryDirectory() as tmp_dumps, tempfile.TemporaryDirectory() as tmp_chrome:
            script = f"""
            const {{ evaluateCleanupState }} = require({json.dumps(RUNNER_PATH)});

            const dumpsDir = {json.dumps(tmp_dumps)} + '_removed';
            const chromeDir = {json.dumps(tmp_chrome)} + '_removed';

            const result = evaluateCleanupState({{
              dumpsDir,
              chromeDir,
              browserCleanupOk: true,
              fixture: {{ created: true, removed: true, verified_absent: false }},
              paymentFixture: {{ created: true, removed: true, verified_absent: true }},
            }});
            console.log(JSON.stringify(result));
            """
            data = run_node_eval(script)
            self.assertFalse(data['ok'])


class TestRedactionAndSerializationIntegrity(unittest.TestCase):
    """Ensure boolean and integer types are preserved across redaction and serialization."""

    def test_redact_value_preserves_boolean_and_numeric_types(self):
        """redactValue must not convert booleans or integers into strings or placeholder corruptions."""
        script = f"""
        const {{ redactValue }} = require({json.dumps(RUNNER_PATH)});

        const input = {{
          status: 'NOT RUN',
          scan_failure: {{
            exit_status: 2,
            error_type: 'snapshot_unusable',
            detail: 'snapshot_too_small'
          }},
          cleanup: {{
            ok: true,
            dump_dir_outside_repo: true,
            dumps_dir_removed: true,
            chrome_profile_dir_removed: true,
            raw_snapshots_remaining: 0
          }}
        }};

        const cleaned = redactValue(input);
        const serialized = JSON.stringify(cleaned);
        const reparsed = JSON.parse(serialized);

        console.log(JSON.stringify({{
          ok_is_bool: typeof reparsed.cleanup.ok === 'boolean' && reparsed.cleanup.ok === true,
          dump_dir_is_bool: typeof reparsed.cleanup.dump_dir_outside_repo === 'boolean' && reparsed.cleanup.dump_dir_outside_repo === true,
          remaining_is_number: typeof reparsed.cleanup.raw_snapshots_remaining === 'number' && reparsed.cleanup.raw_snapshots_remaining === 0,
          exit_status_is_number: typeof reparsed.scan_failure.exit_status === 'number' && reparsed.scan_failure.exit_status === 2,
          detail_is_string: typeof reparsed.scan_failure.detail === 'string'
        }}));
        """
        data = run_node_eval(script)
        self.assertTrue(data['ok_is_bool'])
        self.assertTrue(data['dump_dir_is_bool'])
        self.assertTrue(data['remaining_is_number'])
        self.assertTrue(data['exit_status_is_number'])
        self.assertTrue(data['detail_is_string'])


if __name__ == '__main__':
    unittest.main()
