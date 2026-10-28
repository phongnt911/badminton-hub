from pathlib import Path
import subprocess,hashlib,json,re
ROOT=Path('/workspace/badminton-hub'); OUT=Path('/workspace/scratch/retained-runtime-close');osroot=ROOT/'docs/reviews/bh07'
qa=osroot/'review_runtime_b13e468_evidence'; s=json.loads((qa/'summary.json').read_text()); results={}
for folder in ['review_runtime_b13e468_evidence','retained_path_r1_evidence','retained_path_evidence','app_profile_heap_evidence','review_runtime_97d0e7e_evidence']:
 d=osroot/folder;before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()}
 lines=(d/'hashes.sha256').read_text().splitlines(); names=[]
 for line in lines:
  h,n=line.split('  ',1);assert n not in names;names.append(n);assert before[n]==h
 assert set(names)==set(before)-{'hashes.sha256'}
 for p in d.iterdir():
  raw=p.read_bytes();assert raw==subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))]);assert not raw.startswith(b'\xef\xbb\xbf') and b'\r' not in raw; text=raw.decode('utf-8')
  assert not re.search(r'eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}|sb_secret_[A-Za-z0-9_-]+|PRIVATE KEY-----|postgres(?:ql)?://[^\s]+',text)
 cmds=[['python','scripts/bh07_browser/clean_and_manifest.py','--verify','--evidence-dir',str(d)]]
 if folder!='review_runtime_97d0e7e_evidence':cmds.append(['python','-X','utf8','scripts/bh07_appheap/verify_evidence.py','--dir',str(d)])
 exits=[]
 for index,cmd in enumerate(cmds):
  p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);(OUT/(folder+'_'+str(index)+'.log')).write_text(p.stdout+p.stderr);expected=1 if index==1 and folder in ['retained_path_evidence','app_profile_heap_evidence'] else 0;assert p.returncode==expected,(folder,p.stdout,p.stderr);exits.append({'command':cmd,'exit':p.returncode,'expected':expected})
 after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()};assert after==before
 if folder!='review_runtime_b13e468_evidence':assert not subprocess.check_output(['git','diff','b13e468..HEAD','--',str(d.relative_to(ROOT))])
 results[folder]={'hashes':before,'payloads_verified':len(names),'readonly':before==after,'commands':exits}
assert s['tested_source_sha']=='b13e468d33e0d96437b58bb2da6088bff689b9eb' and s['git_dirty'] is False and s['git_dirty_paths']==[]
assert s['status']=='RUN' and s['verdict']=='PASS' and not s['findings'];assert len(s['cycles'])==2
rows=[]
for c in s['cycles']:
 assert c['same_document'] is True
 for epoch,scan in c['epochs'].items():
  assert scan['ok'] is True
  for name in ['expense_id','expense_id_2']:
   hit=epoch=='owner_active';v=scan['sentinels'][name];path=scan['paths'][name];assert v['present']==hit and path['reachable']==hit
   assert v['scope']=='finance' and v['rendered'] is False and v['distinctive'] is True
   if not hit:assert v['occurrences']==0 and path['string_nodes']==0
   rows.append({'cycle':c['cycle'],'actor':c.get('actor'),'epoch':epoch,'sentinel':name,'present':v['present'],'reachable':path['reachable'],'path_len':path.get('path_len',0)})
assert len(s['residual_risks'])==8 and all(x['attribution']=='unattributed' for x in s['residual_risks'])
cl=s['cleanup'];assert cl['raw_snapshots_remaining']==0
for k in ['ok','dump_dir_outside_repo','dumps_dir_removed','chrome_profile_dir_removed','run_only_fixture_created','extra_expense_removed','extra_expense_verified_absent']:assert cl[k] is True
assert len(s['environment']['build']['artifacts'])==39 and s['environment']['build']['served_match'] is True
assert not subprocess.check_output(['git','diff','b13e468..HEAD','--','lib','test','supabase','scripts','tests'])
results['runtime_audit']={'tested_source':s['tested_source_sha'],'snapshot_count':8,'finance_records':rows,'residual_risk_count':8,'cleanup':cl,'build_artifacts':39,'new_runtime_by_coordinator':False,'qa_count_claims':'312 Python,247 Flutter+1skip: report only; individual suite logs not in this 4-file bundle.'}
(OUT/'audit.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS: five bundles, readonly; 8 snapshots,16 finance records; source unchanged')
