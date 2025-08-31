from datetime import datetime, timezone, timedelta
from pathlib import Path
import csv

from skoolhud.db import SessionLocal
from skoolhud.models import Member

OUT_DIR = Path("exports/reports")

def norm(x, hi):
    if x is None or x <= 0:
        return 0.0
    return min(1.0, float(x)/float(hi))

def recency_bonus(last_active_utc: datetime):
    if not last_active_utc:
        return 0.0
    now = datetime.now(timezone.utc)
    delta = now - last_active_utc.replace(tzinfo=timezone.utc)
    days = delta.total_seconds() / 86400.0
    if days <= 1:   return 1.0
    if days <= 3:   return 0.9
    if days <= 7:   return 0.8
    if days <= 14:  return 0.6
    if days <= 30:  return 0.4
    if days <= 60:  return 0.2
    return 0.0

def health_score(p7, p30, level, last_active_utc):
    # Gewichte: 7d (40%), 30d (30%), Recency (20%), Level (10%)
    s7  = norm(p7 or 0,  max(50, (p7 or 0), 200))
    s30 = norm(p30 or 0, max(150, (p30 or 0), 600))
    sLv = norm(level or 0, 20)
    sRc = recency_bonus(last_active_utc)
    score = 100.0 * (0.40*s7 + 0.30*s30 + 0.20*sRc + 0.10*sLv)
    return round(score, 1)

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    s = SessionLocal()
    rows = []
    try:
        for m in s.query(Member).all():
            score = health_score(m.points_7d, m.points_30d, m.level_current, m.last_active_at_utc)
            rows.append({
                "user_id": m.user_id,
                "name": m.name or "",
                "level": m.level_current or 0,
                "points_7d": m.points_7d or 0,
                "points_30d": m.points_30d or 0,
                "points_all": m.points_all or 0,
                "last_active_at_utc": m.last_active_at_utc.isoformat() if m.last_active_at_utc else "",
                "score": score,
            })
    finally:
        s.close()

    # CSV schreiben
    csv_path = OUT_DIR / "member_health.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV geschrieben: {csv_path}")

    # Advocates / At Risk
    advocates = sorted(rows, key=lambda r: r["score"], reverse=True)[:10]
    # "at risk": niedriger Score, aber hatten mal nennenswerte 30d / all (Reaktivierungspotential)
    at_risk = sorted(
        [r for r in rows if r["score"] < 40 and (r["points_30d"] > 0 or r["points_all"] > 50)],
        key=lambda r: r["score"]
    )[:10]

    # Markdown Quick Report
    md_lines = ["# Member Health — Top Advocates & At Risk", ""]
    md_lines.append("## Advocates (Top 10)")
    for r in advocates:
        md_lines.append(f"- {r['name']} — score {r['score']} | 7d:{r['points_7d']} 30d:{r['points_30d']} lvl:{r['level']}")
    md_lines.append("")
    md_lines.append("## At Risk (Top 10)")
    for r in at_risk:
        md_lines.append(f"- {r['name']} — score {r['score']} | 7d:{r['points_7d']} 30d:{r['points_30d']} all:{r['points_all']}")
    md_path = OUT_DIR / "member_health_summary.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Summary geschrieben: {md_path}")

if __name__ == "__main__":
    main()
