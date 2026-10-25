"""Readonly audit of the handed-off QA bundle and Git provenance. Run from repo root."""
import hashlib,json,re,subprocess
from pathlib import Path
root=Path.cwd();ev=root/'docs/reviews/bh07/full_reset_8c107e9_evidence'
source='8c107e9692b89f4a0aadeafc0ae139736f9b2622';base='a55c2d2416f37a0bb8ac985e80bdee579b40774b'
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
def read(name):return json.loads((ev/name).read_text())
def snap(d):return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()}
before=snap(ev);env=read('environment.json');summary=read('summary.json');oracle=read('snapshot_comparison.json');exits=read('exits.json');result={}
assert git('rev-parse',source+'^')==base
subprocess.run(['git','cat-file','-e',base+'^{commit}'],check=True)
assert not git('diff',source+'..HEAD','--','scripts','tests','lib','test','supabase')
assert env['tested_source_sha']==summary['tested_source_sha']==source
assert env['base_review_sha']==summary['base_review_sha']==base
assert env['git_dirty'] is False and env['git_dirty_files']==[]
result['source_provenance']={'source':source,'base':base,'docs_tip':git('rev-parse','HEAD'),'source_tree_unchanged':True,'clean_qa_checkout_reported':True}
result['source_hashes']={}
for name in ['scripts/bh07_reset/run_full_reset.py','tests/test_v5b_runner_flaws.py']:
 blob=subprocess.check_output(['git','show',source+':'+name]);assert blob==(root/name).read_bytes();result['source_hashes'][name]=hashlib.sha256(blob).hexdigest()
repo_migrations=sorted(p.name for p in (root/'supabase/migrations').glob('*.sql'));assert len(repo_migrations)==18
cycles={}
expected_details=['charges=150000, payments=70000','court_count=4',"visibility=public"]
for c in (1,2):
 log=(ev/f'reset_cycle{c}.log').read_text();names=re.findall(r'Applying migration (\S+)\.\.\.',log)
 assert names==repo_migrations
 auth=(ev/f'auth_seed_cycle{c}.log').read_text();assert len(re.findall(r'^created ',auth,re.M))==7
 db=read(f'db_assertions_cycle{c}.json');assert db['total_assertions']==db['passed_assertions']==len(db['assertions'])==23 and all(x['pass'] for x in db['assertions'])
 details=[x['detail'] for x in db['assertions']];assert all(v in details for v in expected_details)
 http=read(f'http_audit_cycle{c}.json');assert len(http)==16 and all(x['pass'] for x in http)
 assert sum(x['operation']=='login' for x in http)==7
 assert all(set(x)=={'actor_alias','operation','http_status','pass','error_code','notes'} for x in http)
 cycles[str(c)]={'migration_names_match_git':True,'migrations':len(names),'auth_users':7,'db_assertions':23,'http_audit_records':len(http),'http_statuses':[x['http_status'] for x in http]}
assert summary['cycles_executed']==2 and summary['cleanup_success'] and summary['negative_controls_pass']
assert exits=={'supabase_start':0,'reset_cycle1':0,'reset_cycle2':0,'supabase_stop':0}
assert oracle['oracle_scope']=='schema_sha256_and_row_counts' and oracle['oracle_schema_match'] and oracle['oracle_counts_match']
a,b=oracle['cycle1_tables'],oracle['cycle2_tables'];assert len(a)==len(b)==48 and set(a)==set(b)
assert oracle['cycle1_schema_sha256']==oracle['cycle2_schema_sha256']
assert all(a[k]['count']==b[k]['count'] for k in a)
diff=[k for k in a if a[k]['sha256']!=b[k]['sha256']];assert len(diff)==oracle['different_data_tables_count']==24
neg=read('negative_controls.log');assert len(neg)==4 and all(x['rejected'] for x in neg)
assert [(n.get('status'),n.get('code')) for n in neg[:3]]==[(401,'42501'),(401,'42501'),(403,'42501')]
assert env['project_id'] in (ev/'commands.md').read_text() and env['project_id'] in (ev/'stop.log').read_text()
assert len(env['container_images'])==12 and all(x['image_tag'] and x['image_id'] and 'repo_digests' in x for x in env['container_images'])
for p in ev.iterdir():
 if p.is_file():
  raw=p.read_bytes();text=raw.decode('utf-8');assert b'\r' not in raw and not raw.startswith(b'\xef\xbb\xbf')
  assert not re.search(r'bh07-http-pass-'+'123456',text)
result['qa_runtime_audited_not_reexecuted']=True;result['cycles']=cycles;result['oracle']={'scope':oracle['oracle_scope'],'tables':48,'schema_match':True,'row_counts_match':True,'different_data_hashes':24};result['exits']=exits
history=['full_reset_evidence','codex_v5b_fix_evidence','review_8e26e06_evidence','review_19ab207_evidence','review_3b515f2_evidence','full_reset_p2_fix_evidence','review_cad3fa0_evidence','review_8c107e9_evidence']
result['historical_bundles_unchanged_since_prior_review']=not bool(git('diff','f6451a7..HEAD','--',*[f'docs/reviews/bh07/{n}' for n in history]))
assert result['historical_bundles_unchanged_since_prior_review']
r=subprocess.run(['python','scripts/bh07_browser/clean_and_manifest.py','--verify','--evidence-dir',str(ev)],capture_output=True,text=True);assert r.returncode==0
result['strict_verify_exit']=r.returncode;result['readonly_before']=before;result['readonly_after']=snap(ev);assert result['readonly_before']==result['readonly_after'];result['readonly_unchanged']=True
print(json.dumps(result,indent=2))
