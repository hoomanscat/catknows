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
finally:
    s.close()
