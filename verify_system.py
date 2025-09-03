# REPLACE FILE: verify_system.py  (more diagnostics)
from datetime import date
from skoolhud.db import SessionLocal
from skoolhud.models import Member, LeaderboardSnapshot
from sqlalchemy import text
try:
    from skoolhud.models import MemberDailySnapshot
except ImportError:
    MemberDailySnapshot = None

s = SessionLocal()
try:
    try:
        total = s.query(Member).count()
        with_points = s.query(Member).filter(Member.points_all != None).count()
    except Exception:
        # fallback to raw SQL if ORM mapping references a column not present in DB
        total = int(s.execute(text("SELECT count(*) FROM members")).scalar() or 0)
        try:
            with_points = int(s.execute(text("SELECT count(*) FROM members WHERE points_all IS NOT NULL")).scalar() or 0)
        except Exception:
            with_points = 0
    try:
        snaps = s.query(LeaderboardSnapshot).count()
    except Exception:
        snaps = int(s.execute(text("SELECT count(*) FROM leaderboard_snapshots")).scalar() or 0)
    print(f"Members: {total} (with points_all: {with_points}) | LeaderboardSnapshots: {snaps}")
    if MemberDailySnapshot:
        today = date.today()
        today_rows = s.query(MemberDailySnapshot).filter(MemberDailySnapshot.day==today).count()
        any_rows = s.query(MemberDailySnapshot).count()
        print(f"MemberDailySnapshot: today={today_rows} | total={any_rows}")
        rows = (s.query(MemberDailySnapshot)
                  .filter(MemberDailySnapshot.day==today)
                  .limit(5).all())
        for r in rows:
            print(" -", r.tenant, r.user_id, r.points_7d, r.points_30d, r.points_all, r.rank_7d, r.rank_30d, r.rank_all, r.last_active_at_utc)
finally:
    s.close()

# Smoke-check: verify joiners files exist for a sample tenant (if exports/reports present)
from pathlib import Path
reports_root = Path(__file__).resolve().parent / "exports" / "reports"
sample = "hoomans"
jt = reports_root / sample
if jt.exists():
    wk = jt / "new_joiners_week.md"
    last = jt / "new_joiners_last_week.md"
    d30 = jt / "new_joiners_30d.md"
    print("Joiners files present:", wk.exists(), last.exists(), d30.exists())
