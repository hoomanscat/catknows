from datetime import datetime, timezone, timedelta
from pathlib import Path

from skoolhud.db import SessionLocal
from skoolhud.models import Member

REPORT_DIR = Path("exports/reports")

def pct(part, whole):
    return 0.0 if not whole else round(100.0 * part / whole, 1)

def format_dt(dt):
    if not dt:
        return "-"
    if isinstance(dt, str):
        return dt
    return dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    s = SessionLocal()

    try:
        total = s.query(Member).count()

        active_7 = s.query(Member).filter(Member.points_7d != None, Member.points_7d > 0).count()
        active_30 = s.query(Member).filter(Member.points_30d != None, Member.points_30d > 0).count()

        top5_all = (
            s.query(Member.name, Member.points_all, Member.rank_all)
            .filter(Member.points_all != None)
            .order_by(Member.points_all.desc(), Member.rank_all.asc().nulls_last())
            .limit(5).all()
        )

        # "Beweger" heuristisch: hohe 7d/30d Punkte bei mittlerem All-Time (frische Aktivität)
        movers7 = (
            s.query(Member.name, Member.points_7d, Member.points_all)
            .filter(Member.points_7d != None, Member.points_7d > 0)
            .order_by(Member.points_7d.desc()).limit(5).all()
        )
        movers30 = (
            s.query(Member.name, Member.points_30d, Member.points_all)
            .filter(Member.points_30d != None, Member.points_30d > 0)
            .order_by(Member.points_30d.desc()).limit(5).all()
        )

        # Neuzugänge (falls joined_date vorhanden)
        try:
            last_7d = now - timedelta(days=7)
            new_last_7 = (
                s.query(Member.name, Member.joined_date)
                .filter(Member.joined_date != None)
                .filter(Member.joined_date >= last_7d.date())
                .order_by(Member.joined_date.desc()).limit(10).all()
            )
        except Exception:
            new_last_7 = []

        # Markdown bauen
        lines = []
        lines.append(f"# SkoolHUD Daily KPI — {now.strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append(f"- **Mitglieder gesamt:** {total}")
        lines.append(f"- **Aktiv (7 Tage):** {active_7} ({pct(active_7, total)}%)")
        lines.append(f"- **Aktiv (30 Tage):** {active_30} ({pct(active_30, total)}%)")
        lines.append(f"- **Erstellt um:** {format_dt(now)}")
        lines.append("")
        lines.append("## Top 5 (All-Time Punkte)")
        for n, p, r in top5_all:
            r_disp = r if r is not None else "-"
            p_disp = p if p is not None else 0
            lines.append(f"- #{r_disp}  {n} — {p_disp} pts")
        lines.append("")
        lines.append("## movers — past 7 days")
        for n, p7, pall in movers7:
            p7 = p7 or 0
            pall = pall or 0
            lines.append(f"- {n} — {p7} pts (7d) | {pall} all")
        lines.append("")
        lines.append("## movers — past 30 days")
        for n, p30, pall in movers30:
            p30 = p30 or 0
            pall = pall or 0
            lines.append(f"- {n} — {p30} pts (30d) | {pall} all")
        lines.append("")
        if new_last_7:
            lines.append("## Neuzugänge (letzte 7 Tage)")
            for n, jd in new_last_7:
                lines.append(f"- {n} — joined {jd}")
            lines.append("")

        report_path = REPORT_DIR / f"kpi_{now.strftime('%Y-%m-%d')}.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")

        # Kurz-Output Konsole
        print(f"Mitglieder: {total} | Aktiv 7d: {active_7} | Aktiv 30d: {active_30}")
        print(f"Report geschrieben: {report_path}")

    finally:
        s.close()

if __name__ == "__main__":
    main()
