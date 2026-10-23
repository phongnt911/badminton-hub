from pathlib import Path
import shutil,subprocess,hashlib,json,base64,hmac
root=Path('/workspace/badminton-hub');out=Path('/workspace/scratch/bh07-review-eadb5c7');src=root/'scripts/bh07_browser/clean_and_manifest.py';original=root/'docs/reviews/bh07/browser_evidence';results=[]
def snap(ev):return {str(p.relative_to(ev)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ev.rglob('*') if p.is_file()}
for name in ['baseline','missing','hash_mismatch','fake_sb_secret','fake_service_role_JWT','invalid_UTF8']:
 case=out/'verifier-cases'/name;script=case/'scripts/bh07_browser/clean_and_manifest.py';script.parent.mkdir(parents=True,exist_ok=True);shutil.copy(src,script);ev=case/'docs/reviews/bh07/browser_evidence';shutil.copytree(original,ev,dirs_exist_ok=True);manifest=ev/'hashes.sha256'
 if name=='missing':(ev/'analyze.log').unlink()
 if name=='hash_mismatch':(ev/'analyze.log').write_bytes((ev/'analyze.log').read_bytes()+b'changed\n')
 if name in ['fake_sb_secret','fake_service_role_JWT','invalid_UTF8']:
  if name=='fake_sb_secret':raw=b'sb_' + b'secret_REVIEW_CONTROL_FAKE_NOT_A_REAL_CREDENTIAL\n'
  elif name=='fake_service_role_JWT':
   enc=lambda d:base64.urlsafe_b64encode(json.dumps(d,separators=(',',':')).encode()).rstrip(b'=')
   message=enc({'alg':'HS256','typ':'JWT'})+b'.'+enc({'role':'service_role','iss':'synthetic-review-only','exp':1})
   raw=message+b'.'+base64.urlsafe_b64encode(hmac.new(b'NONFUNCTIONAL-REVIEW-CONTROL',message,hashlib.sha256).digest()).rstrip(b'=')+b'\n'
  else:raw=b'invalid UTF8 control: \xff\n'
  (ev/'commands.md').write_bytes(raw);lines=[]
  for line in manifest.read_text().splitlines():
   h,p=line.split('  ')
   if p=='commands.md':h=hashlib.sha256(raw).hexdigest()
   lines.append(h+'  '+p)
  manifest.write_text('\n'.join(lines)+'\n')
 before=snap(ev);before_manifest=manifest.read_bytes()
 r=subprocess.run(['python',str(script),'--verify'],capture_output=True,text=True)
 (out/(name+'-verify.log')).write_text(r.stdout+r.stderr)
 after=snap(ev);expected=0 if name=='baseline' else 1
 results.append({'case':name,'expected_zero_exit':expected==0,'actual_exit':r.returncode,'verdict_matches_expectation':(r.returncode==0)==(expected==0),'manifest_unchanged':manifest.read_bytes()==before_manifest,'all_files_unchanged':after==before})
(out/'verifier-controls.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
