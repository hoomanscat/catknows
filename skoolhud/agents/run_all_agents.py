# REPLACE FILE: copied from ai/agents
import subprocess, sys
from pathlib import Path
import argparse
from skoolhud.config import get_tenant_slug

AGENTS = [
    "ai_kpi.py",
    "ai_health.py",
    "kpi_report.py",
    "health_score.py",
    "leaderboard_delta.py",          # (optional: ebenfalls tenantisieren)
    "export_members_snapshot.py",
    "joiners.py",
    "leaderboard_delta_true.py",
    "alerts.py",
    "celebrations.py",
    "snapshot_report.py",
]

def run_agent(script: str, slug: str):
    path = Path(__file__).parent / script
    print(f"\n--- RUNNING {script} ({slug}) ---\n")
    if not path.exists():
        print(f"⚠️ Skipping {script}: file not found at {path}")
        return
    res = subprocess.run([sys.executable, str(path), "--slug", slug])
    if res.returncode != 0:
        print(f"❌ Fehler bei {script}")
        sys.exit(res.returncode)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default=None)
    args = ap.parse_args()
    resolved = get_tenant_slug(args.slug)
    for script in AGENTS:
        run_agent(script, resolved)
    print("\n[OK] Agents completed (tenantized)\n")

if __name__ == "__main__":
    main()
