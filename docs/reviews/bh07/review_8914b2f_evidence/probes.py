import importlib.util,json,tempfile,shutil,hashlib
from pathlib import Path
R=Path.cwd()
def load(n):
 s=importlib.util.spec_from_file_location(n,R/'scripts/bh07_appheap'/f'{n}.py'); m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
o=load('heap_oracle');v=load('verify_evidence');out={}
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'bad.dump'
 # Deliberately invalid JSON with all substring markers and closing brace.
 p.write_bytes(b'{"snapshot":BROKEN,'+b'x'*5000+b',"nodes":[],"edges":[],"strings":["ALIVE"]}')
 try:json.loads(p.read_text());valid=True
 except json.JSONDecodeError:valid=False
 s=o.scan(p,{'bank':'PRIVATE_CANARY','probe':'ALIVE'})
 out['invalid_snapshot']={'valid_json':valid,'scan':s,'decision':o.decide({'post_logout':s},{'post_logout':{'bank':False,'probe':True}},True,'profile')}
 full={epoch:json.loads(json.dumps(s)) for epoch in ['baseline','owner_active','post_logout','post_actor']}
 p.write_text(json.dumps({'snapshot':{},'pad':'x'*5000,'nodes':[],'edges':[],'strings':['PRIVATE_CANARY','ALIVE']},separators=(',',':')))
 full['owner_active']=o.scan(p,{'bank':'PRIVATE_CANARY','probe':'ALIVE'})
 expected={epoch:{'probe':True,'bank':epoch=='owner_active'} for epoch in full}
 out['full_cycle_with_invalid_snapshot']=o.decide(full,expected,True,'profile')
 def bundle():
  d=Path(td)/'ev';shutil.rmtree(d,ignore_errors=True);shutil.copytree(R/'docs/reviews/bh07/app_profile_heap_evidence',d);return d
 def rehash(d):
  (d/'hashes.sha256').write_text(''.join(hashlib.sha256((d/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in ['summary.json','run.log','report.md']))
 d=bundle();p=d/'run.log';p.write_bytes(p.read_bytes().replace(b'\n',b'\r\n'));rehash(d);out['crlf']=v.verify(d)
 d=bundle();p=d/'run.log';p.write_bytes(p.read_bytes()+b'\xff\n');rehash(d);out['invalid_utf8']=v.verify(d)
 d=bundle();(d/'extra.txt').write_text('bh07-http-'+'pass-canary\n');out['unmanifested_secret_extra']=v.verify(d)
 d=bundle();p=d/'summary.json';s=json.loads(p.read_text());s['cycles']=[];p.write_text(json.dumps(s));rehash(d);out['zero_cycles']=v.verify(d)
 d=bundle();p=d/'summary.json';s=json.loads(p.read_text());del s['cycles'][0]['epochs']['post_actor'];p.write_text(json.dumps(s));rehash(d);out['missing_epoch']=v.verify(d)
 d=bundle();p=d/'summary.json';s=json.loads(p.read_text());s['cycles'][0]['epochs']['post_actor']['ok']=False;s['cycles'][0]['epochs']['post_actor']['sentinels']['bank']['present']=True;p.write_text(json.dumps(s));rehash(d);out['leaked_failed_scan']=v.verify(d)
print(json.dumps(out,indent=2))
