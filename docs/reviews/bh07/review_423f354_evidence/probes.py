"""Reviewer synthetic controls; no Docker, SQL, HTTP, or implementation edits."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tests'))
from test_bh07_v4_backup_concurrency import V4FailClosedValidatorTests
from scripts.bh07_backup.run_v4_concurrent_rehearsal import validate_v4_rehearsal

fixture = V4FailClosedValidatorTests()
fixture.setUp()
positive = validate_v4_rehearsal(fixture.valid_summary, fixture.valid_source_fingerprint,
                                 fixture.valid_restored_fingerprint)
missing_status = copy.deepcopy(fixture.valid_summary)
missing_status.pop('status')
negative = validate_v4_rehearsal(missing_status, fixture.valid_source_fingerprint,
                                 fixture.valid_restored_fingerprint)
assert positive['ok'] is True
assert negative['ok'] is False
assert any('failed_status' in item for item in negative['findings'])

source = ROOT / 'scripts/bh07_backup/run_v4_concurrent_rehearsal.py'
report = {
    'scope': 'synthetic reviewer control only; not DB or runtime rehearsal',
    'tested_head': '423f3546aec671f1f345d0bd4af26334c2b1c5ea',
    'runner_worktree_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'canonical_positive': positive,
    'main_success_receipt_without_status': negative,
    'runtime': 'NOT RUN',
}
(Path(__file__).parent / 'results.json').write_text(
    json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('PASS: canonical accepted, receipt without status rejected; runtime NOT RUN')
