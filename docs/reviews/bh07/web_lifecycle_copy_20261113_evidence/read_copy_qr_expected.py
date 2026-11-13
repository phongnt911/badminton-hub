from pathlib import Path
import json,subprocess
root=Path.cwd();out=root/'.build/web-lifecycle-20261113'
docker='C:/Users/PHONGNT/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
sql="""BEGIN;
DO $$ BEGIN PERFORM set_config('request.jwt.claims',jsonb_build_object('sub',(SELECT id FROM auth.users WHERE email='guesta@example.test'),'role','authenticated')::text,true); END $$;
SELECT public.get_payment_instructions('10000000-0000-4000-8000-000000000099',NULL);
ROLLBACK;"""
r=subprocess.run([docker,'exec','-i','bh07-android-db','psql','-X','-U','postgres','-v','ON_ERROR_STOP=1','-t','-A'],input=sql,text=True,capture_output=True,encoding='utf-8')
assert r.returncode==0,'Read-only instructions query failed'
data,=[json.loads(line) for line in r.stdout.splitlines() if line.startswith('{')]
assert data['amount_due_vnd']==100000 and data['total_paid_vnd']==0 and data['outstanding_vnd']==100000
receiver=data['receiver_snapshot'];assert receiver is not None
expected={k:receiver[k] for k in ['bank_code','account_number','account_name']};expected['reference']=data['reference']
assert all(isinstance(v,str) and v.strip() for v in expected.values())
(out/'copy-qr-private-expected.json').write_text(json.dumps(expected,ensure_ascii=False),encoding='utf-8')
print('Guest A due/paid/outstanding100000/0/100000 and receiver expected values ready in ignored file; no raw values published')
