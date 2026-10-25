"""Run from repository root; AST controls do not change implementation files."""
import ast,json,os,signal,subprocess,sys,tempfile,time,shutil
from pathlib import Path
from types import SimpleNamespace
p=Path('scripts/bh07_reset/run_full_reset.py');tree=ast.parse(p.read_text());out={}
def load(names,env):
 exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),str(p),'exec'),env);return env
base=dict(shutil=shutil,subprocess=subprocess,sys=sys,ROOT=Path.cwd(),SimpleNamespace=SimpleNamespace)
e=load(['kill_proc_tree','run_cmd'],base.copy())
with tempfile.TemporaryDirectory(prefix='v5b-review-owned-') as d:
 f=Path(d)/'ids.json'
 child='import os,signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)'
 parent='import subprocess,sys,json,os,time,signal; signal.signal(signal.SIGTERM,signal.SIG_IGN);p=subprocess.Popen([sys.executable,"-c",sys.argv[2]]);open(sys.argv[1],"w").write(json.dumps([os.getpid(),p.pid,os.getpgrp()]));time.sleep(60)'
 t=time.monotonic()
 try:e['run_cmd']([sys.executable,'-c',parent,str(f),child],timeout=.5)
 except TimeoutError:out['timeout_raised']=True
 elapsed=time.monotonic()-t
 ids=json.loads(f.read_text());states={}
 for pid in ids[:2]:
  status=Path(f'/proc/{pid}/stat')
  states[str(pid)]=status.read_text().split()[2] if status.exists() else 'absent'
 out['parent_and_grandchild']={'elapsed_seconds':elapsed,'runner_group':os.getpgrp(),'command_group':ids[2],'group_isolated':ids[2]!=os.getpgrp(),'post_timeout_states':states,'all_not_running':all(s in ('Z','absent') for s in states.values())}
 if any(s not in ('Z','absent') for s in states.values()):os.killpg(ids[2],signal.SIGKILL)
 assert out['parent_and_grandchild']['group_isolated'] and out['parent_and_grandchild']['all_not_running'] and elapsed<4
calls=[]
def fake_run(args,**kw):
 calls.append({'timeout':kw.get('timeout'),'check':kw.get('check',True),'stdin_supplied':'input_text' in kw})
 return SimpleNamespace(stdout='fake-uid',stderr='',returncode=0)
e=load(['sql','sql_run','sql_as'],{'run_cmd':fake_run,'CONTAINER_DB':'synthetic'})
e['sql']('SELECT 1');e['sql_run']('SELECT 1');e['sql_as']('synthetic@example.test','SELECT 1')
out['sql_calls']=calls;assert len(calls)==4 and all(c['timeout']==60 for c in calls)
e=load(['resolve_base_review'],load(['kill_proc_tree','run_cmd'],base.copy()))
actual='a55c2d2416f37a0bb8ac985e80bdee579b40774b';requested='a55c2d22b27bc89d53f58a74b0fa038ff31c0396'
out['actual_base_resolves']=e['resolve_base_review'](['--base-review',actual])==actual
try:e['resolve_base_review'](['--base-review',requested]);out['invalid_requested_base_rejected']=False
except ValueError:out['invalid_requested_base_rejected']=True
assert out['actual_base_resolves'] and out['invalid_requested_base_rejected']
print(json.dumps(out,indent=2))
