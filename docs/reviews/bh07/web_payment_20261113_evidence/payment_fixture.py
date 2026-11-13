from pathlib import Path
import hashlib,json,re,subprocess,sys,uuid
ROOT=Path.cwd();OUT=ROOT/'.build/web-payment-20261113';OUT.mkdir(exist_ok=True)
DOCKER='C:/Users/PHONGNT/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe';DB='bh07-android-db'
def sql(source):
 r=subprocess.run([DOCKER,'exec','-i',DB,'psql','-X','-U','postgres','-v','ON_ERROR_STOP=1','-t','-A'],input=source,text=True,capture_output=True,encoding='utf-8')
 if r.returncode:raise RuntimeError('Owned payment fixture SQL failed')
 return r.stdout.strip()
def obj(source):return json.loads(sql(source))
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def load_result(label,phase):
 raw=(OUT/(label+'-'+phase+'.log')).read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
 assert '### Error' not in text,'UI phase failed'
 r,=[json.loads(line) for line in text.splitlines() if line.startswith('{') and json.loads(line).get('ok') is True]
 return r
def validate_gate(r,confirmed):
 assert r['payment_count']==1 and r['amount']==100000 and r['method']=='bank_transfer'
 assert r['status']==('confirmed' if confirmed else 'submitted') and r['submitted_by_guest'] is True
 assert r['confirmed_by_owner'] is bool(confirmed)
 assert r['confirmed_by_is_null'] is (not confirmed) and r['confirmed_at_is_null'] is (not confirmed)
 assert r['submit_ops']==r['submit_audits']==1 and r['all_submit_audits']==1
 assert r['ledger_count']==r['confirm_ops']==r['confirm_audits']==r['all_confirm_audits']==int(confirmed)
 assert r['ledger_total']==(100000 if confirmed else 0) and r['ledger_valid'] is True
 assert r['total_paid']==(100000 if confirmed else 0) and r['outstanding']==(0 if confirmed else 100000)
 assert r['charges']==[100000,100000] and r['billing_current'] is True
action,label=sys.argv[1:3];assert re.fullmatch(r'(edge|firefox)(-r[123])?',label)
meta=OUT/(label+'-ownership.json')
if action=='seed':
 assert not meta.exists(),'Never reuse ownership metadata'
 d={k:str(uuid.uuid4()) for k in ['session','guest','member','revision','charge_guest','charge_member','expense','marker']}
 sid=d['session'];guest=d['guest'];member=d['member'];rev=d['revision'];exp=d['expense']
 collision=obj(f"SELECT json_build_object('count',(SELECT count(*) FROM sessions WHERE id='{sid}')+(SELECT count(*) FROM session_players WHERE id IN ('{guest}','{member}'))+(SELECT count(*) FROM charge_revisions WHERE id='{rev}')+(SELECT count(*) FROM session_expenses WHERE id='{exp}')+(SELECT count(*) FROM session_charges WHERE id IN ('{d['charge_guest']}','{d['charge_member']}')));")
 assert collision['count']==0
 d.update(preflight_absent=True,insert_attempted=True,created=False);write(meta,d)
 sql(f"""BEGIN;
 INSERT INTO sessions SELECT (jsonb_populate_record(NULL::sessions,to_jsonb(s)||jsonb_build_object('id','{sid}','title','BH07 V2 isolated payment','description','{d['marker']}','starts_at',now()-interval '2 hours','ends_at',now()-interval '1 hour','version',3,'billing_input_version',3))).* FROM sessions s WHERE id='10000000-0000-4000-8000-000000000099';
 INSERT INTO session_players SELECT (jsonb_populate_record(NULL::session_players,to_jsonb(p)||jsonb_build_object('id',CASE WHEN p.display_name='Guest A' THEN '{guest}' ELSE '{member}' END,'session_id','{sid}'))).* FROM session_players p WHERE session_id='10000000-0000-4000-8000-000000000099' AND display_name IN ('Guest A','Member A');
 INSERT INTO session_expenses(id,session_id,category,title,amount_vnd,status,created_by) SELECT '{exp}','{sid}','court','V2 synthetic payment court',200000,'posted',host_user_id FROM sessions WHERE id='{sid}';
 UPDATE sessions SET lifecycle='completed',version=3,billing_input_version=3 WHERE id='{sid}';
 INSERT INTO charge_revisions(id,session_id,revision_no,source_version,status,allocation_total_vnd,fee_mode,reason,finalized_by) SELECT '{rev}','{sid}',1,3,'active',200000,'split_actual','Synthetic current billing fixture',host_user_id FROM sessions WHERE id='{sid}';
 INSERT INTO session_charges(id,revision_id,session_player_id,amount_due_vnd) VALUES ('{d['charge_guest']}','{rev}','{guest}',100000),('{d['charge_member']}','{rev}','{member}',100000);
 COMMIT;""")
 r=obj(f"SELECT json_build_object('owned',description='{d['marker']}','completed',lifecycle='completed','receiver',receiver_snapshot IS NOT NULL,'players',(SELECT count(*) FROM session_players WHERE session_id='{sid}' AND registration_status='confirmed' AND attendance_status='present'),'charges',(SELECT json_agg(amount_due_vnd ORDER BY amount_due_vnd) FROM session_charges WHERE revision_id='{rev}'),'payments',(SELECT count(*) FROM payments WHERE session_player_id IN ('{guest}','{member}')),'billing_current',(SELECT source_version=billing_input_version FROM charge_revisions WHERE id='{rev}')) FROM sessions WHERE id='{sid}';")
 assert r==dict(owned=True,completed=True,receiver=True,players=2,charges=[100000,100000],payments=0,billing_current=True)
 d['created']=True;write(meta,d);write(OUT/(label+'-seed.json'),r)
 print(json.dumps({'label':label,'seed':'PASS','session_sha12':hashlib.sha256(sid.encode()).hexdigest()[:12]}));raise SystemExit
