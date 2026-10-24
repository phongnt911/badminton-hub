import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\Users\POTA\Documents\GitHub\badminton-hub")
OUT = Path(r"C:\Users\POTA\AppData\Local\Temp\bh07-v1-review")
OUT.mkdir(parents=True, exist_ok=True)
PRIVATE = OUT / "private"
PRIVATE.mkdir(exist_ok=True)
PASSWORD = secrets.token_urlsafe(40)
SECRET = secrets.token_urlsafe(48)
NETWORK = "bh07v1-net"
KONG_PORT = 55422
PREFIX = "bh07v1"


def cmd(args, input_text=None, check=True, timeout=180):
    r = subprocess.run(args, input=input_text, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError(f"command failed {r.returncode}: {args[:3]} stderr={r.stderr[-2000:]}")
    return r


def docker(*args, **kw):
    return cmd(["docker", *args], **kw)


def wait_db():
    for _ in range(60):
        r = docker("exec", f"{PREFIX}-db", "pg_isready", "-U", "postgres", check=False)
        if r.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError("db not ready")


def token(role):
    def enc(x):
        return base64.urlsafe_b64encode(json.dumps(x, separators=(",", ":")).encode()).rstrip(b"=").decode()
    raw = enc({"alg": "HS256", "typ": "JWT"}) + "." + enc({
        "role": role, "iss": "supabase-demo", "iat": int(time.time()) - 60, "exp": int(time.time()) + 7200
    })
    return raw + "." + base64.urlsafe_b64encode(
        hmac.new(SECRET.encode(), raw.encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()


# Cleanup any previous attempt with the same names, only local containers/network.
for name in [f"{PREFIX}-kong", f"{PREFIX}-rest", f"{PREFIX}-auth", f"{PREFIX}-db"]:
    docker("rm", "-f", name, check=False)
docker("network", "rm", NETWORK, check=False)

docker("network", "create", "--internal", NETWORK)
env = {"POSTGRES_PASSWORD": PASSWORD}
(PRIVATE / "db.env").write_text("\n".join(f"{k}={v}" for k, v in env.items()) + "\n", encoding="utf-8")
docker("run", "-d", "--name", f"{PREFIX}-db", "--network", NETWORK, "--env-file", str(PRIVATE / "db.env"), "postgres:17")
wait_db()

bootstrap = f'''
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN BYPASSRLS;
CREATE ROLE authenticator LOGIN NOINHERIT PASSWORD '{PASSWORD}';
GRANT anon,authenticated,service_role TO authenticator;
CREATE ROLE supabase_auth_admin LOGIN CREATEROLE NOINHERIT PASSWORD '{PASSWORD}';
GRANT ALL ON DATABASE postgres TO supabase_auth_admin;
CREATE SCHEMA auth AUTHORIZATION supabase_auth_admin;
CREATE SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
GRANT USAGE ON SCHEMA public,auth,extensions TO anon,authenticated,service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;
'''
docker("exec", "-i", f"{PREFIX}-db", "psql", "-U", "postgres", "-v", "ON_ERROR_STOP=1", input_text=bootstrap)
(OUT / "bootstrap.sql.txt").write_text(bootstrap.replace(PASSWORD, "<runtime-local-password>"), encoding="utf-8")

auth_env = {
    "GOTRUE_API_HOST": "0.0.0.0",
    "GOTRUE_API_PORT": "9999",
    "API_EXTERNAL_URL": f"http://127.0.0.1:{KONG_PORT}",
    "GOTRUE_SITE_URL": "http://127.0.0.1:8088",
    "GOTRUE_DB_DRIVER": "postgres",
    "GOTRUE_DB_DATABASE_URL": f"postgres://supabase_auth_admin:{PASSWORD}@{PREFIX}-db:5432/postgres?search_path=auth",
    "GOTRUE_JWT_SECRET": SECRET,
    "GOTRUE_JWT_EXP": "3600",
    "GOTRUE_JWT_AUD": "authenticated",
    "GOTRUE_JWT_DEFAULT_GROUP_NAME": "authenticated",
    "GOTRUE_JWT_ADMIN_ROLES": "service_role",
    "GOTRUE_EXTERNAL_EMAIL_ENABLED": "true",
    "GOTRUE_DISABLE_SIGNUP": "false",
    "GOTRUE_MAILER_AUTOCONFIRM": "true",
    "GOTRUE_RATE_LIMIT_EMAIL_SENT": "1000",
    "GOTRUE_RATE_LIMIT_SIGN_IN_SIGN_UP": "1000",
}
(PRIVATE / "auth.env").write_text("\n".join(f"{k}={v}" for k, v in auth_env.items()) + "\n", encoding="utf-8")
docker("run", "-d", "--name", f"{PREFIX}-auth", "--network", NETWORK, "--env-file", str(PRIVATE / "auth.env"),
       "ghcr.io/supabase/gotrue:v2.197.0")

for _ in range(60):
    r = docker("exec", f"{PREFIX}-db", "psql", "-U", "postgres", "-Atqc",
               "SELECT to_regclass('auth.users') IS NOT NULL", check=False)
    if r.stdout.strip() == "t":
        break
    time.sleep(1)
else:
    raise RuntimeError("GoTrue did not initialize auth.users")

for _ in range(60):
    logs = docker("logs", f"{PREFIX}-auth", check=False)
    if "GoTrue API started" in (logs.stdout + logs.stderr):
        break
    time.sleep(1)
else:
    raise RuntimeError("GoTrue did not start")

docker("exec", "-i", f"{PREFIX}-db", "psql", "-U", "postgres", "-v", "ON_ERROR_STOP=1", input_text="""
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT COALESCE(NULLIF(current_setting('request.jwt.claim.sub',true),''),
                  (NULLIF(current_setting('request.jwt.claims',true),'')::jsonb ->> 'sub'))::uuid
$$;
GRANT USAGE ON SCHEMA auth TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION auth.uid() TO anon,authenticated,service_role;
""")

for p in sorted((ROOT / "supabase/migrations").glob("*.sql")):
    docker("exec", "-i", f"{PREFIX}-db", "psql", "-U", "postgres", "-v", "ON_ERROR_STOP=1", input_text=p.read_text(encoding="utf-8"))
    print("migration", p.name, flush=True)

rest_env = {
    "PGRST_DB_URI": f"postgres://authenticator:{PASSWORD}@{PREFIX}-db:5432/postgres",
    "PGRST_DB_SCHEMAS": "public",
    "PGRST_DB_ANON_ROLE": "anon",
    "PGRST_JWT_SECRET": SECRET,
    "PGRST_SERVER_PORT": "3000",
}
(PRIVATE / "rest.env").write_text("\n".join(f"{k}={v}" for k, v in rest_env.items()) + "\n", encoding="utf-8")
docker("run", "-d", "--name", f"{PREFIX}-rest", "--network", NETWORK, "--env-file", str(PRIVATE / "rest.env"),
       "ghcr.io/supabase/postgrest:v16.4")

anon = token("anon")
service = token("service_role")
kong = {
    "_format_version": "2.1",
    "_transform": True,
    "consumers": [
        {"username": "anon", "keyauth_credentials": [{"key": anon}]},
        {"username": "service_role", "keyauth_credentials": [{"key": service}]},
    ],
    "services": [
        {
            "name": "auth", "url": f"http://{PREFIX}-auth:9999/",
            "routes": [{"name": "auth", "paths": ["/auth/v1/"], "strip_path": True}],
            "plugins": [{"name": "key-auth", "config": {"key_names": ["apikey"], "hide_credentials": False}},
                        {"name": "cors", "config": {
                            "origins": ["http://127.0.0.1:8088"],
                            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                            "headers": ["authorization", "apikey", "content-type", "x-client-info",
                                        "accept-profile", "content-profile", "x-supabase-api-version"],
                            "credentials": True,
                        }}],
        },
        {
            "name": "rest", "url": f"http://{PREFIX}-rest:3000/",
            "routes": [{"name": "rest", "paths": ["/rest/v1/"], "strip_path": True}],
            "plugins": [{"name": "key-auth", "config": {"key_names": ["apikey"], "hide_credentials": False}},
                        {"name": "cors", "config": {
                            "origins": ["http://127.0.0.1:8088"],
                            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                            "headers": ["authorization", "apikey", "content-type", "x-client-info",
                                        "accept-profile", "content-profile", "x-supabase-api-version"],
                            "credentials": True,
                        }}],
        },
    ],
}
(PRIVATE / "kong.json").write_text(json.dumps(kong), encoding="utf-8")
docker("run", "-d", "--name", f"{PREFIX}-kong", "--network", NETWORK,
       "-p", f"127.0.0.1:{KONG_PORT}:8000",
       "-e", "KONG_DATABASE=off",
       "-e", "KONG_DECLARATIVE_CONFIG=/home/kong/kong.json",
       "-e", "KONG_PROXY_LISTEN=0.0.0.0:8000",
       "-e", "KONG_ADMIN_LISTEN=off",
       "--mount", f"type=bind,src={PRIVATE / 'kong.json'},dst=/home/kong/kong.json,readonly",
       "ghcr.io/supabase/kong:2.8.1")
docker("network", "connect", "bridge", f"{PREFIX}-kong")

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
url = f"http://127.0.0.1:{KONG_PORT}"
for _ in range(60):
    try:
        req = urllib.request.Request(url + "/auth/v1/health", headers={"apikey": anon})
        opener.open(req, timeout=2).read()
        break
    except Exception:
        time.sleep(1)
else:
    raise RuntimeError("local gateway/auth health failed")

users = ["ownera", "financea", "cohosta", "membera", "guesta", "ownerb", "outsider"]
user_ids = {}
for name in users:
    body = json.dumps({
        "email": name + "@example.test",
        "password": "bh07-http-pass-123456",
        "email_confirm": True,
        "user_metadata": {"display_name": name},
    }).encode()
    req = urllib.request.Request(
        url + "/auth/v1/admin/users", data=body,
        headers={"apikey": service, "Authorization": "Bearer " + service, "Content-Type": "application/json"},
    )
    with opener.open(req, timeout=20) as r:
        created = json.load(r)
    user_ids[name] = created["id"]
    print("created", name, created["id"], flush=True)

docker("exec", "-i", f"{PREFIX}-db", "psql", "-U", "postgres", "-v", "ON_ERROR_STOP=1",
       input_text=(ROOT / "scripts/bh07_http/seed.sql").read_text(encoding="utf-8"))

src = (ROOT / "scripts/bh07_browser/seed_setup.js").read_text(encoding="utf-8")
ui_sql = src.split("const uiSessionSql = `", 1)[1].split("`;", 1)[0]
docker("exec", "-i", f"{PREFIX}-db", "psql", "-U", "postgres", "-v", "ON_ERROR_STOP=1", input_text=ui_sql)

meta = {
    "network": NETWORK,
    "kong_port": KONG_PORT,
    "api_url": url,
    "anon": anon,
    "service": service,
    "password": PASSWORD,
    "secret": SECRET,
    "users": user_ids,
    "stack": {
        "postgres": "postgres:17 (17.11)",
        "gotrue": "ghcr.io/supabase/gotrue:v2.197.0",
        "postgrest": "ghcr.io/supabase/postgrest:v16.4",
        "kong": "ghcr.io/supabase/kong:2.8.1",
    },
}
(PRIVATE / "runtime.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
(OUT / "stack-ready.txt").write_text(
    "isolated local stack ready; not staging/production; runtime credentials stored outside repo\n", encoding="utf-8"
)
print("STACK READY", url)
