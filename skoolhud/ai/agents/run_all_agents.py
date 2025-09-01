# REPLACE FILE: skoolhud/ai/agents/run_all_agents.py  (ensure true-delta is executed)
import subprocess, sys
from pathlib import Path

AGENTS = [
    "kpi_report.py",
    "health_score.py",
    "leaderboard_delta.py",
    "export_members_snapshot.py",
    "leaderboard_delta_true.py",
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
    print("\n✅ Alle Agents OK (exports/reports + data_lake/members)\n")

if __name__ == "__main__":
    main()
