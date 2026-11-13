from pathlib import Path
import hashlib,json,re,subprocess,sys,uuid

ROOT=Path.cwd()
OUT=ROOT/'.build/web-lifecycle-20261113'
OUT.mkdir(exist_ok=True)
DOCKER='C:/Users/PHONGNT/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
DB='bh07-android-db'
def sql(source):
    r=subprocess.run([DOCKER,'exec','-i',DB,'psql','-X','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1','-t','-A'],input=source,text=True,capture_output=True,encoding='utf-8')
    if r.returncode: raise RuntimeError('Local fixture SQL failed; inspect bounded diagnostic locally')
    return r.stdout.strip()
def obj(source): return json.loads(sql(source))
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def validate_gate(r,action):
    assert r['players_present']==2 and r['revision_count']==1 and r['charge_count']==2 and r['charge_total']==200000,r
    assert r['lifecycle']==('in_progress' if action=='offline' else 'completed'),r
    assert r['version']==(2 if action=='offline' else 3),r
    assert r['completed_audits']==r['complete_operations']==(0 if action=='offline' else 1),r
    assert r['exact_request_operations']==r['exact_request_audits']==(0 if action=='offline' else 1),r
    assert r['charges']==[100000,100000] and r['payments']==0 and r['billing_current'] is True,r
action,label=sys.argv[1:3]
assert re.fullmatch(r'(edge|firefox)(-r[123])?',label),'Invalid owned label'
meta=OUT/(label+'-ownership.json')
if action=='seed':
    assert not meta.exists(),'Do not reuse an ownership receipt'
    ids={k:str(uuid.uuid4()) for k in ['session','member','guest','expense','marker']}
    sid=ids['session'];m=ids['member'];g=ids['guest'];e=ids['expense']
    collision=obj(f"SELECT json_build_object('count',(SELECT count(*) FROM sessions WHERE id='{sid}')+(SELECT count(*) FROM session_players WHERE id IN ('{m}','{g}'))+(SELECT count(*) FROM session_expenses WHERE id='{e}'));")
    assert collision['count']==0,'Collision; no writes and no cleanup authorized'
    ids.update({'preflight_collision_count':0,'created':False})
    write(meta,ids)
    sql(f"""BEGIN;
    INSERT INTO sessions(id,club_id,host_user_id,venue_id,title,description,starts_at,ends_at,capacity,court_count,visibility,lifecycle,approval_mode,fee_mode,version,billing_input_version)
    SELECT '{sid}','aaaaaaaa-1111-4111-8111-111111111111',id,'cccccccc-3333-4333-8333-333333333333','BH07 V2 isolated lifecycle','{ids['marker']}',now()+interval '1 hour',now()+interval '3 hours',8,2,'public','published','auto_confirm','split_actual',1,1 FROM auth.users WHERE email='ownera@example.test';
    INSERT INTO session_staff(session_id,user_id,role,status) SELECT '{sid}',id,'cohost','active' FROM auth.users WHERE email='cohosta@example.test';
    INSERT INTO session_players(id,session_id,user_id,club_member_id,display_name,registration_status,attendance_status,source,participant_type,fee_exempt,requested_at,confirmed_at,created_by)
    SELECT '{m}','{sid}',id,'a0000004-0000-4000-8000-000000000004','Member A','confirmed','not_checked_in','self','member',false,now(),now(),id FROM auth.users WHERE email='membera@example.test';
    INSERT INTO session_players(id,session_id,user_id,display_name,registration_status,attendance_status,source,participant_type,fee_exempt,requested_at,confirmed_at,created_by)
    SELECT '{g}','{sid}',id,'Guest A','confirmed','not_checked_in','self','guest',false,now(),now(),id FROM auth.users WHERE email='guesta@example.test';
    INSERT INTO session_expenses(id,session_id,category,title,amount_vnd,status,created_by)
    SELECT '{e}','{sid}','court','V2 local court fixture',200000,'posted',id FROM auth.users WHERE email='ownera@example.test';
    COMMIT;""")
    read=obj(f"SELECT json_build_object('owned',description='{ids['marker']}','lifecycle',lifecycle,'version',version,'players',(SELECT count(*) FROM session_players WHERE session_id='{sid}'),'expense',(SELECT sum(amount_vnd) FROM session_expenses WHERE session_id='{sid}')) FROM sessions WHERE id='{sid}';")
    assert read=={'owned':True,'lifecycle':'published','version':1,'players':2,'expense':200000},read
    ids['created']=True;write(meta,ids);write(OUT/(label+'-seed.json'),read)
    source=(ROOT/'scripts/bh07_browser/web_lifecycle_scenario.js').read_text(encoding='utf-8') if (ROOT/'scripts/bh07_browser/web_lifecycle_scenario.js').exists() else None
    if source:(OUT/(label+'-prepare.js')).write_text(source.replace("const SESSION_ID = '__BH07_SESSION_ID__';",f"const SESSION_ID = '{sid}';"),encoding='utf-8')
    print(json.dumps({'label':label,'seed':'PASS','session_id':sid}))
    raise SystemExit
