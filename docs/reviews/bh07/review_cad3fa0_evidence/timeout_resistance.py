import subprocess,sys,os,signal,json
worker=r'''
import ast,subprocess,shutil,sys,signal
from pathlib import Path
from types import SimpleNamespace
signal.signal(signal.SIGTERM,signal.SIG_IGN)
p=Path('scripts/bh07_reset/run_full_reset.py');t=ast.parse(p.read_text());e=dict(subprocess=subprocess,shutil=shutil,sys=sys,ROOT=Path.cwd(),SimpleNamespace=SimpleNamespace)
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in ('run_cmd','kill_proc_tree')],type_ignores=[]),str(p),'exec'),e)
e['run_cmd']([sys.executable,'-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)'],timeout=.2)
'''
p=subprocess.Popen([sys.executable,'-c',worker],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
try:
 o,e=p.communicate(timeout=2);r={'bounded':True,'exit':p.returncode}
except subprocess.TimeoutExpired:
 os.killpg(p.pid,signal.SIGKILL);o,e=p.communicate(timeout=2);r={'bounded':False,'requested_timeout_seconds':.2,'supervisor_deadline_seconds':2,'supervisor_killed_only_own_probe_group':True,'returncode_after_forced_cleanup':p.returncode}
print(json.dumps(r,indent=2))
