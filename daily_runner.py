import subprocess, sys

def run(cmd: str):
    print(f"\n--- RUN: {cmd}\n")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        sys.exit(res.returncode)

def main():
    # 1. Fetch + Normalize
    run("python update_all.py")

    # 2. Daily Snapshot
    run("skoolhud snapshot-members-daily hoomans")

    # 3. Run all agents (generiert Reports in exports/reports)
    run("python skoolhud/ai/agents/run_all_agents.py")

    # 4. Notify Discord (lokal, nutzt .env mit allen DISCORD_WEBHOOK_* Variablen)
    try:
       run("python scripts/notify_reports_local.py hoomans")
    except SystemExit as e:
        print(f"[WARN] notify failed: {e}")

    print("\n✅ Daily run complete.\n")

if __name__ == "__main__":
    main()
