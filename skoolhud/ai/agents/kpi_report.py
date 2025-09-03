# REPLACE FILE: skoolhud/ai/agents/kpi_report.py
import argparse
from datetime import datetime, timezone
from skoolhud.db import SessionLocal
from skoolhud.models import Member
from skoolhud.utils import reports_dir_for
from skoolhud.utils.schema_utils import validate_json
import json
from pathlib import Path

# load schema if available
SCHEMA_PATH = Path(__file__).resolve().parents[3] / "project-status" / "schemas" / "kpi_report.schema.json"
_KPI_SCHEMA = None
try:
    _KPI_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
except Exception:
    _KPI_SCHEMA = None

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

        # Recent New Joiners (if available)
        try:
            recent = s.query(Member.name, Member.joined_date).filter(Member.joined_date != None).order_by(Member.joined_date.desc()).limit(20).all()
        except Exception:
            recent = []

        if recent:
            lines.append("")
            lines.append("## New Joiners")
            for name, jd in recent:
                try:
                    date_str = jd.isoformat() if hasattr(jd, "isoformat") else str(jd)
                except Exception:
                    date_str = str(jd)
                lines.append(f"- {name} — joined {date_str}")

    # Build a minimal data dict for schema validation
    data = {
        "date": now.date().isoformat(),
        "tenant": args.slug,
        "metrics": {
            "total": total,
            "active7": active7,
            "active30": active30,
        },
        "new_joiners": [
            name for name, _ in (s.query(Member.name, Member.joined_date).filter(Member.joined_date != None).order_by(Member.joined_date.desc()).limit(20).all() or [])
        ],
    }

    if _KPI_SCHEMA is not None:
        ok, err = validate_json(data, _KPI_SCHEMA)
        if not ok:
            print(f"KPI schema validation failed: {err}")

    p = out_dir / f"kpi_{now.date().isoformat()}.md"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report geschrieben: {p}")

if __name__ == "__main__":
    main()
