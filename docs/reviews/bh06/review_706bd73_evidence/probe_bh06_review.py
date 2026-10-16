import subprocess,json,uuid
from pathlib import Path
C='bh02-review-bh06';DBS=['bh06_clean_20261016153544','bh06_legacy_20261016153544'];out=[]
def sql(db,q):
 return subprocess.run(['docker','exec','-i',C,'psql','-U','postgres','-d',db,'-X','-qAt','-v','ON_ERROR_STOP=1'],input=q,text=True,capture_output=True)
def must(db,q):
 r=sql(db,q);assert r.returncode==0,r.stderr
 return r.stdout.strip().splitlines()[-1]
def user(db,n,q):
 return sql(db,f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-{n:012d}',true); {q}; ROLLBACK;")
for db in DBS:
 sid=str(uuid.uuid4());pid=str(uuid.uuid4());rid=str(uuid.uuid4())
 # Dedicated synthetic fixtures only. Real probes execute public RPC as role authenticated.
 fixture=f"""INSERT INTO sessions(id,host_user_id,venue_id,title,starts_at,ends_at,capacity,court_count,lifecycle,receiver_snapshot)
 SELECT '{sid}','00000000-0000-0000-0000-000000000001',id,'review-only synthetic',now()+interval '1 day',now()+interval '2 days',4,1,'in_progress',
 '{{"bank_code":"TEST_ONLY","account_number":"00001234","account_name":"SYNTHETIC"}}'::jsonb FROM venues LIMIT 1;
 INSERT INTO session_players(id,session_id,display_name,user_id,registration_status,attendance_status,source,created_by)
 VALUES('{pid}','{sid}','Synthetic offline guest',NULL,'confirmed','present','host','00000000-0000-0000-0000-000000000001');
 INSERT INTO charge_revisions(id,session_id,revision_no,source_version,allocation_total_vnd,fee_mode,finalized_by)
 VALUES('{rid}','{sid}',1,1,100000,'split_actual','00000000-0000-0000-0000-000000000001');
 INSERT INTO session_charges(revision_id,session_player_id,amount_due_vnd) VALUES('{rid}','{pid}',100000);"""
 must(db,fixture+'SELECT 1;')
 r=user(db,10,f"SELECT public.get_payment_instructions('{sid}','{pid}')")
 row={'db':db,'probe':'R1 outsider reads offline confirmed guest','expected':'FORBIDDEN','exit':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip(),'pass':r.returncode!=0 and 'FORBIDDEN' in r.stderr};out.append(row)
 # Negative control: same player account-linked to somebody else must be denied.
 must(db,f"UPDATE session_players SET user_id='00000000-0000-0000-0000-000000000005' WHERE id='{pid}'; SELECT 1;")
 r=user(db,10,f"SELECT public.get_payment_instructions('{sid}','{pid}')")
 out.append({'db':db,'probe':'control outsider reads account-linked guest','exit':r.returncode,'pass':r.returncode!=0 and 'FORBIDDEN' in r.stderr})
 # Stale via actual expense mutation under authenticated actor, rather than direct version UPDATE.
 r=user(db,1,f"SELECT public.post_session_expense('{sid}','court','review-only',1000,'{uuid.uuid4()}'); SELECT public.get_payment_instructions('{sid}','{pid}')")
 out.append({'db':db,'probe':'control new read after expense','expected':'BILLING_STALE','exit':r.returncode,'stderr':r.stderr.strip(),'pass':r.returncode!=0 and 'BILLING_STALE' in r.stderr})
 r=user(db,5,f"SELECT public.post_session_expense('{sid}','court','forbidden',1000,'{uuid.uuid4()}')")
 assert r.returncode and 'FORBIDDEN' in r.stderr
 # Same fixture participant invokes old read after an authorized expense in same transaction.
 r=sql(db,f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true); SELECT public.post_session_expense('{sid}','court','review-only',1000,'{uuid.uuid4()}'); SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000005',true); SELECT public.get_session_payment_instructions('{sid}'); ROLLBACK;")
 out.append({'db':db,'probe':'R2 legacy bank read after expense makes billing stale','expected':'BILLING_STALE','exit':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip(),'pass':r.returncode!=0 and 'BILLING_STALE' in r.stderr})
Path('/workspace/scratch/bh06-review-706bd73/probes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
for r in out:print(('PASS' if r['pass'] else 'FAIL'),r['db'],r['probe'])

import sys
sys.exit(1 if any(not r["pass"] for r in out) else 0)
