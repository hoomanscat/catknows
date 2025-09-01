import subprocess
import sys
from pathlib import Path

SLUG = "hoomans"
COOKIE_FILE = Path(__file__).parent / "cookie.txt"

def run(cmd: list[str]):
    print(f"\n>>> {' '.join(cmd)}")
    res = subprocess.run(cmd, text=True)
    if res.returncode != 0:
        sys.exit(res.returncode)

def main():
    print("==== SkoolHUD Update gestartet ====")

    if not COOKIE_FILE.exists():
        print(f"FEHLER: cookie.txt fehlt in {COOKIE_FILE}")
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

if __name__ == "__main__":
    main()
