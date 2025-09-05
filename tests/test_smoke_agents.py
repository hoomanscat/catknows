import subprocess
from pathlib import Path


def test_run_agents_and_outputs():
    # Run the agents runner for the default tenant resolved by get_tenant_slug
    from skoolhud.config import get_tenant_slug
    tenant = get_tenant_slug(None)
    res = subprocess.run(["python", "skoolhud/ai/agents/run_all_agents.py", "--slug", tenant], capture_output=True, text=True)
    assert res.returncode == 0, f"Agents runner failed: {res.stderr}\n{res.stdout}"

    out = Path("exports") / "reports" / tenant
    assert out.exists(), "Reports dir missing"

    # Key artifacts we expect
    must_have = [
        f"kpi_2025-09-03.md",
        "member_health.csv",
        "new_joiners_week.md",
        "verify.txt",
    ]
    missing = [p for p in must_have if not (out / p).exists()]
    assert not missing, f"Missing expected artifacts: {missing}"