ids=json.loads(meta.read_text());sid=str(uuid.UUID(ids['session']));marker=str(uuid.UUID(ids['marker']))
owned=obj(f"SELECT json_build_object('count',count(*),'owned',coalesce(bool_and(description='{marker}'),false)) FROM sessions WHERE id='{sid}';")
assert owned=={'count':1,'owned':True},'Refuse operations without exact owned fixture row'
if action in ['offline','completed']:
    raw=(OUT/(label+'-prepare.log')).read_bytes()
    log=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    assert '### Error' not in log,'Prepare did not finish successfully'
    first,=[json.loads(line) for line in log.splitlines() if line.startswith('{') and json.loads(line).get('ok') is True]
    payload=first['FIRST_COMPLETE_PAYLOAD']
    assert set(payload)=={'p_session_id','p_expected_version','p_request_id'} and payload['p_session_id']==sid and payload['p_expected_version']==2
    rid=str(uuid.UUID(payload['p_request_id']))
    ids['complete_request_id']=rid;write(meta,ids)
    r=obj(f"""SELECT json_build_object(
    'lifecycle',lifecycle,'version',version,'billing_input_version',billing_input_version,
    'players_present',(SELECT count(*) FROM session_players WHERE session_id='{sid}' AND attendance_status='present'),
    'revision_count',(SELECT count(*) FROM charge_revisions WHERE session_id='{sid}' AND status='active'),
    'charge_count',(SELECT count(*) FROM session_charges WHERE revision_id IN (SELECT id FROM charge_revisions WHERE session_id='{sid}')),
    'charge_total',(SELECT coalesce(sum(amount_due_vnd),0) FROM session_charges WHERE revision_id IN (SELECT id FROM charge_revisions WHERE session_id='{sid}')),
    'completed_audits',(SELECT count(*) FROM audit_events WHERE session_id='{sid}' AND action='SESSION_COMPLETED'),
    'complete_operations',(SELECT count(*) FROM operation_requests WHERE operation='complete_session' AND request_id IN (SELECT request_id FROM audit_events WHERE session_id='{sid}')),
    'exact_request_operations',(SELECT count(*) FROM operation_requests WHERE request_id='{rid}' AND operation='complete_session' AND actor_user_id=(SELECT id FROM auth.users WHERE email='ownera@example.test')),
    'exact_request_audits',(SELECT count(*) FROM audit_events WHERE session_id='{sid}' AND request_id='{rid}' AND action='SESSION_COMPLETED'),
    'charges',(SELECT json_agg(amount_due_vnd ORDER BY amount_due_vnd) FROM session_charges WHERE revision_id IN (SELECT id FROM charge_revisions WHERE session_id='{sid}' AND status='active')),
    'payments',(SELECT count(*) FROM payments WHERE session_player_id IN (SELECT id FROM session_players WHERE session_id='{sid}')),
    'billing_current',EXISTS(SELECT 1 FROM charge_revisions WHERE session_id='{sid}' AND status='active' AND source_version=sessions.billing_input_version)
    ) FROM sessions WHERE id='{sid}';""")
    write(OUT/(label+'-'+action+'-db.json'),r)
    validate_gate(r,action)
    if action=='offline':
        source=(ROOT/'scripts/bh07_browser/web_lifecycle_scenario.js').read_text(encoding='utf-8')
        source=source.replace("const SESSION_ID = '__BH07_SESSION_ID__';",f"const SESSION_ID = '{sid}';")
        source=source.replace("const PHASE = 'prepare_offline';","const PHASE = 'retry_online';")
        source=source.replace('const FIRST_COMPLETE_PAYLOAD = null;','const FIRST_COMPLETE_PAYLOAD = '+json.dumps(payload,separators=(',',':'))+';')
        (OUT/(label+'-retry.js')).write_text(source,encoding='utf-8')
    else:
        raw=(OUT/(label+'-retry.log')).read_bytes()
        text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
        assert '### Error' not in text,'Retry did not complete successfully'
        second,=[json.loads(line) for line in text.splitlines() if line.startswith('{') and json.loads(line).get('ok') is True]
        assert first['document_time_origin']==second['document_time_origin'],'Document changed between phases'
        assert second['full_payload_same'] and second['request_id_same'] and second['rpc_status']==200
    print(json.dumps({'label':label,'stage':action,'db_gate':'PASS',**r}))
