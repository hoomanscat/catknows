import subprocess
import sys
from pathlib import Path

AGENTS = [
    "kpi_report.py",
    "health_score.py",
    "leaderboard_delta.py",
    "export_members_snapshot.py",
]

def run_agent(script: str):
    path = Path(__file__).parent / script
    print(f"\n--- RUNNING {script} ---\n")
    res = subprocess.run([sys.executable, str(path)])
    if res.returncode != 0:
        print(f"❌ Fehler bei {script}")
        sys.exit(res.returncode)

def main():
    for script in AGENTS:
        run_agent(script)
    print("\n✅ Alle Agents erfolgreich durchgelaufen. Reports liegen in exports/reports/ + data_lake/members/\n")

if __name__ == "__main__":
    main()
