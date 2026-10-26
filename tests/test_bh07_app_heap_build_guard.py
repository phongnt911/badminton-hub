"""Controls for the BH-07 app-profile build/serve guards (review AH5).

A heap measurement of a build we did not produce is not evidence, so the runner must
refuse `--reuse-build`, prove the artifacts are the ones this run just wrote, prove the
static server answers with those bytes, and refuse a port someone else already owns.

Run: python -m unittest tests.test_bh07_app_heap_build_guard -v
"""
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / 'scripts/bh07_appheap/build_guard.js'
RUNNER = ROOT / 'scripts/bh07_appheap/run_app_profile_heap.js'
REUSE_PROBE = ROOT / 'docs/reviews/bh07/review_8914b2f_evidence/build_probe.js'
CONTROLS = ('missing_artifact', 'stale_artifact', 'rebuilt_identical_artifact', 'fresh_artifact',
            'served_match', 'served_mismatch', 'occupied_port', 'free_port')


class BuildGuardControls(unittest.TestCase):
    def test_self_test_exits_zero_and_covers_every_control(self):
        result = subprocess.run(['node', str(GUARD), '--self-test'], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('controls passed', result.stdout)
        for name in CONTROLS:
            self.assertIn(f'ok {name}', result.stdout, result.stdout)
        self.assertNotIn('FAIL', result.stdout)

    def test_runner_and_guard_parse(self):
        for script in (GUARD, RUNNER):
            result = subprocess.run(['node', '--check', str(script)], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_reviewer_reuse_build_probe_now_fails(self):
        # Reviewer fixture, unchanged: it runs the current `--reuse-build` branch with no
        # artifact and used to print mode:'profile'. It must now be refused.
        result = subprocess.run(['node', str(REUSE_PROBE)], capture_output=True, text=True, cwd=ROOT)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('reuse-build', result.stdout + result.stderr)


class PublicationSanitizerControls(unittest.TestCase):
    """Review 57ec02c AH3-B: the run must refuse to publish a raw sentinel value."""

    SNIPPET = (
        "const r = require('./scripts/bh07_appheap/run_app_profile_heap.js');"
        "const values = { bank: '0123456789', probe: 'PROBE-abc' };"
        "console.log(JSON.stringify({"
        " clean: r.findSentinelLeaks(['sha 65dce15efcc4 length 10'], values),"
        " leak: r.findSentinelLeaks(['account 0123456789', 'ok'], values),"
        " redacted: r.redactSentinels('acct 0123456789 probe PROBE-abc', values),"
        " status: r.renderReport({gate: 'g', reference: 'r', status: 'FAIL', verdict: 'FAIL',"
        " tested_source_sha: 'a'.repeat(40), git_dirty: false, measurement_surface: 'm', oracle: 'o',"
        " environment: {build: {mode: 'profile', artifacts: {}, served_match: false}},"
        " sentinels: {}, cycles: [], findings: ['cycle 1: leak'], cleanup: {}}).split('\\n')"
        " .filter((line) => line.startsWith('- Status: ') || line.startsWith('- Build: ')),"
        "}));"
    )

    def test_leak_detection_and_redaction(self):
        result = subprocess.run(['node', '-e', self.SNIPPET], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['clean'], [])
        self.assertEqual(payload['leak'], ['bank'])
        self.assertNotIn('0123456789', payload['redacted'])
        self.assertNotIn('PROBE-abc', payload['redacted'])
        self.assertIn('<redacted>', payload['redacted'])
        self.assertIn('- Status: **FAIL** (verdict FAIL)', payload['status'])
        self.assertIn('- Build: mode=profile reused=false artifacts=0 served_match=false', payload['status'])


if __name__ == '__main__':
    unittest.main()
