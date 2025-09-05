import subprocess
from pathlib import Path
import sys

def main():
    from skoolhud.config import get_tenant_slug
    tenant = get_tenant_slug(None)
    print(f"Running agents runner for '{tenant}'...")
    res = subprocess.run([sys.executable, "skoolhud/ai/agents/run_all_agents.py", "--slug", tenant], capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr)
        raise SystemExit(2)

    out = Path("exports") / "reports" / tenant
    if not out.exists():
        print("Reports dir missing")
        raise SystemExit(3)

    must_have = [
        f"kpi_2025-09-03.md",
        "member_health.csv",
        "new_joiners_week.md",
        "verify.txt",
    ]
    missing = [p for p in must_have if not (out / p).exists()]
    if missing:
        print("Missing expected artifacts:", missing)
        raise SystemExit(4)

    print("Smoke test OK — all artifacts present.")

if __name__ == '__main__':
    main()
