# REPLACE FILE: skoolhud/ai/agents/health_score.py
import argparse
from datetime import datetime, timezone
import csv
from skoolhud.db import SessionLocal
from skoolhud.models import Member
from skoolhud.utils import reports_dir_for

def norm(x, hi): return 0.0 if x is None or x <= 0 else min(1.0, float(x)/float(hi))
def _to_dt(x):
    if x is None: return None
    if isinstance(x, datetime): return x.astimezone(timezone.utc) if x.tzinfo else x.replace(tzinfo=timezone.utc)
    s = str(x).strip()
    if s.endswith("Z"): s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except: return None
def _to_iso(x): 
    if x is None: return ""
    if isinstance(x, datetime): return x.astimezone(timezone.utc).isoformat()
    return str(x)

def recency_bonus(last_active):
    dt = _to_dt(last_active)
    if not dt: return 0.0
    days = (datetime.now(timezone.utc) - dt).total_seconds()/86400
    if days <= 1: return 1.0
    if days <= 3: return 0.9
    if days <= 7: return 0.8
    if days <= 14: return 0.6
    if days <= 30: return 0.4
    if days <= 60: return 0.2
    return 0.0

def health_score(p7, p30, lvl, last):
    s7  = norm(p7 or 0,  max(50, (p7 or 0), 200))
    s30 = norm(p30 or 0, max(150, (p30 or 0), 600))
    sLv = norm(lvl or 0, 20)
    sRc = recency_bonus(last)
    return round(100*(0.40*s7 + 0.30*s30 + 0.20*sRc + 0.10*sLv), 1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="hoomans")
    args = ap.parse_args()

    out_dir = reports_dir_for(args.slug)
    s = SessionLocal()
    rows = []
    try:
        for m in s.query(Member).all():
            rows.append({
                "user_id": m.user_id,
                "name": m.name or "",
                "level": m.level_current or 0,
                "points_7d": m.points_7d or 0,
                "points_30d": m.points_30d or 0,
                "points_all": m.points_all or 0,
                "last_active_at_utc": _to_iso(m.last_active_at_utc),
                "score": health_score(m.points_7d, m.points_30d, m.level_current, m.last_active_at_utc),
            })
    finally:
        s.close()

    csv_path = out_dir / "member_health.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader(); writer.writerows(rows)
    print(f"CSV geschrieben: {csv_path}")

    advocates = sorted(rows, key=lambda r: r["score"], reverse=True)[:10]
    at_risk = sorted([r for r in rows if r["score"] < 40 and (r["points_30d"] > 0 or r["points_all"] > 50)],
                     key=lambda r: r["score"])[:10]
    md = ["# Member Health — Top Advocates & At Risk", "", "## Advocates (Top 10)"]
    for r in advocates:
        md.append(f"- {r['name']} — score {r['score']} | 7d:{r['points_7d']} 30d:{r['points_30d']} lvl:{r['level']}")
    md.append(""); md.append("## At Risk (Top 10)")
    for r in at_risk:
        md.append(f"- {r['name']} — score {r['score']} | 7d:{r['points_7d']} 30d:{r['points_30d']} all:{r['points_all']}")
    (out_dir / "member_health_summary.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Summary geschrieben: {(out_dir / 'member_health_summary.md')}")

if __name__ == "__main__":
    main()
