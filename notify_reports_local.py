#!/usr/bin/env python3
"""
Local wrapper to call the notify script with sensible defaults.
Usage: python notify_reports_local.py --slug hoomans --modes status,kpi,movers,health,joiners,celebrations,snapshots,alerts
"""
import argparse, os, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("--slug", required=True)
ap.add_argument("--modes", default="status,kpi,movers,health,joiners,celebrations,snapshots,alerts")
args = ap.parse_args()

modes = [m.strip() for m in args.modes.split(",") if m.strip()]
for m in modes:
    print(f"-> Notify mode: {m}")
    env = os.environ.copy()
    env["MODE"] = m
    env["TENANT_SLUG"] = args.slug
    subprocess.run(["python", ".github/scripts/discord_notify.py"], env=env)
