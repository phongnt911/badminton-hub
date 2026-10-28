from pathlib import Path
import subprocess,hashlib,json
r=Path.cwd();out=Path('/workspace/scratch/attribution-close');records={}
folders=['review_41c1ea1_evidence','retention_attribution_codex_r3_evidence','review_5226a3d_evidence','retention_attribution_evidence','review_eda1ead_evidence','review_37b4954_evidence','review_runtime_b13e468_evidence','retained_path_r1_evidence','retained_path_evidence','app_profile_heap_evidence','review_runtime_97d0e7e_evidence']
for name in folders:
 d=r/'docs/reviews/bh07'/name;before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()};names=[]
 for line in (d/'hashes.sha256').read_text().splitlines():
  h,n=line.split('  ',1);assert n not in names and before[n]==h;assert (d/n).read_bytes()==subprocess.check_output(['git','show','HEAD:'+str((d/n).relative_to(r))]);names.append(n)
 assert set(names)|{'hashes.sha256'}==set(before)
 cmd=['python','scripts/bh07_browser/clean_and_manifest.py','--verify','--evidence-dir',str(d)];p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stdout;(out/(name+'.log')).write_text(p.stdout+p.stderr)
 assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()}
 if name!='review_41c1ea1_evidence':assert not subprocess.check_output(['git','diff','41c1ea1..HEAD','--',str(d.relative_to(r))])
 records[name]={'verified_payloads':len(names),'before':before,'after':before,'readonly':True,'exit':p.returncode}
d=r/'docs/reviews/bh07/review_41c1ea1_evidence';prov=json.loads((d/'provenance.json').read_text())
assert prov['tested_source_sha']=='f11d20f6c5025f7f774c266298bc0309fcd0de0c';assert prov['dirty_before_run']=='';assert prov['new_runtime_executed'] is False
for name,h in prov['source_hashes'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==h
assert not subprocess.check_output(['git','diff','f11d20f6..HEAD','--','scripts','tests','lib','test','supabase'])
assert all(json.loads((d/'exits.json').read_text())[n]['exit']==0 for n in ['unit','analyze','flutter_test','auditor_temp_out'])
assert 'Ran 319 tests' in (d/'unit.log').read_text() and 'OK' in (d/'unit.log').read_text();assert 'No issues found' in (d/'analyze.log').read_text();assert '+247 ~1: All tests passed!' in (d/'flutter_test.log').read_text()
for name,path in {'probes':'review_37b4954_evidence/probes.py','extra_controls':'review_eda1ead_evidence/extra_controls.py','closure_controls':'review_5226a3d_evidence/closure_controls.py'}.items():
 p=subprocess.run(['python','docs/reviews/bh07/'+path],capture_output=True,text=True);assert p.returncode==0;got=json.loads(p.stdout);saved=json.loads((d/(name+'.json')).read_text());assert got==saved;assert all(v['exit']==(0 if k=='positive' else 1) for k,v in got.items());(out/(name+'.json')).write_text(p.stdout)
controls=json.loads((d/'reviewer_at1_controls.json').read_text());assert len(controls)==12 and all(v['exit']==1 and v['valid'] is False and v['status']=='FAIL' and v['primary_retainer_component']=='UNATTRIBUTED' for v in controls.values())
records['checks']={'scope':'docs/status only; runtime source unchanged','independent_reviewer':'Antigravity per provenance; coordinator authored source and does not claim independence','reviewer_counts':'319Python,analyze0,247Flutter+1skip supported by saved logs; not new coordinator suite runs','fresh_coordinator_replay':'3 positive0,10mutant1; equal to independent reviewer output','reviewer_extra_controls':'12 mutant records coherent; no replay script supplied, not rerun by coordinator','checkout':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'dirty_before_report':subprocess.check_output(['git','status','--porcelain'],text=True)}
(out/'audit.json').write_text(json.dumps(records,indent=2)+'\n');print('PASS: 11bundles readonly,reviewer14/14,source hashes/logs/3probes coherent')
