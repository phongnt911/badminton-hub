from pathlib import Path
import json,copy,tempfile,subprocess
r=Path.cwd();base=json.loads((r/'docs/reviews/bh07/review_runtime_b13e468_evidence/summary.json').read_text());results={}
for case in ['positive','duplicate_cycle_payload','rendered_presence_contradiction','risk_path_hash_mismatch']:
 s=copy.deepcopy(base)
 if case=='duplicate_cycle_payload':s['cycles'][1]=copy.deepcopy(s['cycles'][0])
 if case=='rendered_presence_contradiction':
  for c in s['cycles']:
   for e in ['post_logout','post_actor']:
    for k in ['expense','expense2']:c['epochs'][e]['sentinels'][k].update(present=False,occurrences=0)
 if case=='risk_path_hash_mismatch':
  for rr in s['residual_risks']:rr['path_sha256_12']='000000000000'
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'input.json';o=Path(td)/'out';p.write_text(json.dumps(s));run=subprocess.run(['python','scripts/bh07_appheap/audit_retention_attribution.py','--summary',str(p),'--out-dir',str(o)],capture_output=True,text=True)
  f=o/'attribution_audit.json';a=json.loads(f.read_text())['attribution'] if f.exists() else {}
  results[case]={'exit':run.returncode,'verdict':a.get('attribution_verdict')}
print(json.dumps(results,indent=2))
