const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

async function main() {
  console.log('--- Step 1: Getting Supabase status ---');
  const statusRaw = execSync('npx --yes supabase@2.121.0 status -o json', { encoding: 'utf-8' });
  const jsonStart = statusRaw.indexOf('{');
  const jsonEnd = statusRaw.lastIndexOf('}');
  const status = JSON.parse(statusRaw.substring(jsonStart, jsonEnd + 1));

  const apiUrl = status.API_URL;
  const anonKey = status.ANON_KEY;
  const serviceRoleKey = status.SERVICE_ROLE_KEY;
  console.log(`API URL: ${apiUrl}`);

  const users = [
    { email: 'ownera@example.test', name: 'Owner A' },
    { email: 'financea@example.test', name: 'Finance A' },
    { email: 'cohosta@example.test', name: 'Cohost A' },
    { email: 'membera@example.test', name: 'Member A' },
    { email: 'guesta@example.test', name: 'Guest A' },
    { email: 'ownerb@example.test', name: 'Owner B' },
    { email: 'outsider@example.test', name: 'Outsider' },
  ];

  console.log('--- Step 2: Ensuring GoTrue Auth users exist ---');
  for (const u of users) {
    const res = await fetch(`${apiUrl}/auth/v1/admin/users`, {
      method: 'POST',
      headers: {
        'apikey': serviceRoleKey,
        'Authorization': `Bearer ${serviceRoleKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: u.email,
        password: 'bh07-http-pass-123456',
        email_confirm: true,
        user_metadata: { display_name: u.name },
      }),
    });
    if (!res.ok) {
      const errText = await res.text();
      // 422 email_exists is expected on re-runs
      if (!errText.includes('email_exists')) {
        console.warn(`User ${u.email} note: ${res.status} ${errText}`);
      }
    } else {
      const data = await res.json();
      console.log(`Created user ${u.email} (id: ${data.id})`);
    }
  }

  console.log('--- Step 3: Truncating fixture tables for clean re-seed ---');
  const dbContainer = 'supabase_db_badminton-hub';
  execSync(`docker exec -i ${dbContainer} psql -U postgres -d postgres -c "TRUNCATE TABLE venues, clubs, club_members, sessions, session_staff, session_players, member_contacts, session_player_contacts, club_bank_accounts, host_bank_accounts, session_expenses, charge_revisions, session_charges, payments, club_transactions, operation_requests, audit_events RESTART IDENTITY CASCADE;"`, {
    stdio: 'inherit',
  });

  console.log('--- Step 4: Seeding SQL fixtures ---');
  const seedSqlPath = path.resolve(__dirname, '../bh07_http/seed.sql');
  const seedContent = fs.readFileSync(seedSqlPath);
  execSync(`docker exec -i ${dbContainer} psql -U postgres -d postgres -v ON_ERROR_STOP=1`, {
    input: seedContent,
    stdio: ['pipe', 'inherit', 'inherit'],
  });

  console.log('--- Seeding completed successfully! ---');
}

main().catch(err => {
  console.error('Seed setup failed:', err);
  process.exit(1);
});
