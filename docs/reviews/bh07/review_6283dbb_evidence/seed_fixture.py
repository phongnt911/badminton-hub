import subprocess
from pathlib import Path

ROOT = Path(r"C:\Users\POTA\Documents\GitHub\badminton-hub")
OUT = Path(r"C:\Users\POTA\AppData\Local\Temp\bh07-v1-review")
CONTAINER = "bh07v1-db"


def psql(sql):
    r = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1"],
        input=sql, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=180,
    )
    if r.returncode:
        raise RuntimeError(f"psql failed: {r.stderr[-3000:]}")
    return r.stdout


truncate = """
TRUNCATE TABLE venues, clubs, club_members, sessions, session_staff, session_players,
member_contacts, session_player_contacts, club_bank_accounts, host_bank_accounts,
session_expenses, charge_revisions, session_charges, payments, club_transactions,
operation_requests, audit_events RESTART IDENTITY CASCADE;
"""
psql(truncate)
psql((ROOT / "scripts/bh07_http/seed.sql").read_text(encoding="utf-8"))
src = (ROOT / "scripts/bh07_browser/seed_setup.js").read_text(encoding="utf-8")
ui_sql = src.split("const uiSessionSql = `", 1)[1].split("`;", 1)[0]
psql(ui_sql)
(OUT / "seed_ok.txt").write_text("fixture reset and seeded\n", encoding="utf-8")
print("seed ok")
