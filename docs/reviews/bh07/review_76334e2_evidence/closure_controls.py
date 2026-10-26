"""Adversarial closure checks on temporary fixtures, not app/backend changes."""
import json,tempfile,hashlib
from pathlib import Path
from tests.test_bh07_app_heap_oracle import snapshot_body,ORACLE,SENTINELS
from tests.test_bh07_app_heap_evidence import make_bundle,write_manifest,read_summary,write_summary,VERIFIER,render_report
out={}
with tempfile.TemporaryDirectory(prefix='appheap_r2_controls_') as td:
 r=Path(td)
 def scan(body):
  p=r/'fixture.dump';p.write_bytes(body.encode());return ORACLE.scan(p,SENTINELS)
 body=snapshot_body([SENTINELS['bank'],SENTINELS['probe']])
 escaped=body.replace(SENTINELS['bank'], ''.join('\\u%04x'%ord(c) for c in SENTINELS['bank']))
 out['escaped_retained_bank']={'decoded_documents_equal':json.loads(body)==json.loads(escaped),'bank_in_decoded_strings':SENTINELS['bank'] in json.loads(escaped)['strings'],'scan_literal':scan(body),'scan_escaped':scan(escaped)}
 scans={e:scan(snapshot_body([SENTINELS['probe']])) for e in ['baseline','owner_active','post_logout','post_actor']}
 scans['owner_active']=scan(body);scans['post_actor']=scan(escaped)
 expected={e:{'probe':True,'bank':e=='owner_active'} for e in scans}
 out['cycle_with_retained_escaped_bank']=ORACLE.decide(scans,expected,True,'profile')
 for missing in ['length','sha256_12']:
  b=make_bundle(r/missing);s=read_summary(b);canary='Q7TESTBANK9';s['sentinels']['bank'].update(length=len(canary),sha256_12=hashlib.sha256(canary.encode()).hexdigest()[:12]);s['sentinels']['bank'].pop(missing);write_summary(b,s)
  (b/'report.md').write_bytes(render_report(s).encode());p=b/'run.log';p.write_bytes(p.read_bytes()+canary.encode()+b'\n');write_manifest(b)
  out['raw_bank_missing_'+missing]={'problems':VERIFIER.verify(b)}
print(json.dumps(out,indent=2))
