import argparse
from datetime import date, datetime, timedelta
from dateutil import parser as dtparser
from skoolhud.db import SessionLocal
from skoolhud.models import Member
from skoolhud.utils import reports_dir_for

def _to_dt(x):
    if x is None:
        return None
    if isinstance(x, datetime):
        return x
    try:
        return dtparser.parse(str(x))
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="hoomans")
    args = ap.parse_args()

    out_dir = reports_dir_for(args.slug)
    today = date.today()
    # start of current week (Monday)
    weekday = today.isoweekday()  # Monday=1
    start_this_week = today - timedelta(days=(weekday - 1))
    start_last_week = start_this_week - timedelta(days=7)
    end_last_week = start_this_week - timedelta(days=1)
    cutoff_30 = today - timedelta(days=30)

    s = SessionLocal()
    try:
        # detect whether the members table has a skool_tag column
        try:
            from sqlalchemy import text
            cols = [r[1] for r in s.execute(text("PRAGMA table_info(members)")).fetchall()]
            has_skool = "skool_tag" in cols
        except Exception:
            has_skool = False

        if has_skool:
            rows = s.query(Member.name, Member.joined_date, Member.skool_tag).filter(Member.joined_date != None).all()
        else:
            # return rows with None for skool_tag
            rows = [(r[0], r[1], None) for r in s.query(Member.name, Member.joined_date).filter(Member.joined_date != None).all()]
    finally:
        s.close()

    def fmt_entry(name: str, dt: datetime, skool_tag: str | None, user_id: str | None = None) -> str:
        # ensure @ prefix
        tag = (skool_tag or "").strip()
        if tag and not tag.startswith("@"):
            tag = f"@{tag}"
        date_str = dt.strftime("%d.%m.%Y")
        # relative time (hours/days ago) — handle tz-aware datetimes
        now = datetime.now(dt.tzinfo) if getattr(dt, 'tzinfo', None) else datetime.now()
        delta = now - dt
        rel = ""
        if delta.total_seconds() < 86400:
            # less than a day -> show hours
            hours = int(delta.total_seconds() // 3600)
            if hours <= 0:
                rel = "( <1 Day ago )"
            else:
                rel = f"( <{hours} Hours ago )"
        else:
            days = int(delta.total_seconds() // 86400)
            rel = f"( {days} Days ago )"

        # Format: Name - @skooltag joined on DD.MM.YYYY (X Hours/Days ago) [user_id]
        parts = [name]
        if tag:
            parts.append(tag)
        joined_part = f"joined on {date_str} {rel}".strip()
        parts.append(joined_part)
        if user_id:
            parts.append(f"[{user_id}]")
        return " - ".join(parts)

    week = []
    last_week = []
    d30 = []
    seen = set()
    for row in rows:
        # rows may be tuples (name, joined_date, skool_tag) or (name, joined_date, None)
        if len(row) == 3:
            name, jd, skool_tag = row
            user_id = None
        else:
            name, jd = row[0], row[1]
            skool_tag = None
            user_id = None
        dt = _to_dt(jd)
        if not dt:
            continue
        d = dt.date()
        entry = fmt_entry(name or "(no name)", dt, skool_tag, user_id)
        if d >= start_this_week and name not in seen:
            week.append(entry); seen.add(name)
        if start_last_week <= d <= end_last_week:
            last_week.append(entry)
        if d >= cutoff_30:
            d30.append(entry)

    # write files (names only)
    (out_dir / "new_joiners_week.md").write_text("\n".join([f"- {n}" for n in week]) + ("\n" if week else ""), encoding="utf-8")
    (out_dir / "new_joiners_last_week.md").write_text("\n".join([f"- {n}" for n in last_week]) + ("\n" if last_week else ""), encoding="utf-8")
    (out_dir / "new_joiners_30d.md").write_text("\n".join([f"- {n}" for n in d30]) + ("\n" if d30 else ""), encoding="utf-8")

    print(f"Wrote joiners: week={len(week)} last_week={len(last_week)} 30d={len(d30)}")

if __name__ == '__main__':
    main()
