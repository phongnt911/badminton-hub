from pathlib import Path
import subprocess,hashlib,json,re
r=Path.cwd();o=Path('/workspace/scratch/attribution-r1');data={}
for f in ['retention_attribution_evidence','review_runtime_b13e468_evidence','retained_path_r1_evidence','retained_path_evidence','app_profile_heap_evidence']:
 d=r/'docs/reviews/bh07'/f
 def snapshot():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()}
 before=snapshot();names=[]
 for line in (d/'hashes.sha256').read_text().splitlines():
  h,n=line.split('  ',1);assert before[n]==h;assert (d/n).read_bytes()==subprocess.check_output(['git','show','HEAD:'+str((d/n).relative_to(r))]);names.append(n)
 assert set(before)==set(names)|{'hashes.sha256'}
 cmd=['python','scripts/bh07_browser/clean_and_manifest.py','--verify','--evidence-dir',str(d)]
 p=subprocess.run(cmd,capture_output=True,text=True);(o/(f+'_integrity.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stdout
 assert before==snapshot(),f
 if f!='retention_attribution_evidence':assert not subprocess.check_output(['git','diff','272bb29..HEAD','--',str(d.relative_to(r))]),f
 data[f]={'payloads':len(names),'before':before,'after':snapshot(),'readonly':True,'exit':p.returncode}
links=0
for name in ['retention_attribution_handoff.md','retention_attribution_report.md','v2b_coverage_map.md']:
 p=r/'docs/reviews/bh07'/name
 for raw in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text()):
  dest=raw.split('#')[0]
  if not dest or '://' in dest:continue
  assert (p.parent/dest).exists(),(name,raw);links+=1
assert not subprocess.check_output(['git','diff','272bb29..HEAD','--','lib','test','supabase'])
data['links']=links;data['checkout']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();data['dirty_before_report']=subprocess.check_output(['git','status','--porcelain'],text=True);(o/'integrity.json').write_text(json.dumps(data,indent=2)+'\n');print('five bundles readonly;links',links)
