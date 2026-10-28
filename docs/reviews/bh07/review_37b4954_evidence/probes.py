from pathlib import Path
import importlib.util,json,copy,tempfile,subprocess
r=Path.cwd();spec=importlib.util.spec_from_file_location('a',r/'scripts/bh07_appheap/audit_retention_attribution.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
original=json.loads((r/'docs/reviews/bh07/review_runtime_b13e468_evidence/summary.json').read_text());out={}
for case in ['positive','peer_retained','wrong_environment','missing_rendered_paths']:
 s=copy.deepcopy(original)
 if case=='peer_retained':
  e=s['cycles'][0]['epochs']['post_logout'];e['sentinels']['expense_id'].update(present=True,occurrences=1);e['paths']['expense_id']['reachable']=True
 if case=='wrong_environment':s['environment']['flutter']='Wrong SDK';s['environment']['build']['mode']='debug'
 if case=='missing_rendered_paths':
  for c in s['cycles']:
   for e in c['epochs'].values():e['paths'].pop('expense',None);e['paths'].pop('expense2',None)
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'input.json';p.write_text(json.dumps(s));v=a.audit_summary_json(p);claim=a.analyze_attribution(v)
  run=subprocess.run(['python','scripts/bh07_appheap/audit_retention_attribution.py','--summary',str(p),'--out-dir',str(Path(td)/'out')],capture_output=True,text=True)
  out[case]={'exit':run.returncode,'environment_consistent':v['environment']['consistent'],'peer_clean':[x['peer_sentinels_clean'] for x in v['cycle_findings']],'path_cache':claim['engine_criteria']['path_leads_to_segmentationCache'],'verdict':claim['attribution_verdict']}
print(json.dumps(out,indent=2))
