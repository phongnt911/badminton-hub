-- Migration: 20261015051808_init_schema_v1_1.sql
-- Mô tả: Khởi tạo schema đích v1.1 cho Badminton Hub (BH-02)
-- Tuân thủ: docs/03_DATABASE.md, docs/08_DOMAIN_CONTRACTS.md, docs/11_ARCHITECTURE_DECISIONS.md
-- Ghi chú an toàn: Không xóa dữ liệu cũ (preserve data), hỗ trợ cả DB mới tinh và nâng cấp DB 3 bảng.

-- ============================================================================
-- 1. EXTENSIONS & CÁC TRIGGER CƠ SỞ
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Hàm tự động cập nhật trường updated_at
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- ============================================================================
-- 2. PROFILES & PROFILE_PRIVATE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL,
  avatar_path TEXT,
  skill_level TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger tự động đồng bộ khi có user đăng ký mới trong auth.users
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth, pg_temp
AS $$
BEGIN
  INSERT INTO public.profiles (id, display_name, avatar_path)
  VALUES (
    NEW.id,
    COALESCE(NULLIF(NEW.raw_user_meta_data->>'display_name', ''), split_part(COALESCE(NEW.email, 'User'), '@', 1)),
    NEW.raw_user_meta_data->>'avatar_path'
  )
  ON CONFLICT (id) DO UPDATE
  SET display_name = EXCLUDED.display_name,
      updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Thông tin liên lạc riêng tư (chỉ chủ sở hữu được đọc/ghi)
CREATE TABLE IF NOT EXISTS public.profile_private (
  user_id UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
  phone_number TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Bảng phân quyền quản trị hệ thống (không để user tự phong)
CREATE TABLE IF NOT EXISTS public.app_roles (
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('admin', 'venue_manager')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, role)
);

