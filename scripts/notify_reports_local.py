# scripts/notify_reports_local.py
# Sendet lokal generierte Reports (exports/reports) per Discord Webhooks aus .env
import os
import sys
import re
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from skoolhud.utils.net import post_with_retry

# .env laden (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = ROOT / "exports" / "reports"

# kleine Utils
def _env(*names: str) -> Optional[str]:
    """Erste gesetzte Env-Var aus names zurückgeben."""
    for n in names:
        v = os.getenv(n)
        if v:
            return v.strip()
    return None

def _short(s: str, limit: int = 1800) -> str:
    s = s.strip()
    return s if len(s) <= limit else (s[: limit - 20].rstrip() + "\n… (truncated)")

def _read_text(p: Path) -> Optional[str]:
    if p.exists() and p.is_file():
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return p.read_text(errors="ignore")
    return None

def _glob_one(*patterns) -> Optional[Path]:
    """Erstes existierende File nach Patterns (in Priorität) zurückgeben."""
    for pat in patterns:
        matches = sorted(REPORTS_ROOT.glob(pat), reverse=True)
        if matches:
            return matches[0]
    return None

def _glob_tenant(tenant: str, *patterns) -> Optional[Path]:
    """Sucht zuerst unter exports/reports/{tenant}, sonst im Root."""
    base_tenant = REPORTS_ROOT / tenant
    for pat in patterns:
        # tenantisiert
        matches = sorted(base_tenant.glob(pat), reverse=True)
        if matches:
            return matches[0]
        # un-tenantisiert (fallback)
        matches = sorted(REPORTS_ROOT.glob(pat), reverse=True)
        if matches:
            return matches[0]
    return None

def _send_discord(webhook_url: str, content: Optional[str] = None,
                  username: Optional[str] = None,
                  embeds: Optional[List[Dict[str, Any]]] = None,
                  file_path: Optional[Path] = None) -> int:
    if not webhook_url:
        print("SKIP: webhook_url empty")
        return 0

    payload: Dict[str, Any] = {}
    if content:
        payload["content"] = content
    if username:
        payload["username"] = username
    if embeds:
        payload["embeds"] = embeds

    files = None
    if file_path and file_path.exists():
        files = {"file": (file_path.name, file_path.open("rb"))}

    # Für Debug im CI nicht ganze URL loggen
    head = webhook_url[:60] + "..."
    print(f"POST -> {head}  file={file_path.name if file_path else '-'}")

    try:
        if files:
            resp = post_with_retry(webhook_url, json=payload, files=files, timeout=15)
        else:
            resp = post_with_retry(webhook_url, json=payload, timeout=15)
        print(f"Discord status: {getattr(resp, 'status_code', '??')}")
        if getattr(resp, 'status_code', 0) >= 300:
            try:
                print("Response:", resp.text[:500])
            except Exception:
                pass
        return getattr(resp, 'status_code', -1)
    except Exception as e:
        print("ERROR sending to discord:", e)
        return -1
    finally:
        if files:
            try:
                files["file"][1].close()
            except Exception:
                pass

def post_kpi(tenant: str):
    webhook = _env("DISCORD_WEBHOOK_KPI", "DISCORD_WEBHOOK_KPIS")
    if not webhook:
        print("SKIP KPI: no webhook")
        return
    md = _glob_tenant(tenant, f"{tenant}/kpi_*.md", "kpi_*.md")
    if not md:
        print("SKIP KPI: no file found")
        return
    text = _read_text(md) or ""
    title = f"📊 KPI Daily — {tenant}"
    embeds = [{
        "title": title,
        "description": _short(text),
        "footer": {"text": "SkoolHUD"},
    }]
    _send_discord(webhook, embeds=embeds, username="SkoolHUD")

def post_movers(tenant: str):
    webhook = _env("DISCORD_WEBHOOK_MOVERS")
    if not webhook:
        print("SKIP MOVERS: no webhook")
        return
    md = _glob_tenant(tenant,
                      f"{tenant}/leaderboard_movers.md",
                      f"{tenant}/leaderboard_delta_true.md",
                      "leaderboard_movers.md",
                      "leaderboard_delta_true.md")
    if not md:
        print("SKIP MOVERS: no file found")
        return
    text = _read_text(md) or ""
    embeds = [{
        "title": f"📈 Movers — {tenant} (7d)",
        "description": _short(text),
        "footer": {"text": "SkoolHUD"},
        "color": 0x2ecc71
    }]
    _send_discord(webhook, embeds=embeds, username="Spidey Bot")

