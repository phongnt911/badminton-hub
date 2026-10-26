"""Controls for the BH-07 app-profile heap evidence auditor.

The auditor is what lets a reviewer trust the bundle without the raw heap, so it must
actually fail when the bundle lies: a missing cycle or epoch, a scan that failed while
the verdict still says PASS, an unmanifested file, a secret, CRLF or a tampered hash.

Mutants are built on a synthetic bundle so each control fails for exactly one reason,
and every mutant is re-hashed: the gate must be semantic, not a hash gate.

Run: python -m unittest tests.test_bh07_app_heap_evidence -v
"""
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / 'scripts/bh07_appheap/verify_evidence.py'
EVIDENCE = ROOT / 'docs/reviews/bh07/app_profile_heap_evidence'
_spec = importlib.util.spec_from_file_location('verify_evidence', VERIFIER_PATH)
VERIFIER = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(VERIFIER)

EPOCHS = ('baseline', 'owner_active', 'post_logout', 'post_actor')
ACTORS = ('cohost', 'member')
TESTED_SHA = 'bb2d2130276ad31824acc650a02ecee4b6ba95a6'
MANIFESTED = ('summary.json', 'run.log', 'report.md')


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def make_bundle(root, cycles=2, actors=ACTORS, bank_epochs=('owner_active',)):
    """Write the smallest bundle the auditor should accept, then mutate it per control."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    recorded = []
    for index in range(cycles):
        epochs = {}
        for epoch in EPOCHS:
            present = epoch in bank_epochs
            epochs[epoch] = {
                'ok': True,
                'size_bytes': 100000 + index * 1000 + len(epoch),
                'sha256_12': digest(f'{index}-{epoch}')[:12],
                'sentinels': {
                    'bank': {'present': present, 'occurrences': 1 if present else 0},
                    'probe': {'present': True, 'occurrences': 1},
                },
            }
        recorded.append({
            'cycle': index + 1,
            'actor': actors[index % len(actors)],
            'same_document': True,
            'time_origin': 1792993862681.5 + index,
            'epochs': epochs,
            'verdict': {'verdict': 'PASS', 'findings': [], 'epochs_checked': 4},
        })
    summary = {
        'gate': 'V2b - app-profile Dart heap / in-memory retention after actor switch',
        'reference': 'docs/reviews/bh07/bh07_readiness.md 4.4',
        'status': 'RUN',
        'measurement_surface': 'Flutter Web profile build + Chrome DevTools Protocol HeapProfiler',
        'oracle': 'fixture sentinel strings counted in live V8 heap snapshots',
        'tested_source_sha': TESTED_SHA,
        'git_dirty': False,
        'git_dirty_paths': [],
        'started_at': '2026-10-26T05:50:13.979Z',
        'finished_at': '2026-10-26T05:53:49.028Z',
        'environment': {
            'os': 'win32 10.0.26100',
            'node': 'v24.21.0',
            'flutter': 'Flutter 3.47.6 - channel stable',
            'chrome': 'Chrome/155.0.8059.85',
            'build': {
                'mode': 'profile',
                'build_ms': 44925,
                'started_at': '2026-10-26T05:50:14.000Z',
                'artifacts_root': 'build/web',
                'artifacts': {name: digest(name) for name in ('index.html', 'main.dart.js', 'flutter_bootstrap.js')},
                'served_match': True,
            },
        },
        'sentinels': {
            'bank': {'sha256_12': '65dce15efcc4', 'length': 10, 'kind': 'club bank account number'},
            'probe': {'sha256_12': '16d8da2f71d6', 'length': 25, 'kind': 'detector sanity marker'},
        },
        'cycles': recorded,
        'cleanup': {
            'dump_dir_outside_repo': True,
            'raw_snapshots_remaining': 0,
            'dumps_dir_removed': True,
            'chrome_profile_dir_removed': True,
            'ok': True,
        },
        'verdict': 'PASS',
        'findings': [],
    }
    lines = [
        '# V2b - app-profile heap / in-memory retention after actor switch',
        '',
        '- Status: **RUN** (verdict PASS)',
        f'- Tested source: `{TESTED_SHA}` (git dirty: False)',
        '- Build: ' + json.dumps(summary['environment']['build'], sort_keys=True),
        '',
        '| cycle | epoch | snapshot bytes | snapshot sha256[:12] |',
        '| --- | --- | --- | --- |',
    ]
    for cycle in recorded:
        for epoch, scan in cycle['epochs'].items():
            lines.append(f"| {cycle['cycle']} | {epoch} | {scan['size_bytes']} | {scan['sha256_12']} |")
    (root / 'report.md').write_bytes(('\n'.join(lines) + '\n').encode('utf-8'))
    (root / 'summary.json').write_bytes((json.dumps(summary, indent=2) + '\n').encode('utf-8'))
    (root / 'run.log').write_bytes(b'[2026-10-26T05:50:13.979Z] cycle 1: actor path Owner -> logout -> cohost\n')
    write_manifest(root)
    return root


def write_manifest(root, names=MANIFESTED):
    root = Path(root)
    body = ''.join(f'{hashlib.sha256((root / name).read_bytes()).hexdigest()}  {name}\n' for name in names)
    (root / 'hashes.sha256').write_bytes(body.encode('utf-8'))


def read_summary(root):
    return json.loads((Path(root) / 'summary.json').read_bytes())


def write_summary(root, summary):
    (Path(root) / 'summary.json').write_bytes((json.dumps(summary, indent=2) + '\n').encode('utf-8'))


class EvidenceAuditControls(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='bh07_appheap_audit_'))
        self.bundle = make_bundle(self.tmp / 'evidence')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def mutate_summary(self, mutate, rehash=True):
        summary = read_summary(self.bundle)
        mutate(summary)
        write_summary(self.bundle, summary)
        if rehash:
            write_manifest(self.bundle)

    def assert_rejected(self, needle):
        problems = VERIFIER.verify(self.bundle)
        self.assertTrue(problems, 'auditor accepted a bundle that should fail')
        self.assertTrue(any(needle.lower() in p.lower() for p in problems),
                        f'expected a problem mentioning {needle!r}, got {problems}')
        return problems

    def test_synthetic_bundle_passes(self):
        self.assertEqual(VERIFIER.verify(self.bundle), [])

    def test_published_bundle_passes(self):
        self.assertEqual(VERIFIER.verify(EVIDENCE), [])

    def test_zero_cycles_fails(self):
        self.mutate_summary(lambda s: s.update(cycles=[]))
        self.assert_rejected('cycle')

    def test_single_cycle_fails(self):
        self.mutate_summary(lambda s: s.update(cycles=s['cycles'][:1]))
        self.assert_rejected('cycle')

    def test_same_actor_twice_fails(self):
        def mutate(summary):
            summary['cycles'][1]['actor'] = 'cohost'
        self.mutate_summary(mutate)
        self.assert_rejected('actor')

    def test_missing_epoch_fails(self):
        def mutate(summary):
            del summary['cycles'][0]['epochs']['post_actor']
        self.mutate_summary(mutate)
        self.assert_rejected('post_actor')

    def test_extra_epoch_fails(self):
        def mutate(summary):
            epochs = summary['cycles'][0]['epochs']
            epochs['after_reload'] = epochs['post_actor']
        self.mutate_summary(mutate)
        self.assert_rejected('after_reload')

    def test_failed_scan_with_leak_fails(self):
        # A scan that failed is not "absent", and a leak must not stay PASS.
        def mutate(summary):
            epoch = summary['cycles'][0]['epochs']['post_actor']
            epoch['ok'] = False
            epoch['sentinels']['bank']['present'] = True
        self.mutate_summary(mutate)
        self.assert_rejected('verdict')

    def test_retained_after_logout_fails(self):
        def mutate(summary):
            summary['cycles'][0]['epochs']['post_logout']['sentinels']['bank']['present'] = True
        self.mutate_summary(mutate)
        self.assert_rejected('post_logout')

    def test_dead_detector_fails(self):
        def mutate(summary):
            for cycle in summary['cycles']:
                cycle['epochs']['baseline']['sentinels']['probe']['present'] = False
        self.mutate_summary(mutate)
        self.assert_rejected('probe')

    def test_cycle_verdict_mismatch_fails(self):
        def mutate(summary):
            summary['cycles'][0]['verdict']['findings'] = ['hand written']
        self.mutate_summary(mutate)
        self.assert_rejected('verdict')

    def test_overall_verdict_mismatch_fails(self):
        def mutate(summary):
            summary['verdict'] = 'FAIL'
        self.mutate_summary(mutate)
        self.assert_rejected('verdict')

    def test_report_status_mismatch_fails(self):
        path = self.bundle / 'report.md'
        path.write_bytes(path.read_bytes().replace(b'- Status: **RUN**', b'- Status: **FAIL**'))
        write_manifest(self.bundle)
        self.assert_rejected('report.md')

    def test_report_missing_epoch_row_fails(self):
        path = self.bundle / 'report.md'
        sha = read_summary(self.bundle)['cycles'][1]['epochs']['post_actor']['sha256_12']
        path.write_bytes(path.read_bytes().replace(sha.encode(), b'000000000000'))
        write_manifest(self.bundle)
        self.assert_rejected('report.md')

    def test_missing_build_provenance_fails(self):
        self.mutate_summary(lambda s: s['environment']['build'].pop('artifacts'))
        self.assert_rejected('artifact')

    def test_reused_build_fails(self):
        self.mutate_summary(lambda s: s['environment']['build'].update(reused=True))
        self.assert_rejected('reused')

    def test_served_bytes_mismatch_fails(self):
        self.mutate_summary(lambda s: s['environment']['build'].update(served_match=False))
        self.assert_rejected('served')

    def test_non_profile_build_fails(self):
        self.mutate_summary(lambda s: s['environment']['build'].update(mode='debug'))
        self.assert_rejected('profile')

    def test_unmanifested_extra_fails(self):
        (self.bundle / 'notes.txt').write_bytes(b'extra evidence\n')
        self.assert_rejected('manifest')

    def test_unmanifested_secret_fails(self):
        (self.bundle / 'extra.txt').write_bytes(b'bh07-http-' + b'pass-canary\n')
        problems = VERIFIER.verify(self.bundle)
        self.assertTrue(any('manifest' in p for p in problems), problems)

    def test_secret_in_manifested_file_fails(self):
        (self.bundle / 'run.log').write_bytes(b'password bh07-http-pass-123456\n')
        write_manifest(self.bundle)
        self.assert_rejected('password')

    def test_manifest_traversal_fails(self):
        body = (self.bundle / 'hashes.sha256').read_bytes()
        (self.bundle / 'hashes.sha256').write_bytes(body + b'0' * 64 + b'  ../escape.txt\n')
        self.assert_rejected('unsafe')

    def test_manifest_absolute_fails(self):
        body = (self.bundle / 'hashes.sha256').read_bytes()
        (self.bundle / 'hashes.sha256').write_bytes(body + b'0' * 64 + b'  C:/windows/win.ini\n')
        self.assert_rejected('unsafe')

    def test_manifest_duplicate_fails(self):
        body = (self.bundle / 'hashes.sha256').read_bytes()
        line = [l for l in body.splitlines() if l.endswith(b'  run.log')][0]
        (self.bundle / 'hashes.sha256').write_bytes(body + line + b'\n')
        self.assert_rejected('twice')

    def test_manifest_missing_entry_fails(self):
        write_manifest(self.bundle, ('summary.json', 'run.log'))
        self.assert_rejected('manifest')

    def test_manifest_self_entry_fails(self):
        write_manifest(self.bundle, MANIFESTED + ('hashes.sha256',))
        self.assert_rejected('manifest')

    def test_tampered_file_fails(self):
        (self.bundle / 'run.log').write_bytes(b'rewritten after hashing\n')
        self.assert_rejected('hash mismatch')

    def test_crlf_fails(self):
        path = self.bundle / 'run.log'
        path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
        write_manifest(self.bundle)
        self.assert_rejected('CR')

    def test_lone_cr_fails(self):
        path = self.bundle / 'run.log'
        path.write_bytes(path.read_bytes().replace(b'\n', b'\r'))
        write_manifest(self.bundle)
        self.assert_rejected('CR')

    def test_invalid_utf8_fails(self):
        path = self.bundle / 'run.log'
        path.write_bytes(path.read_bytes() + b'\xff\n')
        write_manifest(self.bundle)
        self.assert_rejected('UTF-8')

    def test_bom_fails(self):
        path = self.bundle / 'report.md'
        path.write_bytes(b'\xef\xbb\xbf' + path.read_bytes())
        write_manifest(self.bundle)
        self.assert_rejected('BOM')

    def test_crlf_manifest_fails(self):
        path = self.bundle / 'hashes.sha256'
        path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
        self.assert_rejected('CR')

    def test_unverified_cleanup_fails(self):
        self.mutate_summary(lambda s: s['cleanup'].update(dumps_dir_removed=False))
        self.assert_rejected('cleanup')

    def test_published_raw_heap_fails(self):
        (self.bundle / 'owner_active.heapsnapshot').write_bytes(b'{}')
        self.assert_rejected('raw heap')

    def test_sentinel_value_published_fails(self):
        self.mutate_summary(lambda s: s['sentinels']['bank'].update(value='0123456789'))
        self.assert_rejected('raw value')

    def test_audit_is_readonly(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.bundle.iterdir() if p.is_file()}
        VERIFIER.verify(self.bundle)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.bundle.iterdir() if p.is_file()}
        self.assertEqual(before, after, 'auditor modified the bundle')
        self.assertFalse(any(p.name.endswith('.heapsnapshot') for p in self.bundle.iterdir()))


if __name__ == '__main__':
    unittest.main()
