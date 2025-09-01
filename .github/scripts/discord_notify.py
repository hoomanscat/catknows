# REPLACE FILE: .github/scripts/discord_notify.py
#!/usr/bin/env python3
"""
Discord Notify Script for SkoolHUD
Sends embeds to different Discord channels based on MODE.
Robust: never fails the CI if Discord rejects request.
"""
import os, json, pathlib, urllib.request, urllib.error
from datetime import datetime, timezone

def _send_discord(webhook_url: str, payload: dict) -> None:
    if not webhook_url:
        print("WARN: webhook_url empty -> skip")
        return
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            print("Discord status:", r.status)
    except urllib.error.HTTPError as e:
        # Loggen, aber CI nicht hart failen
        print(f"ERROR: HTTPError {e.code} from Discord: {e.read().decode('utf-8', 'ignore')}")
    except Exception as e:
        print(f"ERROR: sending to Discord failed: {e}")

def _embed(title: str, description: str, color_hex: str = "5865F2", fields=None, url: str = "") -> dict:
    color = int(color_hex.replace("#", ""), 16)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    emb = {
        "title": title,
        "description": description[:1900] if description else "",
        "color": color,
        "footer": {"text": f"SkoolHUD • {now}"},
    }
    if url:
        emb["url"] = url
    if fields:
        emb["fields"] = fields
    return emb

def _read_text(path: str) -> str:
    p = pathlib.Path(path)
    if not p.exists(): return ""
    try:
        return p.read_text(encoding="utf-8")
    except:
        return p.read_text(errors="ignore")

def send_status(slug: str, run_url: str):
    raw = _read_text("verify.txt") or "verify.txt not found."
    # klein parsen
    import re
    def m(rx): 
        r = re.search(rx, raw)
        return int(r.group(1)) if r else None
    members = m(r"Members:\s*(\d+)")
    with_pts = m(r"with points_all:\s*(\d+)")
    lbs = m(r"LeaderboardSnapshots:\s*(\d+)")
    today = m(r"today\s*=\s*(\d+)")
    total = m(r"total\s*=\s*(\d+)")

    ok = (today or 0) > 0
    emoji = "✅" if ok else "❌"
    color = "2ECC71" if ok else "E74C3C"
    fields = []
    if members is not None:
        fields.append({"name":"Members","value":f"{members} (points_all: {with_pts or 0})","inline":True})
    if lbs is not None:
        fields.append({"name":"LB Snapshots","value":str(lbs),"inline":True})
    fields.append({"name":"Daily Snapshots (today)","value":str(today or 0),"inline":True})
    if total is not None:
        fields.append({"name":"Daily Snapshots (total)","value":str(total),"inline":True})

    desc = f"```text\n{raw[:1900]}\n```"
    emb = _embed(f"{emoji} SkoolHUD Daily — {slug}", desc, color, fields, run_url)
    _send_discord(os.environ.get("DISCORD_WEBHOOK_STATUS") or os.environ.get("DISCORD_WEBHOOK_ALERTS"), {"embeds":[emb]})
    if not ok:
        _send_discord(os.environ.get("DISCORD_WEBHOOK_ALERTS"), {"embeds":[emb]})

def send_kpi(slug: str, run_url: str):
    from glob import glob
    files = sorted(glob(f"exports/reports/{slug}/kpi_*.md"))
    txt = _read_text(files[-1]) if files else ""
    if not txt: txt = "No KPI file found."
    emb = _embed(f"📊 KPI Daily — {slug}", f"```md\n{txt[:1900]}\n```", "7289DA", url=run_url)
    _send_discord(os.environ.get("DISCORD_WEBHOOK_KPI") or os.environ.get("DISCORD_WEBHOOK_STATUS"), {"embeds":[emb]})

def send_movers(slug: str, run_url: str):
    txt = _read_text(f"exports/reports/{slug}/leaderboard_delta_true_7.md")
    if not txt:
        txt = _read_text(f"exports/reports/{slug}/leaderboard_movers.md")
    if not txt: txt = "No movers file found."
    emb = _embed(f"📈 Movers — {slug} (7d)", f"```md\n{txt[:1900]}\n```", "2ECC71", url=run_url)
    _send_discord(os.environ.get("DISCORD_WEBHOOK_MOVERS") or os.environ.get("DISCORD_WEBHOOK_STATUS"), {"embeds":[emb]})

def send_health(slug: str, run_url: str):
    txt = _read_text(f"exports/reports/{slug}/member_health_summary.md") or "No health summary file found."
    emb = _embed(f"❤️ Member Health — {slug}", f"```md\n{txt[:1900]}\n```", "E67E22", url=run_url)
    _send_discord(os.environ.get("DISCORD_WEBHOOK_HEALTH") or os.environ.get("DISCORD_WEBHOOK_STATUS"), {"embeds":[emb]})

def send_joiners(slug: str, run_url: str):
    from glob import glob
    files = sorted(glob(f"exports/reports/{slug}/kpi_*.md"))
    txt = _read_text(files[-1]) if files else ""
    if txt:
        lines = [ln for ln in txt.splitlines() if "joined" in ln]
        txt = "\n".join(lines) if lines else "No new joiners today."
    else:
        txt = "No KPI file to extract joiners."
    emb = _embed(f"✨ New Joiners — {slug}", f"```md\n{txt[:1900]}\n```", "9B59B6", url=run_url)
    _send_discord(os.environ.get("DISCORD_WEBHOOK_NEWJOINERS") or os.environ.get("DISCORD_WEBHOOK_STATUS"), {"embeds":[emb]})

def main():
    mode = os.environ.get("MODE", "status").lower()
    slug = os.environ.get("TENANT_SLUG", "hoomans")
    run_url = os.environ.get("RUN_URL", "")

    if mode == "status":   send_status(slug, run_url)
    elif mode == "kpi":    send_kpi(slug, run_url)
    elif mode == "movers": send_movers(slug, run_url)
    elif mode == "health": send_health(slug, run_url)
    elif mode == "joiners":send_joiners(slug, run_url)
    else:
        print(f"WARN: Unknown MODE={mode} -> skipping")

if __name__ == "__main__":
    main()
