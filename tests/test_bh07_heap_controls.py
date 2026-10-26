"""Regression controls for BH-07 V2b heap verification tooling (review 33ad6e6: HP2/HP3/HP6/HP7).

Behavioral reproductions of the reviewer's `extra_controls.py` findings:
- HP2: comments/strings must never count as a real dispose call (cancel/removeListener).
- HP3: a subset of tests, zero tests, skipped tests or an unknown test name must not turn
  every control green; JSON/Markdown/counts must agree; metadata must not claim Finalizer.
- HP6: a failing `git status`/`rev-parse` must yield UNKNOWN provenance, never "clean".
- HP7: every full SHA in the handoff must resolve in Git and commit links must be absolute.

Run: python -m unittest tests.test_bh07_heap_controls -v
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts/bh07_heap'
HANDOFF = ROOT / 'docs/reviews/bh07/private_heap_handoff.md'
SHA_RE = re.compile(r'\b[0-9a-f]{40}\b')


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = _load('bh07_heap_audit_under_test', SCRIPTS / 'audit_ast_memory.py')
RUNNER = _load('bh07_heap_runner_under_test', SCRIPTS / 'run_heap_verification.py')


def audit_provider(code, tmp):
    lib = Path(tmp) / 'lib'
    (lib / 'providers').mkdir(parents=True, exist_ok=True)
    (lib / 'providers/auth_provider.dart').write_text(code, encoding='utf-8')
    return AUDIT.audit_listeners_and_subscriptions(str(lib))['auth_provider.dart']


def static_issues(code, tmp):
    p = Path(tmp) / 'static_case'
    p.mkdir(exist_ok=True)
    (p / 'sample.dart').write_text(code, encoding='utf-8')
    return AUDIT.audit_static_and_globals(str(p))[1]


def events(results):
    """Flutter `--reporter json` events for a mapping of test name -> result."""
    lines, ok = [], True
    for idx, (name, result) in enumerate(results.items(), start=1):
        lines.append(json.dumps({'type': 'testStart', 'test': {'id': idx, 'name': name}}))
        lines.append(json.dumps({'type': 'testDone', 'testID': idx, 'result': result,
                                 'skipped': result == 'skipped', 'hidden': False}))
        ok = ok and result == 'success'
    lines.append(json.dumps({'type': 'done', 'success': ok}))
    return '\n'.join(lines) + '\n'


def all_pass():
    return {name: 'success' for name in RUNNER.EXPECTED_TESTS}


GROUP_PREFIX = 'V2b — Provider In-Memory State Purge & WeakReference Retention (Supporting Evidence) '


def json_stream(rows, extra_events=()):
    """Stream `flutter test --reporter json` thật: loader hidden + tên test có prefix group.

    `rows` là danh sách (tên test, result, skipped) đúng như protocol Flutter phát ra.
    """
    lines = [
        json.dumps({'protocolVersion': '0.1.1', 'type': 'start'}),
        json.dumps({'suite': {'id': 0, 'platform': 'vm', 'path': 'suite.dart'}, 'type': 'suite'}),
        json.dumps({'type': 'testStart', 'test': {'id': 1, 'name': 'loading suite.dart'}}),
        json.dumps({'type': 'testDone', 'testID': 1, 'result': 'success', 'skipped': False, 'hidden': True}),
        json.dumps({'type': 'group', 'group': {'id': 2, 'name': '', 'parentID': None}}),
    ]
    for idx, (name, result, skipped) in enumerate(rows, start=10):
        lines.append(json.dumps({'type': 'testStart', 'test': {'id': idx, 'name': GROUP_PREFIX + name}}))
        lines.append(json.dumps({'type': 'testDone', 'testID': idx, 'result': result,
                                 'skipped': skipped, 'hidden': False}))
    lines.extend(extra_events)
    lines.append(json.dumps({'type': 'done', 'success': all(r == 'success' and not s for _, r, s in rows)}))
    return '\n'.join(lines) + '\n'


def real_rows(skip_name=None):
    return [(name, 'success', name == skip_name) for name in RUNNER.EXPECTED_TESTS]


class DisposeLexicalControls(unittest.TestCase):
    """HP2: only executable tokens inside dispose() count as a dispose call."""

    def test_real_cancel_in_dispose_is_clean(self):
        code = 'class X {\n StreamSubscription<int>? _sub;\n void dispose() { _sub?.cancel(); }\n}'
        with tempfile.TemporaryDirectory() as d:
            res = audit_provider(code, d)
        self.assertEqual(res['leak_risk'], 'NONE')
        self.assertEqual(res['un_cancelled_subscriptions'], [])

    def test_line_comment_cancel_is_not_a_call(self):
        code = 'class X {\n StreamSubscription<int>? _sub;\n void dispose() {\n // _sub?.cancel();\n }\n}'
        with tempfile.TemporaryDirectory() as d:
            res = audit_provider(code, d)
        self.assertEqual(res['leak_risk'], 'HIGH')
        self.assertIn('_sub', res['un_cancelled_subscriptions'])

    def test_string_literal_cancel_is_not_a_call(self):
        code = "class X {\n StreamSubscription<int>? _sub;\n void dispose() { print('_sub?.cancel()'); }\n}"
        with tempfile.TemporaryDirectory() as d:
            res = audit_provider(code, d)
        self.assertEqual(res['leak_risk'], 'HIGH')
        self.assertIn('_sub', res['un_cancelled_subscriptions'])

    def test_block_comment_remove_listener_is_not_a_call(self):
        code = ('class X {\n void init() { auth.addListener(_onAuthChanged); }\n'
                ' void dispose() { /* auth.removeListener(_onAuthChanged); */ }\n}')
        with tempfile.TemporaryDirectory() as d:
            res = audit_provider(code, d)
        self.assertEqual(res['leak_risk'], 'HIGH')
        self.assertFalse(res['removes_auth_listener_on_dispose'])

    def test_brace_inside_string_does_not_truncate_dispose_body(self):
        code = ("class X {\n StreamSubscription<int>? _sub;\n"
                " void dispose() { print('}'); _sub?.cancel(); }\n}")
        with tempfile.TemporaryDirectory() as d:
            res = audit_provider(code, d)
        self.assertEqual(res['leak_risk'], 'NONE')
        self.assertEqual(res['un_cancelled_subscriptions'], [])

    def test_commented_add_listener_is_not_a_listener(self):
        code = 'class X {\n // auth.addListener(_onAuthChanged);\n void dispose() {}\n}'
        with tempfile.TemporaryDirectory() as d:
            res = audit_provider(code, d)
        self.assertFalse(res['has_auth_listener'])
        self.assertEqual(res['leak_risk'], 'NONE')

    def test_static_mutable_with_trailing_const_comment_is_flagged(self):
        code = 'class X {\n static final leak = <Object>[]; // static const\n}'
        with tempfile.TemporaryDirectory() as d:
            issues = static_issues(code, d)
        self.assertEqual(len(issues), 1)

    def test_static_const_is_not_flagged(self):
        code = 'class X {\n static const List<Object> safe = <Object>[];\n}'
        with tempfile.TemporaryDirectory() as d:
            issues = static_issues(code, d)
        self.assertEqual(len(issues), 0)


def generate(test_ok, output, ast_ok=True):
    """Chạy generate_summary trên evidence dir tạm; trả (suite, report, summary)."""
    with tempfile.TemporaryDirectory() as d:
        RUNNER.EVIDENCE_DIR = str(d)
        (Path(d) / 'ast_memory_audit.json').write_text(json.dumps({
            'total_dart_files_scanned': 38,
            'static_mutable_collections_found': 0,
            'providers_lifecycle_audit': {
                'auth_provider.dart': {'leak_risk': 'NONE', 'removes_auth_listener_on_dispose': True,
                                       'un_cancelled_subscriptions': [], 'proper_dispose': True,
                                       'has_auth_listener': True, 'has_clear_all_method': False,
                                       'stream_subscriptions_tracked': 1}},
            'overall_ast_verdict': 'CLEAN',
        }), encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            RUNNER.generate_summary('synthetic-sha', False, {'os': 'synthetic'}, ast_ok, test_ok, output)
        summary = json.loads((Path(d) / 'summary.json').read_text(encoding='utf-8'))
        report = (Path(d) / 'heap_verification_report.md').read_text(encoding='utf-8')
    return summary['heap_test_suite'], report, summary


class SummaryControls(unittest.TestCase):
    """HP3: verdict, counts, JSON and Markdown must all come from the same parsed evidence."""

    def generate(self, test_ok, output, ast_ok=True):
        return generate(test_ok, output, ast_ok)

    def test_full_suite_passes_and_markdown_agrees(self):
        suite, report, _ = self.generate(True, events(all_pass()))
        self.assertEqual(suite['verdict'], 'PASS')
        self.assertEqual((suite['tests_passed'], suite['tests_failed']), (7, 0))
        self.assertEqual(set(suite['controls'].values()), {'PASS'})
        # verdict PASS phải khớp coverage/count, không được báo missing identity nào
        self.assertEqual(suite['identity_coverage'], 'VERIFIED')
        self.assertEqual(suite['tests_missing'], [])
        self.assertIn('7/7 Provider test PASS', report)

    def test_group_prefixed_test_names_are_matched(self):
        # `flutter test --reporter json` prefix tên test bằng tên group
        prefixed = {f'V2b — Provider Harness (Supporting Evidence) {name}': 'success'
                    for name in RUNNER.EXPECTED_TESTS}
        suite, _, _ = self.generate(True, events(prefixed))
        self.assertEqual(suite['verdict'], 'PASS')
        self.assertEqual(suite['tests_missing'], [])

    def test_subset_of_tests_does_not_turn_all_controls_green(self):
        subset = {'Baseline Epoch: Initial providers state is empty, zero retained objects': 'success'}
        suite, report, _ = self.generate(True, events(subset))
        self.assertNotEqual(suite['verdict'], 'PASS')
        self.assertNotEqual(set(suite['controls'].values()), {'PASS'})
        self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')

    def test_unknown_test_name_is_not_accepted_as_coverage(self):
        wrong = {f'Some other test {i}': 'success' for i in range(7)}
        suite, report, _ = self.generate(True, events(wrong))
        self.assertNotEqual(suite['verdict'], 'PASS')
        self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')

    def test_no_tests_ran_is_not_pass(self):
        suite, report, _ = self.generate(True, '00:00 +0: No tests ran.\n')
        self.assertEqual(suite['verdict'], 'NOT_RUN')
        self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')

    def test_skipped_test_is_not_pass(self):
        mixed = all_pass()
        mixed['Mutant Control M1: Static/global strong reference leak is reliably caught by Oracle'] = 'skipped'
        suite, report, _ = self.generate(True, events(mixed))
        self.assertNotEqual(suite['verdict'], 'PASS')
        self.assertEqual(suite['controls']['mutant_static_leak_detected_m1'], 'NOT_RUN')
        self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')

    def test_failed_suite_reports_failure_everywhere(self):
        failed = all_pass()
        failed['Negative Control N4: Late-arriving response after logout is dropped & GC-collected'] = 'failure'
        suite, report, _ = self.generate(False, events(failed))
        self.assertEqual(suite['verdict'], 'FAIL')
        self.assertEqual(suite['controls']['late_response_after_logout_n4'], 'FAIL')
        self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')

    def test_legacy_text_output_is_count_only_and_never_overclaims(self):
        suite, report, _ = self.generate(True, '00:00 +1: All tests passed!\n')
        self.assertNotEqual(suite['verdict'], 'PASS')
        self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')

    def test_metadata_does_not_claim_finalizer(self):
        _, report, summary = self.generate(True, events(all_pass()))
        blob = report + json.dumps(summary)
        self.assertNotIn('Finalizer', blob)


class ProtocolStreamControls(unittest.TestCase):
    """HP3-A/B/C (review cb5bf41): real Flutter JSON protocol, not output-shape guessing."""

    def generate(self, test_ok, output, ast_ok=True):
        return generate(test_ok, output, ast_ok)

    def test_diagnostics_prefix_before_json_does_not_downgrade_to_text(self):
        # HP3-A: `Resolving dependencies...` đứng trước JSON events trong checkout mới.
        raw = ('Resolving dependencies...\nDownloading packages...\n'
               '  meta 1.18.3 (1.19.0 available)\n  supabase 2.16.2 (2.16.5 available)\n'
               + json_stream(real_rows()))
        suite, report, _ = self.generate(True, raw)
        self.assertEqual(suite['verdict'], 'PASS')
        self.assertEqual((suite['tests_passed'], suite['tests_missing']), (7, []))
        self.assertEqual(suite['identity_coverage'], 'VERIFIED')
        self.assertIn('7/7 Provider test PASS', report)

    def test_malformed_lines_between_events_are_ignored(self):
        body = json_stream(real_rows()).splitlines()
        noisy = [body[0], '{not json at all', 'Some pub warning', body[1]] + body[2:]
        suite, _, _ = self.generate(True, '\n'.join(noisy) + '\n')
        self.assertEqual(suite['verdict'], 'PASS')
        self.assertEqual(suite['tests_missing'], [])

    def test_incomplete_protocol_is_not_pass(self):
        # Chỉ có testStart, không có testDone: không được rơi về text "All tests passed!".
        partial = (json.dumps({'protocolVersion': '0.1.1', 'type': 'start'}) + '\n'
                   + json.dumps({'type': 'testStart', 'test': {'id': 10, 'name': GROUP_PREFIX + 'x'}}) + '\n'
                   + '00:03 +7: All tests passed!\n')
        suite, report, _ = self.generate(True, partial)
        self.assertNotEqual(suite['verdict'], 'PASS')
        self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')

    def test_real_protocol_skip_is_not_run_and_blocks_pass(self):
        # HP3-B: Flutter thật phát result="success" + skipped=true cho test bị skip.
        skipped_name = 'Mutant Control M1: Static/global strong reference leak is reliably caught by Oracle'
        suite, report, summary = self.generate(True, json_stream(real_rows(skipped_name)))
        self.assertNotEqual(suite['verdict'], 'PASS')
        self.assertEqual(suite['tests_skipped'], 1)
        self.assertEqual(suite['controls']['mutant_static_leak_detected_m1'], 'NOT_RUN')
        self.assertEqual(suite['identity_coverage'], 'INCOMPLETE')
        self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')
        self.assertEqual(summary['heap_test_suite']['tests_skipped'], 1)

    def test_real_protocol_success_without_skip_is_positive(self):
        suite, report, _ = self.generate(True, json_stream(real_rows()))
        self.assertEqual(suite['verdict'], 'PASS')
        self.assertEqual((suite['tests_passed'], suite['tests_skipped']), (7, 0))
        self.assertEqual(set(suite['controls'].values()), {'PASS'})
        self.assertIn('7/7 Provider test PASS', report)

    def test_extra_unknown_identity_blocks_verified_and_counts(self):
        # HP3-C: 7 expected success + 1 visible identity lạ.
        extra = [
            json.dumps({'type': 'testStart', 'test': {'id': 999, 'name': GROUP_PREFIX + 'unrecognized extra test'}}),
            json.dumps({'type': 'testDone', 'testID': 999, 'result': 'success',
                        'skipped': False, 'hidden': False}),
        ]
        suite, report, summary = self.generate(True, json_stream(real_rows(), extra))
        self.assertNotEqual(suite['verdict'], 'PASS')
        self.assertNotEqual(suite['identity_coverage'], 'VERIFIED')
        self.assertEqual(suite['tests_passed'], 7)  # không được đếm 8/7
        self.assertEqual(len(suite['tests_unexpected']), 1)
        self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')
        self.assertEqual(summary['heap_test_suite']['tests_unexpected'], suite['tests_unexpected'])

    def test_duplicate_identity_blocks_verified(self):
        duplicate = [
            json.dumps({'type': 'testStart', 'test': {'id': 998, 'name': 'Other group ' + list(RUNNER.EXPECTED_TESTS)[0]}}),
            json.dumps({'type': 'testDone', 'testID': 998, 'result': 'success',
                        'skipped': False, 'hidden': False}),
        ]
        suite, report, _ = self.generate(True, json_stream(real_rows(), duplicate))
        self.assertNotEqual(suite['verdict'], 'PASS')
        self.assertNotEqual(suite['identity_coverage'], 'VERIFIED')
        self.assertTrue(suite['tests_duplicate'])
        self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')

    def test_exact_full_name_duplicate_ids_block_verified(self):
        # HP3-C (review b7eb881): hai test ID khác nhau nhưng cùng exact full name là protocol hợp lệ.
        exact_name = GROUP_PREFIX + list(RUNNER.EXPECTED_TESTS)[0]
        duplicate = [
            json.dumps({'type': 'testStart', 'test': {'id': 998, 'name': exact_name}}),
            json.dumps({'type': 'testDone', 'testID': 998, 'result': 'success',
                        'skipped': False, 'hidden': False}),
        ]
        suite, report, summary = self.generate(True, json_stream(real_rows(), duplicate))
        self.assertNotEqual(suite['verdict'], 'PASS')
        self.assertNotEqual(suite['identity_coverage'], 'VERIFIED')
        self.assertTrue(suite['tests_duplicate'], 'exact-name duplicate must be reported, not collapsed')
        self.assertIn('998', ' '.join(suite['tests_duplicate']))
        self.assertEqual(suite['tests_passed'], 7)  # counts canonical không vượt 7
        self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')
        self.assertNotEqual(summary['heap_test_suite']['verdict'], 'PASS')

    def test_counts_always_reconcile_with_expected_identities(self):
        skipped_name = 'Negative Control N4: Late-arriving response after logout is dropped & GC-collected'
        extra = [
            json.dumps({'type': 'testStart', 'test': {'id': 997, 'name': GROUP_PREFIX + 'unknown'}}),
            json.dumps({'type': 'testDone', 'testID': 997, 'result': 'success',
                        'skipped': False, 'hidden': False}),
        ]
        for output in (json_stream(real_rows()),
                       json_stream(real_rows(skipped_name)),
                       json_stream(real_rows(), extra)):
            suite, report, _ = self.generate(True, output)
            total = suite['tests_passed'] + suite['tests_failed'] + suite['tests_skipped'] + len(suite['tests_missing'])
            self.assertEqual(total, suite['tests_expected'], output[:40])
            claim = f"{suite['tests_passed']}/{suite['tests_expected']} kiểm thử"
            self.assertIn(claim, report)
            if suite['verdict'] != 'PASS':
                self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')


class ProvenanceControls(unittest.TestCase):
    """HP6: provenance read failures must be UNKNOWN/FAIL, never a clean checkout."""

    def get_git_info_with(self, fake):
        original = RUNNER.subprocess.check_output
        RUNNER.subprocess.check_output = fake
        try:
            return RUNNER.get_git_info()
        finally:
            RUNNER.subprocess.check_output = original

    def test_status_failure_is_unknown_not_clean(self):
        sha = '33ad6e6fd7e33b8495ec9dda0732df1b6df2096b'

        def fake(args, **kw):
            if args[:3] == ['git', 'rev-parse', 'HEAD']:
                return sha + '\n'
            raise subprocess.CalledProcessError(128, args)

        got_sha, dirty, paths, _ = self.get_git_info_with(fake)
        self.assertEqual(got_sha, sha)
        self.assertEqual(dirty, 'UNKNOWN')
        self.assertTrue(any('status' in str(p).lower() for p in paths), paths)
        self.assertTrue(RUNNER.provenance_errors(got_sha, dirty, {}))

    def test_rev_parse_failure_invalidates_provenance(self):
        def fake(args, **kw):
            if args[:3] == ['git', 'rev-parse', 'HEAD']:
                raise subprocess.CalledProcessError(128, args)
            return ''

        sha, dirty, _, _ = self.get_git_info_with(fake)
        self.assertEqual(sha, 'UNKNOWN_SHA')
        self.assertTrue(RUNNER.provenance_errors(sha, dirty, {}))

    def test_missing_source_hash_invalidates_provenance(self):
        errors = RUNNER.provenance_errors('a' * 40, False, {'scripts/x.py': 'MISSING'})
        self.assertTrue(errors)

    def test_clean_and_dirty_checkouts_are_valid(self):
        def clean(args, **kw):
            return 'a' * 40 + '\n' if args[:2] == ['git', 'rev-parse'] else ''

        def dirty(args, **kw):
            return 'a' * 40 + '\n' if args[:2] == ['git', 'rev-parse'] else ' M scripts/x.py\n'

        sha, dirty_state, paths, _ = self.get_git_info_with(clean)
        self.assertEqual((dirty_state, paths), (False, []))
        self.assertEqual(RUNNER.provenance_errors(sha, dirty_state, {}), [])
        sha, dirty_state, paths, _ = self.get_git_info_with(dirty)
        self.assertEqual(dirty_state, True)
        self.assertEqual(paths, ['M scripts/x.py'])
        self.assertEqual(RUNNER.provenance_errors(sha, dirty_state, {}), [])

    def test_unknown_git_state_blocks_success_conclusion(self):
        with tempfile.TemporaryDirectory() as d:
            RUNNER.EVIDENCE_DIR = str(d)
            (Path(d) / 'ast_memory_audit.json').write_text(json.dumps({
                'total_dart_files_scanned': 38, 'static_mutable_collections_found': 0,
                'providers_lifecycle_audit': {}, 'overall_ast_verdict': 'CLEAN'}), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                RUNNER.generate_summary('a' * 40, 'UNKNOWN', {'os': 'synthetic'}, True, True,
                                        events(all_pass()), provenance_errors=['git status failed (exit 128)'])
            report = (Path(d) / 'heap_verification_report.md').read_text(encoding='utf-8')
            summary = json.loads((Path(d) / 'summary.json').read_text(encoding='utf-8'))
        self.assertFalse('7/7 Provider test PASS' in report, 'markdown must not claim 7/7 PASS')
        self.assertIn('UNKNOWN', report)
        self.assertEqual(summary['provenance']['git_cleanliness'], 'UNKNOWN')
        self.assertTrue(summary['provenance']['errors'])


class HandoffProvenanceControls(unittest.TestCase):
    """HP7: every SHA in the handoff must resolve in Git; commit links must be absolute."""

    def test_handoff_shas_resolve(self):
        text = HANDOFF.read_text(encoding='utf-8')
        shas = sorted(set(SHA_RE.findall(text)))
        self.assertTrue(shas, 'handoff must cite at least the tested source SHA')
        for sha in shas:
            res = subprocess.run(['git', 'cat-file', '-e', f'{sha}^{{commit}}'],
                                 cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f'SHA {sha} in handoff does not resolve')

    def test_handoff_commit_links_are_absolute(self):
        text = HANDOFF.read_text(encoding='utf-8')
        self.assertFalse('](../../../commit/' in text, 'commit links must be absolute URLs')


if __name__ == '__main__':
    unittest.main()
