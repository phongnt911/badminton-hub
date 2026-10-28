"""Observation probe: positive expects auditor0; all negative cases expect1.
Overall exit0 prints results, not a passing-control verdict. No original source/evidence edits.
"""
from pathlib import Path
import subprocess,json,copy,hashlib,tempfile,sys,shutil
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts/bh07_appheap'))
import heap_oracle
source=ROOT/'docs/reviews/bh07/finance_heap_evidence';original=json.loads((source/'summary.json').read_text());results={}
(ROOT/'build').mkdir(exist_ok=True)
for case in ['positive','payment_never_loaded','payment_receipt_removed','payment_created_flag_missing','payment_cleanup_false_control','payment_receipt_hash_wrong']:
 data=copy.deepcopy(original)
 if case=='payment_never_loaded':
  for c in data['cycles']:
   for scan in c['epochs'].values():
    for name in ['payment_id','payment_ref']:
     scan['sentinels'][name].update(present=False,occurrences=0)
     scan['paths'][name]={'reachable':False,'string_nodes':0,'exact':False}
 if case=='payment_receipt_removed':
  data['cleanup']={k:v for k,v in data['cleanup'].items() if 'payment' not in k}
 if case=='payment_created_flag_missing':
  data['cleanup'].pop('run_only_payment_created');data['cleanup']['extra_payment_removed']=False;data['cleanup']['extra_payment_verified_absent']=False;data['cleanup']['extra_payment_error']='control: delete failed'
 if case=='payment_cleanup_false_control':data['cleanup']['extra_payment_removed']=False
 if case=='payment_receipt_hash_wrong':data['cleanup']['run_only_payment_id_sha256_12']='000000000000'
 if case=='payment_never_loaded':
  for c in data['cycles']:c['verdict']=heap_oracle.decide(c['epochs'],heap_oracle.derive_expectations(c['epochs']),True,'profile',strict=True)
  data['verdict']='PASS' if all(c['verdict']['verdict']=='PASS' for c in data['cycles']) else 'FAIL'
  data['findings']=[f'cycle {i}: {x}' for i,c in enumerate(data['cycles'],1) for x in c['verdict']['findings']]
  data['notes']=[f'cycle {i}: {x}' for i,c in enumerate(data['cycles'],1) for x in c['verdict']['notes']]
  data['residual_risks']=[{'cycle':i,**x} for i,c in enumerate(data['cycles'],1) for x in c['verdict']['residual_risks']]
 with tempfile.TemporaryDirectory(prefix='bh07_finance_probe_',dir=ROOT/'build') as tmp:
  d=Path(tmp)
  for p in source.iterdir():shutil.copyfile(p,d/p.name)
  (d/'summary.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
  script="const fs=require('fs');const runner=require(process.argv[1]);const s=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));fs.writeFileSync(process.argv[3],runner.renderReport(s));"
  subprocess.run(['node','-e',script,str(ROOT/'scripts/bh07_appheap/run_app_profile_heap.js'),str(d/'summary.json'),str(d/'report.md')],check=True,capture_output=True)
  if case=='payment_never_loaded':
   t=(d/'run.log').read_text().replace('"payment_id":true','"payment_id":false').replace('"payment_ref":true','"payment_ref":false');(d/'run.log').write_text(t)
  (d/'hashes.sha256').write_text(''.join(hashlib.sha256((d/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in ['summary.json','report.md','run.log']))
  p=subprocess.run(['python','-X','utf8','scripts/bh07_appheap/verify_evidence.py','--dir',str(d)],capture_output=True,text=True)
  results[case]={'expected_auditor_exit':0 if case=='positive' else 1,'auditor_exit':p.returncode,'auditor_output':p.stdout.replace(str(d),'TEMP_BUNDLE')+p.stderr.replace(str(d),'TEMP_BUNDLE'),'summary_verdict':data['verdict'],'payment_gated_by_cycle':['payment_id' in heap_oracle.derive_expectations(c['epochs'])['owner_active'] for c in data['cycles']]}
print(json.dumps(results,indent=2))
