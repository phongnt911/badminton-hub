"""Original-AST fault probes. No real HTTP/Docker/credential mutation."""
import ast,json,socket,shutil,tempfile,uuid,urllib.request,urllib.error,runpy,unittest,io,contextlib
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[4];SRC=ROOT/'scripts/bh07_reset/run_full_reset.py';text=SRC.read_text();tree=ast.parse(text)
main=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main');block=next(x for x in main.body if isinstance(x,ast.Try));result={}
def fragment(nodes):
 fn=ast.FunctionDef(name='fragment',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=nodes,decorator_list=[])
 return compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(SRC),'exec')
class Sock:
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def settimeout(self,*a):pass
 def connect_ex(self,*a):return 111
pre=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='preflight_ownership_check');rows=[]
for name,code,out in [('positive',0,''),('existing_container',0,'foreign-id existing-project'),('docker_list_failure',1,'')]:
 env={'print':lambda *a:None,'run_cmd':lambda *a,**kw:SimpleNamespace(returncode=code,stdout=out,stderr='daemon failure' if code else ''),'PROJECT_ID':'synthetic','socket':SimpleNamespace(socket=lambda *a:Sock(),AF_INET=2,SOCK_STREAM=1),'PORT_API':1,'PORT_DB':2,'PORT_SHADOW':3,'PORT_STUDIO':4,'PORT_SMTP':5,'PORT_ANALYTICS':6,'PORT_S3':7,'PORT_POOLER':8}
 exec(compile(ast.Module(body=[pre],type_ignores=[]),str(SRC),'exec'),env)
 try:env['preflight_ownership_check']();accepted=True
 except RuntimeError:accepted=False
 rows.append({'case':name,'expected_accept':name=='positive','actual_accept':accepted})
assert rows[0]['actual_accept'] and not rows[1]['actual_accept'] and rows[2]['actual_accept'];result['preflight']=rows
# Negative controls: same AST, exact guard from source, fake transport responses.
httpdef=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='http_request');guard={'urllib':urllib,'json':json};exec(compile(ast.Module(body=[httpdef],type_ignores=[]),str(SRC),'exec'),guard)
start=next(i for i,x in enumerate(block.body) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='neg_results' for t in x.targets))
code=fragment(block.body[start:]+[ast.Return(value=ast.Call(func=ast.Name(id='locals',ctx=ast.Load()),args=[],keywords=[]))]);rows=[]
for name in ['positive','old_invalid_input','xx000_with_auth_words_in_hint']:
 calls=[]
 def http(url,body=None,headers=None):
  calls.append({"url":url,"headers":headers or {}})
  if '192.168.' in url:return guard['http_request'](url)
  if '/token?' in url:return 200,{'access_token':'synthetic'}
  if name=='old_invalid_input':return 400,{'code':'INVALID_INPUT','message':'invalid argument'}
  if name=='xx000_with_auth_words_in_hint':return 403,{'code':'XX000','message':'unrelated database failure','hint':'JWT api key FORBIDDEN permission denied'}
  if '/get_session_summary' in url:return 403,{'code':'42501','message':'FORBIDDEN'}
  return 401,{'code':'42501','message':'permission denied for function complete_session'}
 env={'print':lambda *a:None,'http_request':http,'http_res2':{'tokens':{'ownera':'owner-synthetic'}},'sql':lambda q:'3','api_url':'http://127.0.0.1:56421','anon_key':'synthetic','uuid':uuid,'json':json,'write_evidence':lambda *a:None,'audit_results':{}}
 exec(code,env)
 try:local=env['fragment']();accepted=True
 except AssertionError:local={};accepted=False
 rows.append({'case':name,'expected_accept':name=='positive','actual_accept':accepted,'pos_st_without_owner_http':local.get('pos_st'),'summary_rpc_count':sum('/get_session_summary' in c['url'] for c in calls),'owner_summary_positive_http_calls':sum('/get_session_summary' in c['url'] and c['headers'].get('Authorization')=='Bearer owner-synthetic' for c in calls)})
