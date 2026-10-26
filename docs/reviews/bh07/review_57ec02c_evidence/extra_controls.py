"""Reviewer controls: temporary fixtures only, no app/backend/source changes."""
import json,tempfile,hashlib,importlib.util,subprocess,sys
from pathlib import Path
from tests.test_bh07_app_heap_oracle import snapshot_body,ORACLE,SENTINELS
from tests.test_bh07_app_heap_evidence import make_bundle,write_manifest,read_summary,write_summary,VERIFIER
out={}
with tempfile.TemporaryDirectory(prefix='appheap_r1_review_') as td:
 root=Path(td)
 valid=snapshot_body([SENTINELS['probe'],'ordinary'])
 cases={'positive_valid':valid,'missing_string_comma':valid.replace('"'+SENTINELS['probe']+'","ordinary"','"'+SENTINELS['probe']+'" "ordinary"'),'garbage_before_nodes':valid.replace(',"nodes":[',',BROKEN,"nodes":['),'leading_zero_integer':valid.replace('"nodes":[0,','"nodes":[00,',1)}
 for name,body in cases.items():
  p=root/'fixture.dump';p.write_bytes(body.encode())
  try:json.loads(body);valid_json=True
  except json.JSONDecodeError:valid_json=False
  scan=ORACLE.scan(p,SENTINELS)
  out[name]={'valid_json':valid_json,'scan':scan,'decision':ORACLE.decide({'post_logout':scan},{'post_logout':{'probe':True,'bank':False}},True,'profile')}
 for name,value in [('empty_summary',{}),('null_summary',None),('empty_list_summary',[])]:
  b=make_bundle(root/name);(b/'summary.json').write_bytes((json.dumps(value)+'\n').encode());write_manifest(b)
  before=VERIFIER._digests(b);problems=VERIFIER.verify(b)
  out[name]={'problems':problems,'readonly':before==VERIFIER._digests(b)}
 b=make_bundle(root/'report_verdict');p=b/'report.md';p.write_bytes(p.read_bytes().replace(b'(verdict PASS)',b'(verdict FAIL)'));write_manifest(b)
 out['contradictory_markdown_verdict']={'problems':VERIFIER.verify(b)}

 b=make_bundle(root/'symlink_dir');target=root/'outside';target.mkdir();(target/'fixture.heapsnapshot').write_bytes(b'{}');(b/'linked').symlink_to(target,target_is_directory=True)
 out['directory_symlink_to_raw_heap']={'problems':VERIFIER.verify(b),'symlink_present':(b/'linked').is_symlink()}
 b=make_bundle(root/'raw_sentinel');canary='Q7TESTBANK9';summary=read_summary(b);summary['sentinels']['bank']['length']=len(canary);summary['sentinels']['bank']['sha256_12']=hashlib.sha256(canary.encode()).hexdigest()[:12];write_summary(b,summary);log=b/'run.log';log.write_bytes(log.read_bytes()+canary.encode()+b'\n');write_manifest(b)
 out['raw_bank_sentinel_in_log']={'problems':VERIFIER.verify(b),'canary_matches_published_length_and_hash':True}
# CLI check inside repository solely because the CLI display uses relative_to(ROOT).
with tempfile.TemporaryDirectory(prefix='.review-appheap-cli-',dir=Path.cwd()) as td:
 b=make_bundle(Path(td)/'bundle');(b/'summary.json').write_bytes(b'{}\n');write_manifest(b)
 proc=subprocess.run([sys.executable,'-X','utf8','scripts/bh07_appheap/verify_evidence.py','--dir',str(b)],capture_output=True,text=True)
 out['empty_summary_cli']={'exit':proc.returncode,'stdout':proc.stdout.strip(),'stderr':proc.stderr.strip()}
print(json.dumps(out,indent=2))
