"""Fault probes execute original AST. No real Docker/HTTP/credential mutation."""
import ast,json,uuid,urllib.request,urllib.error,tempfile,time,os
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[4];SRC=ROOT/'scripts/bh07_reset/run_full_reset.py'
tree=ast.parse(SRC.read_text());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');block=next(n for n in main.body if isinstance(n,ast.Try));outputs={}

def compile_nodes(nodes,name='fragment'):
 fn=ast.FunctionDef(name=name,args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=nodes,decorator_list=[])
 return compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(SRC),'exec')
# A: execute complete negative-control block, with transport stub and real local guard.
idx=next(i for i,n in enumerate(block.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='neg_results' for t in n.targets));code=compile_nodes(block.body[idx:])
http_def=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='http_request');guardenv={'urllib':urllib,'json':json,'OPENER':None};exec(compile(ast.Module(body=[http_def],type_ignores=[]),str(SRC),'exec'),guardenv)
neg=[]
for case in ['positive','generic_invalid_input','outsider_not_found','gateway_route_missing']:
 def fake_http(url,body=None,headers=None,**kw):
  if '192.168.' in url:return guardenv['http_request'](url)
  if '/token?' in url:return 200,{'access_token':'synthetic-token'}
  if case=='generic_invalid_input':return 400,{'code':'INVALID_INPUT','message':'invalid input'}
  if '/get_session_summary' in url:
   return (403,{'code':'NOT_FOUND','message':'NOT_FOUND'}) if case=='outsider_not_found' else (403,{'code':'FORBIDDEN','message':'FORBIDDEN'})
  if not headers:return (404,{'message':'route does not exist'}) if case=='gateway_route_missing' else (401,{'message':'No API key found in request'})
  return 401,{'code':'42501','message':'permission denied for function complete_session'}
 env={'http_request':fake_http,'api_url':'http://127.0.0.1:56421','anon_key':'synthetic-anon','uuid':uuid,'json':json,'print':lambda *a,**kw:None,'audit_results':{},'write_evidence':lambda *a:None}
 exec(code,env);env['fragment']();accepted=all(x['rejected'] for x in env['audit_results']['negative_controls'])
 neg.append({'case':case,'expected_accept':case=='positive','actual_accept':accepted})
assert neg[0]['actual_accept'] and all(x['actual_accept'] for x in neg[1:]);outputs['negative_error_controls']=neg
# B: exact finalbody with stopped-container and retained-temp faults.
cleanup=[]
for case in ['positive','stopped_container_left','private_directory_left']:
 with tempfile.TemporaryDirectory(prefix='v5b-review-fake-') as td:
  work=Path(td)/'work';work.mkdir();(work/'synthetic.txt').write_text('no secrets')
  def cmd(args,**kw):
   if args[:3]==['docker','ps','-q']:
    return SimpleNamespace(returncode=0,stdout='',stderr='') # stopped container not listed without -a
   return SimpleNamespace(returncode=0,stdout='',stderr='')
  env={'run_cmd':cmd,'temp_dir':work,'exits':{},'stop_log':'','write_evidence':lambda *a:None,'log_cmd':lambda *a:None,'audit_results':{},'CONTAINER_DB':'synthetic','PROJECT_ID':'synthetic-project','print':lambda *a,**kw:None,'shutil':SimpleNamespace(rmtree=(lambda p,**kw:None) if case=='private_directory_left' else __import__('shutil').rmtree)}
  exec(compile_nodes(block.finalbody),env);env['fragment']();actual=env['audit_results']['cleanup']['remaining_containers_count']==0
  cleanup.append({'case':case,'expected_success':case=='positive','reported_remaining_containers':env['audit_results']['cleanup']['remaining_containers_count'],'stopped_container_represented':case=='stopped_container_left','private_path_still_exists':work.exists(),'actual_cleanup_success':actual})
assert all(x['actual_cleanup_success'] for x in cleanup) and cleanup[-1]['private_path_still_exists'];outputs['cleanup_controls']=cleanup
# C: original main on an already-existing dedicated project. Abort at first reset.
class StopAtReset(Exception):pass
with tempfile.TemporaryDirectory(prefix='v5b-review-owned-') as td:
 calls=[];state={'preexisting_project':True}
 def cmd(args,**kw):
  calls.append(args)
  if args[:3]==['npx','supabase','db']:raise StopAtReset('reset would target pre-existing project')
  if args[:3]==['npx','supabase','stop']:state['stop_targeted_existing_project']=True
  if args[:3]==['npx','supabase','status']:return SimpleNamespace(returncode=0,stdout=json.dumps({'API_URL':'http://127.0.0.1:56421','ANON_KEY':'synthetic-anon','SERVICE_ROLE_KEY':'synthetic-service'}),stderr='')
  return SimpleNamespace(returncode=0,stdout='' if args[:3]==['git','status','--porcelain'] or args[:2]==['docker','ps'] else 'synthetic-version',stderr='')
 env={'print':lambda *a,**kw:None,'STAMP':'synthetic','BASE_SHA':'synthetic','PROJECT_ID':'synthetic-project','PORT_API':56421,'PORT_DB':56422,'PORT_STUDIO':56423,'PORT_POOLER':56429,'run_cmd':cmd,'Path':Path,'tempfile':SimpleNamespace(gettempdir=lambda:td),'os':os,'prepare_project_dir':lambda p:p.mkdir(parents=True),'log_cmd':lambda *a:None,'exits':{},'write_evidence':lambda *a:None,'json':json,'urllib':urllib,'audit_results':{},'shutil':__import__('shutil')}
 exec(compile(ast.Module(body=[main],type_ignores=[]),str(SRC),'exec'),env)
 try:env['main']()
 except StopAtReset:pass
 reset=any(a[:3]==['npx','supabase','db'] for a in calls);assert reset and state['stop_targeted_existing_project']
 outputs['ownership_control']={'preexisting_project':True,'reset_was_attempted':reset,'stop_was_attempted':True,'preflight_container_inspect_before_start':any(a[:2]==['docker','inspect'] for a in calls)}
# D: original failure is replaced if stop fails, and private path is never removed.
class OriginalRunFailure(Exception):pass
class CleanupStopFailure(Exception):pass
with tempfile.TemporaryDirectory(prefix='v5b-review-stop-') as td:
 calls=[]
 def stop_failure_cmd(args,**kw):
  calls.append(args)
  if args[:3]==['npx','supabase','start']:raise OriginalRunFailure('synthetic original failure')
  if args[:3]==['npx','supabase','stop']:raise CleanupStopFailure('synthetic cleanup failure')
  return SimpleNamespace(returncode=0,stdout='' if args[:2]==['git','status'] else 'synthetic-version',stderr='')
 env.update({'run_cmd':stop_failure_cmd,'tempfile':SimpleNamespace(gettempdir=lambda:td),'prepare_project_dir':lambda p:p.mkdir(parents=True)})
 try:env['main']()
 except CleanupStopFailure:observed='CleanupStopFailure'
 else:observed='unexpected'
 assert observed=='CleanupStopFailure'
 outputs['stop_failure_control']={'original_error':'OriginalRunFailure','reported_error':observed,'private_path_remains':(Path(td)/('bh07_reset_project_'+str(os.getpid()))).exists(),'docker_postcheck_attempted':any(a[:2]==['docker','ps'] for a in calls)}
print(json.dumps(outputs,indent=2))
