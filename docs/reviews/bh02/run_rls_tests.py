import subprocess, json, datetime
from pathlib import Path
ROOT=Path(__file__).parent
import os
CONTAINER=os.environ.get('BH02_TEST_CONTAINER','bh02-review-postgres')
if not CONTAINER.startswith('bh02-'):
 raise SystemExit('Refuse a non-bh02 test container name')
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
CLEAN='bh02_clean_'+stamp
LEGACY='bh02_legacy_'+stamp

def sql(db,query):
 return subprocess.run(['docker','exec','-i',CONTAINER,'psql','-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-v','VERBOSITY=verbose','-U','postgres','-d',db],input=query,text=True,encoding='utf-8',capture_output=True)
def must(db,query,label):
 r=sql(db,query)
 if r.returncode: raise RuntimeError(label+': '+r.stderr)
 return r.stdout.strip()
def uid(n):return '00000000-0000-0000-0000-'+f'{n:012d}'
def q(n):return "'"+uid(n)+"'"
setup="""CREATE SCHEMA auth;
CREATE TABLE auth.users(id uuid primary key,email text,raw_user_meta_data jsonb);
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
GRANT USAGE ON SCHEMA auth TO anon,authenticated;
GRANT EXECUTE ON FUNCTION auth.uid() TO anon,authenticated;
"""
migration=(ROOT.parents[2]/'supabase/migrations/20261015051808_init_schema_v1_1.sql').read_text(encoding='utf-8')
for db in [CLEAN,LEGACY]:
 must('postgres','CREATE DATABASE '+db+';', 'create database')
 must(db,setup,'auth stub')
legacy="""CREATE TABLE public.venues(id uuid primary key default gen_random_uuid(),name text not null,address text not null,area text not null,phone_number text,court_count int default 4,price_range text,image_url text,map_url text,created_at timestamptz default now());
CREATE TABLE public.sessions(id uuid primary key default gen_random_uuid(),venue_name text not null,play_date date not null,start_time time not null,end_time time not null,max_slots int default 6,joined_count int default 1,estimated_cost int default 40000,level_requirement text,contact_phone text,status text default 'open',created_at timestamptz default now());
CREATE TABLE public.session_players(id uuid primary key default gen_random_uuid(),session_id uuid references public.sessions(id) on delete cascade,player_name text not null,phone_number text,has_arrived bool default false,has_paid bool default false,created_at timestamptz default now());
"""
must(LEGACY,legacy,'legacy schema')
# Existing Auth account before the migration, for backfill observation.
must(LEGACY,f"INSERT INTO auth.users(id,email) VALUES ({q(90)},'preexisting@example.invalid');",'preexisting auth fixture')
for db in [CLEAN,LEGACY]:
 must(db,migration,'migration execution')

