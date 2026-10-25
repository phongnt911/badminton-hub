"""Read-only audit; never regenerates or writes an author manifest."""
import hashlib,json,re,subprocess
from pathlib import Path
base=Path('docs/reviews/bh07')
names=['full_reset_p2_fix_evidence','full_reset_evidence','codex_v5b_fix_evidence','review_8e26e06_evidence','review_19ab207_evidence','review_3b515f2_evidence']
def snapshot(d):return {str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest() for p in d.rglob('*') if p.is_file()}
results={}
for name in names:
 d=base/name;before=snapshot(d);result={}
 manifests=['hashes.sha256']+(['bundle_hashes.sha256'] if (d/'bundle_hashes.sha256').exists() else [])
 for m in manifests:
  entries={line.split('  ',1)[1]:line.split('  ',1)[0] for line in (d/m).read_text(encoding='utf-8').splitlines()}
  missing=[p for p in entries if not (d/p).is_file()]
  mismatch=[p for p,h in entries.items() if (d/p).is_file() and hashlib.sha256((d/p).read_bytes()).hexdigest()!=h]
  result[m]={'entries':len(entries),'present_matching':len(entries)-len(missing)-len(mismatch),'missing':missing,'mismatch':mismatch}
 defects=[];secret_files=[]
 for p in d.iterdir():
  if not p.is_file():continue
  raw=p.read_bytes()
  try:txt=raw.decode('utf-8')
  except UnicodeDecodeError:defects.append({'file':p.name,'invalid_utf8':True});continue
  if raw.startswith(b'\xef\xbb\xbf') or b'\r' in raw:defects.append({'file':p.name,'bom':raw.startswith(b'\xef\xbb\xbf'),'cr_count':raw.count(b'\r'),'crlf_count':raw.count(b'\r\n')})
  if re.search(r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}|sb_secret_[A-Za-z0-9_-]+|bh07-http-pass-123456|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY',txt):secret_files.append(p.name)
 result['encoding_defects']=defects;result['secret_pattern_files']=secret_files
 if name!='full_reset_p2_fix_evidence':result['changed_since_review_base']=bool(subprocess.check_output(['git','diff','--name-only','e00db30..55716e2','--',str(d)],text=True))
 after=snapshot(d);result['before_after_equal']=before==after;result['directory_fingerprint_before']=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest();result['directory_fingerprint_after']=hashlib.sha256(json.dumps(after,sort_keys=True).encode()).hexdigest()
 results[name]=result
print(json.dumps(results,indent=2))
