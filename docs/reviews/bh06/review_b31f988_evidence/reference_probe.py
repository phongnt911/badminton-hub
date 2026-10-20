from pathlib import Path
import textwrap
src=Path('/workspace/badminton-hub/docs/reviews/bh06/run_bh06_tests.py').read_text()
exec(src[:src.index('print(f"Khởi tạo')])
CONTAINER='bh02-review-bh06'
r=sql('postgres',"SELECT datname FROM pg_database WHERE datname LIKE 'bh06_clean_%' ORDER BY datname DESC LIMIT 1")
db=r.stdout.strip()
SHARED={'venue':must(db,'SELECT id FROM public.venues LIMIT 1','venue')}
exec(textwrap.dedent(src[src.index('    def create_and_publish'):src.index('    def billing_state')]))
sid=create_and_publish(1,'Reviewer C2 fixed reference')
p=join(5,sid)['player_id']
start(sid); attend(sid,p);post_expense(sid,100000);finalize(sid)
def instructions():
 return json.loads(must_user(db,5,f"SELECT public.get_payment_instructions('{sid}');",'instructions'))
a=instructions(); req1=newreq()
first=submit_ok(p,100000,actor=5,reference=None,req=req1)
replayed=submit_ok(p,100000,actor=5,reference=None,req=req1)
assert replayed==first
must_user(db,1,f"SELECT public.reject_payment('{first['payment_id']}', 'review rejected', '{newreq()}');",'reject')
b=instructions(); second=submit_ok(p,100000,actor=5,reference=None)
assert second['payment_id'] != first['payment_id']
confirm(second['payment_id'])
post_expense(sid,50000); finalize(sid,reason='review additional cost')
c=instructions(); assert c['outstanding_vnd']==50000
third=submit_ok(p,50000,actor=5,reference=None)
refs=must(db,f"SELECT count(DISTINCT reference) FROM public.payments WHERE session_player_id='{p}'",'unique refs')
assert refs=='3'
assert a['reference']==b['reference']==c['reference']
print(json.dumps({'db':db,'checks':{'retry_same_request_same_response':True,'new_intent_after_reject_succeeds':True,'additional_intent_after_refinalize_50000':True,'three_unique_payment_references':True,'qr_description_stays_stable':True},'passed':5},ensure_ascii=False,indent=2))
