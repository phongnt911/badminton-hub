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

  console.log('--- Step 5: Seeding UI flow specific session (published -> in_progress -> complete) ---');
  const uiSessionSql = `
    DO $$
    DECLARE
      v_owner_a uuid;
      v_cohost_a uuid;
      v_member_a uuid;
      v_guest_a uuid;
      v_club_a constant uuid := 'aaaaaaaa-1111-4111-8111-111111111111';
      v_venue constant uuid := 'cccccccc-3333-4333-8333-333333333333';
      v_member_a_row constant uuid := 'a0000004-0000-4000-8000-000000000004';
      v_session_ui constant uuid := '10000000-0000-4000-8000-000000000099';
      v_p1 constant uuid := '30000000-0000-4000-8000-000000000091';
      v_p2 constant uuid := '30000000-0000-4000-8000-000000000092';
    BEGIN
      SELECT id INTO v_owner_a FROM auth.users WHERE email = 'ownera@example.test';
      SELECT id INTO v_cohost_a FROM auth.users WHERE email = 'cohosta@example.test';
      SELECT id INTO v_member_a FROM auth.users WHERE email = 'membera@example.test';
      SELECT id INTO v_guest_a FROM auth.users WHERE email = 'guesta@example.test';

      INSERT INTO public.sessions (
        id, club_id, host_user_id, venue_id, title, description,
        starts_at, ends_at, capacity, court_count, visibility, lifecycle,
        approval_mode, fee_mode, version, billing_input_version
      ) VALUES (
        v_session_ui, v_club_a, v_owner_a, v_venue, 'UI Flow Session published to complete',
        'Session seeded in published state to test real start -> checkin -> finalize -> complete via UI',
        now() + interval '1 hour', now() + interval '3 hours', 8, 2,
        'public', 'published', 'auto_confirm', 'split_actual', 1, 1
      ) ON CONFLICT (id) DO UPDATE SET
        lifecycle = 'published',
        version = 1,
        billing_input_version = 1;

      INSERT INTO public.session_staff (session_id, user_id, role, status)
      VALUES (v_session_ui, v_cohost_a, 'cohost', 'active')
      ON CONFLICT DO NOTHING;

      INSERT INTO public.session_players (
        id, session_id, user_id, club_member_id, display_name,
        registration_status, attendance_status, source, participant_type,
        fee_exempt, requested_at, confirmed_at, created_by
      ) VALUES
        (v_p1, v_session_ui, v_member_a, v_member_a_row, 'Member A',
         'confirmed', 'not_checked_in', 'self', 'member', false,
         now() - interval '2 hours', now() - interval '2 hours', v_member_a),
        (v_p2, v_session_ui, v_guest_a, NULL, 'Guest A',
         'confirmed', 'not_checked_in', 'self', 'guest', false,
         now() - interval '2 hours', now() - interval '2 hours', v_guest_a)
      ON CONFLICT (id) DO UPDATE SET
        attendance_status = 'not_checked_in';

      -- Seed non-zero court expense so totals reflect actual numbers > 0 (BR3)
      INSERT INTO public.session_expenses (
        id, session_id, category, title, amount_vnd, status, created_by
      ) VALUES (
        '50000000-0000-4000-8000-000000000099',
        v_session_ui,
        'court',
        'Tiền thuê sân 2h',
        200000,
        'posted',
        v_owner_a
      ) ON CONFLICT (id) DO UPDATE SET
        amount_vnd = 200000,
        status = 'posted';
    END $$;
  `;
  execSync(`docker exec -i ${dbContainer} psql -U postgres -d postgres -v ON_ERROR_STOP=1`, {
    input: uiSessionSql,
    stdio: ['pipe', 'inherit', 'inherit'],
  });

  console.log('--- Seeding completed successfully! ---');
}

main().catch(err => {
  console.error('Seed setup failed:', err);
  process.exit(1);
});
