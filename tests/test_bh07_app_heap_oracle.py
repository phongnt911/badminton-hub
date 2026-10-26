"""Controls for the BH-07 app-profile heap oracle (reviewed logic, no browser needed).

The oracle decides whether Owner-private sentinel strings are still reachable in the
live V8 heap. A wrong oracle turns "no evidence" into "clean", so these controls pin
every way it can lie: a missing sentinel, an unusable snapshot, a snapshot that is
JSON-shaped but structurally broken, and a failed cleanup being read as a pass.

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
NODE_FIELDS = ['type', 'name', 'id', 'self_size', 'edge_count']
NODE_TYPES = [['hidden', 'array', 'string', 'object'], 'string', 'number', 'number', 'number']
EDGE_FIELDS = ['type', 'name_or_index', 'to_node']
EDGE_TYPES = [['context', 'element', 'property'], 'string_or_number', 'node']
FILLER = 'z' * 4200


def snapshot_body(strings, node_units=2, edge_units=2, node_count=None, edge_count=None,
                  meta=None, drop_tail=0, extra_top_level=(), strings_last=True):
    """Build a structurally valid V8-shaped snapshot so controls test logic, not luck."""
    meta = meta if meta is not None else {
        'node_fields': NODE_FIELDS,
        'node_types': NODE_TYPES,
        'edge_fields': EDGE_FIELDS,
        'edge_types': EDGE_TYPES,
    }
    nodes = [0] * (node_units * len(NODE_FIELDS))
    edges = [0] * (edge_units * len(EDGE_FIELDS))
    counts = {
        'node_count': node_units if node_count is None else node_count,
        'edge_count': edge_units if edge_count is None else edge_count,
        'trace_function_count': 0,
    }
    head = {'snapshot': {'meta': meta, **counts}}
    body = json.dumps({**head, 'nodes': nodes, 'edges': edges,
                       'traces': [], 'samples': [], 'locations': []}, separators=(',', ':'))
    tail = json.dumps({'strings': strings + [FILLER]}, separators=(',', ':'))[1:-1]
    if strings_last:
        out = body[:-1] + ',' + tail + '}'
    else:
        out = json.dumps({**head, 'strings': strings, 'nodes': nodes, 'edges': edges},
                         separators=(',', ':'))
    for key, value in extra_top_level:
        out = out[:-1] + ',' + json.dumps({key: value}, separators=(',', ':'))[1:-1] + '}'
    return out[:-drop_tail] if drop_tail else out


def scan_body(body):
    with tempfile.NamedTemporaryFile('wb', suffix='.heapsnapshot', delete=False) as fp:
        fp.write(body.encode('utf-8'))
        path = fp.name
    try:
        return ORACLE.scan(path, SENTINELS)
    finally:
        Path(path).unlink()


class ScanControls(unittest.TestCase):
    def scan(self, body):
        return scan_body(body)

    def assert_unusable(self, result, hint=''):
        self.assertFalse(result['ok'], f'{hint}: expected unusable snapshot, got {result}')
        self.assertTrue(result.get('error'), f'{hint}: unusable snapshot must explain why')

    def test_valid_snapshot_detects_present_sentinel(self):
        result = self.scan(snapshot_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE']))
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['sentinels']['bank']['present'])
        self.assertEqual(result['sentinels']['bank']['occurrences'], 1)
        self.assertFalse(result['sentinels'].get('expense', {}).get('present', False))

    def test_valid_snapshot_reports_absent_sentinel(self):
        result = self.scan(snapshot_body(['SENTINEL-PROBE-ALIVE', 'unrelated']))
        self.assertTrue(result['ok'], result)
        self.assertFalse(result['sentinels']['bank']['present'])

    def test_sentinel_deep_inside_large_string_table_is_found(self):
        strings = ['pad-%d' % i for i in range(2000)] + ['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE']
        result = self.scan(snapshot_body(strings))
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['sentinels']['bank']['present'])

    def test_invalid_literal_snapshot_fails(self):
        # Reviewer fixture: every substring marker and a closing brace, but not JSON.
        body = ('{"snapshot":BROKEN,' + 'x' * 5000
                + ',"nodes":[],"edges":[],"strings":["SENTINEL-PROBE-ALIVE"]}')
        self.assert_unusable(self.scan(body), 'invalid literal')

    def test_truncated_snapshot_fails(self):
        self.assert_unusable(self.scan(snapshot_body(['SENTINEL-PROBE-ALIVE'], drop_tail=40)), 'truncated')

    def test_trailing_garbage_fails(self):
        self.assert_unusable(self.scan(snapshot_body(['SENTINEL-PROBE-ALIVE']) + 'garbage'), 'trailing garbage')

    def test_node_count_mismatch_fails(self):
        body = snapshot_body(['SENTINEL-PROBE-ALIVE'], node_units=3, node_count=2)
        self.assert_unusable(self.scan(body), 'node_count mismatch')

    def test_edge_count_mismatch_fails(self):
        body = snapshot_body(['SENTINEL-PROBE-ALIVE'], edge_units=3, edge_count=7)
        self.assert_unusable(self.scan(body), 'edge_count mismatch')

    def test_missing_chunk_mid_stream_fails(self):
        # A whole run of node numbers is gone; every marker and the tail still match.
        body = snapshot_body(['SENTINEL-PROBE-ALIVE'], node_units=4)
        broken = body.replace('0,0,0,0,0,0,0,0,0,0,', '0,0,0,0,', 1)
        self.assertNotEqual(broken, body)
        self.assert_unusable(self.scan(broken), 'missing chunk')

    def test_unterminated_string_fails(self):
        body = snapshot_body(['SENTINEL-PROBE-ALIVE'])
        broken = body.replace('"SENTINEL-PROBE-ALIVE"', '"SENTINEL-PROBE-ALIVE', 1)
        self.assert_unusable(self.scan(broken), 'unterminated string')

    def test_metadata_without_v8_fields_fails(self):
        body = snapshot_body(['SENTINEL-PROBE-ALIVE'], meta={})
        self.assert_unusable(self.scan(body), 'empty meta')

    def test_metadata_with_inconsistent_types_fails(self):
        body = snapshot_body(['SENTINEL-PROBE-ALIVE'],
                             meta={'node_fields': NODE_FIELDS, 'node_types': NODE_TYPES[:2],
                                   'edge_fields': EDGE_FIELDS, 'edge_types': EDGE_TYPES})
        self.assert_unusable(self.scan(body), 'node_types length mismatch')

    def test_strings_not_last_fails(self):
        body = snapshot_body(['SENTINEL-PROBE-ALIVE'], strings_last=False)
        self.assert_unusable(self.scan(body), 'strings not last')

    def test_empty_snapshot_fails(self):
        with tempfile.NamedTemporaryFile('wb', suffix='.heapsnapshot', delete=False) as fp:
            path = fp.name
        try:
            result = ORACLE.scan(path, SENTINELS)
        finally:
            Path(path).unlink()
        self.assert_unusable(result, 'empty file')


class ReviewerGrammarControls(unittest.TestCase):
    """Review 57ec02c AH1: near-JSON dumps must never be certified as a clean heap.

    Each fixture below is a real V8-shaped body with one byte-level grammar fault; the
    old regex scanner looked only for markers, so every one of them read `ok:true` with
    `bank:false` and decided PASS. Presence must be `None` (unknown), never `False`.
    """

    def assert_unknown(self, body, hint):
        result = scan_body(body)
        self.assertFalse(result['ok'], f'{hint}: accepted a corrupt dump {result}')
        self.assertTrue(result.get('error'), f'{hint}: unusable dump must explain why')
        for name, sentinel in result['sentinels'].items():
            self.assertIsNone(sentinel['present'], f'{hint}: {name} presence must be unknown')

    def test_missing_string_comma_fails(self):
        valid = snapshot_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE', 'ordinary'])
        broken = valid.replace('"SENTINEL-PROBE-ALIVE","ordinary"', '"SENTINEL-PROBE-ALIVE" "ordinary"')
        self.assertNotEqual(broken, valid)
        self.assert_unknown(broken, 'missing string comma')

    def test_garbage_before_nodes_fails(self):
        valid = snapshot_body(['SENTINEL-PROBE-ALIVE'])
        broken = valid.replace(',"nodes":[', ',BROKEN,"nodes":[')
        self.assertNotEqual(broken, valid)
        self.assert_unknown(broken, 'garbage before nodes')

    def test_leading_zero_integer_fails(self):
        valid = snapshot_body(['SENTINEL-PROBE-ALIVE'])
        broken = valid.replace('"nodes":[0,', '"nodes":[00,', 1)
        self.assertNotEqual(broken, valid)
        self.assert_unknown(broken, 'leading zero integer')

    def test_trailing_comma_in_node_table_fails(self):
        valid = snapshot_body(['SENTINEL-PROBE-ALIVE'], node_units=2)
        broken = valid.replace('"nodes":[0,0,0,0,0,0,0,0,0,0]', '"nodes":[0,0,0,0,0,0,0,0,0,0,]')
        self.assertNotEqual(broken, valid)
        self.assert_unknown(broken, 'trailing comma')

    def test_duplicate_top_level_key_fails(self):
        valid = snapshot_body(['SENTINEL-PROBE-ALIVE'])
        broken = valid.replace('{"snapshot":', '{"nodes":[],"snapshot":', 1)
        self.assertNotEqual(broken, valid)
        self.assert_unknown(broken, 'duplicate top-level key')

    def test_escaped_string_literals_still_pass(self):
        body = snapshot_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE',
                              'quote " inside', 'tab\tinside', 'slash \\ inside',
                              'unicode \u00e9 inside'])
        result = scan_body(body)
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['sentinels']['bank']['present'])
        self.assertEqual(result['sentinels']['bank']['occurrences'], 1)


class RepresentationControls(unittest.TestCase):
    """Review 76334e2 AH7: the same decoded string must give the same presence.

    `json.loads` treats "ABC" and "\\u0041\\u0042\\u0043" as one value, so a raw-byte
    count silently reports "absent" for the escaped representation — a false negative on
    a *valid* snapshot. Presence must come from the decoded string table.
    """

    EPOCHS = ('baseline', 'owner_active', 'post_logout', 'post_actor')

    @staticmethod
    def escaped(text):
        return ''.join('\\u%04x' % ord(char) for char in text)

    def escaped_body(self, strings):
        body = snapshot_body(strings)
        return body.replace('"SENTINEL-BANK-998877"', '"' + self.escaped('SENTINEL-BANK-998877') + '"')

    def test_escaped_and_literal_documents_are_equal(self):
        body = snapshot_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE'])
        escaped = self.escaped_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE'])
        self.assertNotEqual(body, escaped)
        self.assertEqual(json.loads(body), json.loads(escaped))
        self.assertIn('SENTINEL-BANK-998877', json.loads(escaped)['strings'])

    def test_escaped_representation_detects_present_sentinel(self):
        literal = scan_body(snapshot_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE']))
        escaped = scan_body(self.escaped_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE']))
        self.assertTrue(literal['ok'], literal)
        self.assertTrue(escaped['ok'], escaped)
        self.assertTrue(literal['sentinels']['bank']['present'], literal)
        self.assertTrue(escaped['sentinels']['bank']['present'], escaped)
        self.assertEqual(literal['sentinels']['bank']['occurrences'],
                         escaped['sentinels']['bank']['occurrences'])

    def test_escaped_absence_passes_clean_cycle(self):
        scans = {epoch: scan_body(snapshot_body(['SENTINEL-PROBE-ALIVE'])) for epoch in self.EPOCHS}
        scans['owner_active'] = scan_body(snapshot_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE']))
        scans['post_actor'] = scan_body(self.escaped_body(['SENTINEL-PROBE-ALIVE']))
        expectations = {epoch: {'probe': True, 'bank': epoch == 'owner_active'} for epoch in self.EPOCHS}
        verdict = ORACLE.decide(scans, expectations, True, 'profile')
        self.assertEqual(verdict['verdict'], 'PASS', verdict)

    def test_retained_escaped_bank_fails_cycle(self):
        scans = {epoch: scan_body(snapshot_body(['SENTINEL-PROBE-ALIVE'])) for epoch in self.EPOCHS}
        scans['owner_active'] = scan_body(snapshot_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE']))
        # Same retained value, only the JSON representation differs.
        scans['post_actor'] = scan_body(self.escaped_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE']))
        expectations = {epoch: {'probe': True, 'bank': epoch == 'owner_active'} for epoch in self.EPOCHS}
        verdict = ORACLE.decide(scans, expectations, True, 'profile')
        self.assertEqual(verdict['verdict'], 'FAIL', verdict)
        self.assertTrue(any('post_actor' in finding for finding in verdict['findings']), verdict)

    def test_retained_literal_bank_fails_cycle(self):
        scans = {epoch: scan_body(snapshot_body(['SENTINEL-PROBE-ALIVE'])) for epoch in self.EPOCHS}
        scans['owner_active'] = scan_body(snapshot_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE']))
        scans['post_actor'] = scan_body(snapshot_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE']))
        expectations = {epoch: {'probe': True, 'bank': epoch == 'owner_active'} for epoch in self.EPOCHS}
        self.assertEqual(ORACLE.decide(scans, expectations, True, 'profile')['verdict'], 'FAIL')

    def test_mixed_representations_in_one_cycle_agree(self):
        scans = {epoch: scan_body(snapshot_body(['SENTINEL-PROBE-ALIVE'])) for epoch in self.EPOCHS}
        scans['owner_active'] = scan_body(self.escaped_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE']))
        scans['post_logout'] = scan_body(snapshot_body(['SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE']))
        expectations = {epoch: {'probe': True, 'bank': epoch == 'owner_active'} for epoch in self.EPOCHS}
        verdict = ORACLE.decide(scans, expectations, True, 'profile')
        self.assertEqual(verdict['verdict'], 'FAIL', verdict)
        self.assertTrue(any('post_logout' in finding for finding in verdict['findings']), verdict)


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
        scans['post_logout'] = {'ok': False, 'error': 'snapshot_structurally_invalid'}
        self.assertEqual(ORACLE.decide(scans, self.EXPECTATIONS, True, 'profile')['verdict'], 'FAIL')

    def test_missing_epoch_fails(self):
        scans = self.scans({'baseline': False, 'owner_active': True})
        self.assertEqual(ORACLE.decide(scans, self.EXPECTATIONS, True, 'profile')['verdict'], 'FAIL')

    def test_unexpected_epoch_fails(self):
        # An extra epoch cannot hide a leak or pad a short cycle.
        scans = self.scans({'baseline': False, 'owner_active': True, 'post_logout': False})
        scans['post_actor'] = scans['post_logout']
        verdict = ORACLE.decide(scans, self.EXPECTATIONS, True, 'profile')
        self.assertEqual(verdict['verdict'], 'FAIL')
        self.assertTrue(any('post_actor' in f for f in verdict['findings']))

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
