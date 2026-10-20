from pathlib import Path
import textwrap
src=Path('/workspace/badminton-hub/docs/reviews/bh06/run_bh06_tests.py').read_text()
exec(src[:src.index('print(f"Khởi tạo')])
CONTAINER='bh02-review-bh06'
r=sql('postgres',"SELECT datname FROM pg_database WHERE datname LIKE 'bh06_clean_%' ORDER BY datname DESC LIMIT 1")
db=r.stdout.strip()
SHARED={'venue':must(db,'SELECT id FROM public.venues LIMIT 1','venue')}
exec(textwrap.dedent(src[src.index('    def create_and_publish'):src.index('    def billing_state')]))
sid=create_and_publish(1,'Reviewer water expense')
r=user_exec(db,1,f"SELECT public.post_session_expense('{sid}', 'other', 'Nuoc fixture', 10000, '{newreq()}');")
print(json.dumps({'rpc_category':'other','exit':r.returncode,'error':r.stderr.strip()},ensure_ascii=False,indent=2))
assert r.returncode==0, 'UI mapped category must be accepted'
row=must(db,f"SELECT category || '|' || title || '|' || amount_vnd FROM public.session_expenses WHERE session_id='{sid}'",'stored expense')
assert row=='other|Nuoc fixture|10000', row
print('PASS: mapped other category, title and amount persisted')
