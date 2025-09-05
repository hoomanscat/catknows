import argparse
from datetime import datetime
from typing import List

from skoolhud.db import SessionLocal
from skoolhud.utils import reports_dir_for
from skoolhud.ai.tools import discord_report_post, STATUS_DIR
import json
import os
from datetime import timezone


def _format_alert(row: dict) -> str:
	"""Format a single alert row into a markdown line.

	Accepts either a mapping-like row (from SQLAlchemy .mappings()) or an object with attributes.
	"""
	try:
		title = row.get("title") if isinstance(row, dict) else getattr(row, "title", "(no title)")
		level = row.get("level") if isinstance(row, dict) else getattr(row, "level", "info")
		ts = row.get("created_at") if isinstance(row, dict) else getattr(row, "created_at", None)
		details = row.get("details") if isinstance(row, dict) else getattr(row, "details", "")
	except Exception:
		# defensive fallback
		title = getattr(row, "title", "(no title)")
		level = getattr(row, "level", "info")
		ts = getattr(row, "created_at", None)
		details = getattr(row, "details", "")

	if isinstance(ts, (int, float)):
		try:
			ts = datetime.fromtimestamp(ts)
		except Exception:
			ts = None

	ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts, datetime) else str(ts or "")
	lvl = str(level or "info").upper()
	summary = f"**{lvl}**: {title} — {ts_str}"
	if details:
		summary = f"{summary}\n\n{details}"
	return summary


def main() -> None:
	ap = argparse.ArgumentParser(description="Write tenantized alerts to exports/reports/<slug>/alerts.md")
	ap.add_argument("--slug", default=None)
	ap.add_argument("--limit", type=int, default=100, help="Max number of alerts to include")
	args = ap.parse_args()
	from skoolhud.config import get_tenant_slug
	args.slug = get_tenant_slug(args.slug)

	out_dir = reports_dir_for(args.slug)

	# prepare status guard file for rate-limiting posts per-tenant
	STATUS_DIR.mkdir(parents=True, exist_ok=True)
	guard_file = STATUS_DIR / f"alerts_last_post_{args.slug}.json"
	# cooldown seconds before posting again
	post_cooldown = int(os.getenv('ALERTS_POST_COOLDOWN', '3600'))

	s = SessionLocal()
	try:
		# Prefer using an Alert model if available, otherwise raw SQL
		alerts: List[dict] = []
		# Read alerts via SQL; this works regardless of whether an ORM model exists
		from sqlalchemy import text
		try:
			rows = s.execute(text("SELECT title, level, created_at, details FROM alerts ORDER BY created_at DESC LIMIT :lim"), {"lim": args.limit})
			alerts = [dict(r) for r in rows.mappings().all()]
		except Exception:
			alerts = []

	finally:
		s.close()

	if not alerts:
		# write an empty file (no alerts) but avoid posting placeholder content elsewhere
		(out_dir / "alerts.md").write_text("", encoding="utf-8")
		print("Wrote alerts: 0")
		return

	lines: List[str] = []
	for a in alerts:
		lines.append(_format_alert(a))
		lines.append("---")

	content = "\n\n".join(lines).rstrip() + "\n"
	(out_dir / "alerts.md").write_text(content, encoding="utf-8")

	print(f"Wrote alerts: {len(alerts)}")

	webhook = os.getenv('DISCORD_WEBHOOK_ALERTS')
	if webhook:
		from skoolhud.ai.tools import post_guard_allowed, post_guard_mark
		if post_guard_allowed(args.slug, 'alerts', cooldown_env_var='ALERTS_POST_COOLDOWN'):
			status = discord_report_post(webhook, out_dir / "alerts.md", username=f"SkoolHUD Alerts ({args.slug})")
			if status:
				post_guard_mark(args.slug, 'alerts')
			print(f"Posted alerts to Discord: {status}")
		else:
			print("Skipping Discord post: cooldown not expired")


if __name__ == '__main__':
	main()