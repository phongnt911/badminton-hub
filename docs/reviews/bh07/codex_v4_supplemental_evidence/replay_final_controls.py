"""Replay the immutable pre-repair controls without rewriting historical evidence."""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=HERE / 'guard_replay_20261109.json')
    args = parser.parse_args()
    output = args.out.resolve()
    if not output.is_relative_to(ROOT.resolve()) or output.exists():
        raise SystemExit('Output must be a new workspace file')
    source = ROOT / 'scripts/bh07_backup/run_v4_concurrent_rehearsal.py'
    receipt = json.loads((HERE / 'guard_edit_receipt.json').read_text(encoding='utf-8'))
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    if before != receipt['postimage_sha256']:
        raise SystemExit('Unexpected repaired source hash')
    input_path = HERE.parent / 'v4_review_r1_evidence/final_capture_20261109.json'
    raw = input_path.read_bytes()
    frozen = json.loads(raw)
    from scripts.bh07_backup.run_v4_concurrent_rehearsal import validate_v4_rehearsal
    results = []
    for case in frozen['cases']:
        result = validate_v4_rehearsal(copy.deepcopy(case['summary']),
                                       copy.deepcopy(frozen['source_fp']), copy.deepcopy(frozen['restored_fp']))
        expected = case['name'] == 'positive'
        results.append({'name': case['name'], 'expected_ok': expected, 'result': result,
                        'matches_expected': result.get('ok') is expected})
    if hashlib.sha256(source.read_bytes()).hexdigest() != before:
        raise SystemExit('Source changed during replay')
    payload = {'kind': 'synthetic replay of immutable pre-repair inputs; no DB runtime',
               'input_file': str(input_path.relative_to(ROOT)), 'input_sha256': hashlib.sha256(raw).hexdigest(),
               'runner_sha256': before, 'results': results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
    passed = sum(item['matches_expected'] for item in results)
    print(json.dumps({'cases': len(results), 'matched_expected': passed,
                      'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest()}))
    return 0 if passed == len(results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
