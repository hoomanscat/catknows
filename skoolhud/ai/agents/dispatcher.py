from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional
import time
import json
from skoolhud.ai.tools import discord_report_post, post_guard_allowed, post_guard_mark
import os


class Dispatcher:
    def __init__(self, channels_config: Optional[Dict[str, str]] = None):
        # channels_config maps logical names to webhook urls; fallback to env vars
        if channels_config:
            self.channels = channels_config
        else:
            # accept multiple common env var names (singular/plural and status/kpi variants)
            ai_insights = (
                os.getenv('DISCORD_WEBHOOK_KPIS')
                or os.getenv('DISCORD_WEBHOOK_KPI')
                or os.getenv('DISCORD_WEBHOOK_STATUS')
                or os.getenv('DISCORD_WEBHOOK_URL')
            )
            self.channels = {'ai_insights': ai_insights}

    def dispatch(self, tenant: str, out_dir: Path, force: bool = False) -> Dict[str, Any]:
        insights = (out_dir / 'insights.md')
        actions = (out_dir / 'actions.md')
        results = {'tenant': tenant, 'posted': [], 'errors': []}

        # Post insights to configured channel if allowed
        webhook = self.channels.get('ai_insights')
        if webhook and insights.exists():
            allowed = True if force else post_guard_allowed(tenant, 'ai_insights')
            if allowed:
                try:
                    from skoolhud.ai.tools import discord_report_post_verbose
                    res = discord_report_post_verbose(webhook, insights, username=f"SkoolHUD AI — {tenant}")
                except Exception as e:
                    res = {'status': 0, 'text': str(e)}
                results['posted'].append({'channel': 'ai_insights', 'status': res.get('status'), 'body': res.get('text')})
                try:
                    st = int(res.get('status') or 0)
                    if st >= 200 and st < 300:
                        post_guard_mark(tenant, 'ai_insights')
                    else:
                        results['errors'].append({'channel': 'ai_insights', 'status': st, 'body': res.get('text')})
                except Exception:
                    pass
            else:
                results['errors'].append({'channel': 'ai_insights', 'status': 'guard-blocked'})

        # Always write a local dispatch preview
        try:
            (out_dir / 'dispatch_preview.json').write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception:
            pass

        return results
