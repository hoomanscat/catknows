# REPLACE FILE: skoolhud/ai/agents/kpi_report.py
import argparse
from datetime import datetime, timezone
from skoolhud.db import SessionLocal
from skoolhud.models import Member
from skoolhud.utils import reports_dir_for

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="hoomans")
    args = ap.parse_args()

    out_dir = reports_dir_for(args.slug)
    s = SessionLocal()
    try:
        total = s.query(Member).count()
        active7 = s.query(Member).filter((Member.points_7d!=None) & (Member.points_7d>0)).count()
        active30 = s.query(Member).filter((Member.points_30d!=None) & (Member.points_30d>0)).count()
        top5 = (s.query(Member.name, Member.points_all, Member.rank_all)
                  .filter(Member.points_all!=None)
                  .order_by(Member.points_all.desc(), Member.rank_all.asc().nulls_last())
                  .limit(5).all())
    finally:
        s.close()

    now = datetime.now(timezone.utc)
    lines = [f"# SkoolHUD Daily KPI — {now.date().isoformat()}", ""]
    a7_pct = (active7 / total * 100) if total else 0
    a30_pct = (active30 / total * 100) if total else 0
    lines += [
        f"- **Mitglieder gesamt:** {total}",
        f"- **Aktiv (7 Tage):** {active7} ({a7_pct:.1f}%)",
        f"- **Aktiv (30 Tage):** {active30} ({a30_pct:.1f}%)",
        f"- **Erstellt um:** {now.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        "## Top 5 (All-Time Punkte)",
    ]
    for name, pts, rank in top5:
        lines.append(f"- #{rank if rank is not None else '-'}  {name} — {pts} pts")

    p = out_dir / f"kpi_{now.date().isoformat()}.md"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report geschrieben: {p}")

if __name__ == "__main__":
    main()
