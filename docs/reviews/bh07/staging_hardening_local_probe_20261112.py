"""Local candidate verification only; never connects to hosted Supabase."""
import contextlib
import hashlib
import importlib.util
import io
import json
import subprocess
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.build' / 'bh07-staging-local-semantic-v3-20261112.json'
name = 'bh07-staging-verify-' + uuid.uuid4().hex[:12]
label = uuid.uuid4().hex
cid = None
checks = []
receipt = {'scope': 'local PostgreSQL17 + auth.uid stub, NOT hosted/Auth/acceptance',
           'container_name': name, 'checks': checks, 'cleanup_verified': False}
stage = 'preflight'

def command(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, encoding='utf-8', **kw)

def check(title, condition):
    checks.append({'name': title, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(title)

try:
    r = command(['docker', 'inspect', name])
    if r.returncode == 0:
        raise RuntimeError('unexpected existing resource')
    stage = 'create_owned_container'
    r = command(['docker', 'run', '-d', '--pull=never', '--network', 'none',
                 '--name', name, '--label', 'bh07.staging.verify=' + label,
                 '-e', 'POSTGRES_PASSWORD=' + uuid.uuid4().hex, 'postgres:17'])
    if r.returncode:
        raise RuntimeError('container creation failed')
    cid = r.stdout.strip()
    receipt['container_id'] = cid
    stage = 'readiness'
    for _ in range(60):
        # The image's temporary init server accepts Unix sockets before restarting.
        # TCP readiness only succeeds for the final server, even on network=none.
        r = command(['docker', 'exec', cid, 'pg_isready', '-h', '127.0.0.1', '-U', 'postgres'])
        if r.returncode == 0:
            break
        time.sleep(0.5)
    else:
        raise RuntimeError('readiness failed')
    spec = importlib.util.spec_from_file_location('existing_bh07_db', ROOT / 'docs/reviews/bh07/run_bh07_tests.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.CONTAINER = cid
    db = 'bh07_staging_verify'
    stage = 'canonical_migrations'
    mod.must('postgres', 'CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN; CREATE DATABASE ' + db + ';', 'roles')
    mod.must(db, mod.setup_auth, 'auth stub')
    paths = sorted((ROOT / 'supabase/migrations').glob('*.sql'))
    for p in paths:
        mod.apply_migration(db, p)
    candidate = ROOT / 'scripts/bh07_staging/role_helper_hardening.sql'
    receipt['candidate_sha256'] = hashlib.sha256(candidate.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    receipt['migration_sha256'] = {p.name: hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in paths}
    funcs = ['is_app_admin','is_club_owner','is_club_member_active','has_club_role',
             'is_session_host','has_session_staff_role','has_session_management_access',
             'has_session_finance_access','is_session_participant','has_session_player_finance_access']
    literals = ','.join("'" + f + "'" for f in funcs)
    definition_query = "SELECT jsonb_object_agg(proname, md5(prosrc))::text FROM pg_proc JOIN pg_namespace n ON n.oid=pronamespace WHERE n.nspname='public' AND (proname IN (" + literals + ") OR proname LIKE 'sync_legacy_session%');"
    view_query = "SELECT jsonb_object_agg(viewname, md5(definition))::text FROM pg_views WHERE schemaname='public';"
    before_functions = mod.must(db, definition_query, 'before functions')
    before_views = mod.must(db, view_query, 'before views')
    stage = 'apply_local_candidate'
    mod.apply_migration(db, candidate)
    check('function bodies unchanged', before_functions == mod.must(db, definition_query, 'after functions'))
    check('view definitions unchanged', before_views == mod.must(db, view_query, 'after views'))
    grants = json.loads(mod.must(db, "SELECT jsonb_agg(jsonb_build_object('name',proname,'anon',has_function_privilege('anon',p.oid,'EXECUTE'),'authenticated',has_function_privilege('authenticated',p.oid,'EXECUTE'))) FROM pg_proc p JOIN pg_namespace n ON n.oid=pronamespace WHERE n.nspname='public' AND proname IN (" + literals + ");", 'grants'))
    check('all10 helper role grants', len(grants) == 10 and all(not g['anon'] and g['authenticated'] for g in grants))
    receipt['helper_grants'] = grants
    zero = "'00000000-0000-0000-0000-000000000000'::uuid"
    for f in funcs:
        args = [zero] if f == 'is_app_admin' else [zero, zero]
        if f in ('has_club_role','has_session_staff_role'):
            args.append("ARRAY['member']::text[]")
        call = 'SELECT public.' + f + '(' + ','.join(args) + ');'
        res = mod.anon_exec(db, call)
        check('anon deny ' + f, res.returncode != 0 and 'permission denied for function' in res.stderr)
        res = mod.user_exec(db, 1, call)
        check('authenticated execute ' + f, res.returncode == 0)
    cfg = json.loads(mod.must(db, "SELECT jsonb_agg(jsonb_build_object('name',proname,'config',proconfig)) FROM pg_proc p JOIN pg_namespace n ON n.oid=pronamespace WHERE n.nspname='public' AND proname IN ('sync_legacy_session_columns','sync_legacy_session_player_columns');", 'paths'))
    check('both trigger paths pinned', len(cfg) == 2 and all('search_path=public, pg_temp' in x['config'] for x in cfg))
    receipt['trigger_config'] = cfg
    stage = 'existing_db_suite'
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        mod.run_suite(db)
    receipt['existing_suite'] = mod.results
    check('existing BH07 clean suite', bool(mod.results) and all(x['status'] == 'PASS' for x in mod.results))
    stage = 'guest_and_caller_controls'
    fixtures = {}
    for tag, vis, published in [('public','public',True),('unlisted','unlisted',True),('private','private',True),('draft','public',False)]:
        sid = mod.create_session(1, 'Hardening-' + tag, club=mod.CLUB1, visibility=vis)
        fixtures[tag] = sid
        if published:
            mod.publish(sid, 1)
    allids = ','.join("'" + v + "'::uuid" for v in fixtures.values())
    visible = json.loads(mod.must_user(db, None, "SELECT coalesce(jsonb_agg(id::text),'[]') FROM public.public_session_summary WHERE id IN (" + allids + ");", 'guest summary', role='anon'))
    check('guest summary public only', visible == [fixtures['public']])
    listing = json.loads(mod.must_user(db, None, 'SELECT public.list_public_sessions();', 'guest listing', role='anon'))
    visible_ids = {x['id'] for x in listing}
    check('guest listing public only among fixtures', visible_ids.intersection(fixtures.values()) == {fixtures['public']})
    for tag in ('public','unlisted'):
        value = json.loads(mod.must_user(db, None, "SELECT public.get_session_public_detail('" + fixtures[tag] + "');", 'guest detail', role='anon'))
        check('guest detail ' + tag, value['id'] == fixtures[tag])
    for tag in ('private','draft'):
        res = mod.anon_exec(db, "SELECT public.get_session_public_detail('" + fixtures[tag] + "');")
        check('guest detail denies ' + tag, mod.expect_error(res, 'UNAUTHENTICATED'))
    check('guest venues readable', int(mod.must_user(db, None, 'SELECT count(*) FROM public.venues;', 'venues', role='anon')) > 0)
    res = mod.anon_exec(db, 'SELECT * FROM public.player_outstanding;')
    check('guest outstanding denied', mod.expect_error(res, 'permission denied'))
    sid = fixtures['public']
    p5 = mod.join(5, sid)['player_id']
    p6 = mod.join(6, sid)['player_id']
    mod.start(sid, 1)
    mod.attend(sid, p5, 1)
    mod.attend(sid, p6, 1)
    mod.post_expense(sid, 200000)
    mod.finalize(sid)
    for actor, expected in [(5,1),(6,1),(1,2),(3,2),(9,0)]:
        value = int(mod.must_user(db, actor, "SELECT count(*) FROM public.player_outstanding WHERE session_id='" + sid + "';", 'caller outstanding'))
        check('outstanding isolation actor' + str(actor), value == expected)
    for actor in (5,6):
        rows = json.loads(mod.must_user(db, actor, "SELECT jsonb_agg(user_id::text) FROM public.player_outstanding WHERE session_id='" + sid + "';", 'own identity'))
        check('outstanding identity actor' + str(actor), rows == [mod.uid(actor)])
    legacy_session_sql = """
    CREATE TEMP TABLE legacy_session_probe(venue_id uuid, venue_name text, starts_at timestamptz, ends_at timestamptz, play_date date, start_time time, end_time time);
    CREATE TRIGGER legacy_session_sync BEFORE INSERT OR UPDATE ON legacy_session_probe FOR EACH ROW EXECUTE FUNCTION public.sync_legacy_session_columns();
    GRANT SELECT,INSERT,UPDATE ON legacy_session_probe TO authenticated;
    SET ROLE authenticated;
    SELECT set_config('request.jwt.claim.sub', '""" + mod.uid(1) + """', false);
    INSERT INTO legacy_session_probe(venue_id,starts_at,ends_at) VALUES ('""" + mod.VENUE + """', '2026-11-20 03:00:00+00','2026-11-20 05:00:00+00');
    UPDATE legacy_session_probe SET starts_at='2026-11-21 04:00:00+00', ends_at='2026-11-21 06:00:00+00';
    SELECT (venue_name IS NOT NULL AND play_date='2026-11-21'::date AND start_time='11:00'::time AND end_time='13:00'::time)::text FROM legacy_session_probe;
    """
    check('legacy session trigger insert/update', mod.must(db, legacy_session_sql, 'legacy session sync').splitlines()[-1] == 'true')
    legacy_player_sql = """
    CREATE TEMP TABLE legacy_player_probe(display_name text, player_name text);
    CREATE TRIGGER legacy_player_sync BEFORE INSERT OR UPDATE ON legacy_player_probe FOR EACH ROW EXECUTE FUNCTION public.sync_legacy_session_player_columns();
    GRANT SELECT,INSERT,UPDATE ON legacy_player_probe TO authenticated;
    SET ROLE authenticated;
    INSERT INTO legacy_player_probe(display_name) VALUES ('Synthetic player');
    UPDATE legacy_player_probe SET display_name='Synthetic updated';
    SELECT (player_name=display_name AND display_name='Synthetic updated')::text FROM legacy_player_probe;
    """
    check('legacy player trigger insert/update', mod.must(db, legacy_player_sql, 'legacy player sync').splitlines()[-1] == 'true')
    receipt['status'] = 'PASS'
except Exception as exc:
    receipt['status'] = 'FAIL'
    receipt['failure'] = {'stage':stage, 'type':type(exc).__name__, 'message':str(exc)[:1200]}
finally:
    if cid:
        owned = command(['docker','inspect','--format','{{index .Config.Labels "bh07.staging.verify"}}',cid])
        if owned.returncode == 0 and owned.stdout.strip() == label:
            removed = command(['docker','rm','-f',cid])
            inventory = command(['docker','ps','-a','--no-trunc','--filter','id=' + cid,'--format','{{.ID}}'])
            receipt['cleanup_verified'] = removed.returncode == 0 and inventory.returncode == 0 and not inventory.stdout.strip()
    if not receipt['cleanup_verified']:
        receipt['status'] = 'FAIL'
    OUT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':receipt['status'],'checks':len(checks),'passed':sum(x['passed'] for x in checks),'existing_suite_count':len(receipt.get('existing_suite',[])),'cleanup_verified':receipt['cleanup_verified'],'failure':receipt.get('failure'),'receipt':str(OUT)},ensure_ascii=False))
raise SystemExit(0 if receipt['status'] == 'PASS' else 1)
