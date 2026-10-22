# BH-07 HTTP/Auth verification commands

Generated (UTC): 2026-10-22T12:25:14Z
Base SHA: `a0f831af47f98c7649e0c80dce4d5f13004a0db2` (thực tế commit cha của cbcc46c; tham số ban đầu: `a0f831ae3f47e305608bfa0dff19ae035b31f798`)
Tested checkout SHA: `cbcc46c2e125b156b53f4297ef864cf658855d37`

```powershell
npx --yes supabase@2.121.0 start
npx --yes supabase@2.121.0 db reset --local --no-seed --yes
# POST /auth/v1/admin/users for each fixture email through GoTrue Admin API
# (service role key read from local `supabase status`; never sent to a remote URL)
Get-Content scripts/bh07_http/seed.sql -Raw | docker exec -i supabase_db_badminton-hub psql -U postgres -d postgres -v ON_ERROR_STOP=1
$env:BH07_HTTP_TEST = '1'
$env:BH07_HTTP_URL = <local API_URL from `supabase status`>
$env:BH07_HTTP_ANON_KEY = <local ANON_KEY>
$env:BH07_HTTP_SERVICE_ROLE_KEY = <local SERVICE_ROLE_KEY>
flutter test test/integration/bh07_http_auth_test.dart --reporter expanded
flutter analyze
flutter test
```

Local-only guard: the runner aborts unless API_URL host is 127.0.0.1, localhost or ::1.
