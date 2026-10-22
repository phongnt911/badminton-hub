import json,subprocess
from pathlib import Path
p=json.loads(Path('/tmp/bh07-http-review-runtime/kong.json').read_text());anon=p['consumers'][0]['keyauth_credentials'][0]['key']
with open('/workspace/scratch/bh07-review-b00b580/build-web.log','w') as f:r=subprocess.run(['/workspace/toolchains/flutter-review-3.47.7/bin/flutter','build','web','--no-pub','--no-web-resources-cdn','--dart-define=APP_ENV=test','--dart-define=SUPABASE_URL=http://127.0.0.1:54321','--dart-define=SUPABASE_ANON_KEY='+anon],stdout=f,stderr=subprocess.STDOUT)
Path('/workspace/scratch/bh07-review-b00b580/build-web-exit.txt').write_text(str(r.returncode)+'\n')