d=json.loads(meta.read_text());sid=str(uuid.UUID(d['session']));guest=str(uuid.UUID(d['guest']));marker=str(uuid.UUID(d['marker']))
owned=obj(f"SELECT json_build_object('count',count(*),'owned',coalesce(bool_and(description='{marker}'),false)) FROM sessions WHERE id='{sid}';")
assert owned==dict(count=1,owned=True),'Refuse access without exact marker'
if action=='pristine':
 r=obj(f"SELECT json_build_object('payments',(SELECT count(*) FROM payments WHERE session_player_id IN (SELECT id FROM session_players WHERE session_id='{sid}')),'audits',(SELECT count(*) FROM audit_events WHERE session_id='{sid}'),'operations',(SELECT count(*) FROM operation_requests WHERE result->>'session_id'='{sid}'));")
 assert all(v==0 for v in r.values());write(OUT/(label+'-pristine.json'),r);print('Owned fixture still has no payment/audit/operation');raise SystemExit
if action=='drivers':
 source=(ROOT/'scripts/bh07_browser/web_payment_scenario.js').read_text(encoding='utf-8')
 source=source.replace("const SESSION_ID = '__BH07_SESSION_ID__';",f"const SESSION_ID = '{sid}';").replace("const GUEST_PLAYER_ID = '__BH07_PLAYER_ID__';",f"const GUEST_PLAYER_ID = '{guest}';")
 (OUT/(label+'-submit.js')).write_text(source,encoding='utf-8')
 (OUT/(label+'-verify.js')).write_text(source.replace("const PHASE = 'submit';","const PHASE = 'verify_guest';"),encoding='utf-8')
 if (OUT/(label+'-submit.log')).exists():
  r=load_result(label,'submit');pid=str(uuid.UUID(r['payment_id']))
  (OUT/(label+'-confirm.js')).write_text(source.replace("const PHASE = 'submit';","const PHASE = 'confirm';").replace('const PAYMENT_ID = null;',f"const PAYMENT_ID = '{pid}';"),encoding='utf-8')
 print('Owned phase drivers ready');raise SystemExit
