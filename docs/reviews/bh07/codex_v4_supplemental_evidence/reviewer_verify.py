"""Independent bounded verification; never prints runner source."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.bh07_backup import v4_concurrent_probe as probe

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('guard_editor', HERE / 'apply_request_guard.py')
editor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(editor)
receipt = json.loads((HERE / 'guard_edit_receipt.json').read_text())
actual = (ROOT / receipt['file']).read_bytes()
offset, length = receipt['insert_byte_offset'], receipt['insert_byte_length']
guard = actual[offset:offset + length]
assert guard in (editor.GUARD.encode(), editor.GUARD.replace('\n', '\r\n').encode())
assert hashlib.sha256(actual).hexdigest() == receipt['postimage_sha256']
assert hashlib.sha256(guard).hexdigest() == receipt['insert_sha256']
assert hashlib.sha256(actual[:offset] + actual[offset + length:]).hexdigest() == receipt['preimage_sha256']
print('byte verification PASS: pinned guard, postimage and reconstructed preimage')

canonical = probe.build_canonical_summary()
source, restored = probe.fp(3), probe.fp(1, sha_hex='e' * 64)
assert probe.validate_v4_rehearsal(canonical, source, restored)['ok'] is True
count = 0
changes = [
    lambda r: r.pop('operation'),
    lambda r: r.__setitem__('operation', False),
    lambda r: r.pop('result'),
    *[lambda r, value=value: r.__setitem__('result', value)
      for value in (None, [], False, 0, 'confirmed', {})],
    lambda r: r['result'].pop('status'),
    *[lambda r, value=value: r['result'].__setitem__('status', value)
      for value in ('rejected', 'CONFIRMED', 'confirmed ', None, True, 1)],
]
for label in canonical['source_operations']:
    for change in changes:
        summary = copy.deepcopy(canonical)
        op = summary['source_operations'][label]
        change(op['row_evidence']['request'])
        op['relational_digest'] = probe.digest(op['row_evidence'])
        if label == 'p0_precommit':
            summary['restored_verification']['restored_row_evidence'] = copy.deepcopy(op['row_evidence'])
        result = probe.validate_v4_rehearsal(summary, source, restored)
        assert result['ok'] is False and result['verdict'] == 'FAIL', (label, result)
        count += 1
print(f'independent controls PASS: 1 positive, {count} recalculated-digest mutants')
