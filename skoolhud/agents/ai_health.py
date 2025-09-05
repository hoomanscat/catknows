#!/usr/bin/env python3
from __future__ import annotations
import os
from datetime import datetime
from skoolhud.utils import reports_dir_for
from skoolhud.config import get_tenant_slug
from skoolhud.db import SessionLocal
from skoolhud.models import Member
from skoolhud.ai.tools import llm_complete
from skoolhud.ai.tools import discord_report_post, STATUS_DIR
import json
import time
import os


def find_at_risk(tenant: str):
    s = SessionLocal()
    try:
        rows = s.query(Member.user_id, Member.name, Member.points_30d, Member.points_all, Member.last_active_at_utc).filter(Member.tenant == tenant).all()
    finally:
        s.close()
    at_risk = [r for r in rows if (r[2] or 0) < 5 and (r[3] or 0) > 50]
    return at_risk


def main(slug: str | None = None) -> int:
    slug = get_tenant_slug(slug)
    out_dir = reports_dir_for(slug)
    at_risk = find_at_risk(slug)
    sample = at_risk[:10]

    prompt = (
        "You are a community manager coach. Given the following list of at-risk users (id, name), write a short re-engagement plan with 5 steps and a sample message template.\n\n"
        f"At-risk sample: { [{'user_id': r[0], 'name': r[1]} for r in sample] }\n"
        "Respond with markdown: short plan and a message template."
    )

    provider = os.getenv('LLM_PROVIDER', 'ollama')
    out = llm_complete(prompt, max_tokens=512, provider=provider, purpose='health')

    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    md = out_dir / f"ai_health_plan_{ts}.md"
    md.write_text(f"# AI Health Plan ({slug})\n\nGenerated: {ts} UTC\n\n" + out, encoding='utf-8')
    print(f"Wrote AI health plan: {md}")
    webhook = os.getenv('DISCORD_WEBHOOK_HEALTH')
    if webhook:
        from skoolhud.ai.tools import post_guard_allowed, post_guard_mark
        if post_guard_allowed(slug, 'health', cooldown_env_var='HEALTH_POST_COOLDOWN'):
            status = discord_report_post(webhook, md, username=f"AI Health ({slug})")
            if status:
                post_guard_mark(slug, 'health')
            print(f"Discord post status: {status}")
        else:
            print("Skipping Discord post: Health cooldown not expired")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
