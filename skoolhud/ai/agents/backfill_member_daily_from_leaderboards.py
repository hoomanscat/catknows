from datetime import datetime, date, timezone, timedelta
from pathlib import Path
import argparse
from collections import defaultdict

from skoolhud.db import SessionLocal
from skoolhud.models import LeaderboardSnapshot, Member, MemberDailySnapshot

WINDOWS = ("all", "30", "7")  # allTime, past30Days, past7Days
END_OF_DAY = lambda d: datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)

def daterange(d0: date, d1: date):
    cur = d0
    while cur <= d1:
        yield cur
        cur = cur + timedelta(days=1)

def newest_ts_per_day(session, day: date, window: str):
    """Neuester captured_at am Tag (UTC) für ein Fenster."""
    eod = END_OF_DAY(day)
    row = (
        session.query(LeaderboardSnapshot.captured_at)
        .filter(LeaderboardSnapshot.window == window)
        .filter(LeaderboardSnapshot.captured_at <= eod)
        .order_by(LeaderboardSnapshot.captured_at.desc())
        .first()
    )
    return row[0] if row else None

def snapshot_map(session, window: str, ts):
    rows = (
        session.query(LeaderboardSnapshot.user_id,
                      LeaderboardSnapshot.points,
                      LeaderboardSnapshot.rank)
        .filter(LeaderboardSnapshot.window == window)
        .filter(LeaderboardSnapshot.captured_at == ts)
        .all()
    )
    return {uid: (pts or 0, rk) for uid, pts, rk in rows}

def names_map(session, user_ids):
    if not user_ids: return {}
    rows = session.query(Member.user_id, Member.name).filter(Member.user_id.in_(list(user_ids))).all()
    return {uid: (nm or f"user:{uid}") for uid, nm in rows}

def upsert_daily(session, tenant, user_id, day, values):
    now = datetime.now(timezone.utc)
    row = (
        session.query(MemberDailySnapshot)
        .filter(MemberDailySnapshot.tenant == tenant)
        .filter(MemberDailySnapshot.user_id == user_id)
        .filter(MemberDailySnapshot.day == day)
        .one_or_none()
    )
    values = dict(values)
    values.update({"tenant": tenant, "user_id": user_id, "day": day, "captured_at": now})
    if row is None:
        session.add(MemberDailySnapshot(**values))
        return "insert"
    else:
        for k, v in values.items():
            setattr(row, k, v)
        return "update"

def infer_range(session):
    """Auto-Zeitraum: min..max Datum aus LeaderboardSnapshot.captured_at."""
    row_min = session.query(LeaderboardSnapshot.captured_at).order_by(LeaderboardSnapshot.captured_at.asc()).first()
    row_max = session.query(LeaderboardSnapshot.captured_at).order_by(LeaderboardSnapshot.captured_at.desc()).first()
    if not row_min or not row_max:
        return None, None
    return row_min[0].date(), row_max[0].date()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_day", help="YYYY-MM-DD (inklusive)")
    ap.add_argument("--to", dest="to_day", help="YYYY-MM-DD (inklusive)")
    ap.add_argument("--slug", default="hoomans")
    args = ap.parse_args()

    s = SessionLocal()
    try:
        if args.from_day and args.to_day:
            y0,m0,d0 = map(int, args.from_day.split("-"))
            y1,m1,d1 = map(int, args.to_day.split("-"))
            d0, d1 = date(y0,m0,d0), date(y1,m1,d1)
        else:
            d0, d1 = infer_range(s)
            if not d0:
                print("Keine LeaderboardSnapshot-Daten gefunden.")
                return

        total_ins = total_upd = 0
        for day in daterange(d0, d1):
            # hole je Fenster den neuesten TS <= Tagesende
            ts = {w: newest_ts_per_day(s, day, w) for w in WINDOWS}
            if not any(ts.values()):
                # keine Daten für diesen Tag
                continue

            maps = {w: (snapshot_map(s, w, ts[w]) if ts[w] else {}) for w in WINDOWS}
            user_ids = set().union(*[set(m.keys()) for m in maps.values()])

            # optional: Names/Member holen für level/last_active (fallback: None)
            members = {m.user_id: m for m in s.query(Member).filter(Member.user_id.in_(list(user_ids))).all()}

            ins = upd = 0
            for uid in user_ids:
                m = members.get(uid)
                vals = {
                    "level_current": (m.level_current if m else None),
                    "points_7d":   maps["7"].get(uid, (None, None))[0],
                    "points_30d":  maps["30"].get(uid, (None, None))[0],
                    "points_all":  maps["all"].get(uid, (None, None))[0],
                    "rank_7d":     maps["7"].get(uid, (None, None))[1],
                    "rank_30d":    maps["30"].get(uid, (None, None))[1],
                    "rank_all":    maps["all"].get(uid, (None, None))[1],
                    "last_active_at_utc": (m.last_active_at_utc if m else None),
                }
                res = upsert_daily(s, getattr(m, "tenant", args.slug), uid, day, vals)
                if res == "insert": ins += 1
                else: upd += 1

            s.commit()
            total_ins += ins; total_upd += upd
            print(f"{day}: inserted={ins} updated={upd}")

        print(f"FERTIG — inserted={total_ins} updated={total_upd} (range {d0}..{d1})")
    finally:
        s.close()

if __name__ == "__main__":
    main()
