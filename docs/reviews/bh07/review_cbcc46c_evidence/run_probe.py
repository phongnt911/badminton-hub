from pathlib import Path
import json,subprocess,os
p=json.loads(Path('/tmp/bh07-http-review-runtime/kong.json').read_text());keys={x['username']:x['keyauth_credentials'][0]['key'] for x in p['consumers']}
env=dict(os.environ,BH07_HTTP_URL='http://127.0.0.1:54321',BH07_HTTP_ANON_KEY=keys['anon'],BH07_HTTP_SERVICE_ROLE_KEY=keys['service_role'])
with open('/workspace/scratch/bh07-review-cbcc46c/probes.log','w') as f:
 r=subprocess.run(['/workspace/toolchains/flutter-review-3.47.7/bin/flutter','test','--no-pub','test/integration/reviewer_concurrency_probe_test.dart','--reporter','expanded'],env=env,stdout=f,stderr=subprocess.STDOUT)
Path('/workspace/scratch/bh07-review-cbcc46c/probes-exit.txt').write_text(str(r.returncode)+'\n')