assert rows[0]['actual_accept'] and not rows[1]['actual_accept'] and rows[2]['actual_accept'];result['negative_controls']=rows
# Cleanup: real finally, stateful mock container inventory and exceptions.
class PrimaryError(Exception):pass
class FinalInspectError(Exception):pass
rows=[]
for name in ['positive','inspection_nonzero','unowned_container_seen','final_inspect_raises_with_primary','private_delete_failure','stop_failure_preserves_primary']:
 with tempfile.TemporaryDirectory(prefix='v5b-r1-fault-') as td:
  work=Path(td)/'work';work.mkdir();inventory=['foreign-id'] if name=='unowned_container_seen' else [];removed=[];counter=[0]
  def cmd(args,**kw):
   if args[:3]==['npx','supabase','stop']:return SimpleNamespace(returncode=1 if name=='stop_failure_preserves_primary' else 0,stdout='',stderr='synthetic stop error')
   if args[:2]==['docker','ps']:
    counter[0]+=1
    if name=='final_inspect_raises_with_primary' and counter[0]==2:raise FinalInspectError('synthetic inspect exception')
    return SimpleNamespace(returncode=1 if name=='inspection_nonzero' else 0,stdout='\n'.join(inventory),stderr='daemon failure')
   if args[:3]==['docker','rm','-f']:removed.extend(args[3:]);inventory.clear();return SimpleNamespace(returncode=0,stdout='',stderr='')
   raise AssertionError(args)
  cleanup_shutil=SimpleNamespace(rmtree=lambda *a,**kw:None) if name=='private_delete_failure' else shutil
  env={'print':lambda *a:None,'run_cmd':cmd,'temp_dir':work,'exits':{},'write_evidence':lambda *a:None,'log_cmd':lambda *a:None,'audit_results':{},'PROJECT_ID':'synthetic','shutil':cleanup_shutil,'owned_containers':['owned-id'],'primary_error':PrimaryError('synthetic primary') if name in ['final_inspect_raises_with_primary','stop_failure_preserves_primary'] else None}
  exec(fragment(block.finalbody),env)
  try:env['fragment']();error=None
  except Exception as e:error=type(e).__name__
  rows.append({'case':name,'error':error,'cleanup':env['audit_results'].get('cleanup'),'removed_container_ids':removed,'owned_container_ids':['owned-id'],'private_path_remains':work.exists()})
assert rows[0]['cleanup']['clean'] and rows[1]['cleanup']['clean'];assert rows[2]['removed_container_ids']==['foreign-id'];assert rows[3]['error']=='FinalInspectError';assert rows[4]['error']=='RuntimeError';assert rows[5]['error']=='PrimaryError';result['cleanup']=rows
# Mutant lives only in a temporary file. Original author's tests run unchanged.
with tempfile.TemporaryDirectory(prefix='v5b-r1-mutant-') as td:
 mutant=Path(td)/'runner.py';needle='    print("Running Preflight Ownership & Resource Isolation Check...")';assert needle in text;mutant.write_text(text.replace(needle,needle+'\n    return {"status":"PASS"} # reviewer mutant: disable ownership gate',1))
 ns=runpy.run_path(str(ROOT/'tests/test_v5b_runner_flaws.py'));cls=ns['TestV5bRunnerFlawsAndFixes'];cls.setUpClass.__func__.__globals__['RUNNER_SRC']=mutant
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(cls);capture=io.StringIO()
 with contextlib.redirect_stdout(capture):run=unittest.TextTestRunner(stream=capture).run(suite)
 assert run.wasSuccessful();result['test_suite_mutant']={'mutation':'preflight returns PASS before all checks','tests_run':run.testsRun,'suite_still_passes':run.wasSuccessful(),'expected_suite_pass':False}
print(json.dumps(result,indent=2))
