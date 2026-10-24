-- BH-07 HTTP/Auth verification seed (local isolated Supabase only).
--
-- Preconditions:
--   * `supabase db reset --local --no-seed` completed.
--   * Auth users below were created through GoTrue Admin API:
--       ownera@example.test, financea@example.test, cohosta@example.test,
--       membera@example.test, guesta@example.test, ownerb@example.test,
--       outsider@example.test
--   * The password is supplied only by the local runner; it is not stored here.
--
-- This file only writes fixture rows. It does not alter a contract, RPC,
-- migration or permission. Deterministic IDs let the HTTP test address the
-- same fixture across resets.

DO $$
DECLARE
  v_owner_a uuid;
  v_finance_a uuid;
  v_cohost_a uuid;
  v_member_a uuid;
  v_guest_a uuid;
  v_owner_b uuid;
  v_outsider uuid;

  v_club_a constant uuid := 'aaaaaaaa-1111-4111-8111-111111111111';
  v_club_b constant uuid := 'bbbbbbbb-2222-4222-8222-222222222222';
  v_venue constant uuid := 'cccccccc-3333-4333-8333-333333333333';

  v_member_a_row constant uuid := 'a0000004-0000-4000-8000-000000000004';
  v_player_debt_member constant uuid := '30000000-0000-4000-8000-000000000001';
  v_player_debt_guest constant uuid := '30000000-0000-4000-8000-000000000002';
  v_player_free_guest constant uuid := '30000000-0000-4000-8000-000000000003';
  v_player_stale constant uuid := '30000000-0000-4000-8000-000000000004';
  v_player_version constant uuid := '30000000-0000-4000-8000-000000000005';
  v_player_fin constant uuid := '30000000-0000-4000-8000-000000000006';

  v_session_debt constant uuid := '10000000-0000-4000-8000-000000000001';
  v_session_free constant uuid := '10000000-0000-4000-8000-000000000002';
  v_session_stale constant uuid := '10000000-0000-4000-8000-000000000003';
  v_session_version constant uuid := '10000000-0000-4000-8000-000000000004';
  v_session_fin constant uuid := '10000000-0000-4000-8000-000000000005';
  v_session_cancelled constant uuid := '10000000-0000-4000-8000-000000000006';
  v_session_private constant uuid := '10000000-0000-4000-8000-000000000007';
  v_session_club_b constant uuid := '20000000-0000-4000-8000-000000000001';

  v_rev_debt constant uuid := '40000000-0000-4000-8000-000000000001';
  v_rev_free constant uuid := '40000000-0000-4000-8000-000000000002';
  v_rev_stale constant uuid := '40000000-0000-4000-8000-000000000003';
  v_rev_version constant uuid := '40000000-0000-4000-8000-000000000004';
  v_rev_fin constant uuid := '40000000-0000-4000-8000-000000000005';

  v_session_cc_complete constant uuid := '20000000-0000-4000-8000-000000000002';
  v_session_cc_competing constant uuid := '20000000-0000-4000-8000-000000000003';
  v_session_cc_pay constant uuid := '20000000-0000-4000-8000-000000000004';
  v_session_cc_drop constant uuid := '20000000-0000-4000-8000-000000000005';

  v_player_cc_complete constant uuid := '30000000-0000-4000-8000-000000000021';
  v_player_cc_competing constant uuid := '30000000-0000-4000-8000-000000000022';
  v_player_cc_pay constant uuid := '30000000-0000-4000-8000-000000000023';
  v_player_cc_drop constant uuid := '30000000-0000-4000-8000-000000000024';

  v_rev_cc_complete constant uuid := '40000000-0000-4000-8000-000000000021';
  v_rev_cc_competing constant uuid := '40000000-0000-4000-8000-000000000022';
  v_rev_cc_pay constant uuid := '40000000-0000-4000-8000-000000000023';
  v_rev_cc_drop constant uuid := '40000000-0000-4000-8000-000000000024';

  v_expense_debt constant uuid := '50000000-0000-4000-8000-000000000001';
  v_expense_fin constant uuid := '50000000-0000-4000-8000-000000000002';
  v_payment_debt constant uuid := '60000000-0000-4000-8000-000000000001';
  v_ledger_debt_expense constant uuid := '70000000-0000-4000-8000-000000000001';
  v_ledger_fin_expense constant uuid := '70000000-0000-4000-8000-000000000002';
  v_ledger_debt_payment constant uuid := '70000000-0000-4000-8000-000000000003';
