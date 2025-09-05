from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime


def compose_insights(findings: List[Dict[str, Any]], tenant: str, run_id: str) -> Dict[str, Any]:
    insights_lines = [f"# Insights — {tenant} — {run_id}", ""]
    actions_lines = [f"# Actions — {tenant} — {run_id}", ""]
    for f in findings:
        agent = f.get('agent', 'unknown')
        insights_lines.append(f"## {agent}")
        for b in f.get('bullets', [])[:8]:
            insights_lines.append(f"- {b}")
        insights_lines.append("")
        for a in f.get('actions', [])[:8]:
            actions_lines.append(f"- {a.get('title')} (owner={a.get('owner')})")

    return {
        'insights_md': '\n'.join(insights_lines),
        'actions_md': '\n'.join(actions_lines),
        'summary': {'agents': [f.get('agent') for f in findings]}
    }