def seed(db):
 statements=[]
 for n in [1,2,3,4,5,6,7]:
  statements.append(f"INSERT INTO auth.users(id,email,raw_user_meta_data) VALUES ({q(n)},'test{n}@example.invalid','{{\"display_name\":\"Test {n}\"}}');")
 statements += [f"INSERT INTO clubs(id,owner_user_id,name) VALUES ({q(101)},{q(1)},'CLB A'),({q(102)},{q(6)},'CLB B');"]
 for mid,club,user,role in [(111,101,1,'owner'),(112,101,2,'member'),(114,101,4,'treasurer'),(115,101,5,'member'),(116,102,6,'owner')]:
  statements.append(f"INSERT INTO club_members(id,club_id,user_id,display_name,role) VALUES ({q(mid)},{q(club)},{q(user)},'Member {user}','{role}');")
 statements += [f"INSERT INTO venues(id,name,address,area) VALUES ({q(201)},'Test venue','Test address','Test');",
 f"INSERT INTO club_bank_accounts(id,club_id,bank_code,account_number,account_name) VALUES ({q(601)},{q(101)},'TEST','FAKE-NO-REAL-ACCOUNT','Test');",
 f"INSERT INTO host_bank_accounts(id,user_id,bank_code,account_number,account_name) VALUES ({q(602)},{q(1)},'TEST','FAKE-HOST-ACCOUNT','Test');"]
 for sid,club,host,visibility,lifecycle in [(301,101,1,'public','published'),(302,101,1,'unlisted','draft'),(303,102,6,'private','published'),(304,101,1,'private','published')]:
  extra_cols=',venue_name,play_date,start_time,end_time' if db==LEGACY else ''
  extra_vals=",'Test venue',DATE '2026-10-20',TIME '17:00',TIME '19:00'" if db==LEGACY else ''
  statements.append(f"INSERT INTO sessions(id,club_id,host_user_id,venue_id,title,starts_at,ends_at,capacity,court_count,visibility,lifecycle,receiver_snapshot{extra_cols}) VALUES ({q(sid)},{q(club)},{q(host)},{q(201)},'Test session {sid}','2026-10-20T10:00:00Z','2026-10-20T12:00:00Z',8,2,'{visibility}','{lifecycle}','{{\"account_number\":\"FAKE-SNAPSHOT\"}}'{extra_vals});")
 statements += [f"INSERT INTO session_staff(session_id,user_id,role) VALUES ({q(301)},{q(5)},'cohost');"]
 for pid,user in [(401,2),(402,7)]:
  extra_cols=',player_name,phone_number' if db==LEGACY else ''
  extra_vals=f",'Legacy player {user}','FAKE-PRIVATE-PHONE-{user}'" if db==LEGACY else ''
  statements.append(f"INSERT INTO session_players(id,session_id,user_id,display_name,registration_status,created_by{extra_cols}) VALUES ({q(pid)},{q(301)},{q(user)},'Player {user}','confirmed',{q(1)}{extra_vals});")
  statements.append(f"INSERT INTO session_player_contacts(player_id,phone_number) VALUES ({q(pid)},'FAKE-PRIVATE-PHONE-{user}');")
 statements += [f"INSERT INTO charge_revisions(id,session_id,revision_no,source_version,allocation_total_vnd,fee_mode,finalized_by) VALUES ({q(501)},{q(301)},1,1,140000,'split_actual',{q(1)});",
 f"INSERT INTO session_charges(id,revision_id,session_player_id,amount_due_vnd) VALUES ({q(701)},{q(501)},{q(401)},70000),({q(702)},{q(501)},{q(402)},70000);",
 f"INSERT INTO payments(id,session_player_id,amount_vnd,method,status,reference,submitted_by,confirmed_by) VALUES ({q(801)},{q(401)},20000,'cash','confirmed','TEST-REF',{q(1)},{q(1)});",
 f"INSERT INTO club_transactions(club_id,direction,amount_vnd,title,source_type,created_by) VALUES ({q(101)},'income',100000,'Test ledger','manual',{q(1)});",
 f"INSERT INTO profile_private(user_id,phone_number) VALUES ({q(1)},'FAKE-HOST-PRIVATE');"]
 must(db,'\n'.join(statements),'fixture seed')
for db in [CLEAN,LEGACY]:seed(db)
results=[]
def case(name,query,expected=None,denied=False,role='authenticated',actor=3,db=CLEAN,denial_or_zero=False):
 actor_setting=f"SELECT set_config('request.jwt.claim.sub','{uid(actor) if actor else ''}',true);"
 # set_config result is suppressed to keep output deterministic.
 request=f"BEGIN; SET LOCAL ROLE {role}; DO $$ BEGIN PERFORM set_config('request.jwt.claim.sub','{uid(actor) if actor else ''}',true); END $$;\n{query}\nROLLBACK;"
 r=sql(db,request)
 output=r.stdout.strip()
 is_denied=r.returncode!=0 and '42501' in r.stderr
 passed=is_denied if denied else (is_denied or output=='0') if denial_or_zero else r.returncode==0 and output==str(expected)
 results.append({'name':name,'db':'legacy' if db==LEGACY else 'clean','role':role,'actor':actor,'expected':'permission denied' if denied else 'denied or 0' if denial_or_zero else str(expected),'actual':output if r.returncode==0 else r.stderr.strip(),'pass':passed})
 print(('PASS ' if passed else 'FAIL ')+name,flush=True)

