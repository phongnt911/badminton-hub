"""Coordinator audit: read-only reconciliation of QA runtime bundle and Git provenance."""
from pathlib import Path
import datetime,hashlib,json,re,subprocess
ROOT=Path.cwd()
def g(*a):return subprocess.check_output(['git',*a],text=True).strip()
def sha(b):return hashlib.sha256(b).hexdigest()
qa=ROOT/'docs/reviews/bh07/review_runtime_97d0e7e_evidence';author=ROOT/'docs/reviews/bh07/app_profile_heap_evidence'
report=ROOT/'docs/reviews/bh07/review_runtime_97d0e7e.md'
result={'checkout':g('rev-parse','HEAD'),'dirty_before_acceptance':g('status','--porcelain'),'runtime_tested_source':'97d0e7e3be59fa8504d7ec0d6b55a0e67495ebff','source_code':'c04ce551a4cb7fa8cbddcd5f06dbc790a39889f6','bundles':{},'checks':{}}
for name,d in [('qa',qa),('author',author)]:
 before={p.name:sha(subprocess.check_output(['git','show','2d16369b:'+p.relative_to(ROOT).as_posix()])) for p in d.iterdir() if p.is_file()}
 after={p.name:sha(p.read_bytes()) for p in d.iterdir() if p.is_file()};assert before==after
 entries={n:h for h,n in (l.split('  ') for l in (d/'hashes.sha256').read_text().splitlines())}
 assert set(entries)==set(after)-{'hashes.sha256'} and all(after[n]==h for n,h in entries.items())
 for p in d.iterdir():
  b=p.read_bytes();t=b.decode('utf-8','strict');assert b'\r' not in b and not b.startswith(b'\xef\xbb\xbf')
  assert not re.search(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|postgres(?:ql)?://[^\s]+:[^\s]+@|bh07-http-'+'pass|sb_secret_',t)
 result['bundles'][name]={'entries':len(entries),'file_hashes':after,'tracked_before_equals_after':True}
s=json.loads((qa/'summary.json').read_text());a=json.loads((author/'summary.json').read_text());assert s['tested_source_sha']==result['runtime_tested_source'] and s['git_dirty'] is False and s['git_dirty_paths']==[]
assert s['status']=='RUN' and s['verdict']=='PASS' and s['findings']==[]
assert [c['actor'] for c in s['cycles']]==['cohost','member']
log=(qa/'run.log').read_text();snapshots=[];records=0;times=[]
for c in s['cycles']:
 assert c['same_document'] is True and c['time_origin']>0
 assert list(c['epochs'])==['baseline','owner_active','post_logout','post_actor']
 assert c['verdict']=={'verdict':'PASS','findings':[],'epochs_checked':4}
 for epoch,scan in c['epochs'].items():
  assert scan['ok'] is True and scan['structure']['size_bytes']==scan['size_bytes']
  for v in scan['sentinels'].values():
   assert type(v['occurrences']) is int and v['occurrences']>=0 and v['present'] is (v['occurrences']>0);records+=1
  assert scan['sentinels']['bank']=={'present':epoch=='owner_active','occurrences':1 if epoch=='owner_active' else 0}
  assert scan['sentinels']['probe']=={'present':True,'occurrences':1}
  label=f"c{c['cycle']}_{'post_'+c['actor'] if epoch=='post_actor' else epoch}"
  pat=re.compile(r'^\[([^\]]+)\] '+re.escape(label)+r': snapshot (\d+) bytes sha=([0-9a-f]{12}) ok=true present=(.+)$',re.M)
  match=pat.search(log);assert match,label
  assert int(match[2])==scan['size_bytes'] and match[3]==scan['sha256_12']
  assert json.loads(match[4])=={n:v['present'] for n,v in scan['sentinels'].items()}
  snapshots.append(scan['sha256_12']);times.append(datetime.datetime.fromisoformat(match[1].replace('Z','+00:00')))
assert len(set(snapshots))==8 and records==24 and times==sorted(times)
assert datetime.datetime.fromisoformat(s['started_at'].replace('Z','+00:00'))<times[0]<times[-1]<datetime.datetime.fromisoformat(s['finished_at'].replace('Z','+00:00'))
assert all(s['cleanup'][n] is True for n in ['dump_dir_outside_repo','dumps_dir_removed','chrome_profile_dir_removed','ok']) and s['cleanup']['raw_snapshots_remaining']==0
artifacts=s['environment']['build']['artifacts'];assert len(artifacts)==39 and s['environment']['build']['mode']=='profile' and s['environment']['build']['served_match'] is True
assert all(re.fullmatch('[0-9a-f]{64}',h) for h in artifacts.values())
assert all(artifacts[n]==a['environment']['build']['artifacts'][n] for n in ['index.html','main.dart.js'])
for h in result['bundles']['author']['file_hashes'].values():assert h in report.read_text(),h
result['checks']={'metadata_log_match':True,'snapshots':8,'unique_snapshot_hashes':8,'consistent_records':24,'artifact_hashes':39,'entry_artifacts_match_author':True,'cleanup_recorded_verified':True,'runtime_scope':'independent QA as declared in project handoff; not coordinator runtime rerun','source_tree_base_to_qa':g('diff','--name-only','97d0e7e','HEAD','--','scripts','tests','lib','test','supabase'),'source_tree_accepted_to_qa':g('diff','--name-only','c04ce55','HEAD','--','scripts','tests','lib','test','supabase'),'whitespace':g('diff','--check','97d0e7e','HEAD')}
assert result['checks']['source_tree_base_to_qa']==result['checks']['source_tree_accepted_to_qa']==result['checks']['whitespace']==''
result['exits']={'qa_relative_path_cli':1,'qa_absolute_cli':0,'author_cli':0,'qa_strict_verify':0,'author_strict_verify':0}
result['not_replayed_coordinator']=['Chrome runtime','Flutter analyze/tests','Python suite/old controls'];result['reason_no_suite_replay']='docs/evidence-only QA delta; code tree identical to previously accepted source c04ce55'
print(json.dumps(result,indent=2))
