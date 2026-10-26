"""Protocol replay controls; no implementation/author evidence mutation."""
import contextlib,copy,importlib.util,io,json,tempfile
from pathlib import Path
ROOT=Path.cwd();s=importlib.util.spec_from_file_location('heap_runner',ROOT/'scripts/bh07_heap/run_heap_verification.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
scratch=Path(__file__).resolve().parent
raw=(scratch/'runner_output/heap_test_run.log').read_text()
# Runner adds one capture header; remaining text is the command stdout.
raw=raw.split('\n',1)[1]
events=[]
for line in raw.splitlines():
 try:e=json.loads(line)
 except (ValueError,TypeError):continue
 if isinstance(e,dict) and 'type' in e:events.append(e)
json_only='\n'.join(json.dumps(e) for e in events)+'\n'
report={'real_full_runner_raw':r.parse_test_results(True,raw),'same_run_json_only_positive':r.parse_test_results(True,json_only)}
starts={e['test']['id']:e['test']['name'] for e in events if e['type']=='testStart'}
expected_done=[e for e in events if e['type']=='testDone' and not e.get('hidden') and any(starts.get(e['testID'],'').endswith(n) for n in r.EXPECTED_TESTS)]
assert len(expected_done)==7 and all(e['result']=='success' and not e.get('skipped') for e in expected_done)
real_skip=[]
for line in (scratch/'real_skipped_events.log').read_text().splitlines():
 try:e=json.loads(line)
 except ValueError:continue
 if e.get('type')=='testDone' and e.get('skipped'):real_skip.append(e)
assert len(real_skip)==1 and real_skip[0]['result']=='success'
report['real_flutter_skip_protocol']=real_skip[0]
# Same seven real test identities; mark M1 skipped using real Flutter protocol.
skipped=copy.deepcopy(events);target=next(i for i,n in starts.items() if n.endswith('Mutant Control M1: Static/global strong reference leak is reliably caught by Oracle'))
for e in skipped:
 if e['type']=='testDone' and e['testID']==target:e.update(result='success',skipped=True)
 if e['type']=='testStart' and e['test']['id']==target:e['test']['metadata']['skip']=True
skipped_output='\n'.join(json.dumps(e) for e in skipped)+'\n'
report['one_real_protocol_skip']=r.parse_test_results(True,skipped_output)
# Extra unrecognized test is not allowed to claim exactly seven verified identities.
extra=copy.deepcopy(events);extra[-1:-1]=[{'type':'testStart','test':{'id':999,'name':'unrecognized extra test'}},{'type':'testDone','testID':999,'result':'success','skipped':False,'hidden':False}]
extra_output='\n'.join(json.dumps(e) for e in extra)+'\n'
report['unknown_extra_identity']=r.parse_test_results(True,extra_output)
with tempfile.TemporaryDirectory(prefix='v2b-protocol-') as d:
 r.EVIDENCE_DIR=d
 Path(d,'ast_memory_audit.json').write_text(json.dumps({'overall_ast_verdict':'CLEAN','static_mutable_collections_found':0,'providers_lifecycle_audit':{}}))
 for name,output in [('skip',skipped_output),('unknown_extra',extra_output)]:
  with contextlib.redirect_stdout(io.StringIO()):r.generate_summary('f7922ed63f7594ace19daa8b999712fd849f0dbe',False,{'os':'synthetic'},True,True,output)
  report[name+'_markdown_claims_7_of_7']='7/7 Provider test PASS' in Path(d,'heap_verification_report.md').read_text()
print(json.dumps(report,indent=2))
