#!/usr/bin/env python3
"""Test configured Discord webhooks by posting a tiny test message and printing status/body.

Usage: python scripts/test_webhooks.py
"""
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path('.').resolve() / '.env')
from skoolhud.utils.net import post_with_retry

WEBHOOK_KEYS = (
    'DISCORD_WEBHOOK_KPIS',
    'DISCORD_WEBHOOK_KPI',
    'DISCORD_WEBHOOK_STATUS',
    'DISCORD_WEBHOOK_URL',
)

payload = {"content": "[test] SkoolHUD webhook connectivity check", "username": "SkoolHUD Test"}

for k in WEBHOOK_KEYS:
    url = os.getenv(k)
    if not url:
        print(f"{k}: MISSING")
        continue
    print(f"Posting to {k} -> {url[:60]}...")
    try:
        r = post_with_retry(url, json=payload, timeout=15)
        print(f"  status={getattr(r,'status_code', None)} body={getattr(r,'text', '')[:300]!r}")
    except Exception as e:
        print(f"  ERROR: {e}")
