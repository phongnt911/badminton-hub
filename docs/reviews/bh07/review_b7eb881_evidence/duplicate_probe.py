"""Replay real protocol events; duplicate fixtures mutate temp data only."""
import contextlib,copy,importlib.util,io,json,tempfile
from pathlib import Path
FIXTURE=Path(__file__).resolve().parent/'runner_output'
ROOT=Path.cwd();s=importlib.util.spec_from_file_location('heap_runner',ROOT/'scripts/bh07_heap/run_heap_verification.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
events=[]
for line in (FIXTURE/'heap_test_run.log').read_text().splitlines():
 try:e=json.loads(line)
 except ValueError:continue
 if isinstance(e,dict) and 'type' in e:events.append(e)
first=next(e['test']['name'] for e in events if e['type']=='testStart' and e['test']['name'].endswith(next(iter(r.EXPECTED_TESTS))))
def render(data):return '\n'.join(json.dumps(e) for e in data)+'\n'
base=r.parse_test_results(True,render(events));assert base['suite_verdict']=='PASS'
out={'positive_real_seven':base}
names={e['test']['id']:e['test']['name'] for e in events if e['type']=='testStart'}
missing=[e for e in copy.deepcopy(events) if not (e['type']=='testDone' and names.get(e.get('testID'))==first)]
out['missing_expected_testDone']=r.parse_test_results(True,render(missing))
for case,name in [('different_group_duplicate','Other group '+next(iter(r.EXPECTED_TESTS))),('exact_full_name_duplicate',first)]:
 rows=copy.deepcopy(events);rows[-1:-1]=[{'type':'testStart','test':{'id':999,'name':name}},{'type':'testDone','testID':999,'result':'success','skipped':False,'hidden':False}]
 output=render(rows);parsed=r.parse_test_results(True,output)
 with tempfile.TemporaryDirectory(prefix='v2b-exact-dup-') as d:
  r.EVIDENCE_DIR=d;Path(d,'ast_memory_audit.json').write_text((FIXTURE/'ast_memory_audit.json').read_text())
  with contextlib.redirect_stdout(io.StringIO()):r.generate_summary('16e5b5116738ab9d4417fe11b651aea794868401',False,{'os':'synthetic'},True,True,output)
  report=Path(d,'heap_verification_report.md').read_text()
  detail={'parsed':parsed,'markdown_claims_7_of_7':'7/7 Provider test PASS' in report,'visible_test_done_count':sum(e['type']=='testDone' and not e.get('hidden') for e in rows)}
  # Main-boundary control only: external commands are stubs; not a second real runner.
  r.get_git_info=lambda:('16e5b5116738ab9d4417fe11b651aea794868401',False,[],json.loads((FIXTURE/'summary.json').read_text())['source_hashes'])
  r.get_env_info=lambda:{'os':'synthetic','flutter_version':'synthetic'}
  r.run_ast_audit=lambda:True;r.run_heap_tests=lambda:(True,output);r.generate_and_verify_manifest=lambda:True
  with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):detail['main_boundary_control_exit']=r.main()
 out[case]=detail
print(json.dumps(out,indent=2))
