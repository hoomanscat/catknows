#!/usr/bin/env python3
"""Load .env into process and run the orchestrator for a tenant.

Usage: python scripts/run_orchestrator_with_env.py <tenant> [--force]
"""
import sys
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(dotenv_path=Path('.').resolve() / '.env')

def print_webhooks():
    keys = ('DISCORD_WEBHOOK_KPIS','DISCORD_WEBHOOK_KPI','DISCORD_WEBHOOK_STATUS','DISCORD_WEBHOOK_URL')
    for k in keys:
        v = os.getenv(k)
        if v:
            print(f"{k} => SET (prefix: {v[:60]})")
        else:
            print(f"{k} => MISSING")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python scripts/run_orchestrator_with_env.py <tenant> [--force]')
        raise SystemExit(2)
    tenant = sys.argv[1]
    force = '--force' in sys.argv[2:]
    print('Loading .env and printing webhook vars:')
    print_webhooks()
    print('\nRunning orchestrator for tenant:', tenant, 'force=', force)
    try:
        from skoolhud.ai.orchestrator import run_orchestrator
        rc = run_orchestrator(tenant, force=force)
        print('Orchestrator exit code:', rc)
    except Exception as e:
        print('Orchestrator error:', e)
        raise