case('anon venues active read','SELECT count(*) FROM venues;',1,role='anon',actor=None)
case('anon raw player denied','SELECT count(*) FROM session_players;',denied=True,role='anon',actor=None)
case('outsider player rows hidden','SELECT count(*) FROM session_players;',0)
case('player sees own row',f'SELECT count(*) FROM session_players WHERE id={q(401)};',1,actor=2)
case('player cannot see other row',f'SELECT count(*) FROM session_players WHERE id={q(402)};',0,actor=2)
case('cohost sees session roster','SELECT count(*) FROM session_players;',2,actor=5)
case('outsider contacts hidden','SELECT count(*) FROM session_player_contacts;',0)
case('player only own contact','SELECT count(*) FROM session_player_contacts;',1,actor=2)
case('treasurer cannot read contacts','SELECT count(*) FROM session_player_contacts;',0,actor=4)
case('outsider ledger hidden','SELECT count(*) FROM club_transactions;',0)
case('treasurer reads ledger','SELECT count(*) FROM club_transactions;',1,actor=4)
case('player cannot self elevate',f"INSERT INTO app_roles(user_id,role) VALUES ({q(2)},'admin');",denied=True,actor=2)
case('player cannot direct insert paid flag',f"INSERT INTO payments(session_player_id,amount_vnd,method,status,reference,submitted_by) VALUES ({q(401)},50000,'cash','confirmed','FORGED',{q(2)});",denied=True,actor=2)
case('outsider cannot update private profile',f"UPDATE profile_private SET phone_number='FAKE-EDIT' WHERE user_id={q(1)} RETURNING user_id;",'',actor=3)
case('anon cannot forge audit',f"SELECT log_audit_event({q(102)},{q(303)},'session',{q(303)},'FORGED-ACTION') IS NOT NULL;",denied=True,role='anon',actor=None)
case('outsider cannot forge foreign audit',f"SELECT log_audit_event({q(102)},{q(303)},'session',{q(303)},'FORGED-ACTION') IS NOT NULL;",denied=True)
case('client cannot preseed idempotency',"SELECT record_idempotency('confirm_payment','10000000-0000-0000-0000-000000000001','fake-hash','{\"ok\":true}'); SELECT saved_result->>'ok' FROM check_idempotency('confirm_payment','10000000-0000-0000-0000-000000000001','fake-hash');",denied=True)
case('outsider cannot read bank snapshot',f'SELECT count(*) FROM sessions WHERE id={q(301)} AND receiver_snapshot IS NOT NULL;',denial_or_zero=True)
case('outsider cannot list unlisted drafts',"SELECT count(*) FROM sessions WHERE visibility='unlisted' AND lifecycle='draft';",denial_or_zero=True)
case('anon public summary correct count',f'SELECT confirmed_player_count FROM public_session_summary WHERE id={q(301)};',2,role='anon',actor=None)
case('outsider public summary correct count',f'SELECT confirmed_player_count FROM public_session_summary WHERE id={q(301)};',2)
case('player public summary correct count',f'SELECT confirmed_player_count FROM public_session_summary WHERE id={q(301)};',2,actor=2)
case('host public summary correct count',f'SELECT confirmed_player_count FROM public_session_summary WHERE id={q(301)};',2,actor=1)
case('player sees own outstanding',f'SELECT amount_due_vnd || \',\' || total_paid_vnd || \',\' || outstanding_vnd FROM player_outstanding WHERE session_player_id={q(401)};','70000,20000,50000',actor=2)
case('host sees player outstanding',f'SELECT amount_due_vnd || \',\' || total_paid_vnd || \',\' || outstanding_vnd FROM player_outstanding WHERE session_player_id={q(401)};','70000,20000,50000',actor=1)
case('host can read own bank','SELECT count(*) FROM host_bank_accounts;',1,actor=1)
case('owner can read club bank','SELECT count(*) FROM club_bank_accounts;',1,actor=1)
case('treasurer can read club bank','SELECT count(*) FROM club_bank_accounts;',1,actor=4)
case('public detail hides private fields',f"SELECT (get_session_public_detail({q(301)}) ? 'receiver_snapshot') OR (get_session_public_detail({q(301)}) ? 'phone_number');",'f',role='anon',actor=None)
case('outsider private detail blocked',f'SELECT get_session_public_detail({q(303)});',denied=True)
case('new schema session insert into legacy',f"INSERT INTO sessions(host_user_id,venue_id,title,starts_at,ends_at,capacity,court_count) VALUES ({q(1)},{q(201)},'New payload','2026-10-21T10:00:00Z','2026-10-21T12:00:00Z',8,2) RETURNING title;",'New payload',role='postgres',actor=1,db=LEGACY)
case('new schema player insert into legacy',f"INSERT INTO session_players(session_id,user_id,display_name,created_by) VALUES ({q(301)},{q(3)},'New player',{q(1)}) RETURNING display_name;",'New player',role='postgres',actor=1,db=LEGACY)
case('treasurer cannot read legacy contact',f"SELECT count(*) FROM session_players WHERE phone_number IS NOT NULL;",denial_or_zero=True,actor=4,db=LEGACY)

tested_commit=subprocess.check_output(['git','-C',str(ROOT.parents[2]),'rev-parse','HEAD'],text=True).strip()
report={'tested_commit':tested_commit,'container':CONTAINER,'clean_database':CLEAN,'legacy_database':LEGACY,'auth':'minimal auth.users/auth.uid stubs; no PostgREST or full Supabase stack','migration_clean':'PASS','migration_legacy_execution':'PASS','tests':results,'passed':sum(x['pass'] for x in results),'failed':sum(not x['pass'] for x in results)}
(ROOT/('rls_test_results_'+stamp+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(f"TOTAL {len(results)} PASS {report['passed']} FAIL {report['failed']}")

print('Results file:', ROOT/('rls_test_results_'+stamp+'.json'))