BEGIN
  SELECT id INTO v_owner_a FROM auth.users WHERE email = 'ownera@example.test';
  SELECT id INTO v_finance_a FROM auth.users WHERE email = 'financea@example.test';
  SELECT id INTO v_cohost_a FROM auth.users WHERE email = 'cohosta@example.test';
  SELECT id INTO v_member_a FROM auth.users WHERE email = 'membera@example.test';
  SELECT id INTO v_guest_a FROM auth.users WHERE email = 'guesta@example.test';
  SELECT id INTO v_owner_b FROM auth.users WHERE email = 'ownerb@example.test';
  SELECT id INTO v_outsider FROM auth.users WHERE email = 'outsider@example.test';

  IF v_owner_a IS NULL OR v_finance_a IS NULL OR v_cohost_a IS NULL
     OR v_member_a IS NULL OR v_guest_a IS NULL OR v_owner_b IS NULL
     OR v_outsider IS NULL THEN
    RAISE EXCEPTION 'BH-07 HTTP seed requires all seven Auth users; create them through GoTrue Admin API first';
  END IF;

  INSERT INTO public.venues (id, name, address, area, court_count, status)
  VALUES (v_venue, 'HTTP Venue A', 'Local test venue', 'Local', 4, 'active');

  INSERT INTO public.clubs (id, owner_user_id, name, description, visibility, status)
  VALUES
    (v_club_a, v_owner_a, 'HTTP Club A', 'Owned by owner A', 'public', 'active'),
    (v_club_b, v_owner_b, 'HTTP Club B', 'Owned by owner B', 'public', 'active');

  INSERT INTO public.club_members (id, club_id, user_id, display_name, role, status, joined_at)
  VALUES
    ('a0000001-0000-4000-8000-000000000001', v_club_a, v_owner_a, 'Owner A', 'owner', 'active', now()),
    ('a0000002-0000-4000-8000-000000000002', v_club_a, v_finance_a, 'Finance A', 'treasurer', 'active', now()),
    ('a0000003-0000-4000-8000-000000000003', v_club_a, v_cohost_a, 'Cohost A', 'member', 'active', now()),
    (v_member_a_row, v_club_a, v_member_a, 'Member A', 'member', 'active', now()),
    ('b0000001-0000-4000-8000-000000000001', v_club_b, v_owner_b, 'Owner B', 'owner', 'active', now());

  INSERT INTO public.sessions (
    id, club_id, host_user_id, venue_id, title, description,
    starts_at, ends_at, capacity, court_count, visibility, lifecycle,
    approval_mode, fee_mode, version, billing_input_version
  ) VALUES
    (v_session_debt, v_club_a, v_owner_a, v_venue, 'HTTP current with debt',
     'Current billing, two present players, one partial payment',
     '2026-10-20 10:00:00+00', '2026-10-20 12:00:00+00', 8, 2,
     'public', 'in_progress', 'auto_confirm', 'split_actual', 7, 2),
    (v_session_free, v_club_a, v_owner_a, v_venue, 'HTTP free current',
     'Current billing with zero allocation',
     '2026-10-19 10:00:00+00', '2026-10-19 12:00:00+00', 8, 1,
     'public', 'in_progress', 'auto_confirm', 'split_actual', 3, 1),
    (v_session_stale, v_club_a, v_owner_a, v_venue, 'HTTP stale billing',
     'Active revision is stale',
     '2026-10-21 10:00:00+00', '2026-10-21 12:00:00+00', 8, 1,
     'unlisted', 'in_progress', 'auto_confirm', 'split_actual', 2, 3),
    (v_session_version, v_club_a, v_owner_a, v_venue, 'HTTP version guard',
     'Current billing for wrong-version and cross-club checks',
     '2026-10-22 10:00:00+00', '2026-10-22 12:00:00+00', 8, 1,
     'public', 'in_progress', 'auto_confirm', 'split_actual', 5, 1),
    (v_session_fin, v_club_a, v_owner_a, v_venue, 'HTTP finance after complete',
     'Completed session for expense reversal and refinalize',
     '2026-10-17 10:00:00+00', '2026-10-17 12:00:00+00', 8, 1,
     'unlisted', 'completed', 'auto_confirm', 'split_actual', 4, 4),
    (v_session_cancelled, v_club_a, v_owner_a, v_venue, 'HTTP cancelled history',
     'Cancelled session in history',
     '2026-10-18 10:00:00+00', '2026-10-18 12:00:00+00', 8, 1,
     'public', 'cancelled', 'auto_confirm', 'split_actual', 2, 1),
    (v_session_private, v_club_a, v_owner_a, v_venue, 'HTTP private history',
     'Private completed session',
     '2026-10-16 10:00:00+00', '2026-10-16 12:00:00+00', 8, 1,
     'private', 'completed', 'auto_confirm', 'split_actual', 2, 1),
    (v_session_club_b, v_club_b, v_owner_b, v_venue, 'HTTP club B history',
     'Completed session owned by club B',
     '2026-10-15 10:00:00+00', '2026-10-15 12:00:00+00', 8, 1,
     'public', 'completed', 'auto_confirm', 'split_actual', 2, 1),
    (v_session_cc_complete, v_club_b, v_owner_b, v_venue, 'HTTP concurrency complete replay',
     'In-progress session for concurrent complete replay idempotency',
     '2026-10-25 10:00:00+00', '2026-10-25 12:00:00+00', 8, 1,
     'public', 'in_progress', 'auto_confirm', 'split_actual', 3, 1),
    (v_session_cc_competing, v_club_b, v_owner_b, v_venue, 'HTTP concurrency complete competing',
     'In-progress session for concurrent competing complete conflict',
     '2026-10-25 14:00:00+00', '2026-10-25 16:00:00+00', 8, 1,
     'public', 'in_progress', 'auto_confirm', 'split_actual', 3, 1),
    (v_session_cc_pay, v_club_b, v_owner_b, v_venue, 'HTTP concurrency payments',
     'In-progress session for concurrent cash replay and competing overcollect checks',
     '2026-10-26 10:00:00+00', '2026-10-26 12:00:00+00', 8, 1,
     'public', 'in_progress', 'auto_confirm', 'split_actual', 3, 1),
    (v_session_cc_drop, v_club_b, v_owner_b, v_venue, 'HTTP concurrency transport drop',
     'In-progress session for transport drop response simulation and retry',
     '2026-10-26 14:00:00+00', '2026-10-26 16:00:00+00', 8, 1,
     'public', 'in_progress', 'auto_confirm', 'split_actual', 3, 1);

  INSERT INTO public.session_staff (session_id, user_id, role, status)
  VALUES (v_session_debt, v_cohost_a, 'cohost', 'active');

  INSERT INTO public.session_players (
    id, session_id, user_id, club_member_id, display_name,
    registration_status, attendance_status, source, participant_type,
    fee_exempt, requested_at, confirmed_at, checked_in_at, checked_in_by, created_by
  ) VALUES
    (v_player_debt_member, v_session_debt, v_member_a, v_member_a_row, 'Member A',
     'confirmed', 'present', 'self', 'member', false,
     '2026-10-18 10:00:00+00', '2026-10-18 10:01:00+00', '2026-10-20 10:05:00+00', v_owner_a, v_member_a),
    (v_player_debt_guest, v_session_debt, v_guest_a, NULL, 'Guest A',
     'confirmed', 'present', 'self', 'guest', false,
     '2026-10-18 10:02:00+00', '2026-10-18 10:03:00+00', '2026-10-20 10:06:00+00', v_owner_a, v_guest_a),
    (v_player_free_guest, v_session_free, v_guest_a, NULL, 'Guest A',
     'confirmed', 'present', 'self', 'guest', true,
     '2026-10-17 10:00:00+00', '2026-10-17 10:01:00+00', '2026-10-19 10:05:00+00', v_owner_a, v_guest_a),
    (v_player_stale, v_session_stale, v_member_a, v_member_a_row, 'Member A',
     'confirmed', 'present', 'self', 'member', false,
     '2026-10-19 10:00:00+00', '2026-10-19 10:01:00+00', '2026-10-21 10:05:00+00', v_owner_a, v_member_a),
    (v_player_version, v_session_version, v_member_a, v_member_a_row, 'Member A',
     'confirmed', 'present', 'self', 'member', false,
     '2026-10-20 10:00:00+00', '2026-10-20 10:01:00+00', '2026-10-22 10:05:00+00', v_owner_a, v_member_a),
    (v_player_fin, v_session_fin, v_guest_a, NULL, 'Guest A',
     'confirmed', 'present', 'self', 'guest', false,
     '2026-10-15 10:00:00+00', '2026-10-15 10:01:00+00', '2026-10-17 10:05:00+00', v_owner_a, v_guest_a),
    (v_player_cc_complete, v_session_cc_complete, v_guest_a, NULL, 'Guest A',
     'confirmed', 'present', 'self', 'guest', false,
     '2026-10-24 10:00:00+00', '2026-10-24 10:01:00+00', '2026-10-25 10:05:00+00', v_owner_b, v_guest_a),
    (v_player_cc_competing, v_session_cc_competing, v_guest_a, NULL, 'Guest A',
     'confirmed', 'present', 'self', 'guest', false,
     '2026-10-24 10:00:00+00', '2026-10-24 10:01:00+00', '2026-10-25 14:05:00+00', v_owner_b, v_guest_a),
    (v_player_cc_pay, v_session_cc_pay, v_member_a, NULL, 'Member A',
     'confirmed', 'present', 'self', 'guest', false,
     '2026-10-24 10:00:00+00', '2026-10-24 10:01:00+00', '2026-10-26 10:05:00+00', v_owner_b, v_member_a),
    (v_player_cc_drop, v_session_cc_drop, v_guest_a, NULL, 'Guest A',
     'confirmed', 'present', 'self', 'guest', false,
     '2026-10-24 10:00:00+00', '2026-10-24 10:01:00+00', '2026-10-26 14:05:00+00', v_owner_b, v_guest_a);

  -- Fake private contact markers. They must stay out of history/summary JSON
  -- projections; the HTTP test asserts the source rows exist and are absent
  -- from raw RPC payloads.
  INSERT INTO public.member_contacts (member_id, phone_number, contact_note)
  VALUES (v_member_a_row, '+84900000004', 'BH07-PRIVATE-MEMBER-CONTACT');

  INSERT INTO public.session_player_contacts (player_id, phone_number)
  VALUES
    (v_player_debt_member, '+84900000001'),
    (v_player_debt_guest, '+84900000002'),
    (v_player_free_guest, '+84900000003'),
    (v_player_fin, '+84900000005');

  -- Fake bank/account markers. Inserting an active bank also makes the
  -- receiver trigger freeze a private receiver_snapshot on completed/current
  -- sessions, so projections are checked against real private source rows.
  INSERT INTO public.club_bank_accounts (
    id, club_id, bank_code, account_number, account_name, status
  ) VALUES (
    '90000000-0000-4000-8000-000000000001',
    v_club_a, 'BH07BANK', '0000000007', 'BH07 PRIVATE RECEIVER', 'active'
  );

  INSERT INTO public.host_bank_accounts (
    id, user_id, bank_code, account_number, account_name, status
  ) VALUES (
    '91000000-0000-4000-8000-000000000001',
    v_owner_b, 'BH07HOSTBANK', '0000000008', 'BH07 PRIVATE HOST', 'active'
  );

  INSERT INTO public.session_expenses (
    id, session_id, category, title, amount_vnd, status, created_by, posted_at
  ) VALUES
    (v_expense_debt, v_session_debt, 'court', 'HTTP court debt', 300000, 'posted', v_owner_a, '2026-10-20 09:00:00+00'),
    (v_expense_fin, v_session_fin, 'court', 'HTTP court finance', 100000, 'posted', v_owner_a, '2026-10-17 09:00:00+00');

  INSERT INTO public.charge_revisions (
    id, session_id, revision_no, source_version, status, allocation_total_vnd,
    fee_mode, reason, finalized_by, finalized_at
  ) VALUES
    (v_rev_debt, v_session_debt, 1, 2, 'active', 300000, 'split_actual', 'seed debt current', v_owner_a, '2026-10-20 09:05:00+00'),
    (v_rev_free, v_session_free, 1, 1, 'active', 0, 'split_actual', 'seed free current', v_owner_a, '2026-10-19 09:05:00+00'),
    (v_rev_stale, v_session_stale, 1, 2, 'active', 100000, 'split_actual', 'seed stale', v_owner_a, '2026-10-21 09:05:00+00'),
    (v_rev_version, v_session_version, 1, 1, 'active', 100000, 'split_actual', 'seed version', v_owner_a, '2026-10-22 09:05:00+00'),
    (v_rev_fin, v_session_fin, 1, 4, 'active', 100000, 'split_actual', 'seed finance completed', v_owner_a, '2026-10-17 09:05:00+00'),
    (v_rev_cc_complete, v_session_cc_complete, 1, 1, 'active', 100000, 'split_actual', 'seed cc complete', v_owner_b, '2026-10-25 09:05:00+00'),
    (v_rev_cc_competing, v_session_cc_competing, 1, 1, 'active', 100000, 'split_actual', 'seed cc competing', v_owner_b, '2026-10-25 13:05:00+00'),
    (v_rev_cc_pay, v_session_cc_pay, 1, 1, 'active', 150000, 'split_actual', 'seed cc pay', v_owner_b, '2026-10-26 09:05:00+00'),
    (v_rev_cc_drop, v_session_cc_drop, 1, 1, 'active', 100000, 'split_actual', 'seed cc drop', v_owner_b, '2026-10-26 13:05:00+00');

  INSERT INTO public.session_charges (id, revision_id, session_player_id, amount_due_vnd)
  VALUES
    ('80000000-0000-4000-8000-000000000001', v_rev_debt, v_player_debt_member, 150000),
    ('80000000-0000-4000-8000-000000000002', v_rev_debt, v_player_debt_guest, 150000),
    ('80000000-0000-4000-8000-000000000006', v_rev_free, v_player_free_guest, 0),
    ('80000000-0000-4000-8000-000000000003', v_rev_stale, v_player_stale, 100000),
    ('80000000-0000-4000-8000-000000000004', v_rev_version, v_player_version, 100000),
    ('80000000-0000-4000-8000-000000000005', v_rev_fin, v_player_fin, 100000),
    ('80000000-0000-4000-8000-000000000021', v_rev_cc_complete, v_player_cc_complete, 100000),
    ('80000000-0000-4000-8000-000000000022', v_rev_cc_competing, v_player_cc_competing, 100000),
    ('80000000-0000-4000-8000-000000000023', v_rev_cc_pay, v_player_cc_pay, 150000),
    ('80000000-0000-4000-8000-000000000024', v_rev_cc_drop, v_player_cc_drop, 100000);

  INSERT INTO public.payments (
    id, session_player_id, amount_vnd, method, status, reference,
    submitted_by, confirmed_by, confirmed_at
  ) VALUES (
    v_payment_debt, v_player_debt_member, 50000, 'cash', 'confirmed',
    'SEED-DEBT-CASH', v_owner_a, v_owner_a, '2026-10-20 09:30:00+00'
  );

  INSERT INTO public.club_transactions (
    id, club_id, direction, amount_vnd, title, source_type,
    source_expense_id, source_payment_id, created_by
  ) VALUES
    (v_ledger_debt_expense, v_club_a, 'expense', 300000, 'HTTP court debt',
     'session_expense', v_expense_debt, NULL, v_owner_a),
    (v_ledger_fin_expense, v_club_a, 'expense', 100000, 'HTTP court finance',
     'session_expense', v_expense_fin, NULL, v_owner_a),
    (v_ledger_debt_payment, v_club_a, 'income', 50000, 'HTTP seeded cash payment',
     'payment', NULL, v_payment_debt, v_owner_a);

  -- Guard the intended billing states instead of silently seeding the wrong one.
  IF public.session_billing_state(v_session_debt) <> 'current'
     OR public.session_billing_state(v_session_free) <> 'current'
     OR public.session_billing_state(v_session_stale) <> 'stale'
     OR public.session_billing_state(v_session_version) <> 'current'
     OR public.session_billing_state(v_session_fin) <> 'current'
     OR public.session_billing_state(v_session_cc_complete) <> 'current'
     OR public.session_billing_state(v_session_cc_competing) <> 'current'
     OR public.session_billing_state(v_session_cc_pay) <> 'current'
     OR public.session_billing_state(v_session_cc_drop) <> 'current' THEN
    RAISE EXCEPTION 'BH-07 HTTP seed billing state guard failed';
  END IF;
END $$;
