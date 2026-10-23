"""Execute original cleanup/exit AST with failed cleanup; no real secrets/Docker."""
import ast,json,tempfile,time,shutil
from pathlib import Path
from types import SimpleNamespace
SOURCE=Path(__file__).resolve().parents[4] / 'scripts/bh07_backup/run_local_rehearsal.py'
tree=ast.parse(SOURCE.read_text()); main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
block=next(n for n in main.body if isinstance(n,ast.Try))
probe=ast.FunctionDef(name='probe',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=block.finalbody+[main.body[-1]],decorator_list=[])
code=compile(ast.fix_missing_locations(ast.Module(body=[probe],type_ignores=[])),str(SOURCE),'exec')
results=[]
for case, docker_ok, files_ok in [('positive',True,True),('private_cleanup_failure',True,False),('docker_cleanup_failure',False,True)]:
 with tempfile.TemporaryDirectory(prefix='bh07-review-cleanup-') as d:
  root=Path(d);private=root/'private';private.mkdir();(private/'fake.dump').write_text('synthetic data only');out=root/'out';out.mkdir()
  summary={'status':'PASS local rehearsal; pending review','checks':[{'pass':True}]}
  def fake_cmd(args,**kwargs): return SimpleNamespace(returncode=0 if docker_ok else 1)
  cleanup=shutil if files_ok else SimpleNamespace(rmtree=lambda *a,**kw:None)
  env={'cmd':fake_cmd,'owned':['synthetic-target'],'NETWORK':'synthetic-network','shutil':cleanup,'private':private,'summary':summary,'time':time,'started':time.monotonic(),'out':out,'json':json}
  exec(code,env);exit_code=env['probe']()
  assert exit_code==0
  assert summary['private_dumps_keys_removed']==files_ok
  results.append({'case':case,'docker_cleanup_success':docker_ok,'private_dumps_keys_removed':summary['private_dumps_keys_removed'],'actual_exit':exit_code,'expected_exit_zero':case=='positive','verdict':'PASS control' if case=='positive' else 'FAIL gate reproduced'})
print(json.dumps(results,indent=2))
