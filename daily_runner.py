import subprocess, sys

def run(cmd):
    print(f"\n--- RUN: {cmd}\n")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        sys.exit(res.returncode)

def main():
    run("python update_all.py")  # 1) Daten holen/normalisieren
    run("skoolhud snapshot-members-daily --slug hoomans")  # 2) Tages-Snapshot (über CLI)
    run("python skoolhud/ai/agents/run_all_agents.py")  # 3) KPI/Health/Movers + Data Lake
    print("\n✅ Daily run complete.\n")

if __name__ == "__main__":
    main()