-- ============================================================================
-- 3. CLB, THÀNH VIÊN VÀ TÀI KHOẢN NGÂN HÀNG
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.clubs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id UUID NOT NULL REFERENCES public.profiles(id),
  name TEXT NOT NULL,
  description TEXT,
  visibility TEXT NOT NULL DEFAULT 'private' CHECK (visibility IN ('private', 'public')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.club_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  club_id UUID NOT NULL REFERENCES public.clubs(id) ON DELETE CASCADE,
  user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'host', 'treasurer', 'member')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('invited', 'active', 'inactive')),
  joined_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_club_members_unique_user ON public.club_members(club_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_club_members_unique_owner ON public.club_members(club_id) WHERE role = 'owner' AND status = 'active';

CREATE TABLE IF NOT EXISTS public.member_contacts (
  member_id UUID PRIMARY KEY REFERENCES public.club_members(id) ON DELETE CASCADE,
  phone_number TEXT,
  contact_note TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.club_bank_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  club_id UUID NOT NULL REFERENCES public.clubs(id) ON DELETE CASCADE,
  bank_code TEXT NOT NULL,
  account_number TEXT NOT NULL,
  account_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_club_bank_accounts_unique_active ON public.club_bank_accounts(club_id) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS public.host_bank_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  bank_code TEXT NOT NULL,
  account_number TEXT NOT NULL,
  account_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_host_bank_accounts_unique_active ON public.host_bank_accounts(user_id) WHERE status = 'active';

-- ============================================================================
-- 4. VENUES (DANH BẠ SÂN)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.venues (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  address TEXT NOT NULL,
  area TEXT,
  phone_number TEXT,
  map_url TEXT,
  image_url TEXT,
  court_count INTEGER CHECK (court_count IS NULL OR court_count > 0),
  price_range TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Kế hoạch chuyển đổi cho bảng venues có sẵn từ demo
ALTER TABLE public.venues ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive'));
ALTER TABLE public.venues ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- ============================================================================
-- 5. SESSIONS (BUỔI CHƠI) & SESSION_STAFF
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  club_id UUID REFERENCES public.clubs(id) ON DELETE SET NULL,
  host_user_id UUID NOT NULL REFERENCES public.profiles(id),
  venue_id UUID NOT NULL REFERENCES public.venues(id),
  title TEXT NOT NULL,
  description TEXT,
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  capacity INTEGER NOT NULL CHECK (capacity > 0),
  court_count INTEGER NOT NULL CHECK (court_count > 0),
  level_requirement TEXT,
  visibility TEXT NOT NULL DEFAULT 'unlisted' CHECK (visibility IN ('private', 'unlisted', 'public')),
  lifecycle TEXT NOT NULL DEFAULT 'draft' CHECK (lifecycle IN ('draft', 'published', 'in_progress', 'completed', 'cancelled')),
  approval_mode TEXT NOT NULL DEFAULT 'host_approval' CHECK (approval_mode IN ('host_approval', 'auto_confirm')),
  fee_mode TEXT NOT NULL DEFAULT 'split_actual' CHECK (fee_mode IN ('fixed', 'split_actual')),
  member_fee_vnd BIGINT CHECK (member_fee_vnd IS NULL OR member_fee_vnd >= 0),
  guest_fee_vnd BIGINT CHECK (guest_fee_vnd IS NULL OR guest_fee_vnd >= 0),
  registration_deadline TIMESTAMPTZ,
  cancellation_deadline TIMESTAMPTZ,
  receiver_club_bank_account_id UUID REFERENCES public.club_bank_accounts(id),
  receiver_host_bank_account_id UUID REFERENCES public.host_bank_accounts(id),
  receiver_snapshot JSONB,
  version BIGINT NOT NULL DEFAULT 1,
  billing_input_version BIGINT NOT NULL DEFAULT 1 CHECK (billing_input_version > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_session_times CHECK (ends_at > starts_at),
  CONSTRAINT chk_session_reg_deadline CHECK (registration_deadline IS NULL OR registration_deadline <= ends_at),
  CONSTRAINT chk_session_cancel_deadline CHECK (cancellation_deadline IS NULL OR cancellation_deadline <= starts_at),
  CONSTRAINT chk_session_fixed_fees CHECK (fee_mode != 'fixed' OR (member_fee_vnd IS NOT NULL AND guest_fee_vnd IS NOT NULL))
);

-- Kế hoạch chuyển đổi cho bảng sessions có sẵn từ demo
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS club_id UUID REFERENCES public.clubs(id) ON DELETE SET NULL;
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS host_user_id UUID REFERENCES public.profiles(id);
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS venue_id UUID REFERENCES public.venues(id);
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS starts_at TIMESTAMPTZ;
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS ends_at TIMESTAMPTZ;
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS capacity INTEGER CHECK (capacity IS NULL OR capacity > 0);
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS court_count INTEGER CHECK (court_count IS NULL OR court_count > 0);
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS visibility TEXT DEFAULT 'unlisted' CHECK (visibility IS NULL OR visibility IN ('private', 'unlisted', 'public'));
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS lifecycle TEXT DEFAULT 'draft' CHECK (lifecycle IS NULL OR lifecycle IN ('draft', 'published', 'in_progress', 'completed', 'cancelled'));
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS approval_mode TEXT DEFAULT 'host_approval' CHECK (approval_mode IS NULL OR approval_mode IN ('host_approval', 'auto_confirm'));
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS fee_mode TEXT DEFAULT 'split_actual' CHECK (fee_mode IS NULL OR fee_mode IN ('fixed', 'split_actual'));
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS member_fee_vnd BIGINT CHECK (member_fee_vnd IS NULL OR member_fee_vnd >= 0);
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS guest_fee_vnd BIGINT CHECK (guest_fee_vnd IS NULL OR guest_fee_vnd >= 0);
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS registration_deadline TIMESTAMPTZ;
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS cancellation_deadline TIMESTAMPTZ;
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS receiver_club_bank_account_id UUID REFERENCES public.club_bank_accounts(id);
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS receiver_host_bank_account_id UUID REFERENCES public.host_bank_accounts(id);
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS receiver_snapshot JSONB;
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1;
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS billing_input_version BIGINT NOT NULL DEFAULT 1 CHECK (billing_input_version > 0);
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.session_staff (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('cohost', 'finance')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_session_staff_user_role UNIQUE(session_id, user_id, role)
);

-- ============================================================================
-- 6. SESSION PLAYERS, CONTACTS & WAITLIST INVITATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.session_players (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
  user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  club_member_id UUID REFERENCES public.club_members(id) ON DELETE SET NULL,
  display_name TEXT NOT NULL,
  registration_status TEXT NOT NULL DEFAULT 'pending' CHECK (registration_status IN ('pending', 'confirmed', 'waitlisted', 'cancelled', 'rejected')),
  attendance_status TEXT NOT NULL DEFAULT 'not_checked_in' CHECK (attendance_status IN ('not_checked_in', 'present', 'no_show')),
  source TEXT NOT NULL DEFAULT 'self' CHECK (source IN ('self', 'host')),
  participant_type TEXT NOT NULL DEFAULT 'guest' CHECK (participant_type IN ('member', 'guest')),
  fee_exempt BOOLEAN NOT NULL DEFAULT false,
  agreed_fee_vnd BIGINT CHECK (agreed_fee_vnd IS NULL OR agreed_fee_vnd >= 0),
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  confirmed_at TIMESTAMPTZ,
  cancelled_at TIMESTAMPTZ,
  checked_in_at TIMESTAMPTZ,
  checked_in_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_by UUID NOT NULL REFERENCES public.profiles(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_attendance_only_confirmed CHECK (attendance_status = 'not_checked_in' OR registration_status = 'confirmed')
);

-- Kế hoạch chuyển đổi cho bảng session_players có sẵn từ demo
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL;
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS club_member_id UUID REFERENCES public.club_members(id) ON DELETE SET NULL;
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS display_name TEXT;
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS registration_status TEXT DEFAULT 'pending' CHECK (registration_status IS NULL OR registration_status IN ('pending', 'confirmed', 'waitlisted', 'cancelled', 'rejected'));
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS attendance_status TEXT DEFAULT 'not_checked_in' CHECK (attendance_status IS NULL OR attendance_status IN ('not_checked_in', 'present', 'no_show'));
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'self' CHECK (source IS NULL OR source IN ('self', 'host'));
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS participant_type TEXT DEFAULT 'guest' CHECK (participant_type IS NULL OR participant_type IN ('member', 'guest'));
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS fee_exempt BOOLEAN DEFAULT false;
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS agreed_fee_vnd BIGINT CHECK (agreed_fee_vnd IS NULL OR agreed_fee_vnd >= 0);
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS requested_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS checked_in_at TIMESTAMPTZ;
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS checked_in_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL;
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES public.profiles(id);
ALTER TABLE public.session_players ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE UNIQUE INDEX IF NOT EXISTS idx_session_players_session_user ON public.session_players(session_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_session_players_session_member ON public.session_players(session_id, club_member_id) WHERE club_member_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.session_player_contacts (
  player_id UUID PRIMARY KEY REFERENCES public.session_players(id) ON DELETE CASCADE,
  phone_number TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Bảng lời mời từ danh sách chờ (ADR-09)
CREATE TABLE IF NOT EXISTS public.waitlist_invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_player_id UUID NOT NULL REFERENCES public.session_players(id) ON DELETE CASCADE,
  invited_by UUID NOT NULL REFERENCES public.profiles(id),
  invited_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'revoked', 'expired')),
  accepted_by UUID REFERENCES public.profiles(id),
  accepted_at TIMESTAMPTZ,
  acceptance_mode TEXT CHECK (acceptance_mode IS NULL OR acceptance_mode IN ('self', 'host_recorded')),
  consent_note TEXT,
  revoked_by UUID REFERENCES public.profiles(id),
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_waitlist_invitation_times CHECK (expires_at > invited_at)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_waitlist_invitations_pending ON public.waitlist_invitations(session_player_id) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_waitlist_invitations_lookup ON public.waitlist_invitations(session_player_id, status, expires_at);

-- ============================================================================
-- 7. TÀI CHÍNH: EXPENSES, REVISIONS, CHARGES, PAYMENTS & SỔ QUỸ
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.session_expenses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
  category TEXT NOT NULL CHECK (category IN ('court', 'shuttle', 'other')),
  title TEXT NOT NULL,
  amount_vnd BIGINT NOT NULL CHECK (amount_vnd > 0 AND amount_vnd <= 1000000000),
  status TEXT NOT NULL DEFAULT 'posted' CHECK (status IN ('posted', 'reversed')),
  created_by UUID NOT NULL REFERENCES public.profiles(id),
  posted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reversal_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.charge_revisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
  revision_no INTEGER NOT NULL CHECK (revision_no > 0),
  source_version BIGINT NOT NULL CHECK (source_version > 0),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'superseded')),
  allocation_total_vnd BIGINT NOT NULL CHECK (allocation_total_vnd >= 0 AND allocation_total_vnd <= 1000000000),
  fee_mode TEXT NOT NULL CHECK (fee_mode IN ('fixed', 'split_actual')),
  reason TEXT,
  finalized_by UUID NOT NULL REFERENCES public.profiles(id),
  finalized_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_charge_revisions_no UNIQUE(session_id, revision_no)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_charge_revisions_active ON public.charge_revisions(session_id) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS public.session_charges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  revision_id UUID NOT NULL REFERENCES public.charge_revisions(id) ON DELETE CASCADE,
  session_player_id UUID NOT NULL REFERENCES public.session_players(id) ON DELETE CASCADE,
  amount_due_vnd BIGINT NOT NULL CHECK (amount_due_vnd >= 0 AND amount_due_vnd <= 1000000000),
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_session_charges_rev_player UNIQUE(revision_id, session_player_id)
);

CREATE TABLE IF NOT EXISTS public.payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_player_id UUID NOT NULL REFERENCES public.session_players(id) ON DELETE CASCADE,
  amount_vnd BIGINT NOT NULL CHECK (amount_vnd > 0 AND amount_vnd <= 1000000000),
  method TEXT NOT NULL CHECK (method IN ('cash', 'bank_transfer')),
  status TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted', 'confirmed', 'rejected', 'reversed')),
  reference TEXT NOT NULL UNIQUE,
  receipt_path TEXT,
  submitted_by UUID NOT NULL REFERENCES public.profiles(id),
  confirmed_by UUID REFERENCES public.profiles(id),
  confirmed_at TIMESTAMPTZ,
  reversed_by UUID REFERENCES public.profiles(id),
  reversed_at TIMESTAMPTZ,
  reversal_reason TEXT,
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.club_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  club_id UUID NOT NULL REFERENCES public.clubs(id) ON DELETE CASCADE,
  direction TEXT NOT NULL CHECK (direction IN ('income', 'expense')),
  amount_vnd BIGINT NOT NULL CHECK (amount_vnd > 0 AND amount_vnd <= 1000000000),
  title TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('manual', 'payment', 'session_expense', 'reversal')),
  source_payment_id UUID REFERENCES public.payments(id),
  source_expense_id UUID REFERENCES public.session_expenses(id),
  reversal_of UUID REFERENCES public.club_transactions(id),
  created_by UUID NOT NULL REFERENCES public.profiles(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_club_tx_source_payment ON public.club_transactions(source_payment_id) WHERE source_type = 'payment';
CREATE UNIQUE INDEX IF NOT EXISTS idx_club_tx_source_expense ON public.club_transactions(source_expense_id) WHERE source_type = 'session_expense';
CREATE UNIQUE INDEX IF NOT EXISTS idx_club_tx_reversal_of ON public.club_transactions(reversal_of) WHERE reversal_of IS NOT NULL;

-- ============================================================================
-- 8. AUDIT EVENTS & OPERATION REQUESTS (IDEMPOTENCY)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id UUID REFERENCES public.profiles(id),
  club_id UUID REFERENCES public.clubs(id) ON DELETE SET NULL,
  session_id UUID REFERENCES public.sessions(id) ON DELETE SET NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID NOT NULL,
  action TEXT NOT NULL,
  old_state JSONB,
  new_state JSONB,
  reason TEXT,
  request_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.operation_requests (
  actor_user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  operation TEXT NOT NULL,
  request_id UUID NOT NULL,
  payload_hash TEXT NOT NULL,
  result JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (actor_user_id, operation, request_id)
);

-- ============================================================================
-- 9. CHỈ MỤC TỐI ƯU HIỆU NĂNG (INDEXES)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_sessions_club_starts ON public.sessions(club_id, starts_at);
CREATE INDEX IF NOT EXISTS idx_sessions_lifecycle_visibility ON public.sessions(lifecycle, visibility, starts_at);
CREATE INDEX IF NOT EXISTS idx_session_players_reg_status ON public.session_players(session_id, registration_status);
CREATE INDEX IF NOT EXISTS idx_club_members_user_status ON public.club_members(user_id, club_id, status);
CREATE INDEX IF NOT EXISTS idx_expenses_session ON public.session_expenses(session_id);
CREATE INDEX IF NOT EXISTS idx_revisions_session_status ON public.charge_revisions(session_id, status);
CREATE INDEX IF NOT EXISTS idx_payments_player_status ON public.payments(session_player_id, status);
CREATE INDEX IF NOT EXISTS idx_club_tx_created ON public.club_transactions(club_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_session_created ON public.audit_events(session_id, created_at);

-- Gắn trigger updated_at cho tất cả bảng có trường updated_at
DO $$
DECLARE
  tbl text;
BEGIN
  FOR tbl IN
    SELECT table_name
    FROM information_schema.columns
    WHERE table_schema = 'public' AND column_name = 'updated_at'
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_update_%I ON public.%I', tbl, tbl);
    EXECUTE format('CREATE TRIGGER trg_update_%I BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at()', tbl, tbl);
  END LOOP;
END;
$$;

-- ============================================================================
-- 10. HELPER FUNCTIONS PHỤC VỤ RLS (SECURITY DEFINER - TRÁNH ĐỆ QUY RLS)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.is_app_admin(p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.app_roles
    WHERE user_id = p_user_id AND role = 'admin'
  );
$$;

CREATE OR REPLACE FUNCTION public.is_club_owner(p_club_id UUID, p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.clubs
    WHERE id = p_club_id AND owner_user_id = p_user_id
  );
$$;

CREATE OR REPLACE FUNCTION public.is_club_member_active(p_club_id UUID, p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.club_members
    WHERE club_id = p_club_id AND user_id = p_user_id AND status = 'active'
  );
$$;

CREATE OR REPLACE FUNCTION public.has_club_role(p_club_id UUID, p_user_id UUID, p_roles TEXT[])
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.club_members
    WHERE club_id = p_club_id AND user_id = p_user_id AND status = 'active' AND role = ANY(p_roles)
  );
$$;

CREATE OR REPLACE FUNCTION public.is_session_host(p_session_id UUID, p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.sessions
    WHERE id = p_session_id AND host_user_id = p_user_id
  );
$$;

CREATE OR REPLACE FUNCTION public.has_session_staff_role(p_session_id UUID, p_user_id UUID, p_roles TEXT[])
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.session_staff
    WHERE session_id = p_session_id AND user_id = p_user_id AND status = 'active' AND role = ANY(p_roles)
  );
