"""
scripts/notify_reports_local.py
Send local exports/reports files to Discord webhooks (used for local runs).
This file provides a small, self-contained notifier that prefers tenantized files
and falls back to simple DB-driven lookups when needed.
"""

import os
import sys
import re
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from skoolhud.utils.net import post_with_retry

# Root directory where agent reports are written
REPORTS_ROOT = Path(__file__).resolve().parent / "exports" / "reports"


def _env(*keys: str) -> str:
    """Return the first non-empty environment variable for the given keys."""
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return ""


def _short(text: Optional[str], max_len: int = 1900) -> str:
    if not text:
        return ""
    s = str(text)
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _read_text(path: Path) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return p.read_text(errors="ignore")


def _glob_tenant(tenant: str, *patterns: str) -> Optional[Path]:
    """Return first matching path searching under REPORTS_ROOT and the repo root.
    Patterns are glob-style like "{tenant}/kpi_*.md" or "kpi_*.md".
    """
    from glob import glob

    for pat in patterns:
        # try under exports/reports first
        candidate = str(REPORTS_ROOT / pat)
        for p in sorted(glob(candidate, recursive=True)):
            if Path(p).is_file():
                return Path(p)
        # fallback to glob pattern as given (repo-root)
        for p in sorted(glob(pat, recursive=True)):
            if Path(p).is_file():
                return Path(p)
    return None


