# REPLACE FILE: verify_system.py  (more diagnostics)
from datetime import date
from skoolhud.db import SessionLocal
from skoolhud.models import Member, LeaderboardSnapshot
try:
    from skoolhud.models import MemberDailySnapshot
except ImportError:
    MemberDailySnapshot = None

s = SessionLocal()
try:
    total = s.query(Member).count()
    with_points = s.query(Member).filter(Member.points_all != None).count()
    snaps = s.query(LeaderboardSnapshot).count()
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
