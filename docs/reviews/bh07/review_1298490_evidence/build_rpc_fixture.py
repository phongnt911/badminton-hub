"""Produce real RPC fixtures for provider probes; synthetic local DB only."""
from pathlib import Path
import importlib.util,json,uuid
root=Path('/workspace/badminton-hub')
spec=importlib.util.spec_from_file_location('fixture',root/'docs/reviews/bh07/run_bh07_tests.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.CONTAINER='bh02-review-bh06'
m.DB='bh07b_review_'+m.STAMP+'_'+uuid.uuid4().hex[:6];m.create_db(m.DB,'reviewer fixture')
for p in sorted(m.MIGRATIONS.glob('*.sql')):m.apply_migration(m.DB,p)
m.VENUE,m.CLUB1,m.CLUB2=m.seed_base(m.DB,'ReviewB')
ids=[]
for day in [1,2,3,4]:
 sid,_,_=m.make_completed('History fixture '+str(day),club=m.CLUB1,expense=0,start_days=day)
 ids.append(sid)
pages={'0':m.history(1,limit=2,offset=0,club_id=m.CLUB1)}
new,_,_=m.make_completed('New completed during pagination',club=m.CLUB1,expense=0,start_days=5)
for offset in [2,3,4]:pages[str(offset)]=m.history(1,limit=2,offset=offset,club_id=m.CLUB1)
sid,_,_=m.make_completed('Finance role fixture',club=m.CLUB1,expense=100000,start_days=6)
m.must(m.DB,f"INSERT INTO public.session_staff(session_id,user_id,role,status) VALUES ('{sid}',{m.q(7)},'finance','active')",'grant fixture finance')
before=m.summary(sid,actor=7)
m.must(m.DB,f"UPDATE public.session_staff SET status='inactive' WHERE session_id='{sid}' AND user_id={m.q(7)}",'revoke fixture finance')
r=m.summary_result(sid,actor=7);assert m.expect_error(r,'FORBIDDEN'),r.stderr
x={'db':m.DB,'club_id':m.CLUB1,'history_pages':pages,'initial_order':list(reversed(ids)),'new_completed_id':new,'summary_before':before,'summary_error_message':r.stderr.splitlines()[0].replace('ERROR:  ','',1),'summary_rpc_exit':r.returncode}
out=Path('/workspace/scratch/bh07-review-1298490/rpc-fixture.json');out.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'db':m.DB,'fixture':str(out),'history_page_ids':{k:[i['id'] for i in v] for k,v in pages.items()},'summary_before_outstanding':before['outstanding_total_vnd'],'summary_after_revoke_exit':r.returncode,'summary_error':r.stderr.strip()},ensure_ascii=False,indent=2))