def _send_discord(webhook_url: str, *, content: Optional[str] = None, embeds: Optional[List[Dict]] = None,
                  username: Optional[str] = None, file_path: Optional[Path] = None) -> int:
    """Post a payload (optionally with a file) to a Discord webhook using post_with_retry.

    Returns the HTTP status code (or -1 on error).
    """
    if not webhook_url:
        print("WARN: webhook_url empty -> skip")
        return -1

    payload: Dict[str, Any] = {}
    if content:
        payload["content"] = content
    if username:
        payload["username"] = username
    if embeds:
        payload["embeds"] = embeds

    files = None
    if file_path and Path(file_path).exists():
        files = {"file": (Path(file_path).name, Path(file_path).open("rb"))}

    head = webhook_url[:60] + ("..." if len(webhook_url) > 60 else "")
    print(f"POST -> {head}  file={file_path.name if file_path else '-'}")

    try:
        if files:
            resp = post_with_retry(webhook_url, json=payload, files=files, timeout=15)
        else:
            resp = post_with_retry(webhook_url, json=payload, timeout=15)
        status = getattr(resp, "status_code", getattr(resp, "status", "??"))
        print(f"Discord status: {status}")
        if getattr(resp, "status_code", 0) >= 300:
            try:
                print("Response:", resp.text[:500])
            except Exception:
                pass
        return int(status) if isinstance(status, int) else 0
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
    # prefer ai-generated KPI summary if present, then legacy kpi_*.md
    md = _glob_tenant(tenant, f"{tenant}/ai_kpi_summary_*.md", f"{tenant}/kpi_*.md", "ai_kpi_summary_*.md", "kpi_*.md")
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
    # prefer ai-generated health plan summary if present
    md = _glob_tenant(tenant, f"{tenant}/ai_health_plan_*.md", f"{tenant}/member_health_summary.md", "ai_health_plan_*.md", "member_health_summary.md")
    csv = _glob_tenant(tenant, f"{tenant}/member_health.csv", "member_health.csv")
    # If a CSV exists, build a concise markdown summary from it (stats + top/bottom lists)
    summary_md = ""
    if csv and csv.exists():
        try:
            import csv as _csv
            from statistics import mean
            rows = []
            csv_path = csv
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as fh:
                reader = _csv.DictReader(fh)
                for r in reader:
                    rows.append(r)

            summary_lines = []
            summary_lines.append(f"# ❤️ Member Health — {tenant}\n")
            summary_lines.append(f"Total rows: {len(rows)}")

            # Try to find a numeric score field
            score_field = None
            if rows:
                sample = rows[0]
                for k in sample.keys():
                    if re.search(r"health|score|engag|points", k, re.IGNORECASE):
                        score_field = k
                        break

            scores = []
            if score_field:
                for r in rows:
                    v = r.get(score_field, "")
                    try:
                        scores.append(float(str(v).replace(',', '.')))
                    except Exception:
                        continue
            if scores:
                avg = mean(scores)
                summary_lines.append(f"\n**{score_field}** — avg: {avg:.2f}, min: {min(scores):.2f}, max: {max(scores):.2f}")

                # build top/bottom tables
                # enrich rows with parsed score
                enriched = []
                for r in rows:
                    try:
                        s = float(str(r.get(score_field, '')).replace(',', '.'))
                    except Exception:
                        s = None
                    enriched.append((s, r))
                enriched_sorted = [e for e in enriched if e[0] is not None]
                enriched_sorted.sort(key=lambda x: x[0], reverse=True)

                def build_table(items):
                    lines = []
                    lines.append("| Rank | Name | Handle | Score |")
                    lines.append("|---:|---|---|---:|")
                    for i, (sc, rr) in enumerate(items, start=1):
                        name = rr.get('name') or rr.get('first_name') or rr.get('display') or rr.get('handle') or ''
                        handle = rr.get('handle') or rr.get('user') or ''
                        lines.append(f"| {i} | {name} | {handle} | {sc:.2f} |")
                    return "\n".join(lines)

                top_n = enriched_sorted[:5]
                bot_n = enriched_sorted[-5:][::-1] if len(enriched_sorted) >= 5 else enriched_sorted[::-1]

                if top_n:
                    summary_lines.append("\n## Top members by score\n")
                    summary_lines.append(build_table(top_n))
                if bot_n:
                    summary_lines.append("\n## Bottom members by score\n")
                    summary_lines.append(build_table(bot_n))
            else:
                # No numeric score, show a small sample of rows for human reading
                sample_rows = rows[:10]
                if sample_rows:
                    cols = list(sample_rows[0].keys())[:4]
                    # build table header
                    header = "| " + " | ".join(cols) + " |"
                    sep = "|" + "---|" * len(cols)
                    lines = [header, sep]
                    for r in sample_rows:
                        vals = [str(r.get(c, ''))[:30].replace('\n',' ') for c in cols]
                        lines.append("| " + " | ".join(vals) + " |")
                    summary_lines.append("\n".join(lines))

            summary_md = "\n\n".join(summary_lines)
        except Exception as e:
            print("Error building health summary from CSV:", e)

    # If there's an AI-generated Markdown summary, prefer it but append CSV-derived summary if present
    if md and md.exists():
        text = _read_text(md) or ""
        if summary_md:
            text = text.strip() + "\n\n---\n\n" + summary_md
        embeds = [{
            "title": f"❤️ Member Health — {tenant}",
            "description": _short(text),
            "footer": {"text": "SkoolHUD"},
            "color": 0xf39c12
        }]
        _send_discord(webhook, embeds=embeds, username="Spidey Bot", file_path=csv)
        return

    # If no md exists but we built a summary from CSV, post it
    if summary_md:
        embeds = [{
            "title": f"❤️ Member Health — {tenant}",
            "description": _short(summary_md, 1900),
            "footer": {"text": "SkoolHUD"},
            "color": 0xf39c12
        }]
        _send_discord(webhook, embeds=embeds, username="Spidey Bot", file_path=csv)
        return

    # fallback: if md present (but csv absent), post md
    if md and md.exists():
        text = _read_text(md) or ""
        embeds = [{
            "title": f"❤️ Member Health — {tenant}",
            "description": _short(text),
            "footer": {"text": "SkoolHUD"},
            "color": 0xf39c12
        }]
        _send_discord(webhook, embeds=embeds, username="Spidey Bot")
        return

    print("SKIP HEALTH: no file found")

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

    # Prefer explicit joiners files produced by agent; otherwise compute from DB
    out_dir = REPORTS_ROOT / tenant
    week_file = out_dir / "new_joiners_week.md"
    last_file = out_dir / "new_joiners_last_week.md"
    d30_file = out_dir / "new_joiners_30d.md"

    if week_file.exists() or last_file.exists() or d30_file.exists():
        # Post any explicit files present
        if week_file.exists():
            text = _read_text(week_file) or ""
            if text.strip():
                _send_discord(webhook, embeds=[{
                    "title": f"✨ New Joiners — This Week — {tenant}",
                    "description": _short(text, 1800),
                    "footer": {"text": "SkoolHUD"},
                    "color": 0x9b59b6
                }], username="Captain Hook")
        if last_file.exists():
            text = _read_text(last_file) or ""
            if text.strip():
                _send_discord(webhook, embeds=[{
                    "title": f"✨ New Joiners — Last Week — {tenant}",
                    "description": _short(text, 1800),
                    "footer": {"text": "SkoolHUD"},
                    "color": 0x9b59b6
                }], username="Captain Hook")
        if d30_file.exists():
            text = _read_text(d30_file) or ""
            if text.strip():
                _send_discord(webhook, embeds=[{
                    "title": f"✨ New Joiners — Last 30 days — {tenant}",
                    "description": _short(text, 1800),
                    "footer": {"text": "SkoolHUD"},
                    "color": 0x9b59b6
                }], username="Captain Hook")
        return

    # Fallback: compute new joiners from DB by joined_date
    try:
        from skoolhud.db import SessionLocal
        from skoolhud.models import Member
        from dateutil import parser as dtparser
        from datetime import datetime, timezone

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        week_members = []
        last_week_members = []
        month_members = []

        with SessionLocal() as s:
            q = s.query(Member).filter(Member.tenant == tenant).all()
            for m in q:
                jd = getattr(m, 'joined_date', None)
                if not jd:
                    continue
                try:
                    dt = dtparser.parse(jd)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                except Exception:
                    # ignore unparsable
                    continue
                delta = now - dt
                days = delta.total_seconds() / 86400.0
                display = f"{m.name or m.first_name or m.handle or m.user_id} - @{m.skool_tag or (m.handle or '')} - joined {dt.date()} ({int(days)}d)"
                if days < 7:
                    week_members.append(display)
                elif 7 <= days < 14:
                    last_week_members.append(display)
                elif 14 <= days < 30:
                    month_members.append(display)

        # helper to post list (if long, attach as file)
        def post_bucket(title: str, items: list):
            if not items:
                return
            body = "\n".join(f"• {it}" for it in items)
            if len(body) > 1800:
                # write temp file and attach
                tmp = out_dir / f"new_joiners_{title.replace(' ','_').lower()}.md"
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(body, encoding='utf-8')
                _send_discord(webhook, content=None, embeds=[{
                    "title": f"✨ New Joiners — {title} — {tenant}",
                    "description": _short(body, 1800),
                    "footer": {"text": "SkoolHUD"},
                    "color": 0x9b59b6
                }], username="Captain Hook", file_path=tmp)
            else:
                _send_discord(webhook, embeds=[{
                    "title": f"✨ New Joiners — {title} — {tenant}",
                    "description": _short(body, 1800),
                    "footer": {"text": "SkoolHUD"},
                    "color": 0x9b59b6
                }], username="Captain Hook")

        post_bucket("This Week (<7d)", week_members)
        post_bucket("Last Week (7-14d)", last_week_members)
        post_bucket("Last 30 days (14-30d)", month_members)
    except Exception as e:
        print("SKIP NEW JOINERS: DB error or missing deps:", e)

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
    from skoolhud.config import get_tenant_slug
    tenant = sys.argv[1] if len(sys.argv) > 1 else None
    tenant = get_tenant_slug(tenant)
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
            # If the snapshot is a CSV, include a small inline preview (first 8 lines) in the embed
            try:
                if snap.suffix.lower() == ".csv":
                    preview_lines = []
                    with open(snap, 'r', encoding='utf-8', errors='ignore') as fh:
                        for i, l in enumerate(fh):
                            if i >= 8:
                                break
                            preview_lines.append(l.rstrip())
                    preview = "\n".join(preview_lines)
                    embeds = [{
                        "title": f"# Snapshot — {tenant} — {snap.stem}",
                        "description": f"Members snapshot CSV attached.\n\n``n{_short(preview, 1000)}``,",
                        "footer": {"text": "SkoolHUD"},
                    }]
                    _send_discord(webhook, embeds=embeds, username="SkoolHUD", file_path=snap)
                else:
                    _send_discord(webhook, content=f"Snapshot Report", username="SkoolHUD", file_path=snap)
            except Exception:
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
