from pathlib import Path
import hashlib,json,sys
root=Path.cwd();sys.path.insert(0,str(root))
from scripts.bh07_backup.run_local_rehearsal import fingerprint,public_rows
label=sys.argv[1];assert label in ('before','after')
out=root/'.build/web-payment-20261113';out.mkdir(exist_ok=True)
p=out/(label+'-fingerprint.json')
assert not p.exists(),'Do not overwrite fingerprint baseline/receipt'
d=fingerprint('bh07-android-db')
r={'public':public_rows(d),'schema':d['_schema'],'roles':d['_roles'],'sequences':d['_sequences']}
p.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
print(json.dumps({'label':label,'tables':len(r['public']),'rows':sum(x['rows'] for x in r['public'].values())}))
if label=='after':
 before=json.loads((out/'before-fingerprint.json').read_text());after=json.loads(p.read_text());values=[]
 for v in [before,after]:
  seq,=[x for x in v['sequences'] if x['schemaname']=='auth' and x['sequencename']=='refresh_tokens_id_seq']
  values.append(seq.pop('last_value'))
 assert before==after,'Baseline state changed beyond Auth sequence'
 receipt={'public_rows_schema_roles_all_other_sequences_equal':True,'public_tables':len(r['public']),'public_rows':sum(x['rows'] for x in r['public'].values()),'auth_rows_excluded':True,'auth_refresh_sequence':values,'before_sha256':hashlib.sha256((out/'before-fingerprint.json').read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 (out/'database-comparison.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('Baseline fingerprint restored after owned fixture cleanup')
