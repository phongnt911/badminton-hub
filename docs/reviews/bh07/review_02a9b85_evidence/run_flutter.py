import subprocess,os,json
from pathlib import Path
out=Path('/workspace/scratch/bh07-review-02a9b85')
flutter='/workspace/toolchains/flutter-review-3.47.7/bin/flutter'
files=['test/core/session_summary_text_test.dart','test/core/time_utils_test.dart','test/screens/session_summary_screen_test.dart','test/screens/session_history_screen_test.dart','test/screens/session_finance_screen_test.dart','test/screens/session_detail_screen_test.dart','test/screens/sessions_screen_test.dart']
checks=[('analyze',[flutter,'analyze','--no-pub'],None),('flutter',[flutter,'test','--no-pub'],None),('targeted_utc',[flutter,'test','--no-pub']+files,'UTC'),('targeted_vietnam',[flutter,'test','--no-pub']+files,'Asia/Ho_Chi_Minh')]
results=[]
for name,cmd,tz in checks:
 env=dict(os.environ)
 if tz: env['TZ']=tz
 with (out/(name+'.log')).open('w') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
 results.append({'name':name,'command':cmd,'TZ':tz,'exit':r.returncode})
 (out/'flutter-exits.json').write_text(json.dumps(results,indent=2))
 print(name,r.returncode,flush=True)
