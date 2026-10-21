from pathlib import Path
import json,urllib.request
out=Path('/workspace/scratch/bh07-review-3ad25a4'); config=json.loads(Path('/tmp/bh07-http-review-runtime/kong.json').read_text());anon=config['consumers'][0]['keyauth_credentials'][0]['key'];base='http://127.0.0.1:54321'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def post(path,payload,token=anon):
 req=urllib.request.Request(base+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','apikey':anon,'Authorization':'Bearer '+token})
 with opener.open(req,timeout=15) as r:return json.load(r)
def login(email):return post('/auth/v1/token?grant_type=password',{'email':email,'password':'bh07-http-pass-123456'})['access_token']
cohost=login('cohosta@example.test');finance=login('financea@example.test')
sid='10000000-0000-4000-8000-000000000001'
raw=post('/rest/v1/rpc/get_session_summary',{'p_session_id':sid},cohost)
fields=['billing_state','active_revision_id','revision_no','source_version','expenses_total_vnd','amount_due_total_vnd','total_paid_vnd','outstanding_total_vnd']
history=post('/rest/v1/rpc/list_my_session_history',{'p_limit':100,'p_offset':0},finance)
blocked=('contact','phone','bank','account','receiver')
def no_sensitive_keys(x):
 if isinstance(x,dict):return all(not any(t in k.lower() for t in blocked) and no_sensitive_keys(v) for k,v in x.items())
 if isinstance(x,list):return all(no_sensitive_keys(v) for v in x)
 return True
checks={'real_HTTP_cohost_summary_all_finance_fields_explicit_null':all(f in raw and raw[f] is None for f in fields),'real_HTTP_summary_recursive_key_check':no_sensitive_keys(raw),'real_HTTP_all_history_rows_recursive_key_check':no_sensitive_keys(history),'history_rows':len(history),'summary_keys':sorted(raw)}
# These predicates reproduce the current test logic; the payloads below are synthetic,
# not server responses and not evidence of an actual leak.
def original_summary_predicate(x):return not any(any(t in k.lower() for t in ('contact','phone','bank','account')) for k in x)
def original_history_predicate(xs):return bool(xs) and not any(any(t in k.lower() for t in ('contact','phone')) for k in xs[0])
checks['synthetic_counterexamples']=[{'case':'bank/account nested under receiver_snapshot','current_assertion_accepts':original_summary_predicate({'session_id':'s','receiver_snapshot':{'account_number':'REVIEW-SENTINEL'}})},{'case':'bank_account directly on first history row','current_assertion_accepts':original_history_predicate([{'id':'s','bank_account':'REVIEW-SENTINEL'}])},{'case':'phone on second history row','current_assertion_accepts':original_history_predicate([{'id':'s1'},{'id':'s2','phone':'REVIEW-SENTINEL'}])}]
assert all(checks[k] for k in ['real_HTTP_cohost_summary_all_finance_fields_explicit_null','real_HTTP_summary_recursive_key_check','real_HTTP_all_history_rows_recursive_key_check'])
assert all(c['current_assertion_accepts'] for c in checks['synthetic_counterexamples'])
(out/'privacy-probe.json').write_text(json.dumps(checks,indent=2)+'\n');print('Raw HTTP privacy currently safe; 3 synthetic unsafe payloads accepted by existing test predicates')
