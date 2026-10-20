"""Independent BH-07A app-role probes on a separate synthetic local DB."""
from pathlib import Path
import importlib.util,json,uuid
root=Path('/workspace/badminton-hub')
spec=importlib.util.spec_from_file_location('bh07_fixture',root/'docs/reviews/bh07/run_bh07_tests.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.CONTAINER='bh02-review-bh06'
m.DB='bh07_review_'+m.STAMP+'_'+uuid.uuid4().hex[:6]
m.create_db(m.DB,'reviewer fixture')
for path in sorted(m.MIGRATIONS.glob('*.sql')):m.apply_migration(m.DB,path)
m.VENUE,m.CLUB1,m.CLUB2=m.seed_base(m.DB,'Reviewer')
sid,players,_=m.make_completed('Reviewer partial-page totals',club=m.CLUB1,expense=100000)
pid=players[5]
# Real RPCs under authenticated role; 60 separate cash intents, one transaction.
m.must_user(m.DB,1,f"DO $$ BEGIN FOR i IN 1..60 LOOP PERFORM public.record_cash_payment('{pid}',1000,NULL,gen_random_uuid()); END LOOP; END $$;",'60 payments')
checks=[]
def check(name,passed,details=None):
 checks.append({'name':name,'passed':bool(passed),'details':details})
f=m.finance(sid,limit=50);s=m.summary(sid)
page_paid=sum(x['amount_vnd'] for x in f['payments'] if x['status']=='confirmed')
check('summary aggregates all 60 confirmed payments beyond first page',len(f['payments'])==50 and page_paid==50000 and s['total_paid_vnd']==60000 and s['outstanding_total_vnd']==40000,{'page_paid':page_paid,'summary_paid':s['total_paid_vnd'],'outstanding':s['outstanding_total_vnd']})
raw_keys=set(s)
check('summary contains no contact/bank/receiver/raw player or payment data',not raw_keys.intersection({'phone_number','contact','account_number','receiver_snapshot','players','payments','charges'}))
m.must(m.DB,f"INSERT INTO public.session_staff(session_id,user_id,role,status) VALUES ('{sid}',{m.q(2)},'cohost','active'),('{sid}',{m.q(7)},'finance','active')",'fixture roles')
cohost=m.summary(sid,actor=2)
money=['billing_state','active_revision_id','revision_no','source_version','expenses_total_vnd','amount_due_total_vnd','total_paid_vnd','outstanding_total_vnd']
check('management-only gets counts and NULL financial fields',cohost['present_count']==1 and cohost['can_manage'] is True and cohost['can_view_finance'] is False and all(cohost[k] is None for k in money))
check('finance staff sees only its authorized completed history and totals',m.summary(sid,actor=7)['total_paid_vnd']==60000 and [x['id'] for x in m.history(7)]==[sid])
m.must(m.DB,f"UPDATE public.session_staff SET status='inactive' WHERE session_id='{sid}' AND user_id={m.q(7)}",'revoke fixture finance')
r=m.summary_result(sid,actor=7)
check('revoked finance loses summary and history access',m.expect_error(r,'FORBIDDEN') and m.history(7)==[])
for actor in [5,8,10]:
 r=m.summary_result(sid,actor=actor)
 check(f'actor {actor} participant/cross-club/outsider gets no summary or history',m.expect_error(r,'FORBIDDEN') and m.history(actor)==[])
payment=m.must(m.DB,f"SELECT id FROM public.payments WHERE session_player_id='{pid}' ORDER BY id LIMIT 1",'payment to reverse')
m.reverse_payment(payment)
s2=m.summary(sid)
check('reversal after complete updates canonical totals without losing history',s2['total_paid_vnd']==59000 and s2['outstanding_total_vnd']==41000 and s2['lifecycle']=='completed')
x={'db':m.DB,'checks':checks,'passed':sum(x['passed'] for x in checks),'failed':sum(not x['passed'] for x in checks)}
print(json.dumps(x,ensure_ascii=False,indent=2))
raise SystemExit(1 if x['failed'] else 0)
