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
import os
import shutil
import subprocess
import sys
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


def js_bool(value):
    return 'true' if value is True else 'false'


def render_report(summary):
    """Mirror the runner's Markdown so the auditor's row-by-row parse has a real target."""
    build = (summary.get('environment') or {}).get('build') or {}
    verdict = f" (verdict {summary['verdict']})" if summary.get('verdict') else ''
    lines = [
        '# V2b - app-profile heap / in-memory retention after actor switch',
        '',
        f"- Gate: {summary.get('gate')}",
        f"- Reference: {summary.get('reference')}",
        f"- Status: **{summary.get('status')}**{verdict}",
        f"- Tested source: `{summary.get('tested_source_sha')}` (git dirty: {js_bool(summary.get('git_dirty'))})",
        f"- Measurement surface: {summary.get('measurement_surface')}",
        f"- Oracle: {summary.get('oracle')}",
        f"- Build: mode={build.get('mode', 'n/a')} reused={js_bool(build.get('reused'))} "
        f"artifacts={len(build.get('artifacts') or {})} served_match={js_bool(build.get('served_match'))}",
        f"- Chrome: {(summary.get('environment') or {}).get('chrome', 'n/a')}; "
        f"Flutter: {(summary.get('environment') or {}).get('flutter', 'n/a')}",
        '',
        '## Sentinels (values never published)',
        '',
        '| sentinel | kind | length | sha256[:12] |',
        '| --- | --- | --- | --- |',
    ]
    for name, sentinel in (summary.get('sentinels') or {}).items():
        length = sentinel.get('length')
        lines.append(f"| {name} | {sentinel.get('kind')} | {length if length is not None else 'n/a'} "
                     f"| {sentinel.get('sha256_12') or 'n/a'} |")
    lines += ['', '## Cycles', '',
              '| cycle | actor path | same document | epoch | snapshot bytes | snapshot sha256[:12] '
              '| present sentinels |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    for cycle in summary.get('cycles') or []:
        for epoch, scan in (cycle.get('epochs') or {}).items():
            present = ', '.join(k for k, v in (scan.get('sentinels') or {}).items() if v.get('present')) or 'none'
            lines.append(f"| {cycle.get('cycle')} | Owner -> logout -> {cycle.get('actor')} "
                         f"| {js_bool(cycle.get('same_document'))} | {epoch} | {scan.get('size_bytes', 'n/a')} "
                         f"| {scan.get('sha256_12') or 'n/a'} | {present} |")
    lines += ['', '## Findings', '']
    findings = summary.get('findings') or []
    lines += [f'- {finding}' for finding in findings] or ['- none']
    if summary.get('error'):
        lines.append(f"- run aborted: {summary['error']}")
    lines += ['', '## Cleanup', '', f"- {json.dumps(summary.get('cleanup') or {}, separators=(',', ':'))}", '']
    return '\n'.join(lines) + '\n'


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
    (root / 'report.md').write_bytes(render_report(summary).encode('utf-8'))
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


class AuditCase(unittest.TestCase):
    """One synthetic bundle per control, plus the two mutation helpers."""

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


class EvidenceAuditControls(AuditCase):
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


class SummaryShapeControls(AuditCase):
    """Review 57ec02c AH2-A: a falsy summary skipped every semantic gate."""

    def replace_summary(self, value):
        (self.bundle / 'summary.json').write_bytes((json.dumps(value) + '\n').encode('utf-8'))
        write_manifest(self.bundle)

    def test_empty_object_summary_fails(self):
        self.replace_summary({})
        self.assert_rejected('missing field')

    def test_null_summary_fails(self):
        self.replace_summary(None)
        self.assert_rejected('JSON object')

    def test_empty_list_summary_fails(self):
        self.replace_summary([])
        self.assert_rejected('JSON object')

    def test_scalar_summary_fails(self):
        self.replace_summary(42)
        self.assert_rejected('JSON object')

    def test_missing_required_field_fails(self):
        self.mutate_summary(lambda s: s.pop('status'))
        self.assert_rejected('missing field')

    def test_cycles_wrong_type_fails(self):
        self.mutate_summary(lambda s: s.update(cycles='two'))
        self.assert_rejected('cycles')

    def test_cycle_entry_not_object_fails(self):
        self.mutate_summary(lambda s: s['cycles'].__setitem__(0, 7))
        self.assert_rejected('not an object')

    def test_epochs_not_object_fails(self):
        self.mutate_summary(lambda s: s['cycles'][0].update(epochs=[]))
        self.assert_rejected('epochs')

    def test_scan_entry_not_object_fails(self):
        self.mutate_summary(lambda s: s['cycles'][0]['epochs'].update(baseline='clean'))
        self.assert_rejected('scan')

    def test_empty_summary_cli_exits_nonzero(self):
        (self.bundle / 'summary.json').write_bytes(b'{}\n')
        write_manifest(self.bundle)
        proc = subprocess.run([sys.executable, '-X', 'utf8', str(VERIFIER_PATH), '--dir', str(self.bundle)],
                              capture_output=True, text=True, cwd=str(ROOT))
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn('PASS:', proc.stdout)


class ReportControls(AuditCase):
    """Review 57ec02c AH2-B: a Markdown verdict that contradicts the JSON must fail."""

    def rewrite_report(self, old, new, count=-1):
        path = self.bundle / 'report.md'
        body = path.read_bytes()
        self.assertIn(old, body)
        path.write_bytes(body.replace(old, new) if count < 0 else body.replace(old, new, count))
        write_manifest(self.bundle)

    def test_report_verdict_contradiction_fails(self):
        self.rewrite_report(b'(verdict PASS)', b'(verdict FAIL)')
        self.assert_rejected('status line')

    def test_report_status_contradiction_fails(self):
        self.rewrite_report(b'- Status: **RUN**', b'- Status: **FAIL**')
        self.assert_rejected('status line')

    def test_report_duplicate_status_line_fails(self):
        path = self.bundle / 'report.md'
        path.write_bytes(path.read_bytes() + b'- Status: **RUN** (verdict PASS)\n')
        write_manifest(self.bundle)
        self.assert_rejected('exactly one status line')

    def test_report_swapped_epoch_rows_fails(self):
        path = self.bundle / 'report.md'
        lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
        rows = [i for i, line in enumerate(lines) if line.startswith('| 1 |')]
        lines[rows[0]], lines[rows[3]] = lines[rows[3]], lines[rows[0]]
        path.write_text(''.join(lines), encoding='utf-8', newline='')
        write_manifest(self.bundle)
        self.assert_rejected('cycle rows')

    def test_report_duplicate_row_fails(self):
        path = self.bundle / 'report.md'
        lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
        rows = [i for i, line in enumerate(lines) if line.startswith('| 1 |')]
        lines.insert(rows[-1] + 1, lines[rows[-1]])
        path.write_text(''.join(lines), encoding='utf-8', newline='')
        write_manifest(self.bundle)
        self.assert_rejected('cycle rows')

    def test_report_actor_label_mismatch_fails(self):
        self.rewrite_report(b'Owner -> logout -> member', b'Owner -> logout -> cohost')
        self.assert_rejected('cycle rows')

    def test_report_present_sentinel_mismatch_fails(self):
        self.rewrite_report(b'| bank, probe |', b'| probe |')
        self.assert_rejected('cycle rows')

    def test_report_missing_findings_section_fails(self):
        self.rewrite_report(b'## Findings', b'## Notes')
        self.assert_rejected('Findings')

    def test_report_build_line_mismatch_fails(self):
        self.rewrite_report(b'served_match=true', b'served_match=false')
        self.assert_rejected('build line')


class LinkControls(AuditCase):
    """Review 57ec02c AH3-A: a link is invisible to a file-only inventory."""

    def make_link(self, target, link, directory=False):
        try:
            os.symlink(target, link, target_is_directory=directory)
        except (OSError, NotImplementedError) as exc:  # Windows without the privilege
            self.skipTest(f'cannot create a link on this host: {exc}')
        if not link.is_symlink():
            self.skipTest('host did not create a real symlink')

    def test_file_symlink_fails(self):
        outside = self.tmp / 'outside.txt'
        outside.write_bytes(b'{}')
        self.make_link(outside, self.bundle / 'linked.txt')
        self.assert_rejected('symlink')

    def test_directory_symlink_fails(self):
        outside = self.tmp / 'outside'
        outside.mkdir()
        (outside / 'fixture.heapsnapshot').write_bytes(b'{}')
        self.make_link(outside, self.bundle / 'linked', directory=True)
        self.assert_rejected('symlink')

    def test_broken_symlink_fails(self):
        self.make_link(self.tmp / 'missing-target', self.bundle / 'broken')
        self.assert_rejected('symlink')

    def test_link_is_part_of_the_readonly_snapshot(self):
        before = VERIFIER._digests(self.bundle)
        outside = self.tmp / 'outside.txt'
        outside.write_bytes(b'{}')
        self.make_link(outside, self.bundle / 'linked.txt')
        after = VERIFIER._digests(self.bundle)
        self.assertIn('linked.txt', after)
        self.assertNotEqual(before, after)


class RawSentinelControls(AuditCase):
    """Review 57ec02c AH3-B: a raw sentinel anywhere in the bundle is unpublished data."""

    CANARY = 'Q7TESTBANK9'
    PROBE_CANARY = 'BH07APPHEAPPROBE-deadbeef'

    def publish_canary(self, name, value):
        def mutate(summary):
            summary['sentinels'][name]['length'] = len(value)
            summary['sentinels'][name]['sha256_12'] = hashlib.sha256(value.encode()).hexdigest()[:12]
        self.mutate_summary(mutate)

    def append_to(self, name, text):
        path = self.bundle / name
        path.write_bytes(path.read_bytes() + text.encode('utf-8') + b'\n')
        write_manifest(self.bundle)

    def test_raw_bank_value_in_log_fails(self):
        self.publish_canary('bank', self.CANARY)
        self.append_to('run.log', f'observed account {self.CANARY}')
        self.assert_rejected('raw value')

    def test_raw_probe_value_in_report_fails(self):
        self.publish_canary('probe', self.PROBE_CANARY)
        self.append_to('report.md', f'- marker {self.PROBE_CANARY}')
        self.assert_rejected('raw value')

    def test_raw_sentinel_in_nested_metadata_fails(self):
        self.publish_canary('bank', self.CANARY)

        def mutate(summary):
            summary['notes'] = {'observed': {'account': self.CANARY}}
        self.mutate_summary(mutate)
        self.assert_rejected('raw value')

    def test_raw_sentinel_in_extra_file_fails(self):
        self.publish_canary('bank', self.CANARY)
        (self.bundle / 'notes.txt').write_bytes(f'{self.CANARY}\n'.encode('utf-8'))
        problems = VERIFIER.verify(self.bundle)
        self.assertTrue(any('raw value' in p for p in problems), problems)

    def test_hash_only_metadata_passes(self):
        self.publish_canary('bank', self.CANARY)
        self.assertEqual(VERIFIER.verify(self.bundle), [])


class SentinelMetadataControls(AuditCase):
    """Review 76334e2 AH8: missing identification metadata must fail, never skip.

    The raw-value detector matches a published length + sha256[:12]. If either field is
    absent the old gate `continue`d, so a bundle could carry the raw value and still be
    certified clean. Every gating sentinel must be identifiable, and a sentinel marked
    unavailable must not be claimed by any scan.
    """

    CANARY = 'Q7TESTBANK9'

    def canary_bundle(self, mutate=None):
        def change(summary):
            bank = summary['sentinels']['bank']
            bank['length'] = len(self.CANARY)
            bank['sha256_12'] = hashlib.sha256(self.CANARY.encode()).hexdigest()[:12]
            if mutate:
                mutate(summary)
        self.mutate_summary(change, rehash=False)
        summary = read_summary(self.bundle)
        (self.bundle / 'report.md').write_bytes(render_report(summary).encode('utf-8'))
        write_manifest(self.bundle)
        return summary

    def put_raw_in_log(self):
        path = self.bundle / 'run.log'
        path.write_bytes(path.read_bytes() + self.CANARY.encode('utf-8') + b'\n')
        write_manifest(self.bundle)

    def test_missing_length_fails(self):
        self.canary_bundle(lambda s: s['sentinels']['bank'].pop('length'))
        self.put_raw_in_log()
        self.assert_rejected('length')

    def test_missing_hash_fails(self):
        self.canary_bundle(lambda s: s['sentinels']['bank'].pop('sha256_12'))
        self.put_raw_in_log()
        self.assert_rejected('sha256_12')

    def test_null_length_fails(self):
        self.canary_bundle(lambda s: s['sentinels']['bank'].update(length=None))
        self.assert_rejected('length')

    def test_zero_length_fails(self):
        self.canary_bundle(lambda s: s['sentinels']['bank'].update(length=0))
        self.assert_rejected('length')

    def test_negative_length_fails(self):
        self.canary_bundle(lambda s: s['sentinels']['bank'].update(length=-10))
        self.assert_rejected('length')

    def test_bool_length_fails(self):
        self.canary_bundle(lambda s: s['sentinels']['bank'].update(length=True))
        self.assert_rejected('length')

    def test_malformed_hash_fails(self):
        self.canary_bundle(lambda s: s['sentinels']['bank'].update(sha256_12='XYZ'))
        self.assert_rejected('sha256_12')

    def test_gating_sentinel_entry_missing_fails(self):
        self.mutate_summary(lambda s: s['sentinels'].pop('bank'))
        self.assert_rejected('bank')

    def test_scan_sentinel_without_metadata_fails(self):
        def mutate(summary):
            for cycle in summary['cycles']:
                cycle['epochs']['baseline']['sentinels']['expense'] = {'present': False, 'occurrences': 0}
        self.mutate_summary(mutate)
        self.assert_rejected('expense')

    def test_unavailable_sentinel_marked_explicitly_passes(self):
        self.mutate_summary(lambda s: s['sentinels'].update(
            expense={'kind': 'posted session expense title (Owner-private)', 'available': False}))
        self.assertEqual(VERIFIER.verify(self.bundle), [])

    def test_unavailable_sentinel_claimed_by_a_scan_fails(self):
        def mutate(summary):
            summary['sentinels']['expense'] = {'kind': 'not loaded', 'available': False}
            for cycle in summary['cycles']:
                cycle['epochs']['owner_active']['sentinels']['expense'] = {'present': True, 'occurrences': 1}
        self.mutate_summary(mutate)
        self.assert_rejected('expense')

    def test_unavailable_sentinel_publishing_hash_fails(self):
        self.mutate_summary(lambda s: s['sentinels'].update(
            expense={'kind': 'not loaded', 'available': False, 'length': 16,
                     'sha256_12': '41a394dd2dcd'}))
        self.assert_rejected('expense')

    def test_raw_value_with_missing_length_still_fails(self):
        self.canary_bundle(lambda s: s['sentinels']['bank'].pop('length'))
        self.put_raw_in_log()
        problems = VERIFIER.verify(self.bundle)
        self.assertTrue(problems, 'a bundle without sentinel length must fail')
        self.assertTrue(any('length' in problem for problem in problems), problems)


if __name__ == '__main__':
    unittest.main()
