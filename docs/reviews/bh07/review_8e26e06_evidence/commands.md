# V5b Full Supabase Reset Verification Commands

```powershell
# Prepare isolated project directory
prepare_project_dir(C:\Users\POTA\AppData\Local\Temp\bh07-reset-verify-ddcc615aacfe4e5c) with dedicated ports 56421-56429

# Start isolated stack
npx supabase start --workdir C:\Users\POTA\AppData\Local\Temp\bh07-reset-verify-ddcc615aacfe4e5c

# Reset cycle 1
npx supabase db reset --workdir C:\Users\POTA\AppData\Local\Temp\bh07-reset-verify-ddcc615aacfe4e5c --local --no-seed --yes

# Reset cycle 2
npx supabase db reset --workdir C:\Users\POTA\AppData\Local\Temp\bh07-reset-verify-ddcc615aacfe4e5c --local --no-seed --yes

# Stop isolated stack
npx supabase stop --workdir C:\Users\POTA\AppData\Local\Temp\bh07-reset-verify-ddcc615aacfe4e5c --no-backup
```
