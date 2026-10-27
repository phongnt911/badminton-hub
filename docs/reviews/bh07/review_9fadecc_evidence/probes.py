"""Reviewer graph/privacy/mutant controls, synthetic data only."""
import copy,hashlib,json,tempfile,shutil,importlib.util
from pathlib import Path
from tests.test_bh07_app_heap_paths import ORACLE,write_snapshot,graph_scan,clean_graph,SYNTHETIC,OBJECT,STRING,BANK_STRING,INTERNAL,PROPERTY,STRINGS
out={}
# Eight orphan string nodes precede the ninth, which is strongly retained.
nodes=[(SYNTHETIC,0,1),(SYNTHETIC,1,1),(OBJECT,3,1)]+[(STRING,BANK_STRING,0)]*9
edges=[(INTERNAL,0,1),(INTERNAL,0,2),(PROPERTY,8,11)]
body=write_snapshot(nodes,edges);doc=json.loads(body);layout,_=ORACLE._layout(doc);parent,pe,error=ORACLE._root_reach(doc,layout)
scan=graph_scan(body)
out['ninth_retained_node']={'graph_error':error,'ninth_actual_parent':parent[11],'reported':scan['paths']['bank'],'counted':scan['sentinels']['bank']}
# Full needle exceeds truncation limit: current redaction looks only at the truncated label.
doc=json.loads(clean_graph(label_as_sentinel=True));needle='PRIVATE_CANARY_'+('q'*65);doc['strings'][BANK_STRING]=needle
layout,_=ORACLE._layout(doc);frame=ORACLE._edge_frame(doc,layout,2,[needle])
out['long_label']={'raw_length':len(needle),'frame_contains_private_prefix':needle[:40] in frame,'frame_has_redacted_marker':'<redacted>' in frame,'full_needle_in_frame':needle in frame}
# Required mutants against the real published record; no edits to source/evidence.
s=json.loads(Path('docs/reviews/bh07/retained_path_evidence/summary.json').read_text());base=s['cycles'][0]['epochs']
def decide(scans):return ORACLE.decide(scans,ORACLE.derive_expectations(scans),True,'profile',strict=True)
out['positive_real_record']=decide(base)['verdict']
mut=copy.deepcopy(base)
for v in mut.values():v['sentinels']['expense_id']['scope']='identity'
out['finance_downgrade']=decide(mut)
mut=copy.deepcopy(base);mut['post_logout']['sentinels']['expense_id']['present']=True;mut['post_logout']['sentinels']['expense_id']['occurrences']=1;mut['post_logout']['paths']['expense_id']=copy.deepcopy(mut['owner_active']['paths']['expense_id']);out['finance_retained']=decide(mut)
mut=copy.deepcopy(base);mut['post_actor'].pop('paths');out['missing_paths']=decide(mut)
# Engine attribution is not read by the oracle: put a rendered title under an app cache.
mut=copy.deepcopy(base);p=mut['post_logout']['paths']['expense'];p.update(reachable=True,root_kind='global_handles',path_len=3,frames=['root','internal:(Global handles) -> synthetic','property:financeProviderCache -> object','property:title -> string']);p['path_sha256_12']=hashlib.sha256('\n'.join(p['frames']).encode()).hexdigest()[:12]
out['rendered_app_cache']={'verdict':decide(mut)['verdict'],'risks':decide(mut)['residual_risks']}
# Identity justification must not label the logged-out Guest as authorized.
mut=copy.deepcopy(base);mut['post_logout']['sentinels']['player_a']['present']=True;mut['post_logout']['sentinels']['player_a']['occurrences']=1;mut['post_logout']['paths']['player_a']=copy.deepcopy(mut['owner_active']['paths']['player_a']);v=decide(mut)
out['identity_after_logout']={'verdict':v['verdict'],'notes':[n for n in v['notes'] if n.startswith('post_logout:') and 'player_a' in n]}
# Short property-label case from the original tests must remain redacted.
x=graph_scan(clean_graph(label_as_sentinel=True));out['short_label_positive']={'redacted':any('<redacted>' in f for f in x['paths']['bank']['frames'])}

# Auditor must independently enforce cleanup and class agreement after rehash.
sp=importlib.util.spec_from_file_location('retained_verifier','scripts/bh07_appheap/verify_evidence.py');v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
with tempfile.TemporaryDirectory(prefix='retained_bundle_controls_') as td:
 for case in ['cleanup_false','cleanup_missing','metadata_scope_drift']:
  d=Path(td)/case;shutil.copytree('docs/reviews/bh07/retained_path_evidence',d);data=json.loads((d/'summary.json').read_text())
  if case=='cleanup_false':data['cleanup']['extra_expense_removed']=False
  elif case=='cleanup_missing':data['cleanup'].pop('extra_expense_removed')
  else:data['sentinels']['expense_id']['scope']='identity'
  (d/'summary.json').write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())
  report=(d/'report.md').read_text()
  if case=='metadata_scope_drift':report='\n'.join(line.replace('finance, not rendered, distinctive','identity, not rendered, distinctive') if line.startswith('| expense_id |') else line for line in report.split('\n'))
  if case=='cleanup_false':report=report.replace('"extra_expense_removed":true','"extra_expense_removed":false')
  (d/'report.md').write_bytes(report.encode())
  (d/'hashes.sha256').write_bytes(''.join(hashlib.sha256((d/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in ['summary.json','report.md','run.log']).encode())
  before=v._digests(d);out[case]={'problems':v.verify(d),'readonly':before==v._digests(d)}
print(json.dumps(out,indent=2))
