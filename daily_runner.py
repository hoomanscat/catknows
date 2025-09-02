# daily_runner.py
import subprocess, sys

def run(cmd: str):
    print(f"\n--- RUN: {cmd}\n")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        sys.exit(res.returncode)

def main():
    run("python update_all.py")                         # Daten holen & normalisieren
    run("skoolhud snapshot-members-daily hoomans")     # Daily Snapshot
    run("python skoolhud/ai/agents/run_all_agents.py") # Reports
    run("skoolhud vector-ingest hoomans")              # <<< Vector Ingest
    print("\n✅ Daily run complete.\n")

    # Reports an Discord senden
    try:
        print("Sende Reports an Discord...")
        subprocess.run([sys.executable, "scripts/notify_reports_local.py", "hoomans"], check=True)
        print("Reports erfolgreich gesendet.")
    except Exception as e:
        print(f"Fehler beim Senden der Reports: {e}")

if __name__ == "__main__":
    main()
