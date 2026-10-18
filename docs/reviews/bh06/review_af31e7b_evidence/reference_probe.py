from pathlib import Path
import textwrap
src=Path('/workspace/badminton-hub/docs/reviews/bh06/run_bh06_tests.py').read_text()
exec(src[:src.index('print(f"Khởi tạo')])
CONTAINER='bh02-review-bh06'
db='bh06_clean_20261018022426'
SHARED={'venue':must(db,'SELECT id FROM public.venues LIMIT 1','venue')}
exec(textwrap.dedent(src[src.index('    def create_and_publish'):src.index('    def billing_state')]))
sid=create_and_publish(1,'Reviewer reference retry')
p=join(5,sid)['player_id']
start(sid); attend(sid,p);post_expense(sid,100000);finalize(sid)
inst=json.loads(must_user(db,5,f"SELECT public.get_payment_instructions('{sid}');",'instructions'))
ref=inst['reference']
first=submit_ok(p,100000,actor=5,reference=ref)
must_user(db,1,f"SELECT public.reject_payment('{first['payment_id']}', 'review rejected', '{newreq()}');",'reject')
second_inst=json.loads(must_user(db,5,f"SELECT public.get_payment_instructions('{sid}');",'instructions again'))
r=submit(p,100000,actor=5,reference=second_inst['reference'])
print(json.dumps({'same_reference': ref==second_inst['reference'],'outstanding_after_reject':second_inst['outstanding_vnd'],'second_submit_exit':r.returncode,'error':r.stderr.strip(),'expected':'new payment intent after rejection succeeds'},ensure_ascii=False,indent=2))
assert r.returncode==0, 'New intent after rejection is blocked by reused QR reference'
