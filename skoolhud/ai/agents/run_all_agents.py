# REPLACE FILE: skoolhud/ai/agents/run_all_agents.py
import subprocess, sys
from pathlib import Path
import argparse

AGENTS = [
    "kpi_report.py",
    "health_score.py",
    "leaderboard_delta.py",          # (optional: ebenfalls tenantisieren)
    "export_members_snapshot.py",
    "leaderboard_delta_true.py",
]

def run_agent(script: str, slug: str):
    path = Path(__file__).parent / script
    print(f"\n--- RUNNING {script} ({slug}) ---\n")
    res = subprocess.run([sys.executable, str(path), "--slug", slug])
    if res.returncode != 0:
        print(f"❌ Fehler bei {script}")
        sys.exit(res.returncode)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="hoomans")
    args = ap.parse_args()
    for script in AGENTS:
        run_agent(script, args.slug)
    print("\n✅ Agents OK (tenantized)\n")

if __name__ == "__main__":
    main()
