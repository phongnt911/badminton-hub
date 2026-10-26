"""Controls for the BH-07 app-profile heap oracle (reviewed logic, no browser needed).

The oracle decides whether Owner-private sentinel strings are still reachable in the
live V8 heap. A wrong oracle turns "no evidence" into "clean", so these controls pin
the three ways it can lie: a missing sentinel, an unusable snapshot, and a failed
cleanup being read as a pass.

Run: python -m unittest tests.test_bh07_app_heap_oracle -v
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / 'scripts/bh07_appheap/heap_oracle.py'
_spec = importlib.util.spec_from_file_location('heap_oracle', ORACLE_PATH)
ORACLE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ORACLE)

SENTINELS = {'bank': 'SENTINEL-BANK-998877', 'probe': 'SENTINEL-PROBE-ALIVE'}
PAD = '"pad":"' + 'x' * 5000 + '",'


def snapshot_body(strings, complete=True):
    body = ('{"snapshot":{"meta":{}},' + PAD + '"nodes":[],"edges":[],"strings":['
            + ','.join(json.dumps(s) for s in strings) + ']}')
    return body if complete else body[:-40]


class ScanControls(unittest.TestCase):
    def scan(self, strings, complete=True):
        with tempfile.NamedTemporaryFile('wb', suffix='.heapsnapshot', delete=False) as fp:
            fp.write(snapshot_body(strings, complete).encode('utf-8'))
            path = fp.name
        try:
            return ORACLE.scan(path, SENTINELS)
        finally:
            Path(path).unlink()

    def test_present_sentinel_is_detected(self):
        result = self.scan(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE', 'unrelated'])
        self.assertTrue(result['ok'])
        self.assertTrue(result['sentinels']['bank']['present'])
        self.assertEqual(result['sentinels']['bank']['occurrences'], 1)
        self.assertFalse(result['sentinels'].get('expense', {}).get('present', False))

    def test_absent_sentinel_is_reported_absent(self):
        result = self.scan(['SENTINEL-PROBE-ALIVE', 'unrelated'])
        self.assertTrue(result['ok'])
        self.assertFalse(result['sentinels']['bank']['present'])

    def test_truncated_snapshot_is_not_read_as_absent(self):
        result = self.scan(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE'], complete=False)
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'snapshot_incomplete_or_unparsable')

    def test_empty_snapshot_is_not_read_as_absent(self):
        with tempfile.NamedTemporaryFile('wb', suffix='.heapsnapshot', delete=False) as fp:
            path = fp.name
        try:
            result = ORACLE.scan(path, SENTINELS)
        finally:
            Path(path).unlink()
        self.assertFalse(result['ok'])

    def test_sentinel_split_across_read_chunks_is_still_found(self):
        # A 1 MiB read boundary must not hide a live sentinel.
        filler = 'y' * (ORACLE.CHUNK - 6)
        result = self.scan([filler, 'SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE'])
        self.assertTrue(result['ok'])
        self.assertTrue(result['sentinels']['bank']['present'])


class DecideControls(unittest.TestCase):
    EXPECTATIONS = {
        'baseline': {'probe': True, 'bank': False},
        'owner_active': {'probe': True, 'bank': True},
        'post_logout': {'probe': True, 'bank': False},
    }

    def scans(self, bank_by_epoch, probe_present=True):
        return {
            epoch: {'ok': True, 'sentinels': {'probe': {'present': probe_present},
                                             'bank': {'present': present}}}
            for epoch, present in bank_by_epoch.items()
        }

    def test_clean_cycle_passes(self):
        scans = self.scans({'baseline': False, 'owner_active': True, 'post_logout': False})
        self.assertEqual(ORACLE.decide(scans, self.EXPECTATIONS, True, 'profile')['verdict'], 'PASS')

    def test_retained_after_logout_fails(self):
        scans = self.scans({'baseline': False, 'owner_active': True, 'post_logout': True})
        verdict = ORACLE.decide(scans, self.EXPECTATIONS, True, 'profile')
        self.assertEqual(verdict['verdict'], 'FAIL')
        self.assertTrue(any('post_logout' in f for f in verdict['findings']))

    def test_missing_positive_signal_fails(self):
        # Owner screen never loaded the sentinel => the detector proved nothing.
        scans = self.scans({'baseline': False, 'owner_active': False, 'post_logout': False})
        self.assertEqual(ORACLE.decide(scans, self.EXPECTATIONS, True, 'profile')['verdict'], 'FAIL')

    def test_dead_detector_fails(self):
        scans = self.scans({'baseline': False, 'owner_active': True, 'post_logout': False},
                           probe_present=False)
        self.assertEqual(ORACLE.decide(scans, self.EXPECTATIONS, True, 'profile')['verdict'], 'FAIL')

    def test_unusable_snapshot_fails(self):
        scans = self.scans({'baseline': False, 'owner_active': True, 'post_logout': False})
        scans['post_logout'] = {'ok': False, 'error': 'snapshot_incomplete_or_unparsable'}
        self.assertEqual(ORACLE.decide(scans, self.EXPECTATIONS, True, 'profile')['verdict'], 'FAIL')

    def test_missing_epoch_fails(self):
        scans = self.scans({'baseline': False, 'owner_active': True})
        self.assertEqual(ORACLE.decide(scans, self.EXPECTATIONS, True, 'profile')['verdict'], 'FAIL')

    def test_failed_cleanup_fails(self):
        scans = self.scans({'baseline': False, 'owner_active': True, 'post_logout': False})
        self.assertEqual(ORACLE.decide(scans, self.EXPECTATIONS, False, 'profile')['verdict'], 'FAIL')

    def test_non_profile_build_fails(self):
        scans = self.scans({'baseline': False, 'owner_active': True, 'post_logout': False})
        self.assertEqual(ORACLE.decide(scans, self.EXPECTATIONS, True, 'debug')['verdict'], 'FAIL')


class CliControls(unittest.TestCase):
    def test_self_test_exits_zero(self):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(ORACLE_PATH), 'self-test'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('controls passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