$$;

CREATE OR REPLACE FUNCTION public.has_session_management_access(p_session_id UUID, p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_club_id UUID;
  v_host_id UUID;
BEGIN
  SELECT club_id, host_user_id INTO v_club_id, v_host_id FROM public.sessions WHERE id = p_session_id;
  IF v_host_id = p_user_id THEN
    RETURN true;
  END IF;
  IF v_club_id IS NOT NULL AND public.is_club_owner(v_club_id, p_user_id) THEN
    RETURN true;
  END IF;
  IF public.has_session_staff_role(p_session_id, p_user_id, ARRAY['cohost']) THEN
    RETURN true;
  END IF;
  RETURN false;
END;
$$;

CREATE OR REPLACE FUNCTION public.has_session_finance_access(p_session_id UUID, p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_club_id UUID;
  v_host_id UUID;
BEGIN
  SELECT club_id, host_user_id INTO v_club_id, v_host_id FROM public.sessions WHERE id = p_session_id;
  IF v_host_id = p_user_id THEN
    RETURN true;
  END IF;
  IF v_club_id IS NOT NULL AND (public.is_club_owner(v_club_id, p_user_id) OR public.has_club_role(v_club_id, p_user_id, ARRAY['treasurer'])) THEN
    RETURN true;
  END IF;
  IF public.has_session_staff_role(p_session_id, p_user_id, ARRAY['finance']) THEN
    RETURN true;
  END IF;
  RETURN false;
END;
$$;

CREATE OR REPLACE FUNCTION public.is_session_participant(p_session_id UUID, p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.session_players
    WHERE session_id = p_session_id AND user_id = p_user_id
  );
$$;

-- ============================================================================
-- 11. CÁC VIEWS VÀ PROJECTIONS BẢO VỆ DỮ LIỆU
-- ============================================================================

-- View công khai tóm tắt buổi chơi (ẩn contact, ngân hàng, ledger)
CREATE OR REPLACE VIEW public.public_session_summary
WITH (security_invoker = true)
AS
SELECT 
  s.id,
  s.club_id,
  s.title,
  s.description,
  s.starts_at,
  s.ends_at,
  s.capacity,
  s.court_count,
  s.level_requirement,
  s.visibility,
  s.lifecycle,
  s.approval_mode,
  s.fee_mode,
  s.member_fee_vnd,
  s.guest_fee_vnd,
  s.registration_deadline,
  s.cancellation_deadline,
  v.name AS venue_name,
  v.address AS venue_address,
  v.area AS venue_area,
  p.display_name AS host_display_name,
  COALESCE(
    (SELECT count(*)::int FROM public.session_players sp 
     WHERE sp.session_id = s.id AND sp.registration_status = 'confirmed'), 0
  ) AS confirmed_player_count
FROM public.sessions s
LEFT JOIN public.venues v ON s.venue_id = v.id
LEFT JOIN public.profiles p ON s.host_user_id = p.id
WHERE s.visibility = 'public'
  AND s.lifecycle IN ('published', 'in_progress');

-- View số dư quỹ CLB (tính từ tổng ledger, không cache thô)
CREATE OR REPLACE VIEW public.club_balance
WITH (security_invoker = true)
AS
SELECT 
  c.id AS club_id,
  c.name AS club_name,
  COALESCE(SUM(CASE WHEN t.direction = 'income' THEN t.amount_vnd ELSE -t.amount_vnd END), 0)::bigint AS balance_vnd
FROM public.clubs c
LEFT JOIN public.club_transactions t ON c.id = t.club_id
GROUP BY c.id, c.name;

-- View công nợ người chơi (Active revision charges - confirmed payments)
CREATE OR REPLACE VIEW public.player_outstanding
WITH (security_invoker = true)
AS
SELECT 
  sp.id AS session_player_id,
  sp.session_id,
  sp.user_id,
  sp.display_name,
  COALESCE(sc.amount_due_vnd, 0)::bigint AS amount_due_vnd,
  COALESCE(p.total_paid_vnd, 0)::bigint AS total_paid_vnd,
  GREATEST(0, COALESCE(sc.amount_due_vnd, 0) - COALESCE(p.total_paid_vnd, 0))::bigint AS outstanding_vnd,
  cr.id AS active_revision_id,
  cr.source_version
FROM public.session_players sp
JOIN public.charge_revisions cr ON cr.session_id = sp.session_id AND cr.status = 'active'
LEFT JOIN public.session_charges sc ON sc.revision_id = cr.id AND sc.session_player_id = sp.id
LEFT JOIN (
  SELECT session_player_id, SUM(amount_vnd)::bigint AS total_paid_vnd
  FROM public.payments
  WHERE status = 'confirmed'
  GROUP BY session_player_id
) p ON p.session_player_id = sp.id;

-- ============================================================================
-- 12. RPC IDEMPOTENCY & AUDIT HELPER FUNCTIONS
-- ============================================================================

-- Kiểm tra tính lặp lại (idempotency)
CREATE OR REPLACE FUNCTION public.check_idempotency(
  p_operation TEXT,
  p_request_id UUID,
  p_payload_hash TEXT,
  OUT is_replay BOOLEAN,
  OUT saved_result JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_rec RECORD;
BEGIN
  is_replay := false;
  saved_result := NULL;
  
  IF v_actor IS NULL OR p_request_id IS NULL THEN
    RETURN;
  END IF;

  SELECT payload_hash, result INTO v_rec
  FROM public.operation_requests
  WHERE actor_user_id = v_actor AND operation = p_operation AND request_id = p_request_id;

  IF FOUND THEN
    IF v_rec.payload_hash != p_payload_hash THEN
      RAISE EXCEPTION 'IDEMPOTENCY_CONFLICT: request_id reused with different payload' USING ERRCODE = '23505';
    END IF;
    is_replay := true;
    saved_result := v_rec.result;
  END IF;
END;
$$;

-- Ghi nhận kết quả request
CREATE OR REPLACE FUNCTION public.record_idempotency(
  p_operation TEXT,
  p_request_id UUID,
  p_payload_hash TEXT,
  p_result JSONB
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
BEGIN
  IF v_actor IS NULL OR p_request_id IS NULL THEN
    RETURN;
  END IF;

  INSERT INTO public.operation_requests (actor_user_id, operation, request_id, payload_hash, result, created_at)
  VALUES (v_actor, p_operation, p_request_id, p_payload_hash, p_result, now())
  ON CONFLICT (actor_user_id, operation, request_id) DO NOTHING;
END;
$$;

-- Ghi log audit event
CREATE OR REPLACE FUNCTION public.log_audit_event(
  p_club_id UUID,
  p_session_id UUID,
  p_entity_type TEXT,
  p_entity_id UUID,
  p_action TEXT,
  p_old_state JSONB DEFAULT NULL,
  p_new_state JSONB DEFAULT NULL,
  p_reason TEXT DEFAULT NULL,
  p_request_id UUID DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_id UUID := gen_random_uuid();
  v_actor UUID := auth.uid();
BEGIN
  INSERT INTO public.audit_events (
    id, actor_user_id, club_id, session_id, entity_type, entity_id, action,
    old_state, new_state, reason, request_id, created_at
  ) VALUES (
    v_id, v_actor, p_club_id, p_session_id, p_entity_type, p_entity_id, p_action,
    p_old_state, p_new_state, p_reason, p_request_id, now()
  );
  RETURN v_id;
END;
$$;

-- RPC đọc chi tiết buổi công khai/unlisted (Whitelist an toàn, không lộ contact/bank)
CREATE OR REPLACE FUNCTION public.get_session_public_detail(p_session_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_res JSONB;
  v_actor UUID := auth.uid();
  v_session RECORD;
BEGIN
  SELECT s.*, v.name AS venue_name, v.address AS venue_address, v.area AS venue_area, p.display_name AS host_display_name
  INTO v_session
  FROM public.sessions s
  LEFT JOIN public.venues v ON s.venue_id = v.id
  LEFT JOIN public.profiles p ON s.host_user_id = p.id
  WHERE s.id = p_session_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'NOT_FOUND: Buổi chơi không tồn tại' USING ERRCODE = 'P0002';
  END IF;

  -- Kiểm tra quyền đọc nếu private
  IF v_session.visibility = 'private' THEN
    IF v_actor IS NULL THEN
      RAISE EXCEPTION 'UNAUTHENTICATED: Cần đăng nhập để xem buổi nội bộ' USING ERRCODE = '42501';
    END IF;
    IF NOT (
      v_session.host_user_id = v_actor OR
      (v_session.club_id IS NOT NULL AND public.is_club_member_active(v_session.club_id, v_actor)) OR
      public.is_session_participant(p_session_id, v_actor) OR
      public.has_session_management_access(p_session_id, v_actor)
    ) THEN
      RAISE EXCEPTION 'FORBIDDEN: Không có quyền xem buổi chơi nội bộ này' USING ERRCODE = '42501';
    END IF;
  END IF;

  -- Whitelist thông tin trả về
  v_res := jsonb_build_object(
    'id', v_session.id,
    'club_id', v_session.club_id,
    'title', v_session.title,
    'description', v_session.description,
    'starts_at', v_session.starts_at,
    'ends_at', v_session.ends_at,
    'capacity', v_session.capacity,
    'court_count', v_session.court_count,
    'level_requirement', v_session.level_requirement,
    'visibility', v_session.visibility,
    'lifecycle', v_session.lifecycle,
    'approval_mode', v_session.approval_mode,
    'fee_mode', v_session.fee_mode,
    'member_fee_vnd', v_session.member_fee_vnd,
    'guest_fee_vnd', v_session.guest_fee_vnd,
    'registration_deadline', v_session.registration_deadline,
    'cancellation_deadline', v_session.cancellation_deadline,
    'venue_name', v_session.venue_name,
    'venue_address', v_session.venue_address,
    'venue_area', v_session.venue_area,
    'host_display_name', v_session.host_display_name,
    'confirmed_count', (
      SELECT count(*)::int FROM public.session_players
      WHERE session_id = p_session_id AND registration_status = 'confirmed'
    )
  );

  RETURN v_res;
END;
$$;

-- RPC đọc đăng ký của chính người chơi trong buổi
CREATE OR REPLACE FUNCTION public.get_my_registration(p_session_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor UUID := auth.uid();
  v_player RECORD;
  v_res JSONB;
BEGIN
  IF v_actor IS NULL THEN
    RETURN NULL;
  END IF;

  SELECT * INTO v_player
  FROM public.session_players
  WHERE session_id = p_session_id AND user_id = v_actor;

  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  v_res := jsonb_build_object(
    'player_id', v_player.id,
    'session_id', v_player.session_id,
    'display_name', v_player.display_name,
    'registration_status', v_player.registration_status,
    'attendance_status', v_player.attendance_status,
    'participant_type', v_player.participant_type,
    'fee_exempt', v_player.fee_exempt,
    'agreed_fee_vnd', v_player.agreed_fee_vnd,
    'requested_at', v_player.requested_at,
    'confirmed_at', v_player.confirmed_at
  );

  RETURN v_res;
END;
$$;

-- ============================================================================
-- 13. KÍCH HOẠT VÀ THIẾT LẬP ROW LEVEL SECURITY (RLS) TRÊN TẤT CẢ CÁC BẢNG
-- ============================================================================

-- Bật RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profile_private ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clubs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.club_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.member_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.club_bank_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.host_bank_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.venues ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.session_staff ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.session_players ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.session_player_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.waitlist_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.session_expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.charge_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.session_charges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.club_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.operation_requests ENABLE ROW LEVEL SECURITY;

-- Thu hồi toàn bộ quyền direct write từ anon và authenticated trên schema public
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;

-- Phân quyền cơ bản (Grants)
GRANT SELECT ON public.venues TO anon, authenticated;
GRANT SELECT ON public.public_session_summary TO anon, authenticated;
GRANT SELECT ON public.profiles TO authenticated;
GRANT UPDATE(display_name, avatar_path, skill_level) ON public.profiles TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.profile_private TO authenticated;
GRANT SELECT ON public.clubs TO authenticated;
GRANT SELECT ON public.club_members TO authenticated;
GRANT SELECT ON public.member_contacts TO authenticated;
GRANT SELECT ON public.sessions TO authenticated;
GRANT SELECT ON public.session_staff TO authenticated;
GRANT SELECT ON public.session_players TO authenticated;
GRANT SELECT ON public.session_player_contacts TO authenticated;
GRANT SELECT ON public.waitlist_invitations TO authenticated;
GRANT SELECT ON public.session_expenses TO authenticated;
GRANT SELECT ON public.charge_revisions TO authenticated;
GRANT SELECT ON public.session_charges TO authenticated;
GRANT SELECT ON public.payments TO authenticated;
GRANT SELECT ON public.club_transactions TO authenticated;
GRANT SELECT ON public.audit_events TO authenticated;
GRANT SELECT ON public.club_balance TO authenticated;
GRANT SELECT ON public.player_outstanding TO authenticated;

-- Cấp quyền thực thi RPC
GRANT EXECUTE ON FUNCTION public.get_session_public_detail(UUID) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_my_registration(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.check_idempotency(TEXT, UUID, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.record_idempotency(TEXT, UUID, TEXT, JSONB) TO authenticated;
GRANT EXECUTE ON FUNCTION public.log_audit_event(UUID, UUID, TEXT, UUID, TEXT, JSONB, JSONB, TEXT, UUID) TO authenticated;

-- Xóa các policy cũ nếu có
DO $$
DECLARE
  pol record;
BEGIN
  FOR pol IN 
    SELECT schemaname, tablename, policyname
    FROM pg_policies
    WHERE schemaname = 'public'
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', pol.policyname, pol.schemaname, pol.tablename);
  END LOOP;
END;
$$;

-- ============================================================================
-- 14. POLICIES CHI TIẾT THEO MA TRẬN PHÂN QUYỀN
-- ============================================================================

-- profiles: ai đã đăng nhập cũng xem được hồ sơ cơ bản; chủ sở hữu được sửa
CREATE POLICY "profiles_select_auth" ON public.profiles
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "profiles_update_own" ON public.profiles
  FOR UPDATE TO authenticated USING (id = auth.uid()) WITH CHECK (id = auth.uid());

-- profile_private: chỉ chính chủ đọc/ghi
CREATE POLICY "profile_private_select_own" ON public.profile_private
  FOR SELECT TO authenticated USING (user_id = auth.uid());

CREATE POLICY "profile_private_insert_own" ON public.profile_private
  FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());

CREATE POLICY "profile_private_update_own" ON public.profile_private
  FOR UPDATE TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- app_roles: chỉ user xem quyền của mình
CREATE POLICY "app_roles_select_own" ON public.app_roles
  FOR SELECT TO authenticated USING (user_id = auth.uid());

-- venues: public/anon đọc sân active, admin sửa
CREATE POLICY "venues_select_active" ON public.venues
  FOR SELECT TO anon, authenticated USING (status = 'active');

CREATE POLICY "venues_admin_all" ON public.venues
  FOR ALL TO authenticated USING (public.is_app_admin(auth.uid())) WITH CHECK (public.is_app_admin(auth.uid()));

-- clubs: public xem club public; member xem club nội bộ
CREATE POLICY "clubs_select_visible" ON public.clubs
  FOR SELECT TO authenticated
  USING (
    visibility = 'public' OR
    owner_user_id = auth.uid() OR
    public.is_club_member_active(id, auth.uid())
  );

-- club_members: owner/host/member xem danh sách trong CLB của mình
CREATE POLICY "club_members_select_internal" ON public.club_members
  FOR SELECT TO authenticated
  USING (
    public.is_club_owner(club_id, auth.uid()) OR
    public.is_club_member_active(club_id, auth.uid())
  );

-- member_contacts: owner/host đọc; thành viên liên kết đọc của mình; treasurer KHÔNG đọc
CREATE POLICY "member_contacts_select_auth" ON public.member_contacts
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.club_members cm
      WHERE cm.id = member_contacts.member_id
        AND (
          cm.user_id = auth.uid() OR
          public.is_club_owner(cm.club_id, auth.uid()) OR
          public.has_club_role(cm.club_id, auth.uid(), ARRAY['owner', 'host'])
        )
    )
  );

-- club_bank_accounts: chỉ owner và treasurer của CLB đọc
CREATE POLICY "club_bank_accounts_select_auth" ON public.club_bank_accounts
  FOR SELECT TO authenticated
  USING (
    public.is_club_owner(club_id, auth.uid()) OR
    public.has_club_role(club_id, auth.uid(), ARRAY['treasurer'])
  );

-- host_bank_accounts: chỉ chính chủ đọc
CREATE POLICY "host_bank_accounts_select_own" ON public.host_bank_accounts
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- sessions: host/staff/owner đọc đầy đủ; thành viên CLB đọc private; người ngoài đọc unlisted/public
CREATE POLICY "sessions_select_auth" ON public.sessions
  FOR SELECT TO authenticated
  USING (
    host_user_id = auth.uid() OR
    visibility IN ('public', 'unlisted') OR
    (club_id IS NOT NULL AND public.is_club_member_active(club_id, auth.uid())) OR
    public.has_session_management_access(id, auth.uid()) OR
    public.is_session_participant(id, auth.uid())
  );

-- session_staff: host của buổi, owner CLB, và chính nhân sự đó được đọc
CREATE POLICY "session_staff_select_auth" ON public.session_staff
  FOR SELECT TO authenticated
  USING (
    user_id = auth.uid() OR
    public.has_session_management_access(session_id, auth.uid())
  );

-- session_players: host/cohost/finance đọc buổi của mình; player đọc bản ghi của mình
CREATE POLICY "session_players_select_auth" ON public.session_players
  FOR SELECT TO authenticated
  USING (
    user_id = auth.uid() OR
    public.has_session_management_access(session_id, auth.uid()) OR
    public.has_session_finance_access(session_id, auth.uid())
  );

-- session_player_contacts: host/cohost đọc; player đọc của chính mình; finance KHÔNG đọc
CREATE POLICY "session_player_contacts_select_auth" ON public.session_player_contacts
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.session_players sp
      WHERE sp.id = session_player_contacts.player_id
        AND (
          sp.user_id = auth.uid() OR
          public.has_session_management_access(sp.session_id, auth.uid())
        )
    )
  );

-- waitlist_invitations: host/cohost và player liên kết được đọc
CREATE POLICY "waitlist_invitations_select_auth" ON public.waitlist_invitations
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.session_players sp
      WHERE sp.id = waitlist_invitations.session_player_id
        AND (
          sp.user_id = auth.uid() OR
          public.has_session_management_access(sp.session_id, auth.uid())
        )
    )
  );

-- session_expenses: host, finance, owner CLB, treasurer CLB đọc
CREATE POLICY "session_expenses_select_auth" ON public.session_expenses
  FOR SELECT TO authenticated
  USING (public.has_session_finance_access(session_id, auth.uid()));

-- charge_revisions: host, finance, owner CLB, treasurer CLB đọc
CREATE POLICY "charge_revisions_select_auth" ON public.charge_revisions
  FOR SELECT TO authenticated
  USING (public.has_session_finance_access(session_id, auth.uid()));

-- session_charges: finance đọc tất cả; player chỉ đọc charge của mình
CREATE POLICY "session_charges_select_auth" ON public.session_charges
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.charge_revisions cr
      WHERE cr.id = session_charges.revision_id
        AND public.has_session_finance_access(cr.session_id, auth.uid())
    ) OR
    EXISTS (
      SELECT 1 FROM public.session_players sp
      WHERE sp.id = session_charges.session_player_id
        AND sp.user_id = auth.uid()
    )
  );

