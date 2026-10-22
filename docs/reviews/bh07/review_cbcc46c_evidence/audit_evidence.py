from pathlib import Path
import json,re,hashlib,subprocess
root=Path('/workspace/badminton-hub');out=Path('/workspace/scratch/bh07-review-cbcc46c');ev=root/'docs/reviews/bh07/http_concurrency_evidence'
def decoded(b):return b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
patterns={'JWT':r'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}','SupabaseKey':r'sb_(?:secret|publishable)_[A-Za-z0-9_-]{10,}','PrivateKey':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'}
hits=[];files=0
for p in ev.iterdir():
 if p.is_file():
  files+=1;s=decoded(p.read_bytes())
  for kind,pat in patterns.items():
   if re.search(pat,s):hits.append({'path':str(p.relative_to(root)),'kind':kind})
(out/'secret-scan.json').write_text(json.dumps({'author_files_scanned':files,'decode_UTF16_before_scan':True,'hits':hits},indent=2)+'\n')
old=json.loads((root/'docs/reviews/bh07/review_2f0aa59_evidence/http-summary.json').read_text());new=json.loads((out/'http/summary.json').read_text());a={x['id'] for x in old['checks']};b={x['id'] for x in new['checks']}
(out/'coverage-delta.json').write_text(json.dumps({'retained':len(a&b),'removed':sorted(a-b),'added':sorted(b-a),'checks_total':new['counts']},indent=2)+'\n')
p='test/integration/bh07_http_auth_test.dart';blob=subprocess.check_output(['git','show','cbcc46c:'+p]);working=(root/p).read_bytes();(out/'source-hashes.json').write_text(json.dumps({'path':p,'tested_source_sha':'cbcc46c2e125b156b53f4297ef864cf658855d37','blob_sha256':hashlib.sha256(blob).hexdigest(),'checkout_sha256':hashlib.sha256(working).hexdigest(),'matches':blob==working},indent=2)+'\n')
print('Author secret scan hits:',len(hits));print('Retained IDs:',len(a&b))
