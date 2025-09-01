#!/usr/bin/env python3
"""
Discord Notify Script for SkoolHUD
Sends embeds to different Discord channels based on MODE.
"""

import os
import json
import pathlib
import urllib.request
from datetime import datetime, timezone

# helper: send embed
def send_discord(webhook_url: str, embed: dict):
    data = {"embeds": [embed]}
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        print("Discord status:", r.status)


def main():
    mode = os.environ.get("MODE", "status")
    run_url = os.environ.get("RUN_URL", "")
    slug = os.environ.get("TENANT_SLUG", "hoomans")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    embed = {
        "title": f"SkoolHUD — {mode.upper()} Report",
        "url": run_url,
        "color": 0x5865F2,  # Discord blurple
        "footer": {"text": f"Tenant: {slug} | {now}"},
        "fields": [],
    }

    if mode == "status":
        webhook = os.environ.get("DISCORD_WEBHOOK_STATUS")
        txt = pathlib.Path("verify.txt").read_text(encoding="utf-8") if pathlib.Path("verify.txt").exists() else "no verify.txt"
        embed["description"] = f"```{txt[:1900]}```"
    elif mode == "kpi":
        webhook = os.environ.get("DISCORD_WEBHOOK_KPI")
        path = pathlib.Path(f"exports/reports/{slug}/kpi_{datetime.now().date()}.md")
        if path.exists():
            content = path.read_text(encoding="utf-8")
            embed["description"] = content[:1900]
        else:
            embed["description"] = "No KPI file found."
    elif mode == "movers":
        webhook = os.environ.get("DISCORD_WEBHOOK_MOVERS")
        path = pathlib.Path(f"exports/reports/{slug}/leaderboard_movers.md")
        if path.exists():
            content = path.read_text(encoding="utf-8")
            embed["description"] = content[:1900]
        else:
            embed["description"] = "No movers file found."
    elif mode == "health":
        webhook = os.environ.get("DISCORD_WEBHOOK_HEALTH")
        path = pathlib.Path(f"exports/reports/{slug}/member_health_summary.md")
        if path.exists():
            content = path.read_text(encoding="utf-8")
            embed["description"] = content[:1900]
        else:
            embed["description"] = "No health summary file found."
    elif mode == "joiners":
        webhook = os.environ.get("DISCORD_WEBHOOK_NEWJOINERS")
        path = pathlib.Path(f"exports/reports/{slug}/kpi_{datetime.now().date()}.md")
        if path.exists():
            lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if "joined" in ln]
            embed["description"] = "\n".join(lines) or "No new joiners today."
        else:
            embed["description"] = "No KPI file to extract joiners."
    else:
        print("Unknown MODE:", mode)
        return

    if not webhook:
        print(f"No webhook configured for mode={mode}")
        return

    send_discord(webhook, embed)


if __name__ == "__main__":
    main()
