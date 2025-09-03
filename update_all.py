import subprocess
import sys
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()

SLUG = "hoomans"

def run(cmd: list[str]):
    print(f"\n>>> {' '.join(cmd)}")
    res = subprocess.run(cmd, text=True)
    if res.returncode != 0:
        sys.exit(res.returncode)

def main():
    print("==== SkoolHUD Update gestartet ====")

    skool_cookie = os.getenv("SKOOL_COOKIE")
    if not skool_cookie:
        print(f"FEHLER: SKOOL_COOKIE nicht in .env gesetzt.")
        sys.exit(1)

    # 1) Members abrufen
    run(["skoolhud", "fetch-members-all", "--slug", SLUG])

    # 2) Leaderboard abrufen
    run(["skoolhud", "fetch-leaderboard", "--slug", SLUG])

    # 3) Leaderboard normalisieren (all/30/7)
    for w in ["all", "30", "7"]:
        run(["skoolhud", "normalize-leaderboard", "--slug", SLUG, "--window", w])

    # 4) Status prüfen
    run(["skoolhud", "count-members", "--slug", SLUG])

    # 5) Täglichen Snapshot in die DB schreiben (Positionsargument, kein --slug)
    run(["skoolhud", "snapshot-members-daily", SLUG])

    print("\n==== SkoolHUD Update fertig ====")

    # NOTE: notification is intentionally left to the caller (daily_runner)
    # If you want to send notifications after an ad-hoc update_all run,
    # call `python scripts/notify_reports_local.py {SLUG}` explicitly.

if __name__ == "__main__":
    main()
