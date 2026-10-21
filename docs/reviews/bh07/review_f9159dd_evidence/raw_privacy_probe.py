from pathlib import Path
import json,urllib.request
out=Path('/workspace/scratch/bh07-review-f9159dd');c=json.loads(Path('/tmp/bh07-http-review-runtime/kong.json').read_text());anon=c['consumers'][0]['keyauth_credentials'][0]['key'];service=c['consumers'][1]['keyauth_credentials'][0]['key'];base='http://127.0.0.1:54321';opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def post(path,data,token=anon):
 req=urllib.request.Request(base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','apikey':anon,'Authorization':'Bearer '+token})
 with opener.open(req,timeout=15) as r:return json.load(r)
def get(path):
 req=urllib.request.Request(base+path,headers={'apikey':service,'Authorization':'Bearer '+service})
 with opener.open(req,timeout=15) as r:return json.load(r)
def login(email):return post('/auth/v1/token?grant_type=password',{'email':email,'password':'bh07-http-pass-123456'})['access_token']
f=login('financea@example.test');m=login('cohosta@example.test');params={'p_session_id':'10000000-0000-4000-8000-000000000001'}
rawf=post('/rest/v1/rpc/get_session_summary',params,f);rawm=post('/rest/v1/rpc/get_session_summary',params,m);history=post('/rest/v1/rpc/list_my_session_history',{'p_limit':100,'p_offset':0},f)
finance_fields=['billing_state','active_revision_id','revision_no','source_version','expenses_total_vnd','amount_due_total_vnd','total_paid_vnd','outstanding_total_vnd']
markers=['+84900000004','+84900000001','+84900000002','+84900000003','+84900000005','BH07-PRIVATE-MEMBER-CONTACT','BH07BANK','0000000007','BH07 PRIVATE RECEIVER','BH07HOSTBANK','0000000008','BH07 PRIVATE HOST']
def values(x):
 if isinstance(x,dict):return [s for v in x.values() for s in values(v)]
 if isinstance(x,list):return [s for v in x for s in values(v)]
 return [x] if isinstance(x,str) else []
payload_values=values([rawf,rawm,history]);source=get('/rest/v1/member_contacts?select=phone_number,contact_note')+get('/rest/v1/session_player_contacts?select=phone_number')+get('/rest/v1/club_bank_accounts?select=bank_code,account_number,account_name')+get('/rest/v1/host_bank_accounts?select=bank_code,account_number,account_name')+get('/rest/v1/sessions?select=receiver_snapshot')
source_values=values(source)
checks={'cohost_all_8_finance_fields_explicit_null':all(k in rawm and rawm[k] is None for k in finance_fields),'all_12_private_fixture_markers_present_in_source':all(v in source_values for v in markers),'all_12_private_fixture_markers_absent_as_scalars_in_projection':all(v not in payload_values for v in markers),'history_rows':len(history)}
assert all(checks[k] for k in checks if k!='history_rows')
(out/'raw-privacy-probe.json').write_text(json.dumps(checks,indent=2)+'\n');print('Raw HTTP privacy probe PASS: all 12 private marker values in source and absent in projection')
