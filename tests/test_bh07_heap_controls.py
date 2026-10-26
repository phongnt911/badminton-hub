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


class SummaryControls(unittest.TestCase):
    """HP3: verdict, counts, JSON and Markdown must all come from the same parsed evidence."""

    def generate(self, test_ok, output, ast_ok=True):
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

    def test_full_suite_passes_and_markdown_agrees(self):
        suite, report, _ = self.generate(True, events(all_pass()))
        self.assertEqual(suite['verdict'], 'PASS')
        self.assertEqual((suite['tests_passed'], suite['tests_failed']), (7, 0))
        self.assertEqual(set(suite['controls'].values()), {'PASS'})
        self.assertIn('7/7 Provider test PASS', report)

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
