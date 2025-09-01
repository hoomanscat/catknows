import subprocess, sys

def run(cmd: str):
    print(f"\n--- RUN: {cmd}\n")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        sys.exit(res.returncode)

def main():
    run("python update_all.py")                    # Daten holen & normalisieren
    run("skoolhud snapshot-members-daily hoomans")  # Daily Snapshot (Positions-Argument!)
    run("python skoolhud/ai/agents/run_all_agents.py")
    print("\n✅ Daily run complete.\n")

if __name__ == "__main__":
    main()