#!/usr/bin/env python3
"""Run full pipeline for a tenant: ingest reports to vector DB, then run orchestrator.

Usage: python scripts/run_full_pipeline.py <tenant> [--force]
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path('.').resolve() / '.env')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python scripts/run_full_pipeline.py <tenant> [--force]')
        raise SystemExit(2)
    tenant = sys.argv[1]
    force = '--force' in sys.argv[2:]

    print('Running full pipeline for tenant:', tenant, 'force=', force)

    # 1) Ingest reports to vector (if function available)
    try:
        from skoolhud.vector.ingest import ingest_reports_to_vector
        print('Starting report -> vector ingest...')
        try:
            ingest_reports_to_vector(tenant)
            print('Report ingest finished')
        except Exception as e:
            print('Report ingest failed:', e)
    except Exception as e:
        print('No ingest_reports_to_vector available, skipping vector ingest:', e)

    # 2) Run orchestrator
    try:
        from skoolhud.ai.orchestrator import run_orchestrator
        rc = run_orchestrator(tenant, force=force)
        print('Orchestrator exit code:', rc)
    except Exception as e:
        print('Orchestrator failed:', e)
        raise
