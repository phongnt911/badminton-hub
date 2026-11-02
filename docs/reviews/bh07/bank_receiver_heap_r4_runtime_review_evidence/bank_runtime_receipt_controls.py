import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
root=Path.cwd()
bundle=root/'docs/reviews/bh07/bank_receiver_heap_r4_runtime_evidence'
out=Path(sys.argv[1]) if len(sys.argv)>1 else root/'build/bank_runtime_receipt_controls'
out.mkdir(parents=True,exist_ok=True)
renderer=Path(__file__).resolve().with_name('render_bank_review_report.cjs')
def run_case(name,change,reason):
    with tempfile.TemporaryDirectory(prefix='bank_receipt_',dir=root/'build') as temp:
        target=Path(temp)/'bundle'
        shutil.copytree(bundle,target)
        summary=json.loads((target/'summary.json').read_bytes())
        change(summary)
        (target/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        render=subprocess.run(['node',str(renderer),str(target/'summary.json'),str(target/'report.md')],cwd=root,capture_output=True,text=True,encoding='utf-8')
        if render.returncode: raise RuntimeError('review renderer failed')
        (target/'hashes.sha256').write_text('\n'.join(f'{hashlib.sha256((target/p).read_bytes()).hexdigest()}  {p}' for p in ('summary.json','run.log','report.md'))+'\n',encoding='utf-8',newline='\n')
        audit=subprocess.run(['python','scripts/bh07_appheap/verify_evidence.py','--dir',str(target)],cwd=root,capture_output=True,text=True,encoding='utf-8')
        output=audit.stdout+audit.stderr
        return {'exit':audit.returncode,'expected_exit':0 if name=='positive' else 1,
                'expected_reason_found':not reason or reason in output,'output':output}
cases=[
 ('positive',lambda s:None,''),
 ('missing_bank_created',lambda s:s['cleanup'].pop('disposable_bank_created'), 'disposable_bank_created=True'),
 ('wrong_bank_receipt_sha12',lambda s:s['cleanup'].__setitem__('disposable_bank_id_sha256_12','0'*12),'does not match'),
 ('club_not_removed',lambda s:s['cleanup'].__setitem__('disposable_club_removed',False),'disposable_club_removed=True'),
 ('bank_not_absent',lambda s:s['cleanup'].__setitem__('disposable_bank_verified_absent',False),'disposable_bank_verified_absent=True'),
 ('missing_contract',lambda s:s.pop('bank_coverage_contract'),'requires bank_coverage_contract object'),
 ('missing_bank_id',lambda s:s['sentinels'].pop('bank_account_id'),'requires bank_account_id'),
 ('wrong_contract_version',lambda s:s['bank_coverage_contract'].__setitem__('version','2.0'),'version must be 1.0'),
]
results={name:run_case(name,change,reason) for name,change,reason in cases}
(out/'receipt_controls.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(results,indent=2))
raise SystemExit(any(r['exit']!=r['expected_exit'] or not r['expected_reason_found'] for r in results.values()))
