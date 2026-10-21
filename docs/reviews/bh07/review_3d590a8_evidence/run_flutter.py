import subprocess,os,json
from pathlib import Path
out=Path('/workspace/scratch/bh07-review-3d590a8')
f='/workspace/toolchains/flutter-review-3.47.7/bin/flutter'
c=['test/screens/session_finance_screen_test.dart','test/screens/session_history_screen_test.dart','test/screens/session_summary_screen_test.dart','test/screens/session_detail_screen_test.dart']
d=['test/integration/bh07_full_flow_test.dart']
checks=[('analyze',[f,'analyze'],None),('flutter',[f,'test'],None),('d_utc',[f,'test']+d,'UTC'),('d_vietnam',[f,'test']+d,'Asia/Ho_Chi_Minh'),('c_utc',[f,'test']+c,'UTC'),('c_vietnam',[f,'test']+c,'Asia/Ho_Chi_Minh')]
results=[]
for name,cmd,tz in checks:
 env=dict(os.environ)
 if tz:env['TZ']=tz
 with (out/(name+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 results.append({'name':name,'command':cmd,'TZ':tz,'exit':r.returncode})
 (out/'flutter-exits.json').write_text(json.dumps(results,indent=2))
 print(name,r.returncode,flush=True)
