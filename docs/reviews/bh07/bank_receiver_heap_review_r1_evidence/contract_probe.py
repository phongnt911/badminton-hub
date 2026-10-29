"""Real CLI clone-only probe; no original evidence or DB mutations."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[4]
source = root / 'docs/reviews/bh07/finance_heap_evidence'
original = json.loads((source / 'summary.json').read_bytes())
results = {}
for case in ('legacy_positive', 'bank_profile_with_no_bank_id_or_owner_load'):
    data = copy.deepcopy(original)
    if case != 'legacy_positive':
        data['coverage_profile'] = 'bank'
        data['bank_coverage_contract'] = {'version': '1.0',
            'required_owner_load': ['bank_account_id', 'bank', 'receiver']}
        data['cleanup'].update(disposable_bank_created=True, disposable_club_created=True,
            disposable_bank_id_sha256_12='0123456789ab', disposable_club_id_sha256_12='abcdef012345',
            disposable_bank_removed=True, disposable_bank_verified_absent=True,
            disposable_club_removed=True, disposable_club_verified_absent=True)
    with tempfile.TemporaryDirectory(prefix='bank_review_control_', dir=root/'build') as tmp:
        directory = Path(tmp)
        for item in source.iterdir():
            if item.is_file(): shutil.copyfile(item, directory/item.name)
        (directory/'summary.json').write_bytes((json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
        renderer = "const fs=require('fs');const r=require(process.argv[1]);fs.writeFileSync(process.argv[3],r.renderReport(JSON.parse(fs.readFileSync(process.argv[2],'utf8'))));"
        subprocess.run(['node','-e',renderer,str(root/'scripts/bh07_appheap/run_app_profile_heap.js'),
                        str(directory/'summary.json'),str(directory/'report.md')],check=True,capture_output=True)
        (directory/'hashes.sha256').write_bytes(''.join(
            hashlib.sha256((directory/name).read_bytes()).hexdigest()+'  '+name+'\n'
            for name in ('summary.json','report.md','run.log')).encode('utf-8'))
        result = subprocess.run(['python','-X','utf8','scripts/bh07_appheap/verify_evidence.py',
                                 '--dir',str(directory)],cwd=root,capture_output=True,text=True)
        results[case] = {'auditor_exit':result.returncode,'output':result.stdout+result.stderr,
            'bank_id_declared':'bank_account_id' in data['sentinels']}
print(json.dumps(results,indent=2))
