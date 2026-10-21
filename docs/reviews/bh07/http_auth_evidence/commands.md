# BH-07 HTTP/Auth verification commands

Generated (UTC): 2026-10-21T08:34:12Z
Base SHA: `593bea86ffb807675387dba6b0276b555fdc87a1`
Tested checkout SHA: `f9159dd483baf2dd219b2854fd8ab08d1e5f0330`

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

## Hồi quy sau ma trận HTTP/Auth

```powershell
flutter analyze
flutter test
python docs/reviews/bh07/run_bh07_tests.py
```

Kết quả ngày 21/10/2026 trên tested source `f9159dd483baf2dd219b2854fd8ab08d1e5f0330`:

- HTTP/Auth: 70/70 PASS, exit 0, `worktree_dirty_before_run=false`.
- `flutter analyze`: sạch, exit 0.
- `flutter test`: 240 pass + 1 skip (HTTP matrix tự skip khi không đặt `BH07_HTTP_TEST=1`), exit 0.
- BH-07 DB runner: 23/23 PASS, exit 0, `worktree_dirty=false`, timestamp `20261021083531`.
- Red run trước seed fix: 67/70, exit 1 (đúng 3 FAIL H1/H2).

## Hash cuối

`hashes.sha256` trong thư mục này phủ source script/test, handoff, toàn bộ evidence và bản sao JSON DB runner:

```powershell
Get-ChildItem docs/reviews/bh07/http_auth_evidence -File |
  Where-Object Name -ne 'hashes.sha256' |
  ForEach-Object {
    $relative = $_.FullName.Substring((Resolve-Path .).Path.Length + 1)
    "$((Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLowerInvariant())  $relative"
  }
```
