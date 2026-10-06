-- 1. Cập nhật bảng session_players (Thêm cột check-in & thanh toán)
ALTER TABLE session_players ADD COLUMN IF NOT EXISTS has_arrived BOOLEAN DEFAULT FALSE;
ALTER TABLE session_players ADD COLUMN IF NOT EXISTS has_paid BOOLEAN DEFAULT FALSE;

-- 2. Bảng clubs (Quản lý Nhóm/CLB)
CREATE TABLE IF NOT EXISTS clubs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    owner_phone TEXT,
    bank_code TEXT,
    bank_account TEXT,
    bank_owner TEXT,
    balance INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Bảng club_transactions (Quản lý thu chi CLB)
CREATE TABLE IF NOT EXISTS club_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID REFERENCES clubs(id) ON DELETE CASCADE,
    type TEXT CHECK (type IN ('thu', 'chi')),
    amount INT NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Bảng player_stats (Thống kê & Xếp hạng vui)
CREATE TABLE IF NOT EXISTS player_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    matches_played INT DEFAULT 0,
    matches_won INT DEFAULT 0,
    win_streak INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Bảng local_partners (Đối tác & Shop căng vợt)
CREATE TABLE IF NOT EXISTS local_partners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    service_type TEXT CHECK (service_type IN ('Shop căng vợt', 'Sân ưu đãi')),
    address TEXT,
    phone TEXT,
    discount_info TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bật RLS (Row Level Security) và cho phép truy cập công khai (Mở)
ALTER TABLE clubs ENABLE ROW LEVEL SECURITY;
ALTER TABLE club_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE local_partners ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read/insert/update on clubs" ON clubs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read/insert/update on club_transactions" ON club_transactions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read/insert/update on player_stats" ON player_stats FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow public read/insert/update on local_partners" ON local_partners FOR ALL USING (true) WITH CHECK (true);
