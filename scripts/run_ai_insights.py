"""Run AI orchestrator for tenants and produce exports/ai outputs.

Usage: python scripts/run_ai_insights.py [--slug SLUG]
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from skoolhud.ai.orchestrator import run_for_tenant

ROOT = Path(__file__).resolve().parents[1]

def load_tenants() -> list[str]:
    tj = ROOT / 'tenants.json'
    if not tj.exists():
        return []
    raw = tj.read_text(encoding='utf-8')
    try:
        return json.loads(raw)
    except Exception:
        # Try a forgiving fallback: newline-separated slugs or a JSON-with-comments style
        lines = [l.strip() for l in raw.splitlines() if l.strip() and not l.strip().startswith('//')]
        # If file looks like a Python/list representation without proper JSON, try eval? Avoid eval for safety.
        return lines

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--slug', help='Run for a single tenant slug', default=None)
    args = p.parse_args()

    tenants = load_tenants()
    if args.slug:
        tenants = [args.slug]

    if not tenants:
        print('No tenants found in tenants.json and no --slug provided.')
        return 1

    for t in tenants:
        out = run_for_tenant(t)
        print(f'Wrote AI outputs to: {out}')

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
