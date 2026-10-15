import json,subprocess
from pathlib import Path
import os
CONTAINER=os.environ.get('BH02_TEST_CONTAINER','bh02-review-postgres')
if not CONTAINER.startswith('bh02-'): raise SystemExit('Refuse a non-bh02 test container name')
ROOT=Path(__file__).resolve().parents[3]
latest=sorted((ROOT/'docs/reviews/bh02').glob('rls_test_results_*.json'))[-1]
meta=json.loads(latest.read_text());clean=meta['clean_database'];legacy=meta['legacy_database']
def q(n):return "'00000000-0000-0000-0000-"+f'{n:012d}'+"'"
results=[]
def case(name,query,expected,actor=4,db=clean,prep=''):
 sql=f"BEGIN; {prep} SET LOCAL ROLE authenticated; DO $$ BEGIN PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-{actor:012d}',true); END $$; {query} ROLLBACK;"
 if actor==0:sql=f'BEGIN; {prep} {query} ROLLBACK;'
 r=subprocess.run(['docker','exec','-i',CONTAINER,'psql','-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-U','postgres','-d',db],input=sql,text=True,capture_output=True)
 actual=r.stdout.strip() if r.returncode==0 else r.stderr.strip()
 results.append(dict(name=name,expected=expected,actual=actual,pass_=r.returncode==0 and actual==expected))
 print(('PASS ' if results[-1]['pass_'] else 'FAIL ')+name+': '+actual)
case('treasurer sees outstanding roster','SELECT count(*) FROM player_outstanding;','2')
case('treasurer sees confirmed payment','SELECT count(*) FROM payments;','1')
case('member without registration cannot read receiver snapshot',f'SELECT count(*) FROM sessions WHERE id={q(301)} AND receiver_snapshot IS NOT NULL;','0',actor=3,prep=f"INSERT INTO club_members(club_id,user_id,display_name) VALUES ({q(101)},{q(3)},'New member');")
case('pending guest cannot read receiver snapshot',f'SELECT count(*) FROM sessions WHERE id={q(301)} AND receiver_snapshot IS NOT NULL;','0',actor=3,prep=f"INSERT INTO session_players(session_id,user_id,display_name,registration_status,created_by) VALUES ({q(301)},{q(3)},'Pending guest','pending',{q(1)});")
case('legacy time follows starts_at update',f"UPDATE sessions SET starts_at='2026-10-20T11:00:00Z' WHERE id={q(301)}; SELECT start_time::text FROM sessions WHERE id={q(301)};",'18:00:00',actor=0,db=legacy)
case('legacy venue name comes from venue rather than session title',f"INSERT INTO sessions(host_user_id,venue_id,title,starts_at,ends_at,capacity,court_count) VALUES ({q(1)},{q(201)},'Tuesday group','2026-10-21T10:00:00Z','2026-10-21T12:00:00Z',8,2) RETURNING venue_name;",'Test venue',actor=0,db=legacy)
result={'tested_commit':meta['tested_commit'],'baseline':'33/33 PASS','tests':results,'passed':sum(x['pass_'] for x in results),'failed':sum(not x['pass_'] for x in results)}
(Path(__file__).parent/('extended_results_'+meta['clean_database'].removeprefix('bh02_clean_')+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
