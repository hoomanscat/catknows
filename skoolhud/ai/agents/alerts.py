import argparse
from datetime import date, datetime
from skoolhud.db import SessionLocal
try:
    from skoolhud.models import MemberDailySnapshot, LeaderboardSnapshot, Member
except Exception:
    MemberDailySnapshot = None
    LeaderboardSnapshot = None
    Member = None
from skoolhud.utils import reports_dir_for

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="hoomans")
    args = ap.parse_args()

    out_dir = reports_dir_for(args.slug)
    today = date.today()
    s = SessionLocal()
    try:
        members = s.query(Member).count() if Member is not None else 0
        snaps_total = s.query(LeaderboardSnapshot).count() if LeaderboardSnapshot is not None else 0
        md_lines = [f"verify.txt:", f"Run at: {datetime.utcnow().isoformat()}Z", f"Members: {members}", f"LeaderboardSnapshots: {snaps_total}"]

        # Check MemberDailySnapshot for today
        has_daily = False
        daily_count = 0
        if MemberDailySnapshot is not None:
            daily_count = s.query(MemberDailySnapshot).filter(MemberDailySnapshot.day==today).count()
            has_daily = daily_count > 0
        md_lines.append(f"MemberDailySnapshot: today={daily_count}")

        # Simple workflow checks: presence of today's kpi / health / movers files
        import glob, os
        rpt = out_dir
        kpi = glob.glob(str(rpt / f"kpi_{today.isoformat()}*.md"))
        health = (rpt / "member_health_summary.md").exists()
        movers = (rpt / "leaderboard_movers.md").exists()
        snapshot_csv = os.path.exists(os.path.join("data_lake", args.slug, "members", f"dt={today.isoformat()}", "members.csv"))

        md_lines.append("")
        md_lines.append("Workflows status:")
        md_lines.append(f"{'✅' if kpi else '❌'} KPI report")
        md_lines.append(f"{'✅' if health else '❌'} Health summary")
        md_lines.append(f"{'✅' if movers else '❌'} Movers")
        md_lines.append(f"{'✅' if snapshot_csv else '❌'} Members snapshot (data_lake)")

        verify_path = out_dir / "verify.txt"
        verify_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

        # Produce alert if no daily snapshot rows or no leaderboard snapshots
        alerts = []
        if not has_daily:
            alerts.append("No MemberDailySnapshot rows for today — ingestion may have failed.")
        if snaps_total == 0:
            alerts.append("No LeaderboardSnapshot rows found — snapshot step may have failed.")

        if alerts:
            alert_fn = out_dir / f"alert_{today.isoformat()}.md"
            lines = ["# ⚠️ SkoolHUD Alerts — {0}".format(today.isoformat()), ""]
            for a in alerts:
                lines.append(f"- {a}")
            alert_fn.write_text("\n".join(lines)+"\n", encoding="utf-8")
            print(f"Wrote alert: {alert_fn}")
        else:
            print("No alerts detected; wrote verify.txt")
    finally:
        s.close()

if __name__ == '__main__':
    main()
