from pathlib import Path
import json,copy,subprocess,tempfile
r=Path.cwd();source=json.loads((r/'docs/reviews/bh07/review_runtime_b13e468_evidence/summary.json').read_text());results={}
for name in ['positive','expense2_path_missing','post_actor_paths_missing','duplicate_risk_record','missing_post_logout_occurrences']:
 s=copy.deepcopy(source)
 if name=='expense2_path_missing':
  for c in s['cycles']:
   for e in ['post_logout','post_actor']:c['epochs'][e]['paths'].pop('expense2')
 if name=='post_actor_paths_missing':
  for c in s['cycles']:
   for key in ['expense','expense2']:c['epochs']['post_actor']['paths'].pop(key)
 if name=='duplicate_risk_record':s['residual_risks']=[copy.deepcopy(s['residual_risks'][0]) for _ in range(8)]
 if name=='missing_post_logout_occurrences':
  for c in s['cycles']:
   for k in ['expense_id','expense_id_2']:c['epochs']['post_logout']['sentinels'][k].pop('occurrences')
 with tempfile.TemporaryDirectory() as td:
  inp=Path(td)/'input.json';out=Path(td)/'out';inp.write_text(json.dumps(s));p=subprocess.run(['python','scripts/bh07_appheap/audit_retention_attribution.py','--summary',str(inp),'--out-dir',str(out)],capture_output=True,text=True)
  f=out/'attribution_audit.json';a=json.loads(f.read_text())['attribution'] if f.exists() else {}
  results[name]={'exit':p.returncode,'verdict':a.get('attribution_verdict'),'unknown_and_limits':a.get('unknown_and_limits')}
print(json.dumps(results,indent=2))
