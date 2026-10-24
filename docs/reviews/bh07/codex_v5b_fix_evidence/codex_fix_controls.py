"""Codex self-verification after direct fix. Same original-AST scenarios, post-fix expected outcomes; original reviewer probe is unchanged."""
import ast,json,tempfile,shutil,uuid,urllib.request,urllib.error,os,runpy,unittest,io,contextlib
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[4];SRC=ROOT/'scripts/bh07_reset/run_full_reset.py';text=SRC.read_text();tree=ast.parse(text);main=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main');block=next(x for x in main.body if isinstance(x,ast.Try));results={}
def define(node,scope):exec(compile(ast.Module(body=[node],type_ignores=[]),str(SRC),'exec'),scope)
def fragment(nodes):
 fn=ast.FunctionDef(name='fragment',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=nodes,decorator_list=[])
 return compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(SRC),'exec')
# Strict helper: positive and known negative controls, plus unknown SQLSTATE.
helper=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='assert_negative_auth_rejection');env={};define(helper,env);f=env['assert_negative_auth_rejection'];rows=[]
cases=[('anon_positive','anon_complete',401,{'code':'42501','message':'permission denied for function complete_session'},True),('gateway_positive','no_apikey',401,{'message':'No API key found in request'},True),('outsider_positive','outsider_summary',403,{'code':'42501','message':'FORBIDDEN'},True),('old_xx000','anon_complete',403,{'code':'XX000','message':'unrelated failure','hint':'JWT api key FORBIDDEN permission denied'},False),('old_invalid','anon_complete',400,{'code':'INVALID_INPUT'},False),('old_not_found','outsider_summary',403,{'code':'NOT_FOUND'},False),('old_route404','no_apikey',404,{'message':'route missing'},False),('unknown_sqlstate_gateway_message','no_apikey',401,{'code':'42P01','message':'No API key found in request'},False)]
for name,kind,status,body,expect in cases:
 try:f(name,status,body,kind);accepted=True
 except (AssertionError,ValueError):accepted=False
 rows.append({'case':name,'status':status,'body':body,'expected_accept':expect,'actual_accept':accepted})
assert all(x['expected_accept']==x['actual_accept'] for x in rows);results['auth_helper']=rows
# Full main control flow: initial preflight is real, owned inventory is failed after successful start.
class Sock:
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def settimeout(self,*a):pass
 def connect_ex(self,*a):return 111
class StopAtReset(Exception):pass
pref=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='preflight_ownership_check');rows=[]
for name,owned_code in [('positive_owned_inventory',0),('owned_inventory_error',1)]:
 with tempfile.TemporaryDirectory(prefix='v5b-r2-owned-') as td:
  calls=[]
  def cmd(args,**kw):
   calls.append(args)
   if args[:3]==['npx','supabase','db']:raise StopAtReset('synthetic boundary: no reset executed')
   if args[:3]==['npx','supabase','status']:return SimpleNamespace(returncode=0,stdout=json.dumps({'API_URL':'http://127.0.0.1:56421','ANON_KEY':'synthetic','SERVICE_ROLE_KEY':'synthetic'}),stderr='')
   if args[:2]==['docker','ps']:
    if '{{.ID}}' in args:return SimpleNamespace(returncode=owned_code,stdout='owned-id' if owned_code==0 else '',stderr='daemon inventory failure' if owned_code else '')
    return SimpleNamespace(returncode=0,stdout='',stderr='')
   return SimpleNamespace(returncode=0,stdout='' if args[:2]==['git','status'] else 'synthetic',stderr='')
  scope={'print':lambda *a,**kw:None,'STAMP':'synthetic','BASE_SHA':'synthetic','PROJECT_ID':'synthetic','PORT_API':56421,'PORT_DB':56422,'PORT_SHADOW':56420,'PORT_STUDIO':56423,'PORT_SMTP':56424,'PORT_ANALYTICS':56427,'PORT_S3':56428,'PORT_POOLER':56429,'run_cmd':cmd,'socket':SimpleNamespace(socket=lambda *a:Sock(),AF_INET=2,SOCK_STREAM=1),'Path':Path,'tempfile':SimpleNamespace(gettempdir=lambda:td),'os':os,'prepare_project_dir':lambda p:p.mkdir(parents=True),'log_cmd':lambda *a:None,'write_evidence':lambda *a:None,'exits':{},'audit_results':{},'json':json,'urllib':urllib,'shutil':shutil}
  define(pref,scope);define(main,scope)
  try:scope['main']()
  except (StopAtReset, RuntimeError):pass
  attempted=any(x[:3]==['npx','supabase','db'] for x in calls)
  rows.append({'case':name,'owned_inventory_exit':owned_code,'expected_reset_attempt':owned_code==0,'actual_reset_attempt':attempted,'actual_stop_attempt':any(x[:3]==['npx','supabase','stop'] for x in calls)})
