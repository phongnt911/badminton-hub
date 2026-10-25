import ast,contextlib,copy,io,json,os,subprocess,sys,tempfile,unittest,runpy
from pathlib import Path
ROOT=Path.cwd(); src=ROOT/'scripts/bh07_reset/run_full_reset.py'; tree=ast.parse(src.read_text()); results={}
def load(names,env):
 exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),str(src),'exec'),env);return env
mod=runpy.run_path(str(ROOT/'tests/test_v5b_runner_flaws.py'));cls=mod['TestV5bRunnerBehavior']
suite=unittest.TestSuite(cls(n) for n in unittest.defaultTestLoader.getTestCaseNames(cls) if 'p2_7' not in n)
s=io.StringIO();r=unittest.TextTestRunner(stream=s,verbosity=2).run(suite);print(s.getvalue());results['remaining_tests']={'run':r.testsRun,'failures':len(r.failures),'errors':len(r.errors)}
# Timeout must only kill an isolated child group. Actual source does not isolate it.
e=load(['kill_proc_tree','run_cmd'],{'sys':sys,'subprocess':subprocess,'shutil':__import__('shutil'),'ROOT':ROOT,'SimpleNamespace':__import__('types').SimpleNamespace})
e['kill_proc_tree']=lambda pid:results.update(timeout_group={'runner_group':os.getpgrp(),'child_group':os.getpgid(pid),'same_group':os.getpgrp()==os.getpgid(pid)}) or os.kill(pid,15)
try:e['run_cmd']([sys.executable,'-c','import time;time.sleep(10)'],timeout=.1)
except TimeoutError:results['timeout_error_with_safe_probe_cleanup']=True
# The real SQL helpers bypass run_cmd timeout.
class Sub:
 def run(self,*a,**kw):
  results.setdefault('sql_calls',[]).append({'timeout_provided':'timeout' in kw,'shell':kw.get('shell',False)})
  return __import__('types').SimpleNamespace(returncode=0,stdout='',stderr='')
e=load(['sql_run','sql_as'],{'subprocess':Sub(),'CONTAINER_DB':'synthetic','sql':lambda *a,**k:'fake-uid'})
e['sql_run']('select 1');e['sql_as']('synthetic@example.test','select 1')
# Authored exact-value test remains green after an incorrect exact target mutation.
mut=src.read_text().replace('pay_cnt == 2','pay_cnt == 999')
old=cls.source_text;oldt=cls.tree;cls.source_text=mut;cls.tree=ast.parse(mut)
try:cls('test_p2_5_db_assertions_exact_fixture_and_req_orig_deterministic').test_p2_5_db_assertions_exact_fixture_and_req_orig_deterministic();results['wrong_exact_target_mutant_accepted_by_authored_test']=True
except AssertionError:results['wrong_exact_target_mutant_accepted_by_authored_test']=False
finally:cls.source_text=old;cls.tree=oldt
print(json.dumps(results,indent=2));Path(__file__).with_name('probes.json').write_text(json.dumps(results,indent=2))