if action in ['submitted','confirmed']:
 submit=load_result(label,'submit');sp=submit['request_payload'];pid=str(uuid.UUID(submit['payment_id']));srid=str(uuid.UUID(sp['p_request_id']))
 assert sp['p_player_id']==guest and sp['p_amount_vnd']==100000 and sp['p_method']=='bank_transfer' and sp['p_reference'] is None
 d.update(payment_id=pid,submit_request_id=srid);write(meta,d)
 confirmed=action=='confirmed';crid='00000000-0000-4000-8000-000000000000';lid=None
 if confirmed:
  confirm=load_result(label,'confirm');cp=confirm['request_payload'];assert cp['p_payment_id']==pid and confirm['payment_id']==pid
  crid=str(uuid.UUID(cp['p_request_id']));lid=str(uuid.UUID(confirm['ledger_id']));d.update(confirm_request_id=crid,ledger_id=lid);write(meta,d)
 r=obj(f"""SELECT json_build_object(
 'payment_count',(SELECT count(*) FROM payments WHERE session_player_id IN (SELECT id FROM session_players WHERE session_id='{sid}')),
 'amount',p.amount_vnd,'method',p.method,'status',p.status,'submitted_by_guest',p.submitted_by=(SELECT id FROM auth.users WHERE email='guesta@example.test'),
 'confirmed_by_owner',coalesce(p.confirmed_by=(SELECT id FROM auth.users WHERE email='ownera@example.test'),false),'confirmed_by_is_null',p.confirmed_by IS NULL,'confirmed_at_is_null',p.confirmed_at IS NULL,
 'submit_ops',(SELECT count(*) FROM operation_requests WHERE request_id='{srid}' AND operation='submit_payment' AND actor_user_id=p.submitted_by AND payload_hash=md5(jsonb_build_array('{guest}'::uuid,100000::bigint,'bank_transfer',NULL)::text)),
 'submit_audits',(SELECT count(*) FROM audit_events WHERE session_id='{sid}' AND entity_type='payment' AND entity_id='{pid}' AND action='PAYMENT_SUBMITTED' AND request_id='{srid}' AND actor_user_id=p.submitted_by),
 'all_submit_audits',(SELECT count(*) FROM audit_events WHERE session_id='{sid}' AND action='PAYMENT_SUBMITTED'),
 'confirm_ops',(SELECT count(*) FROM operation_requests WHERE request_id='{crid}' AND operation='confirm_payment' AND actor_user_id=p.confirmed_by AND payload_hash=md5(jsonb_build_array('{pid}'::uuid)::text)),
 'confirm_audits',(SELECT count(*) FROM audit_events WHERE session_id='{sid}' AND entity_type='payment' AND entity_id='{pid}' AND action='PAYMENT_CONFIRMED' AND request_id='{crid}' AND actor_user_id=p.confirmed_by),
 'all_confirm_audits',(SELECT count(*) FROM audit_events WHERE session_id='{sid}' AND action='PAYMENT_CONFIRMED'),
 'ledger_count',(SELECT count(*) FROM club_transactions WHERE source_payment_id='{pid}'),
 'ledger_total',(SELECT coalesce(sum(amount_vnd),0) FROM club_transactions WHERE source_payment_id='{pid}'),
 'ledger_valid',(SELECT coalesce(bool_and(direction='income' AND source_type='payment' AND amount_vnd=100000 AND created_by=p.confirmed_by AND club_id=s.club_id {"AND id='"+lid+"'" if lid else ''}),true) FROM club_transactions WHERE source_payment_id='{pid}'),
 'total_paid',(SELECT coalesce(sum(amount_vnd),0) FROM payments WHERE session_player_id='{guest}' AND status='confirmed'),
 'outstanding',100000-(SELECT coalesce(sum(amount_vnd),0) FROM payments WHERE session_player_id='{guest}' AND status='confirmed'),
 'charges',(SELECT json_agg(amount_due_vnd ORDER BY amount_due_vnd) FROM session_charges WHERE revision_id IN (SELECT id FROM charge_revisions WHERE session_id='{sid}' AND status='active')),
 'billing_current',EXISTS(SELECT 1 FROM charge_revisions WHERE session_id='{sid}' AND status='active' AND source_version=s.billing_input_version)
 ) FROM payments p JOIN session_players pl ON pl.id=p.session_player_id JOIN sessions s ON s.id=pl.session_id WHERE p.id='{pid}' AND pl.id='{guest}' AND s.id='{sid}';""")
 write(OUT/(label+'-'+action+'-db.json'),r);validate_gate(r,confirmed)
 print(json.dumps({'label':label,'stage':action,'db_gate':'PASS',**r}));raise SystemExit
if action=='cleanup':
 assert d['preflight_absent'] and d['insert_attempted']
 sql(f"""BEGIN;
 DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM sessions WHERE id='{sid}' AND description='{marker}') THEN RAISE EXCEPTION 'ownership mismatch'; END IF; END $$;
 DELETE FROM operation_requests WHERE result->>'session_id'='{sid}' OR request_id IN (SELECT request_id FROM audit_events WHERE session_id='{sid}');
 DELETE FROM club_transactions WHERE source_payment_id IN (SELECT id FROM payments WHERE session_player_id IN (SELECT id FROM session_players WHERE session_id='{sid}'));
 DELETE FROM audit_events WHERE session_id='{sid}';
 DELETE FROM sessions WHERE id='{sid}' AND description='{marker}';COMMIT;""")
 r=obj(f"SELECT json_build_object('session',(SELECT count(*) FROM sessions WHERE id='{sid}'),'players',(SELECT count(*) FROM session_players WHERE session_id='{sid}'),'revision',(SELECT count(*) FROM charge_revisions WHERE session_id='{sid}'),'expenses',(SELECT count(*) FROM session_expenses WHERE session_id='{sid}'),'payments',(SELECT count(*) FROM payments WHERE session_player_id IN ('{guest}','{d['member']}')),'ledger',(SELECT count(*) FROM club_transactions WHERE source_payment_id='{d.get('payment_id','00000000-0000-4000-8000-000000000000')}'),'audits',(SELECT count(*) FROM audit_events WHERE session_id='{sid}'),'operations',(SELECT count(*) FROM operation_requests WHERE result->>'session_id'='{sid}'));")
 assert all(v==0 for v in r.values());write(OUT/(label+'-cleanup.json'),{'created':True,'removed':True,'verified_absent':True,'session_sha12':hashlib.sha256(sid.encode()).hexdigest()[:12],'remaining':r})
 print(json.dumps({'label':label,'cleanup':'PASS'}))
else:raise SystemExit('Invalid action')
