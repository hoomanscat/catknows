import json, subprocess, sys, time
from pathlib import Path

TENANTS = json.loads(Path("tenants.json").read_text(encoding="utf-8"))

def run(cmd: list[str]):
    print(">>>", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        sys.exit(res.returncode)

def main():
    for t in TENANTS:
        slug, group = t["slug"], t["group"]
        print(f"\n==== RUN for tenant: {slug} ({group}) ====\n")
        # ensure tenant exists (idempotent: add again with same cookie is ok)
        import os
        env_cookie = os.getenv("SKOOL_COOKIE")
        if not env_cookie:
            raise RuntimeError("SKOOL_COOKIE nicht in .env gesetzt!")
        run(["skoolhud", "add-tenant", "--slug", slug, "--group", group,
             "--cookie", env_cookie.strip()])

        # fetch & normalize
        run(["skoolhud", "fetch-members-all", "--slug", slug])
        run(["skoolhud", "fetch-leaderboard", "--slug", slug])
        for w in ["all", "30", "7"]:
            run(["skoolhud", "normalize-leaderboard", "--slug", slug, "--window", w])

        # daily snapshot
        run(["skoolhud", "snapshot-members-daily", slug])

        # agents (optional: können tenant-aware erweitert werden; jetzt global)
        run([sys.executable, "skoolhud/ai/agents/run_all_agents.py"])

        # polite delay
        time.sleep(2)

    print("\n✅ Multi-tenant run complete.")

if __name__ == "__main__":
    main()
