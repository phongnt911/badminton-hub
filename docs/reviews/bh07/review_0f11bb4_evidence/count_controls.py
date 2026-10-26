"""Reviewer replay of the handoff's count-consistency mutant, fixtures only."""
import json,tempfile,subprocess,sys
from pathlib import Path
from tests.test_bh07_app_heap_evidence import make_bundle,read_summary,write_summary,write_manifest,VERIFIER,render_report
out={}
with tempfile.TemporaryDirectory(prefix='appheap_count_review_') as td:
 r=Path(td)
 b=make_bundle(r/'positive');out['positive']=VERIFIER.verify(b)
 for label,epoch,name,count in [('retained_bank_count','post_actor','bank',1),('dead_probe_count','post_actor','probe',0),('negative_count','post_actor','bank',-1),('noninteger_count','post_actor','bank',0.5)]:
  b=make_bundle(r/label);s=read_summary(b);record=s['cycles'][0]['epochs'][epoch]['sentinels'][name];record['occurrences']=count
  write_summary(b,s);(b/'report.md').write_bytes(render_report(s).encode());write_manifest(b)
  before=VERIFIER._digests(b);out[label]={'record':record,'problems':VERIFIER.verify(b),'readonly':before==VERIFIER._digests(b)}
with tempfile.TemporaryDirectory(prefix='.review-count-cli-',dir=Path.cwd()) as td:
 b=make_bundle(Path(td)/'bundle');s=read_summary(b);s['cycles'][0]['epochs']['post_actor']['sentinels']['bank']['occurrences']=1
 write_summary(b,s);(b/'report.md').write_bytes(render_report(s).encode());write_manifest(b)
 proc=subprocess.run([sys.executable,'-X','utf8','scripts/bh07_appheap/verify_evidence.py','--dir',str(b)],capture_output=True,text=True)
 out['contradictory_count_cli']={'exit':proc.returncode,'stdout':proc.stdout.strip(),'stderr':proc.stderr.strip()}
print(json.dumps(out,indent=2))
