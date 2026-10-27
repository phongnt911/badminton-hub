"""Controls for the retained-path half of the BH-07 app-profile heap gate (readiness §4.4).

A string-table count only proves a value exists somewhere in the heap. It cannot say
whether a live object still holds it or which GC root keeps it alive, so §4.4 needs the
V8 object graph walked from the synthetic root. These controls pin every way that walk
can lie in the wrong direction ("clean" because the graph was never read):

- the graph is walked over strong edges only, so a weak edge is not retention;
- a string that only exists in the string table (no retainer) is not retention either;
- the published path names a root kind, starts at the root and carries no value;
- the strict verdict requires the analysis to exist, requires a path while Owner is
  viewing, forbids one after logout/actor switch, and refuses "only the bank sentinel
  loaded" as coverage.

Run: python -m unittest tests.test_bh07_app_heap_paths -v
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

# string index 0 is V8's empty string, so names/labels start at 1
STRINGS = ['', '(Global handles)', '(Bootstrapper)', 'Object', 'Object',
           'SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE', 'SENTINEL-EXPENSE-42',
           'bankRef', 'probeRef', 'expenseRef', 'z' * 4200]
NODE_FIELDS = ['type', 'name', 'id', 'self_size', 'edge_count']
NODE_TYPES = [['hidden', 'synthetic', 'object', 'string'], 'string', 'number', 'number', 'number']
EDGE_FIELDS = ['type', 'name_or_index', 'to_node']
EDGE_TYPES = [['property', 'internal', 'weak', 'element'], 'string_or_number', 'node']
SYNTHETIC, OBJECT, STRING = 1, 2, 3
PROPERTY, INTERNAL, WEAK = 0, 1, 2
BANK_STRING, PROBE_STRING, EXPENSE_STRING = 5, 6, 7


def write_snapshot(nodes, edges):
    """nodes: [(type, name, edge_count)], edges: [(type, name_or_index, to_node_index)]."""
    width = len(NODE_FIELDS)
    flat_nodes = []
    for node_type, name, edge_count in nodes:
        flat_nodes += [node_type, name, 0, 0, edge_count]
    flat_edges = []
    for edge_type, name_or_index, to_node in edges:
        flat_edges += [edge_type, name_or_index, to_node * width]
    body = {
        'snapshot': {
            'meta': {'node_fields': NODE_FIELDS, 'node_types': NODE_TYPES,
                     'edge_fields': EDGE_FIELDS, 'edge_types': EDGE_TYPES},
            'node_count': len(nodes), 'edge_count': len(edges), 'trace_function_count': 0,
        },
        'nodes': flat_nodes,
        'edges': flat_edges,
        'traces': [],
        'strings': STRINGS,
    }
    return json.dumps(body, separators=(',', ':')).encode('utf-8')


def clean_graph(weak_bank=False, orphan_objects=False):
    """root -> (Global handles) -> Object -> {bank, probe, expense} string nodes."""
    nodes = [(SYNTHETIC, 0, 1),          # 0 synthetic root
             (SYNTHETIC, 1, 1),          # 1 (Global handles)
             (OBJECT, 3, 3),             # 2 a JS object holding three references
             (STRING, BANK_STRING, 0),   # 3
             (STRING, PROBE_STRING, 0),  # 4
             (STRING, EXPENSE_STRING, 0)]  # 5
    edges = [(INTERNAL, 0, 1),                              # root -> global handles
             (INTERNAL, 0, 2),                              # global handles -> object
             (WEAK if weak_bank else PROPERTY, 8, 3),       # object -> bank
             (PROPERTY, 9, 4),                              # object -> probe
             (PROPERTY, 10, 5)]                             # object -> expense
    if orphan_objects:
        # A string that exists in the table but nothing retains: never referenced.
        nodes.append((STRING, BANK_STRING, 0))
        del edges[2]  # and the object no longer holds the bank value
        nodes[2] = (OBJECT, 3, 2)
    return write_snapshot(nodes, edges)


def graph_scan(body, sentinels=None, with_paths=True):
    with tempfile.NamedTemporaryFile('wb', suffix='.heapsnapshot', delete=False) as fp:
        fp.write(body)
        path = fp.name
    try:
        return ORACLE.scan(path, sentinels or {'bank': 'SENTINEL-BANK-998877',
                                               'probe': 'SENTINEL-PROBE-ALIVE',
                                               'expense': 'SENTINEL-EXPENSE-42'},
                           with_paths=with_paths)
    finally:
        Path(path).unlink()


def path_record(reachable, root_kind='global_handles', path_len=3, exact=True):
    if not reachable:
        return {'reachable': False, 'exact': exact}
    return {'reachable': True, 'root_kind': root_kind, 'path_len': path_len,
            'frames': ['root', 'internal:(Global handles) -> synthetic',
                       'internal:map -> object', 'property:bankRef -> string'],
            'path_sha256_12': '0123456789ab', 'exact': exact}


CLASSES = {
    'probe': {'rendered': False, 'distinctive': True, 'scope': 'control'},
    # The bank digit run is not distinctive (a hit can be a UUID substring) and the title is
    # rendered text, so neither can carry the gate; the two ids below do.
    'bank': {'rendered': False, 'distinctive': False, 'scope': 'bank'},
    'expense': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
    'player': {'rendered': False, 'distinctive': True, 'scope': 'identity'},
}


def scan_record(bank, probe=True, expense=False, paths=True, bank_path=None, exact=True):
    record = {
        'ok': True,
        'sentinels': {
            'probe': {'present': probe, 'occurrences': 1 if probe else 0, **CLASSES['probe']},
            'bank': {'present': bank, 'occurrences': 1 if bank else 0, **CLASSES['bank']},
            'expense': {'present': expense, 'occurrences': 1 if expense else 0, **CLASSES['expense']},
            'player': {'present': expense, 'occurrences': 1 if expense else 0, **CLASSES['player']},
        },
    }
    if paths:
        record['paths'] = {
            'probe': path_record(probe, exact=exact),
            'bank': path_record(bank if bank_path is None else bank_path, exact=exact),
            'expense': path_record(expense, exact=exact),
            'player': path_record(expense, exact=exact),
        }
    return record


def cycle(bank=False, probe=True, expense=False, paths=True, bank_path=None, exact=True):
    return {
        'baseline': scan_record(False, True, False, paths, exact=exact),
        'owner_active': scan_record(bank, probe, expense, paths, bank_path, exact=exact),
        'post_logout': scan_record(False, True, False, paths, exact=exact),
        'post_actor': scan_record(False, True, False, paths, exact=exact),
    }


class GraphWalkControls(unittest.TestCase):
    def test_reachable_sentinel_publishes_a_root_path(self):
        result = graph_scan(clean_graph())
        self.assertTrue(result['ok'], result)
        bank = result['paths']['bank']
        self.assertIs(bank['reachable'], True)
        self.assertEqual(bank['root_kind'], 'global_handles')
        self.assertEqual(bank['frames'][0], 'root')
        self.assertEqual(bank['path_len'], len(bank['frames']) - 1)

    def test_count_alone_is_not_retention(self):
        result = graph_scan(clean_graph(orphan_objects=True))
        self.assertTrue(result['sentinels']['bank']['present'])
        self.assertIs(result['paths']['bank']['reachable'], False)

    def test_weak_edge_is_not_retention(self):
        result = graph_scan(clean_graph(weak_bank=True))
        self.assertTrue(result['sentinels']['bank']['present'])
        self.assertIs(result['paths']['bank']['reachable'], False)

    def test_live_control_probe_is_walked(self):
        result = graph_scan(clean_graph())
        self.assertIs(result['paths']['probe']['reachable'], True)

    def test_paths_are_optional_for_the_count_only_gate(self):
        result = graph_scan(clean_graph(), with_paths=False)
        self.assertTrue(result['ok'], result)
        self.assertNotIn('paths', result)

    def test_path_frames_carry_no_sentinel_value(self):
        result = graph_scan(clean_graph())
        published = json.dumps(result)
        for value in ('SENTINEL-BANK-998877', 'SENTINEL-PROBE-ALIVE', 'SENTINEL-EXPENSE-42'):
            self.assertNotIn(value, published)


class PathSchemaControls(unittest.TestCase):
    def problems(self, record, require=True):
        scan = scan_record(True)
        scan['paths']['bank'] = record
        return ORACLE.path_problems(scan, require)

    def test_valid_path_record_passes(self):
        self.assertEqual(self.problems(path_record(True)), [])

    def test_unreachable_record_passes(self):
        self.assertEqual(self.problems(path_record(False)), [])

    def test_unreachable_record_publishing_a_path_fails(self):
        record = path_record(True)
        record['reachable'] = False
        self.assertTrue(self.problems(record))

    def test_unknown_root_kind_fails(self):
        self.assertTrue(self.problems(path_record(True, root_kind='nowhere')))

    def test_zero_path_length_fails(self):
        self.assertTrue(self.problems(path_record(True, path_len=0)))

    def test_boolean_path_length_fails(self):
        self.assertTrue(self.problems(path_record(True, path_len=True)))

    def test_frames_must_start_at_root(self):
        record = path_record(True)
        record['frames'][0] = 'object'
        self.assertTrue(self.problems(record))

    def test_single_frame_path_fails(self):
        record = path_record(True)
        record['frames'] = ['root']
        self.assertTrue(self.problems(record))

    def test_missing_path_hash_fails(self):
        record = path_record(True)
        record.pop('path_sha256_12')
        self.assertTrue(self.problems(record))

    def test_missing_reachability_fails(self):
        self.assertTrue(self.problems({'path_len': 3}))

    def test_missing_exact_flag_fails(self):
        record = path_record(True)
        record.pop('exact')
        self.assertTrue(self.problems(record))

    def test_non_boolean_exact_flag_fails(self):
        self.assertTrue(self.problems(path_record(True, exact='yes')))

    def test_substring_only_match_is_published_but_not_a_gate(self):
        # A value retained inside a longer string is still exposure, so `exact=False`
        # must not turn a real match into "clean": it is diagnostic only.
        scan = scan_record(True, exact=False)
        self.assertEqual(ORACLE.path_problems(scan), [])
        scans = cycle(bank=True, expense=True, exact=False)
        self.assertEqual(ORACLE.decide(scans, ORACLE.derive_expectations(scans), True,
                                       'profile', strict=True)['verdict'], 'PASS')

    def test_non_boolean_reachability_fails(self):
        self.assertTrue(self.problems({'reachable': 'yes'}))

    def test_record_for_unclaimed_sentinel_fails(self):
        scan = scan_record(True)
        scan['paths']['ghost'] = path_record(True)
        self.assertTrue(ORACLE.path_problems(scan))

    def test_sentinel_without_record_fails(self):
        scan = scan_record(True)
        del scan['paths']['expense']
        self.assertTrue(ORACLE.path_problems(scan))

    def test_missing_analysis_fails_only_when_required(self):
        scan = scan_record(True, paths=False)
        self.assertEqual(ORACLE.path_problems(scan, False), [])
        self.assertTrue(ORACLE.path_problems(scan, True))

    def test_broken_analysis_fails(self):
        scan = scan_record(True)
        scan['paths'] = {'error': 'snapshot_edge_target_invalid'}
        self.assertTrue(ORACLE.path_problems(scan))

    def test_scan_problems_forwards_the_path_gate(self):
        scan = scan_record(True, paths=False)
        self.assertEqual(ORACLE.scan_problems(scan), [])
        self.assertTrue(ORACLE.scan_problems(scan, True))


class StrictVerdictControls(unittest.TestCase):
    def decide(self, scans, strict=True, cleanup_ok=True):
        return ORACLE.decide(scans, ORACLE.derive_expectations(scans), cleanup_ok, 'profile',
                             strict=strict)

    def test_clean_paths_pass(self):
        self.assertEqual(self.decide(cycle(bank=True, expense=True))['verdict'], 'PASS')

    def test_count_only_bundle_fails_the_path_gate(self):
        self.assertEqual(self.decide(cycle(bank=True, expense=True, paths=False))['verdict'], 'FAIL')

    def test_bank_only_coverage_fails(self):
        result = self.decide(cycle(bank=True))
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertTrue(any('at least' in finding for finding in result['findings']))

    def test_two_finance_sentinels_are_enough(self):
        self.assertEqual(self.decide(cycle(bank=True, expense=True))['verdict'], 'PASS')

    def test_reachable_after_logout_fails(self):
        scans = cycle(bank=True, expense=True)
        scans['post_logout'] = scan_record(True, expense=True)
        self.assertEqual(self.decide(scans)['verdict'], 'FAIL')

    def test_owner_value_without_a_path_fails(self):
        scans = cycle(bank=True, expense=True)
        scans['owner_active']['paths']['expense'] = path_record(False)
        self.assertEqual(self.decide(scans)['verdict'], 'FAIL')

    def test_dead_probe_path_fails(self):
        scans = cycle(bank=True, expense=True)
        scans['post_actor']['paths']['probe'] = path_record(False)
        self.assertEqual(self.decide(scans)['verdict'], 'FAIL')

    def test_baseline_sentinel_is_not_gated(self):
        # A value already present before login cannot discriminate: it is not a gate.
        scans = cycle(bank=True, expense=True)
        for epoch in scans:
            scans[epoch]['sentinels']['preloaded'] = {
                'present': True, 'occurrences': 1,
                **ORACLE.sentinel_class({'preloaded': {'scope': 'finance'}}, 'preloaded')}
            scans[epoch]['paths']['preloaded'] = path_record(True)
        self.assertEqual(self.decide(scans)['verdict'], 'PASS')

    def test_loader_that_never_loaded_is_not_coverage(self):
        # expense loaded at baseline only: it is excluded, so the bank alone cannot pass.
        scans = cycle(bank=True)
        for epoch in scans:
            scans[epoch]['sentinels']['expense'] = {
                'present': epoch == 'baseline', 'occurrences': 1, **CLASSES['expense']}
            scans[epoch]['paths']['expense'] = path_record(epoch == 'baseline')
        self.assertEqual(self.decide(scans)['verdict'], 'FAIL')

    def test_rendered_text_retained_after_logout_is_a_residual_risk_not_a_failure(self):
        scans = cycle(bank=True, expense=True)
        for epoch in ('post_logout', 'post_actor'):
            scans[epoch]['sentinels']['rendered_title'] = {
                'present': True, 'occurrences': 1,
                **ORACLE.sentinel_class({'rendered_title': {'rendered': True, 'scope': 'finance'}},
                                        'rendered_title')}
            scans[epoch]['paths']['rendered_title'] = path_record(True)
        result = self.decide(scans)
        self.assertEqual(result['verdict'], 'PASS', result['findings'])
        self.assertEqual([risk['epoch'] for risk in result['residual_risks']],
                         ['post_logout', 'post_actor'])

    def test_non_distinctive_value_is_not_gated(self):
        # Measured in the fixture: `0000000007` only ever matched a fixture UUID.
        scans = cycle(bank=True)
        result = self.decide(scans)
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertTrue(any('not distinctive' in note for note in result['notes']), result)


class DeriveExpectationControls(unittest.TestCase):
    def test_distinctive_unrendered_finance_value_is_gated_everywhere(self):
        expectations = ORACLE.derive_expectations(cycle(expense=True))
        self.assertIs(expectations['owner_active']['expense'], True)
        self.assertIs(expectations['post_logout']['expense'], False)
        self.assertIs(expectations['post_actor']['expense'], False)

    def test_non_distinctive_value_is_never_gated(self):
        # bank is declared non-distinctive, so its presence at Owner proves nothing.
        self.assertNotIn('bank', ORACLE.derive_expectations(cycle(bank=True))['owner_active'])

    def test_rendered_value_is_never_gated(self):
        scans = cycle()
        for epoch in scans:
            scans[epoch]['sentinels']['title'] = {
                'present': epoch == 'owner_active', 'occurrences': 1,
                **ORACLE.sentinel_class({'title': {'rendered': True, 'scope': 'finance'}}, 'title')}
            scans[epoch]['paths']['title'] = path_record(epoch == 'owner_active')
        self.assertNotIn('title', ORACLE.derive_expectations(scans)['owner_active'])

    def test_probe_is_live_everywhere(self):
        expectations = ORACLE.derive_expectations(cycle())
        self.assertTrue(all(epoch['probe'] is True for epoch in expectations.values()))

    def test_value_never_loaded_is_skipped(self):
        self.assertNotIn('expense', ORACLE.derive_expectations(cycle())['owner_active'])

    def test_value_visible_at_baseline_is_skipped(self):
        scans = cycle(expense=True)
        scans['baseline']['sentinels']['expense'] = {
            'present': True, 'occurrences': 1, **CLASSES['expense']}
        self.assertNotIn('expense', ORACLE.derive_expectations(scans)['owner_active'])


class PathCliControls(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='bh07_path_cli_'))
        self.snapshot = self.tmp / 'graph.heapsnapshot'
        self.snapshot.write_bytes(clean_graph())
        self.sentinels = self.tmp / 'sentinels.json'
        self.sentinels.write_text(json.dumps({'bank': 'SENTINEL-BANK-998877',
                                             'probe': 'SENTINEL-PROBE-ALIVE'}),
                                  encoding='utf-8')

    def tearDown(self):
        for path in self.tmp.iterdir():
            path.unlink()
        self.tmp.rmdir()

    def run_oracle(self, *args):
        return subprocess.run([sys.executable, '-X', 'utf8', str(ORACLE_PATH), *args],
                              capture_output=True, text=True)

    def test_scan_paths_flag_publishes_the_walk(self):
        result = self.run_oracle('scan', '--snapshot', str(self.snapshot),
                                 '--sentinels', str(self.sentinels), '--paths')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"paths"', result.stdout)
        self.assertTrue(json.loads(result.stdout)['paths']['bank']['reachable'])

    def test_scan_without_the_flag_stays_count_only(self):
        result = self.run_oracle('scan', '--snapshot', str(self.snapshot),
                                 '--sentinels', str(self.sentinels))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('"paths"', result.stdout)

    def test_decide_require_paths_rejects_count_only_scans(self):
        scans = self.tmp / 'scans.json'
        scans.write_text(json.dumps(cycle(bank=True, expense=True, paths=False)), encoding='utf-8')
        expectations = ORACLE.derive_expectations(cycle(bank=True, expense=True))
        expectations_path = self.tmp / 'expectations.json'
        expectations_path.write_text(json.dumps(expectations), encoding='utf-8')
        strict = self.run_oracle('decide', '--scans', str(scans), '--expectations',
                                 str(expectations_path), '--cleanup-ok', 'true',
                                 '--mode', 'profile', '--require-paths')
        self.assertEqual(strict.returncode, 1)
        self.assertEqual(json.loads(strict.stdout)['verdict'], 'FAIL')
        lenient = self.run_oracle('decide', '--scans', str(scans), '--expectations',
                                  str(expectations_path), '--cleanup-ok', 'true',
                                  '--mode', 'profile')
        self.assertEqual(lenient.returncode, 0, lenient.stdout)

    def test_expectations_command_derives_from_scans(self):
        scans = self.tmp / 'scans.json'
        scans.write_text(json.dumps(cycle(bank=True, expense=True)), encoding='utf-8')
        out = self.tmp / 'derived.json'
        result = self.run_oracle('expectations', '--scans', str(scans), '--out', str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        derived = json.loads(out.read_text(encoding='utf-8'))
        self.assertIs(derived['owner_active']['expense'], True)
        self.assertIs(derived['post_actor']['expense'], False)


class SelfTestCoverage(unittest.TestCase):
    def test_oracle_self_test_covers_the_path_gate(self):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(ORACLE_PATH), 'self-test'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        passed, total = result.stdout.split(':')[1].split('controls')[0].strip().split('/')
        self.assertGreaterEqual(int(total), 23)
        self.assertEqual(passed, total)


if __name__ == '__main__':
    unittest.main()
