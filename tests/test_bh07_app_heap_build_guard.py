"""Controls for the BH-07 app-profile build/serve guards (review AH5).

A heap measurement of a build we did not produce is not evidence, so the runner must
refuse `--reuse-build`, prove the artifacts are the ones this run just wrote, prove the
static server answers with those bytes, and refuse a port someone else already owns.

Run: python -m unittest tests.test_bh07_app_heap_build_guard -v
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / 'scripts/bh07_appheap/build_guard.js'
RUNNER = ROOT / 'scripts/bh07_appheap/run_app_profile_heap.js'
REUSE_PROBE = ROOT / 'docs/reviews/bh07/review_8914b2f_evidence/build_probe.js'
CONTROLS = ('missing_artifact', 'stale_artifact', 'rebuilt_identical_artifact', 'fresh_artifact',
            'served_match', 'served_mismatch', 'occupied_port', 'free_port')

CANARY = 'PRIVATE_CANARY_abcdefghij0123456789klmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
MIN_PRIVATE = 20


def private_windows(value, size=MIN_PRIVATE):
    """Every run of `size` characters the private value exposes."""
    return [value[start:start + size] for start in range(len(value) - size + 1)]


def surviving_private_windows(published, value):
    return [window for window in private_windows(value) if window in published]


def run_node(script, env=None):
    return subprocess.run(['node', '-e', script], capture_output=True, text=True, cwd=ROOT,
                          env={**os.environ, **(env or {})})


# Drives the real writer in an isolated temp output dir: never starts the app, UI or DB.
PUBLICATION_SCRIPT = """
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),{createRequire}=require('node:module');
const file=path.resolve('scripts/bh07_appheap/run_app_profile_heap.js');const dir=process.env.BH07_TEST_DIR;
const value=process.env.BH07_TEST_CANARY;
const context={require:createRequire(file),module:{exports:{}},__dirname:path.dirname(file),process:{...process,env:{...process.env,BH07_APPHEAP_EVIDENCE:dir}},console,setTimeout,clearTimeout,URL};
vm.createContext(context);vm.runInContext(fs.readFileSync(file,'utf8')+'\\nglobalThis.review={writeEvidence,RAW_SENTINEL_VALUES,logLines};',context);
const r=context.review;const quoted='PRIVATE_QUOTED_"0123456789abcdefghij';
r.RAW_SENTINEL_VALUES.short=value.slice(0,25);r.RAW_SENTINEL_VALUES.sample=value;r.RAW_SENTINEL_VALUES.quoted=quoted;
r.logLines.push('window:'+value.slice(20,40));
r.logLines.push('truncated:'+value.slice(0,60));
r.logLines.push('interior:'+value.slice(5,45));
r.logLines.push('overlap:'+value.slice(0,35));
const summary={gate:'synthetic publication control',status:'RUN',verdict:'PASS',findings:[],cycles:[],sentinels:{},notes:['note:'+value.slice(10,50),'quoted:'+quoted.slice(0,30)],cleanup:{ok:true},environment:{}};
r.writeEvidence(summary);
const files={};
for (const name of ['run.log','summary.json','report.md']) files[name]=fs.readFileSync(path.join(dir,name),'utf8');
console.log(JSON.stringify({status:summary.status,verdict:summary.verdict,files}));
"""


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


class RedactionCompletenessControls(unittest.TestCase):
    """Review 4184faf RP3-B: no private fragment may survive publication.

    The old sanitizer replaced the full value, then the 20-character prefix, then the
    40-character prefix. Redacting the short prefix first exposed the rest of a longer
    value, so the 40-character needle had nothing left to match: a 40-character
    truncation published its middle and the leak check then reported it clean.
    """

    def redact(self, inputs, values=None):
        script = (
            "const r = require('./scripts/bh07_appheap/run_app_profile_heap.js');"
            f"const values = {json.dumps(values or {'sample': CANARY})};"
            f"const inputs = {json.dumps(inputs)};"
            "console.log(JSON.stringify({out: inputs.map((text) => r.redactSentinels(text, values)),"
            " leaks: inputs.map((text) => r.findSentinelLeaks([r.redactSentinels(text, values)], values))}));"
        )
        result = run_node(script)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_every_truncation_width_is_removed_completely(self):
        lengths = [MIN_PRIVATE, 21, 24, 30, 39, 40, 41, 50, 60, len(CANARY)]
        payload = self.redact([CANARY[:length] for length in lengths])
        for length, published in zip(lengths, payload['out']):
            with self.subTest(length=length):
                self.assertEqual(published, '<redacted>')
                self.assertEqual(surviving_private_windows(published, CANARY), [])

    def test_embedded_and_overlapping_fragments_are_removed(self):
        inputs = ['before:' + CANARY[:40] + ':after',
                  'before:' + CANARY[5:45] + ':after',
                  'a' + CANARY[20:40] + 'b' + CANARY[:20] + 'c',
                  CANARY[:30] + '|' + CANARY[10:50],
                  'x' + CANARY + 'y']
        payload = self.redact(inputs)
        for text, published in zip(inputs, payload['out']):
            with self.subTest(input=text):
                self.assertEqual(surviving_private_windows(published, CANARY), [], published)
                self.assertIn('<redacted>', published)
        self.assertEqual(payload['leaks'], [[] for _ in inputs])
        # the line around the value is not the leak: only the private bytes go
        self.assertEqual(payload['out'][0], 'before:<redacted>:after')
        self.assertEqual(payload['out'][4], 'x<redacted>y')

    def test_interior_fragment_of_a_mid_length_value_is_removed(self):
        value = 'PRIVATE_MID_' + 'z' * 14
        payload = self.redact([value[3:23]], values={'mid': value})
        self.assertEqual(surviving_private_windows(payload['out'][0], value), [])
        self.assertEqual(payload['leaks'], [[]])

    def test_overlapping_and_multiple_values_are_removed_completely(self):
        cases = [
            (CANARY[:40], {'short_prefix': CANARY[:25], 'long_prefix': CANARY[:40]}, '<redacted>'),
            (CANARY[:55], {'left': CANARY[:40], 'right': CANARY[20:60]}, '<redacted>'),
            (CANARY[:30], {'inner_short': CANARY[15:25], 'full': CANARY}, '<redacted>'),
            ('id=' + CANARY[:40] + ' acct=' + CANARY[20:60],
             {'a': CANARY[:25], 'b': CANARY}, 'id=<redacted> acct=<redacted>'),
        ]
        for text, values, expected in cases:
            with self.subTest(text=text, values=list(values)):
                payload = self.redact([text], values=values)
                self.assertEqual(payload['out'][0], expected)
                self.assertEqual(surviving_private_windows(payload['out'][0], CANARY), [])
                self.assertEqual(payload['leaks'], [[]])

    def test_self_overlapping_runs_within_single_value_are_removed(self):
        # Periodic 25-char value where [0:5] == [20:25]; text[0:20] == value[5:25] and
        # text[15:35] == value[0:20], so every byte of text belongs to a 20-char private run.
        periodic = '0123456789abcdefghij01234'
        text = periodic[5:25] + periodic[5:20]
        payload = self.redact([text], values={'periodic': periodic})
        self.assertEqual(payload['out'][0], '<redacted>')
        self.assertEqual(surviving_private_windows(payload['out'][0], periodic), [])
        self.assertEqual(payload['leaks'], [[]])

    def test_publication_of_a_leaking_draft_redacts_and_fails(self):
        with tempfile.TemporaryDirectory(prefix='bh07_publication_') as tmp:
            result = run_node(PUBLICATION_SCRIPT, {'BH07_TEST_DIR': tmp,
                                                   'BH07_TEST_CANARY': CANARY})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
        self.assertEqual(payload['status'], 'FAIL')
        self.assertEqual(payload['verdict'], 'FAIL')
        for name, published in payload['files'].items():
            with self.subTest(file=name):
                self.assertEqual(surviving_private_windows(published, CANARY), [])
                self.assertNotIn(CANARY[20:35], published)
                self.assertNotIn('PRIVATE_QUOTED_', published)
                self.assertNotIn('0123456789abcdefghij', published)
        # JSON and Markdown syntax remain valid after redaction
        parsed_summary = json.loads(payload['files']['summary.json'])
        self.assertEqual(parsed_summary['status'], 'FAIL')
        self.assertEqual(parsed_summary['verdict'], 'FAIL')
        self.assertEqual(parsed_summary['notes'], ['note:<redacted>', 'quoted:<redacted>'])
        self.assertIn('# V2b — app-profile heap', payload['files']['report.md'])
        self.assertIn('- note:<redacted>', payload['files']['report.md'])
        self.assertIn('- quoted:<redacted>', payload['files']['report.md'])
        self.assertIn('<redacted>', payload['files']['run.log'])
        self.assertIn('raw sentinel value reached the publication step', payload['files']['summary.json'])
        # the failure artifact still says what happened: redaction is not silence
        self.assertIn('window:', payload['files']['run.log'])
        self.assertEqual(payload['files']['run.log'].count('<redacted>'), 4)


class PublicationProbeReplay(unittest.TestCase):
    """Replay `review_4184faf_evidence/*.js` unedited, with the fixed expectations.

    The reviewer's files stay byte-identical: the same synthetic canary that used to survive
    redaction (and reach `run.log`) must now be removed.
    """

    EVIDENCE = ROOT / 'docs/reviews/bh07/review_4184faf_evidence'

    def replay(self, name):
        result = subprocess.run(['node', str(self.EVIDENCE / name)], capture_output=True,
                                text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_redaction_probe_is_now_complete(self):
        report = self.replay('redaction_probe.js')
        for case in ('full_value_positive', 'prefix20_positive'):
            self.assertIs(report[case]['redacted_completely'], True, case)
        self.assertIs(report['prefix60']['redacted_completely'], True, report['prefix60'])
        self.assertIs(report['prefix60']['private_middle40_survives'], False, report['prefix60'])
        self.assertIs(report['prefix40']['redacted_completely'], True, report['prefix40'])
        self.assertIs(report['prefix40']['private_middle20_survives'], False, report['prefix40'])
        self.assertEqual(report['prefix40']['detected_after'], [])

    def test_publication_probe_is_now_clean(self):
        report = self.replay('publication_probe.js')
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['verdict'], 'FAIL')
        self.assertIs(report['published_private_middle20'], False, report)
        self.assertIs(report['published_full_value'], False, report)
        self.assertIs(report['actual_private_fragment_absent'], True, report)


if __name__ == '__main__':
    unittest.main()