assert all(x['expected_reset_attempt']==x['actual_reset_attempt'] for x in rows);results['ownership_after_start']=rows
# Actual finally: previously open R3 cases now fail closed and preserve original error.
class PrimaryError(Exception):pass
class FinalInspectError(Exception):pass
rows=[]
for name in ['positive','inspection_nonzero','final_inspect_raises_with_primary','foreign_container']:
 with tempfile.TemporaryDirectory(prefix='v5b-r2-cleanup-') as td:
  work=Path(td)/'work';work.mkdir();inventory=['owned-id','foreign-id'] if name=='foreign_container' else [];removed=[];cnt=[0]
  def cmd(args,**kw):
   if args[:3]==['npx','supabase','stop']:return SimpleNamespace(returncode=0,stdout='',stderr='')
   if args[:2]==['docker','ps']:
    cnt[0]+=1
    if name=='final_inspect_raises_with_primary' and cnt[0]==2:raise FinalInspectError('synthetic final inspect')
    return SimpleNamespace(returncode=1 if name=='inspection_nonzero' else 0,stdout='\n'.join(inventory),stderr='daemon failure')
   if args[:3]==['docker','rm','-f']:
    removed.extend(args[3:]);inventory[:]=[x for x in inventory if x not in args[3:]];return SimpleNamespace(returncode=0,stdout='',stderr='')
   raise AssertionError(args)
  scope={'print':lambda *a,**kw:None,'run_cmd':cmd,'temp_dir':work,'exits':{},'write_evidence':lambda *a:None,'log_cmd':lambda *a:None,'audit_results':{},'PROJECT_ID':'synthetic','shutil':shutil,'owned_containers':['owned-id'],'primary_error':PrimaryError('synthetic primary') if name=='final_inspect_raises_with_primary' else None}
  exec(fragment(block.finalbody),scope)
  try:scope['fragment']();error=None
  except Exception as e:error=type(e).__name__
  rows.append({'case':name,'error':error,'cleanup':scope['audit_results'].get('cleanup'),'removed':removed,'remaining_inventory':list(inventory)})
assert rows[0]['cleanup']['clean'] and rows[1]['error']=='RuntimeError' and not rows[1]['cleanup']['clean'] and rows[2]['error']=='PrimaryError';assert rows[3]['removed']==['owned-id'] and rows[3]['remaining_inventory']==['foreign-id'];results['cleanup']=rows
# Run whole author behavior suite against a disabled preflight mutant.
with tempfile.TemporaryDirectory(prefix='v5b-r2-mutant-') as td:
 p=Path(td)/'runner.py';needle='    print("Running Preflight Ownership & Resource Isolation Check...")';assert needle in text;p.write_text(text.replace(needle,needle+'\n    return {"status":"PASS"} # reviewer mutant',1))
 ns=runpy.run_path(str(ROOT/'tests/test_v5b_runner_flaws.py'));cls=ns['TestV5bRunnerBehavior'];cls.setUpClass.__func__.__globals__['RUNNER_SRC']=p;suite=unittest.defaultTestLoader.loadTestsFromTestCase(cls);out=io.StringIO()
 with contextlib.redirect_stdout(out):run=unittest.TextTestRunner(stream=out).run(suite)
 assert not run.wasSuccessful();results['full_suite_mutant']={'tests_run':run.testsRun,'failures':len(run.failures),'errors':len(run.errors),'mutant_detected':not run.wasSuccessful()}
# Verify that the new tests kill each newly fixed gate independently.
new_mutants=[]
for name,old,new in [
 ('owned_inventory_guard', 'if p_owned.returncode != 0:', 'if False and p_owned.returncode != 0:'),
 ('gateway_tuple_guard', "if status != 401 or 'code' in body or message.casefold() != 'no api key found in request':", 'if False:'),
]:
 assert old in text
 with tempfile.TemporaryDirectory(prefix='v5b-codex-new-mutant-') as td:
  p=Path(td)/'runner.py';p.write_text(text.replace(old,new,1))
  ns=runpy.run_path(str(ROOT/'tests/test_v5b_runner_flaws.py'));cls=ns['TestV5bRunnerBehavior'];cls.setUpClass.__func__.__globals__['RUNNER_SRC']=p;suite=unittest.defaultTestLoader.loadTestsFromTestCase(cls);out=io.StringIO()
  with contextlib.redirect_stdout(out):run=unittest.TextTestRunner(stream=out).run(suite)
  assert not run.wasSuccessful() and not run.errors
  new_mutants.append({'gate':name,'tests_run':run.testsRun,'expected_suite_pass':False,'suite_pass':run.wasSuccessful(),'failures':len(run.failures),'errors':len(run.errors)})
results['new_gate_mutants']=new_mutants
print(json.dumps(results,indent=2))