def post_health(tenant: str):
    webhook = _env("DISCORD_WEBHOOK_HEALTH")
    if not webhook:
        print("SKIP HEALTH: no webhook")
        return
    md = _glob_tenant(tenant, f"{tenant}/member_health_summary.md", "member_health_summary.md")
    csv = _glob_tenant(tenant, f"{tenant}/member_health.csv", "member_health.csv")
    if not md:
        print("SKIP HEALTH: no file found")
        return
    text = _read_text(md) or ""
    embeds = [{
        "title": f"❤️ Member Health — {tenant}",
        "description": _short(text),
        "footer": {"text": "SkoolHUD"},
        "color": 0xf39c12
    }]
    _send_discord(webhook, embeds=embeds, username="Spidey Bot", file_path=csv)

def _extract_new_joiners_from_kpi(md_text: str) -> List[str]:
    lines = md_text.splitlines()
    out: List[str] = []
    # Titel in deutsch/englisch unterstützen
    start_idx = None
    for i, line in enumerate(lines):
        if re.search(r"(?i)new\s*joiners|neu(z|s)ug(ä|a)nge", line):
            start_idx = i + 1
            break
    if start_idx is None:
        return out
    for line in lines[start_idx: start_idx + 50]:  # max 50 Zeilen nach Titel scannen
        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        if not m:
            if line.strip() == "" or line.strip().startswith("#"):
                break
            continue
        out.append(m.group(1).strip())
        if len(out) >= 20:
            break
    return out

def post_new_joiners(tenant: str):
    webhook = _env("DISCORD_WEBHOOK_NEWJOINERS")
    if not webhook:
        print("SKIP NEW JOINERS: no webhook")
        return
    # Prefer explicit joiners files produced by the joiners agent
    out_dir = REPORTS_ROOT / tenant
    week = out_dir / "new_joiners_week.md"
    last = out_dir / "new_joiners_last_week.md"
    d30 = out_dir / "new_joiners_30d.md"

    sent_any = False
    if week.exists():
        text = _read_text(week) or ""
        if text.strip():
            _send_discord(webhook, embeds=[{
                "title": f"✨ New Joiners — This Week — {tenant}",
                "description": _short(text, 1800),
                "footer": {"text": "SkoolHUD"},
                "color": 0x9b59b6
            }], username="Captain Hook")
            sent_any = True
    if last.exists():
        text = _read_text(last) or ""
        if text.strip():
            _send_discord(webhook, embeds=[{
                "title": f"✨ New Joiners — Last Week — {tenant}",
                "description": _short(text, 1800),
                "footer": {"text": "SkoolHUD"},
                "color": 0x9b59b6
            }], username="Captain Hook")
            sent_any = True
    if d30.exists():
        text = _read_text(d30) or ""
        if text.strip():
            _send_discord(webhook, embeds=[{
                "title": f"✨ New Joiners — Last 30 days — {tenant}",
                "description": _short(text, 1800),
                "footer": {"text": "SkoolHUD"},
                "color": 0x9b59b6
            }], username="Captain Hook")
            sent_any = True

    if sent_any:
        return

    # Fallback: extract from KPI as before
    md = _glob_tenant(tenant, f"{tenant}/kpi_*.md", "kpi_*.md")
    if not md:
        print("SKIP NEW JOINERS: no KPI file and no joiners files")
        return
    text = _read_text(md) or ""
    items = _extract_new_joiners_from_kpi(text)
    if not items:
        print("SKIP NEW JOINERS: no items extracted from KPI")
        return

    # Schöne Liste bauen
    bullet = "\n".join(f"• {it}" for it in items[:20])
    embeds = [{
        "title": f"✨ New Joiners — {tenant}",
        "description": _short(bullet, 1800),
        "footer": {"text": "SkoolHUD"},
        "color": 0x9b59b6
    }]
    _send_discord(webhook, embeds=embeds, username="Captain Hook")

