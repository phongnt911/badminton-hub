# V5b Full Supabase Reset Verification Commands

```powershell
# Prepare isolated project directory
prepare_project_dir(C:\Users\POTA\AppData\Local\Temp\bh07-reset-verify-b7c271296ef940fa) with dedicated ports 56421-56429

# Start isolated stack
npx --yes supabase@2.122.0 start --workdir C:\Users\POTA\AppData\Local\Temp\bh07-reset-verify-b7c271296ef940fa

# Reset cycle 1
npx --yes supabase@2.122.0 db reset --workdir C:\Users\POTA\AppData\Local\Temp\bh07-reset-verify-b7c271296ef940fa --local --no-seed --yes

# Reset cycle 2
npx --yes supabase@2.122.0 db reset --workdir C:\Users\POTA\AppData\Local\Temp\bh07-reset-verify-b7c271296ef940fa --local --no-seed --yes

# Stop isolated stack
npx --yes supabase@2.122.0 stop --workdir C:\Users\POTA\AppData\Local\Temp\bh07-reset-verify-b7c271296ef940fa --no-backup
```
