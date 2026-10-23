"""Run current finally/return AST with real Docker missing-context stderr.
No real resource or credential is created; Docker stub represents existing owned resources.
"""
import runpy,tempfile,json,time,shutil,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
ns=runpy.run_path(str(ROOT/'scripts/bh07_backup/cleanup_probe.py'))
env=os.environ.copy();env['DOCKER_CONTEXT']='bh07-review-missing-context'
real=subprocess.run(['docker','inspect','synthetic-container'],capture_output=True,env=env)
assert real.returncode!=0 and b'context not found' in real.stderr
code=ns['load_probe']();Base=ns['FakeDocker'];results=[]
for case,inspect_error in [('positive',None),('daemon_error',b'Cannot connect to the Docker daemon'),('missing_context_error',real.stderr)]:
 class Docker(Base):
  def __call__(self,args,**kwargs):
   if inspect_error and (args[:2]==['docker','inspect'] or args[:3]==['docker','network','inspect']):return self.result(1,inspect_error)
   return super().__call__(args,**kwargs)
 with tempfile.TemporaryDirectory(prefix='bh07-inspect-probe-') as tmp:
  root=Path(tmp);private=root/'private';private.mkdir();out=root/'out';out.mkdir()
  docker=Docker(['synthetic-owned']);summary={'status':'PASS local rehearsal; pending review','checks':[{'pass':True}]}
  scope={'cmd':docker,'owned':['synthetic-owned'],'NETWORK':'synthetic-network','shutil':shutil,'private':private,'summary':summary,'time':time,'started':time.monotonic(),'out':out,'json':json}
  exec(code,scope);status=scope['probe']()
  results.append({'case':case,'expected_exit_zero':case=='positive','actual_exit':status,'summary':summary,'remaining_container_count':len(docker.containers),'network_remaining':docker.network,'rm_calls':docker.rm_calls,'ok':(status==0)==(case=='positive')})
print(json.dumps({'actual_docker_error':real.stderr.decode().strip(),'controls':results},indent=2))
assert results[0]['ok'] and results[1]['ok'] and not results[2]['ok']
assert results[2]['remaining_container_count']==1 and results[2]['network_remaining']