def post_status(tenant: str):
    webhook = _env("DISCORD_WEBHOOK_STATUS")
    webhook = _env("DISCORD_WEBHOOK_STATUS")
    # prefer tenantized verify file, then exports/reports/verify.txt, then repo-root verify.txt
    verify_txt = REPORTS_ROOT / tenant / "verify.txt"
    if not verify_txt.exists():
        verify_txt = REPORTS_ROOT / "verify.txt"
    if not verify_txt.exists():
        verify_txt = Path("verify.txt")
    if not webhook:
        print("SKIP STATUS: no webhook")
        return
    if not verify_txt.exists():
        print("SKIP STATUS: verify.txt not present")
        return
    text = _read_text(verify_txt) or ""
    # Ein einfaches Embed mit Spaltenähnlicher Formatierung
    embeds = [{
        "title": f"✅ SkoolHUD Daily — {tenant}",
        "description": f"```\n{_short(text, 1800)}\n```",
        "footer": {"text": "SkoolHUD"},
        "color": 0x2ecc71
    }]
    _send_discord(webhook, embeds=embeds, username="Captain Hook")

def main():
    tenant = sys.argv[1] if len(sys.argv) > 1 else "hoomans"
    # optional tenant-spezifische verify.txt erzeugen (für Status), wenn noch nicht da
    verify = REPORTS_ROOT / "verify.txt"
    if not verify.exists():
        verify.parent.mkdir(parents=True, exist_ok=True)
        verify.write_text("verify.txt:\n(local run — no metrics file)\n", encoding="utf-8")

    # Reihenfolge wie in den Discord-Kanälen
    post_status(tenant)
    time.sleep(0.5)
    post_kpi(tenant)
    time.sleep(0.5)
    post_movers(tenant)
    time.sleep(0.5)
    post_health(tenant)
    time.sleep(0.5)
    post_new_joiners(tenant)
    time.sleep(0.5)

    # Snapshots
    webhook = _env("DISCORD_WEBHOOK_SNAPSHOTS")
    snap = _glob_tenant(tenant, f"{tenant}/snapshot*.md", "snapshot*.md", f"{tenant}/snapshot*.csv", "snapshot*.csv")
    if webhook:
        if snap:
            _send_discord(webhook, content=f"Snapshot Report", username="SkoolHUD", file_path=snap)
        else:
            print("SKIP SNAPSHOTS: no file found")
    time.sleep(0.5)

    # Logs
    webhook = _env("DISCORD_WEBHOOK_LOGS")
    log = _glob_tenant(tenant, f"{tenant}/log*.txt", "log*.txt")
    if webhook:
        if log:
            _send_discord(webhook, content=f"Log Report", username="SkoolHUD", file_path=log)
        else:
            print("SKIP LOGS: no file found")
    time.sleep(0.5)

    # Alerts
    webhook = _env("DISCORD_WEBHOOK_ALERTS")
    alert = _glob_tenant(tenant, f"{tenant}/alert*.md", "alert*.md", f"{tenant}/alert*.txt", "alert*.txt")
    if webhook:
        if alert:
            _send_discord(webhook, content=f"Alert Report", username="SkoolHUD", file_path=alert)
        else:
            print("SKIP ALERTS: no file found")
    time.sleep(0.5)

    # Celebrations
    webhook = _env("DISCORD_WEBHOOK_CELEBRATIONS")
    celeb = _glob_tenant(tenant, f"{tenant}/celebration*.md", "celebration*.md", f"{tenant}/celebration*.txt", "celebration*.txt")
    if webhook:
        if celeb:
            _send_discord(webhook, content=f"Celebration Report", username="SkoolHUD", file_path=celeb)
        else:
            print("SKIP CELEBRATIONS: no file found")
    time.sleep(0.5)

    # Shoutouts
    webhook = _env("DISCORD_WEBHOOK_SHOUTOUTS")
    shout = _glob_tenant(tenant, f"{tenant}/shoutout*.md", "shoutout*.md", f"{tenant}/shoutout*.txt", "shoutout*.txt")
    if webhook:
        if shout:
            _send_discord(webhook, content=f"Shoutout Report", username="SkoolHUD", file_path=shout)
        else:
            print("SKIP SHOUTOUTS: no file found")

if __name__ == "__main__":
    main()
