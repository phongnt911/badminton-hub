"""Controls for the BH-07 app-profile heap evidence auditor.

The auditor is what lets a reviewer trust the bundle without the raw heap, so it must
actually fail when the bundle lies: an unverified cleanup, a published raw dump or a
tampered hash cannot pass.

Run: python -m unittest tests.test_bh07_app_heap_evidence -v
"""
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


class EvidenceAuditControls(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='bh07_appheap_audit_'))
        self.bundle = self.tmp / 'evidence'
        shutil.copytree(EVIDENCE, self.bundle)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def edit_summary(self, mutate):
        path = self.bundle / 'summary.json'
        summary = json.loads(path.read_text(encoding='utf-8'))
        mutate(summary)
        path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')

    def test_real_bundle_passes(self):
        self.assertEqual(VERIFIER.verify(self.bundle), [])

    def test_unverified_cleanup_fails(self):
        def mutate(summary):
            summary['cleanup']['dumps_dir_removed'] = False
        self.edit_summary(mutate)
        problems = VERIFIER.verify(self.bundle)
        self.assertTrue(any('cleanup' in p for p in problems), problems)

    def test_published_raw_heap_fails(self):
        (self.bundle / 'owner_active.heapsnapshot').write_bytes(b'{}')
        problems = VERIFIER.verify(self.bundle)
        self.assertTrue(any('raw heap' in p for p in problems), problems)

    def test_tampered_file_fails(self):
        (self.bundle / 'run.log').write_text('rewritten after hashing\n', encoding='utf-8', newline='\n')
        problems = VERIFIER.verify(self.bundle)
        self.assertTrue(any('hash mismatch' in p for p in problems), problems)


if __name__ == '__main__':
    unittest.main()
