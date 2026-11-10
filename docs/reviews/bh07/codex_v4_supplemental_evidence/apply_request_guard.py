"""Apply one pinned AST edit without displaying protected source content."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / 'scripts/bh07_backup/run_v4_concurrent_rehearsal.py'
RECEIPT = Path(__file__).with_name('guard_edit_receipt.json')
EXPECTED = 'bd51710852ec075591e2e263f79c069d0c7988bbdefe4a6db6fc93916ebd95f8'
GUARD = '''    # Owner-authorized supplemental request validation.
    _codex_v4_ops = summary.get('source_operations') if isinstance(summary, dict) else None
    if isinstance(_codex_v4_ops, dict):
        for _codex_v4_label in ('p0_precommit', 'p1a_concurrent', 'p1b_concurrent'):
            _codex_v4_op = _codex_v4_ops.get(_codex_v4_label)
            if not isinstance(_codex_v4_op, dict):
                continue
            _codex_v4_rows = _codex_v4_op.get('row_evidence')
            _codex_v4_request = _codex_v4_rows.get('request') if isinstance(_codex_v4_rows, dict) else None
            if not isinstance(_codex_v4_request, dict):
                continue
            _codex_v4_result = _codex_v4_request.get('result')
            if (_codex_v4_request.get('operation') != 'record_cash_payment'
                    or not isinstance(_codex_v4_result, dict)
                    or _codex_v4_result.get('status') != 'confirmed'):
                return {'ok': False, 'verdict': 'FAIL', 'findings': [
                    'relational_evidence_mismatch: ' + _codex_v4_label
                    + ' requires record_cash_payment with a confirmed stored result'
                ]}
'''


def main():
    if TARGET.is_symlink() or not TARGET.resolve().is_relative_to(ROOT.resolve()):
        raise SystemExit('Target must be a regular workspace file')
    before = TARGET.read_bytes()
    before_hash = hashlib.sha256(before).hexdigest()
    if before_hash != EXPECTED or RECEIPT.exists():
        raise SystemExit('Unexpected preimage or existing receipt; refusing edit')
    bom = b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b''
    source = before[len(bom):].decode('utf-8')
    tree = ast.parse(source)
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef)
               and node.name == 'validate_v4_rehearsal']
    if len(matches) != 1 or matches[0].args.args[0].arg != 'summary':
        raise SystemExit('Unexpected validator interface; refusing edit')
    fn = matches[0]
    if any(isinstance(node, ast.Name) and node.id.startswith('_codex_v4_') for node in ast.walk(fn)):
        raise SystemExit('Guard local names already exist')
    first = fn.body[0]
    is_docstring = isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)
    index = first.end_lineno if is_docstring else first.lineno - 1
    lines = source.splitlines(keepends=True)
    newline = '\r\n' if lines[0].endswith('\r\n') else '\n'
    guard = GUARD.replace('\n', newline)
    prefix = ''.join(lines[:index])
    after_source = prefix + guard + ''.join(lines[index:])
    try:
        ast.parse(after_source)
    except SyntaxError:
        raise SystemExit('Generated edit is not parseable; no write') from None
    after = bom + after_source.encode('utf-8')
    offset = len(bom) + len(prefix.encode('utf-8'))
    inserted = guard.encode('utf-8')
    if after[:offset] + after[offset + len(inserted):] != before:
        raise SystemExit('Edit would change bytes outside the guard')
    TARGET.write_bytes(after)
    receipt = {'file': str(TARGET.relative_to(ROOT)), 'preimage_sha256': before_hash,
               'postimage_sha256': hashlib.sha256(after).hexdigest(), 'insert_line': index + 1,
               'insert_byte_offset': offset, 'insert_byte_length': len(inserted),
               'insert_sha256': hashlib.sha256(inserted).hexdigest(), 'outside_guard_bytes_unchanged': True}
    RECEIPT.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