-- payments: finance đọc tất cả trong buổi; player chỉ đọc thanh toán của mình
CREATE POLICY "payments_select_auth" ON public.payments
  FOR SELECT TO authenticated
  USING (
    submitted_by = auth.uid() OR
    EXISTS (
      SELECT 1 FROM public.session_players sp
      WHERE sp.id = payments.session_player_id
        AND (
          sp.user_id = auth.uid() OR
          public.has_session_finance_access(sp.session_id, auth.uid())
        )
    )
  );

-- club_transactions: chỉ owner và treasurer của CLB đọc sổ quỹ
CREATE POLICY "club_transactions_select_auth" ON public.club_transactions
  FOR SELECT TO authenticated
  USING (
    public.is_club_owner(club_id, auth.uid()) OR
    public.has_club_role(club_id, auth.uid(), ARRAY['treasurer'])
  );

-- audit_events: chỉ owner CLB hoặc host buổi đọc sự kiện trong phạm vi
CREATE POLICY "audit_events_select_auth" ON public.audit_events
  FOR SELECT TO authenticated
  USING (
    actor_user_id = auth.uid() OR
    (club_id IS NOT NULL AND public.is_club_owner(club_id, auth.uid())) OR
    (session_id IS NOT NULL AND public.has_session_management_access(session_id, auth.uid()))
  );

-- operation_requests: chỉ actor đọc idempotency request của chính mình
CREATE POLICY "operation_requests_select_auth" ON public.operation_requests
  FOR SELECT TO authenticated
  USING (actor_user_id = auth.uid());
