from pathlib import Path
import hashlib,json,re,subprocess
root=Path('/workspace/badminton-hub');out=Path('/workspace/scratch/bh07-review-cbcc46c-r2');base=root/'docs/reviews/bh07';ev=base/'http_concurrency_evidence'
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
def decode(b):return b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
manifest=(ev/'hashes.sha256').read_bytes();assert not manifest.startswith(b'\xef\xbb\xbf');assert b'\r' not in manifest
lines=manifest.decode('utf-8').strip().split('\n');assert len(lines)==19
rows=[]
patterns={'jwt':r'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}','supabase_key':r'sb_(?:secret|publishable)_[A-Za-z0-9_-]{10,}','private_key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'}
for line in lines:
 h,p=line.split('  ');assert '\\' not in p;full=base/p;raw=full.read_bytes();assert not raw.startswith((b'\xef\xbb\xbf',b'\xff\xfe',b'\xfe\xff'));assert b'\r' not in raw;txt=raw.decode('utf-8');assert '\r' not in txt;assert hashlib.sha256(raw).hexdigest()==h
 hits=[k for k,v in patterns.items() if re.search(v,txt)];assert not hits
 rows.append({'path':p,'UTF8_no_BOM':True,'decoded_CRLF':txt.count('\r\n'),'decoded_CR':txt.count('\r'),'hash_matches':True,'secret_hits':hits})
(out/'manifest-check.json').write_text(json.dumps(rows,indent=2)+'\n')
names=['bh07_db_runner.log','flutter_analyze.log','flutter_test_full.log','green_probe.log','red_probe.log','seed.log'];comparison=[]
for p in ev.iterdir():
 if p.suffix=='.log':
  old=decode(git('show','4aa304a:docs/reviews/bh07/http_concurrency_evidence/'+p.name)).replace('\r\n','\n');new=p.read_text(encoding='utf-8');assert old==new
  comparison.append({'file':p.name,'decoded_content_preserved':True,'previous_UTF16':p.name in names})
(out/'log-content-comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
actual='a0f831af47f98c7649e0c80dce4d5f13004a0db2';initial='a0f831ae3f47e305608bfa0dff19ae035b31f798';assert git('rev-parse','cbcc46c^').decode().strip()==actual
md=[]
for name in ['environment.json','summary.json']:
 new=json.loads((ev/name).read_text());old=json.loads(decode(git('show','4aa304a:docs/reviews/bh07/http_concurrency_evidence/'+name)))
 assert new['base_sha']==actual;assert new['base_sha_initial_parameter']==initial;assert initial in new['base_sha_note'];filtered={k:v for k,v in new.items() if k not in ['base_sha_initial_parameter','base_sha_note']};filtered['base_sha']=initial;assert filtered==old
 md.append({'file':name,'base_corrected':True,'initial_parameter_preserved':True,'all_other_JSON_fields_unchanged':True})
for p in [ev/'commands.md',base/'http_concurrency_handoff.md']:
 s=p.read_text();assert actual in s and initial in s
(out/'metadata-check.json').write_text(json.dumps(md,indent=2)+'\n')
paths=git('diff','--name-only','cbcc46c','HEAD').decode().splitlines();assert all(p.startswith('docs/') or p in ['AGENTS.md','README.md'] for p in paths)
assert git('diff','--name-only',actual,'cbcc46c').decode().splitlines()==['test/integration/bh07_http_auth_test.dart']
for name,args in [('scope-source.txt',('diff','--stat',actual,'cbcc46c')),('scope-docs.txt',('diff','--name-status','cbcc46c','HEAD')),('scope-main.txt',('diff','--name-status','main...HEAD'))]: (out/name).write_bytes(git(*args))
p='test/integration/bh07_http_auth_test.dart';assert git('show','cbcc46c:'+p)==(root/p).read_bytes()
(out/'summary.json').write_text(json.dumps({'actual_docs_sha':git('rev-parse','HEAD').decode().strip(),'requested_docs_sha_not_found':'bb94028f80459c3a372d8299166f272c7a36cb76','tested_source_sha':'cbcc46c2e125b156b53f4297ef864cf658855d37','base_sha':actual,'manifest_pass':19,'six_logs_UTF8_LF':True,'all_log_decoded_content_preserved':True,'metadata_correction_only':True,'source_unchanged':True,'secret_hits':0,'H3':'CLOSED','H4':'CLOSED','verdict':'Đạt'},ensure_ascii=False,indent=2)+'\n')
print('19/19 manifest PASS, 0 BOM, 0 CRLF; six log contents preserved; metadata audit PASS; source unchanged; 0 secret hits')
