# REPLACE FILE: skoolhud/ai/agents/run_all_agents.py
import argparse, subprocess, sys

def run(cmd):
    print(f"\n--- RUNNING {' '.join(cmd)} ---\n")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"❌ Fehler bei {' '.join(cmd)}")
        sys.exit(r.returncode)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    args = ap.parse_args()

    run([sys.executable, "skoolhud/ai/agents/kpi_report.py", "--slug", args.slug])
    run([sys.executable, "skoolhud/ai/agents/health_score.py", "--slug", args.slug])
    run([sys.executable, "skoolhud/ai/agents/leaderboard_delta.py", "--slug", args.slug])
    run([sys.executable, "skoolhud/ai/agents/export_members_snapshot.py", "--slug", args.slug])

if __name__ == "__main__":
    main()
