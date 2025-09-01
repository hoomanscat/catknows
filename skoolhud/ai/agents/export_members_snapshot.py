# REPLACE FILE: skoolhud/ai/agents/export_members_snapshot.py
import argparse, csv
from datetime import datetime, timezone, date
from skoolhud.db import SessionLocal
from skoolhud.models import Member
from skoolhud.utils import datalake_members_dir_for

def _to_iso(x):
    if x is None: return ""
    if isinstance(x, datetime): return x.astimezone(timezone.utc).isoformat()
    return str(x)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="hoomans")
    args = ap.parse_args()

    today = date.today()
    part_dir = datalake_members_dir_for(args.slug, today)
    path = part_dir / "members.csv"

    s = SessionLocal()
    rows = []
    try:
        for m in s.query(Member).all():
            rows.append({
                "tenant": args.slug,
                "user_id": m.user_id,
                "name": m.name or "",
                "email": m.email or "",
                "level_current": m.level_current or 0,
                "points_7d": m.points_7d or 0,
                "points_30d": m.points_30d or 0,
                "points_all": m.points_all or 0,
                "rank_7d": m.rank_7d,
                "rank_30d": m.rank_30d,
                "rank_all": m.rank_all,
                "last_active_at_utc": _to_iso(m.last_active_at_utc),
                "joined_date": _to_iso(getattr(m, "joined_date", "")),
            })
    finally:
        s.close()

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        w.writeheader(); w.writerows(rows)
    (part_dir / "_SUCCESS").write_text("", encoding="utf-8")
    (part_dir / "manifest.txt").write_text(
        f"rows={len(rows)} generated_at={datetime.now(timezone.utc).isoformat()}",
        encoding="utf-8"
    )
    print(f"geschrieben: {path}")

if __name__ == "__main__":
    main()
