import subprocess,json,os,secrets,time,urllib.request,urllib.error,hashlib,hmac,base64
from pathlib import Path
root=Path('/workspace/badminton-hub'); out=Path('/workspace/scratch/bh07-review-c8a8e7f'); private=Path('/tmp/bh07-http-review-runtime');private.mkdir(exist_ok=True);private.chmod(0o700)
def command(args,input=None):
 r=subprocess.run(args,input=input,text=True,capture_output=True)
 if r.returncode: raise RuntimeError('command failed: '+args[0]+' '+r.stderr[:300])
 return r.stdout
initial_status=command(['git','status','--porcelain']).strip()
secret=secrets.token_urlsafe(48);password=secrets.token_urlsafe(24)
def token(role):
 enc=lambda x:base64.urlsafe_b64encode(json.dumps(x,separators=(',',':')).encode()).rstrip(b'=').decode()
 raw=enc({'alg':'HS256','typ':'JWT'})+'.'+enc({'role':role,'iss':'supabase-demo','iat':int(time.time())-60,'exp':int(time.time())+7200})
 return raw+'.'+base64.urlsafe_b64encode(hmac.new(secret.encode(),raw.encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
anon=token('anon');service=token('service_role')
def envfile(name,values):
 p=private/(name+'.env');p.write_text('\n'.join(k+'='+str(v) for k,v in values.items())+'\n');p.chmod(0o600);return str(p)
command(['docker','network','create','--internal','bh07-http-review-network'])
def run(name,image,env,extra=[]):
 command(['docker','run','-d','--name',name,'--network','bh07-http-review-network','--env-file',envfile(name,env)]+extra+[image]);print('started',name,flush=True)
run('bh07-http-review-db','postgres:17',{'POSTGRES_PASSWORD':password})
for _ in range(30):
 r=subprocess.run(['docker','exec','bh07-http-review-db','pg_isready','-U','postgres'],capture_output=True)
 if r.returncode==0:break
 time.sleep(1)
bootstrap=f'''CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN BYPASSRLS;
CREATE ROLE authenticator LOGIN NOINHERIT PASSWORD '{password}';
GRANT anon,authenticated,service_role TO authenticator;
CREATE ROLE supabase_auth_admin LOGIN CREATEROLE NOINHERIT PASSWORD '{password}';
GRANT ALL ON DATABASE postgres TO supabase_auth_admin;
CREATE SCHEMA auth AUTHORIZATION supabase_auth_admin;
CREATE SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
GRANT USAGE ON SCHEMA public,auth,extensions TO anon,authenticated,service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;
'''
command(['docker','exec','-i','bh07-http-review-db','psql','-U','postgres','-v','ON_ERROR_STOP=1'],bootstrap)
(out/'bootstrap-public.sql.txt').write_text(bootstrap.replace(password,'<runtime-generated-local-password>'))
run('bh07-http-review-auth','ghcr.io/supabase/gotrue:v2.197.0',{'GOTRUE_API_HOST':'0.0.0.0','GOTRUE_API_PORT':9999,'API_EXTERNAL_URL':'http://127.0.0.1:54321','GOTRUE_SITE_URL':'http://127.0.0.1:3000','GOTRUE_DB_DRIVER':'postgres','GOTRUE_DB_DATABASE_URL':f'postgres://supabase_auth_admin:{password}@bh07-http-review-db:5432/postgres?search_path=auth','GOTRUE_JWT_SECRET':secret,'GOTRUE_JWT_EXP':3600,'GOTRUE_JWT_AUD':'authenticated','GOTRUE_JWT_DEFAULT_GROUP_NAME':'authenticated','GOTRUE_JWT_ADMIN_ROLES':'service_role','GOTRUE_EXTERNAL_EMAIL_ENABLED':'true','GOTRUE_DISABLE_SIGNUP':'false','GOTRUE_MAILER_AUTOCONFIRM':'true','GOTRUE_RATE_LIMIT_EMAIL_SENT':1000,'GOTRUE_RATE_LIMIT_SIGN_IN_SIGN_UP':1000})
for _ in range(30):
 r=subprocess.run(['docker','exec','bh07-http-review-db','psql','-U','postgres','-Atqc',"SELECT to_regclass('auth.users') IS NOT NULL"],text=True,capture_output=True)
 if r.stdout.strip()=='t':break
 time.sleep(1)
else: raise RuntimeError('GoTrue did not initialize auth.users')
# GoTrue owns and migrates auth schema; install Supabase's JWT-claims helper after its migration completes.
for _ in range(30):
 logs=command(['docker','logs','bh07-http-review-auth'])
 if 'GoTrue API started' in logs or 'GoTrue API started on' in logs:break
 time.sleep(1)
command(['docker','exec','-i','bh07-http-review-db','psql','-U','postgres','-v','ON_ERROR_STOP=1'],"CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT COALESCE(NULLIF(current_setting('request.jwt.claim.sub',true),''), (NULLIF(current_setting('request.jwt.claims',true),'')::jsonb ->> 'sub'))::uuid $$; GRANT USAGE ON SCHEMA auth TO anon,authenticated,service_role; GRANT EXECUTE ON FUNCTION auth.uid() TO anon,authenticated,service_role;")
for p in sorted((root/'supabase/migrations').glob('*.sql')):
 command(['docker','exec','-i','bh07-http-review-db','psql','-U','postgres','-v','ON_ERROR_STOP=1'],p.read_text());print('migration',p.name,flush=True)
run('bh07-http-review-rest','ghcr.io/supabase/postgrest:v16.4',{'PGRST_DB_URI':f'postgres://authenticator:{password}@bh07-http-review-db:5432/postgres','PGRST_DB_SCHEMAS':'public','PGRST_DB_ANON_ROLE':'anon','PGRST_JWT_SECRET':secret,'PGRST_SERVER_PORT':3000})
kong={'_format_version':'2.1','_transform':True,'consumers':[{'username':'anon','keyauth_credentials':[{'key':anon}]},{'username':'service_role','keyauth_credentials':[{'key':service}]}],'services':[{'name':'auth','url':'http://bh07-http-review-auth:9999/','routes':[{'name':'auth','paths':['/auth/v1/'],'strip_path':True}],'plugins':[{'name':'key-auth','config':{'key_names':['apikey'],'hide_credentials':False}}]},{'name':'rest','url':'http://bh07-http-review-rest:3000/','routes':[{'name':'rest','paths':['/rest/v1/'],'strip_path':True}],'plugins':[{'name':'key-auth','config':{'key_names':['apikey'],'hide_credentials':False}}]}]}
for svc in kong['services']:
 svc['plugins'].append({'name':'cors','config':{'origins':['http://127.0.0.1:8088'],'methods':['GET','POST','PUT','PATCH','DELETE','OPTIONS'],'headers':['authorization','apikey','content-type','x-client-info','accept-profile','content-profile'],'credentials':True}})
p=private/'kong.json';p.write_text(json.dumps(kong));p.chmod(0o644)
run('bh07-http-review-kong','ghcr.io/supabase/kong:2.8.1',{'KONG_DATABASE':'off','KONG_DECLARATIVE_CONFIG':'/home/kong/kong.json','KONG_PROXY_LISTEN':'0.0.0.0:8000','KONG_ADMIN_LISTEN':'off'},['-p','127.0.0.1:54321:8000','--mount',f'type=bind,src={p},dst=/home/kong/kong.json,readonly'])
command(['docker','network','connect','bridge','bh07-http-review-kong'])
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
url='http://127.0.0.1:54321'; assert urllib.parse.urlparse(url).hostname in ('127.0.0.1','localhost','::1')
for _ in range(40):
 try:
  req=urllib.request.Request(url+'/auth/v1/health',headers={'apikey':anon});opener.open(req,timeout=2).read();break
 except Exception:time.sleep(1)
else:raise RuntimeError('local gateway/auth health failed')
users=['ownera','financea','cohosta','membera','guesta','ownerb','outsider']
for name in users:
 body=json.dumps({'email':name+'@example.test','password':'bh07-http-pass-123456','email_confirm':True,'user_metadata':{'display_name':name}}).encode()
 req=urllib.request.Request(url+'/auth/v1/admin/users',data=body,headers={'apikey':service,'Authorization':'Bearer '+service,'Content-Type':'application/json'})
 with opener.open(req,timeout=20) as r:created=json.load(r)
 print('created local Auth user',name,created['id'],flush=True)
command(['docker','exec','-i','bh07-http-review-db','psql','-U','postgres','-v','ON_ERROR_STOP=1'],(root/'scripts/bh07_http/seed.sql').read_text())

(out/'stack-ready.txt').write_text('GoTrue v2.197.0; PostgREST v16.4; PostgreSQL17.11; Kong2.8.1; local only.\n')
