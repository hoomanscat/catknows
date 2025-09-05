# daily_runner.py
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv


def run_cmd(cmd, check=True):
    print(f"\n--- RUN: {cmd}\n")
    res = subprocess.run(cmd, shell=isinstance(cmd, str))
    if check and res.returncode != 0:
        print(f"Command failed: {cmd} (rc={res.returncode})")
        sys.exit(res.returncode)


def main():
    # load .env for any scripts that rely on environment variables
    load_dotenv = None
    try:
        from dotenv import load_dotenv as _ld
        load_dotenv = _ld
    except Exception:
        load_dotenv = None
    if load_dotenv:
        load_dotenv(Path('.').resolve() / '.env')

    # 1) Update data + normalize (existing project step)
    run_cmd("python update_all.py")

    # 2) Snapshot daily members
    run_cmd("skoolhud snapshot-members-daily hoomans")

    # 3) Vector ingest for members (if available via CLI)
    try:
        run_cmd("python -m skoolhud.cli vectors-ingest --tenant hoomans")
    except SystemExit:
        # swallow non-zero exit so we can continue to reports
        pass

    # 4) Ingest reports into vector store and run orchestrator (full pipeline)
    run_cmd("python scripts/run_full_pipeline.py hoomans --force")

    print("\n✅ Daily run complete.\n")

    # 5) Send reports to Discord using local notifier (best-effort)
    try:
        print("Sende Reports an Discord...")
        subprocess.run([sys.executable, "scripts/notify_reports_local.py", "hoomans"], check=True)
        print("Reports erfolgreich gesendet.")
    except Exception as e:
        print(f"Fehler beim Senden der Reports: {e}")


if __name__ == "__main__":
    main()
