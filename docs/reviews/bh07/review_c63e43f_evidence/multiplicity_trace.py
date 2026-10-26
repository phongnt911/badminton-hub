"""Read-only parser/validator boundary check. Run from repository root."""
import importlib.util,json
from pathlib import Path
root=Path.cwd();spec=importlib.util.spec_from_file_location('heap_runner',root/'scripts/bh07_heap/run_heap_verification.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
events=[]
for line in (Path(__file__).resolve().parent/'runner_output/heap_test_run.log').read_text().splitlines():
 try:e=json.loads(line)
 except ValueError:continue
 if isinstance(e,dict) and 'type' in e:events.append(e)
first=next(e['test']['name'] for e in events if e['type']=='testStart' and e['test']['name'].endswith(next(iter(r.EXPECTED_TESTS))))
events[-1:-1]=[{'type':'testStart','test':{'id':999,'name':first}},{'type':'testDone','testID':999,'result':'success','skipped':False,'hidden':False}]
records,protocol=r._parse_json_events('\n'.join(json.dumps(e) for e in events))
assert protocol and len(records)==8 and len({row['id'] for row in records})==8
same=[row for row in records if row['name']==first];assert len(same)==2
result=r._verdict_from_results(records,True);assert result['suite_verdict']=='FAIL' and result['identity_coverage']!='VERIFIED' and result['tests_passed']<=7 and any('testID 999' in x for x in result['tests_duplicate'])
print(json.dumps({'records_before_validator':len(records),'distinct_test_ids':len({row['id'] for row in records}),'same_full_name_records':same,'validator_result':result},indent=2))
