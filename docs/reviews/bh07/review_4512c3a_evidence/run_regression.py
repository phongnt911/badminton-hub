import subprocess,os,json,concurrent.futures
from pathlib import Path
root=Path('/workspace/badminton-hub'); out=Path('/workspace/scratch/bh07-review-4512c3a')
env=dict(os.environ,BH02_TEST_CONTAINER='bh02-review-bh06')
groups=[['bh02/run_rls_tests.py','bh02/extended_tests_15ef59b.py'],['bh03/run_bh03_tests.py','bh03/run_bh03_retry_tests.py'],['bh04/run_bh04_tests.py'],['bh05/run_bh05_tests.py'],['bh06/run_bh06_tests.py'],['bh07/run_bh07_tests.py'],['bh06/integration_evidence/run_integration_tests.py'],['bh06/integration_evidence/run_upgrade_tests.py']]
def group(paths):
 result=[]
 for p in paths:
  name=Path(p).stem
  with (out/(name+'.log')).open('w') as f:
   r=subprocess.run(['python3',str(root/'docs/reviews'/p)],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
  result.append({'script':p,'exit':r.returncode})
  if r.returncode: break
 return result
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 results=list(pool.map(group,groups))
(out/'regression-exits.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results))
