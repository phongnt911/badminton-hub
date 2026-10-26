"""Independent relation checks requested by the AH9 handoff; no source mutations."""
import copy,json
from tests.test_bh07_app_heap_oracle import ORACLE
base={'ok':True,'sentinels':{'bank':{'present':False,'occurrences':0},'probe':{'present':True,'occurrences':1}}}
expect={'baseline':{'bank':False,'probe':True}}
cases=[]
for name,field,value in [('float_integral','occurrences',1.0),('integer_presence_zero','present',0),('integer_presence_one','present',1)]:
 s=copy.deepcopy(base);s['sentinels']['probe'][field]=value;cases.append((name,s,'FAIL'))
s=copy.deepcopy(base);s['ok']=False;cases.append(('unusable_claims_presence',s,'FAIL'))
s=copy.deepcopy(base);s['sentinels']['probe']['occurrences']=1000;cases.append(('large_valid_count',s,'PASS'))
results={}
for name,s,want in cases:
 verdict=ORACLE.decide({'baseline':s},expect,True,'profile');assert verdict['verdict']==want,(name,verdict)
 results[name]={'expected':want,'actual':verdict,'scan_problems':ORACLE.scan_problems(s)}
print(json.dumps(results,indent=2))
