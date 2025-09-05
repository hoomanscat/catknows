#!/usr/bin/env python3
from __future__ import annotations
import os
from datetime import datetime
from skoolhud.utils import reports_dir_for
from skoolhud.config import get_tenant_slug
from skoolhud.agents.kpi_report import generate_kpi
from skoolhud.ai.tools import llm_complete
from skoolhud.ai.tools import discord_report_post, STATUS_DIR
import json
import time
import os
from datetime import timezone


def main(slug: str | None = None) -> int:
    slug = get_tenant_slug(slug)
    out_dir = reports_dir_for(slug)
    kpis = generate_kpi(slug)

    prompt = (
        "You are an analyst. Given the KPI summary below, write a short (3-5 lines) human-friendly summary and suggest 3 concrete actions.\n\n"
        f"KPI JSON: {kpis}\n"
        "Respond with markdown: heading, short summary paragraph, and bullet list of 3 actions."
    )

    provider = os.getenv('LLM_PROVIDER', 'ollama')
    out = llm_complete(prompt, max_tokens=256, provider=provider, purpose='kpi')

    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    md = out_dir / f"ai_kpi_summary_{ts}.md"
    md.write_text(f"# AI KPI Summary ({slug})\n\nGenerated: {ts} UTC\n\n" + out, encoding='utf-8')
    print(f"Wrote AI KPI summary: {md}")
    # post to Discord if webhook available
    # accept either singular or plural env names to match existing .env conventions
    webhook = os.getenv('DISCORD_WEBHOOK_KPIS') or os.getenv('DISCORD_WEBHOOK_KPI')
    if webhook:
        from skoolhud.ai.tools import post_guard_allowed, post_guard_mark
        if post_guard_allowed(slug, 'kpi', cooldown_env_var='KPI_POST_COOLDOWN'):
            status = discord_report_post(webhook, md, username=f"AI KPI ({slug})")
            if status:
                post_guard_mark(slug, 'kpi')
            print(f"Discord post status: {status}")
        else:
            print("Skipping Discord post: KPI cooldown not expired")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