elif action=='cleanup':
    assert ids['created'] and ids['preflight_collision_count']==0
    exact_cleanup='false'
    if ids.get('complete_request_id'):
        rid=str(uuid.UUID(ids['complete_request_id']))
        exact_cleanup=f"(request_id='{rid}' AND operation='complete_session' AND actor_user_id=(SELECT id FROM auth.users WHERE email='ownera@example.test') AND payload_hash=md5(jsonb_build_array('{sid}'::uuid,2::bigint)::text))"
    sql(f"""BEGIN;
    DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM sessions WHERE id='{sid}' AND description='{marker}') THEN RAISE EXCEPTION 'ownership mismatch'; END IF; END $$;
    DELETE FROM operation_requests WHERE request_id IN (SELECT request_id FROM audit_events WHERE session_id='{sid}') OR result->>'id'='{sid}' OR result->'session'->>'id'='{sid}' OR {exact_cleanup};
    DELETE FROM audit_events WHERE session_id='{sid}';
    DELETE FROM sessions WHERE id='{sid}' AND description='{marker}';
    COMMIT;""")
    r=obj(f"SELECT json_build_object('sessions',(SELECT count(*) FROM sessions WHERE id='{sid}'),'players',(SELECT count(*) FROM session_players WHERE session_id='{sid}'),'expenses',(SELECT count(*) FROM session_expenses WHERE session_id='{sid}'),'revisions',(SELECT count(*) FROM charge_revisions WHERE session_id='{sid}'),'charges',(SELECT count(*) FROM session_charges WHERE revision_id IN (SELECT id FROM charge_revisions WHERE session_id='{sid}')),'audits',(SELECT count(*) FROM audit_events WHERE session_id='{sid}'),'operations',(SELECT count(*) FROM operation_requests WHERE result->>'id'='{sid}' OR result->'session'->>'id'='{sid}'));")
    assert all(v==0 for v in r.values()),r
    write(OUT/(label+'-cleanup.json'),{'created':True,'removed':True,'verified_absent':True,'session_sha12':hashlib.sha256(sid.encode()).hexdigest()[:12],'remaining':r})
    print(json.dumps({'label':label,'cleanup':'PASS'}))
else:raise SystemExit('Invalid action')
