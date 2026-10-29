"""Profile-specific positive/negative CLI controls on disposable evidence clones."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(root/'scripts/bh07_appheap'))
import heap_oracle
source = root/'docs/reviews/bh07/finance_heap_evidence'
base = json.loads((source/'summary.json').read_bytes())
identifier='review-only-bank-identifier'
base['coverage_profile']='bank'
base['bank_coverage_contract']={'version':'1.0','required_owner_load':['bank_account_id','bank','receiver']}
base['sentinels']['bank_account_id']={'available':True,'kind':'private bank identifier',
    'length':len(identifier),'sha256_12':hashlib.sha256(identifier.encode()).hexdigest()[:12],
    'rendered':False,'distinctive':True,'scope':'finance'}
for name in ('bank','receiver'):
    base['sentinels'][name].update(rendered=True,distinctive=True,scope='bank')
base['cleanup'].update(disposable_bank_created=True,disposable_club_created=True,
    disposable_bank_id_sha256_12=base['sentinels']['bank_account_id']['sha256_12'],
    disposable_club_id_sha256_12='abcdef012345',disposable_bank_removed=True,
    disposable_bank_verified_absent=True,disposable_club_removed=True,disposable_club_verified_absent=True)
for cycle in base['cycles']:
    owner_path=copy.deepcopy(cycle['epochs']['owner_active']['paths']['expense_id'])
    for epoch,scan in cycle['epochs'].items():
        for name in ('bank_account_id','bank','receiver'):
            meta=base['sentinels'][name]
            active=epoch=='owner_active'
            scan['sentinels'][name]={'present':active,'occurrences':1 if active else 0,
                **{k:meta[k] for k in ('rendered','distinctive','scope')}}
            scan['paths'][name]=copy.deepcopy(owner_path) if active else {'reachable':False,'string_nodes':0,'exact':False}

def recompute(data):
    for cycle in data['cycles']:
        cycle['verdict']=heap_oracle.decide(cycle['epochs'],heap_oracle.derive_expectations(cycle['epochs']),True,'profile',strict=True)
    data['verdict']='PASS' if all(c['verdict']['verdict']=='PASS' for c in data['cycles']) else 'FAIL'
    data['findings']=[f'cycle {i}: {f}' for i,c in enumerate(data['cycles'],1) for f in c['verdict']['findings']]
    data['notes']=[f'cycle {i}: {n}' for i,c in enumerate(data['cycles'],1) for n in c['verdict']['notes']]
    data['residual_risks']=[{'cycle':i,**r} for i,c in enumerate(data['cycles'],1) for r in c['verdict']['residual_risks']]

results={}
for case in ('bank_positive','rendered_owner_values_unreachable','rendered_baseline_path_retained'):
    data=copy.deepcopy(base)
    for cycle in data['cycles']:
        if case=='rendered_owner_values_unreachable':
            for name in ('bank','receiver'):
                cycle['epochs']['owner_active']['paths'][name]={'reachable':False,'string_nodes':1,'exact':True}
        if case=='rendered_baseline_path_retained':
            for name in ('bank','receiver'):
                cycle['epochs']['baseline']['paths'][name]=copy.deepcopy(cycle['epochs']['owner_active']['paths'][name])
    recompute(data)
    with tempfile.TemporaryDirectory(prefix='bank_owner_graph_',dir=root/'build') as temp:
        directory=Path(temp)
        for item in source.iterdir():
            if item.is_file():shutil.copyfile(item,directory/item.name)
        (directory/'summary.json').write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
        render="const fs=require('fs');const r=require(process.argv[1]);fs.writeFileSync(process.argv[3],r.renderReport(JSON.parse(fs.readFileSync(process.argv[2],'utf8'))));"
        subprocess.run(['node','-e',render,str(root/'scripts/bh07_appheap/run_app_profile_heap.js'),str(directory/'summary.json'),str(directory/'report.md')],check=True,capture_output=True)
        (directory/'hashes.sha256').write_bytes(''.join(hashlib.sha256((directory/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in ('summary.json','report.md','run.log')).encode('utf-8'))
        result=subprocess.run(['python','-X','utf8','scripts/bh07_appheap/verify_evidence.py','--dir',str(directory)],cwd=root,capture_output=True,text=True)
        results[case]={'auditor_exit':result.returncode,'oracle_verdict':data['verdict'],'output':result.stdout+result.stderr}
print(json.dumps(results,indent=2))
