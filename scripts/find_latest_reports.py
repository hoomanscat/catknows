#!/usr/bin/env python3
"""Find the latest report files for common report types for a tenant.

Usage: python scripts/find_latest_reports.py <tenant>
"""
import sys
from pathlib import Path

from skoolhud.ai.tools import find_latest


def main(argv):
    if len(argv) < 2:
        print("Usage: find_latest_reports.py <tenant>")
        return 2
    tenant = argv[1]
    types = {
        'kpi': ['*kpi*.json', '*kpi*.csv', '*kpi*.md'],
        'health': ['*health*.json', '*health*.csv', '*health*.md'],
        'movers': ['*movers*.json', '*movers*.csv', '*movers*.md', '*leaderboard_delta*.json'],
        'delta': ['*delta*.json', '*delta*.csv', '*delta*.md'],
        'snapshot': ['*snapshot*.json', '*snapshot*.csv', '*snapshot*.md'],
        'new_joiners': ['*new_joiners*.md', '*new_joiners*.json'],
    }

    out = {}
    for k, pats in types.items():
        p = find_latest(tenant, *pats)
        out[k] = str(p) if p else None

    # print results
    for k, v in out.items():
        if v:
            print(f"{k.upper():12}: {v}")
        else:
            print(f"{k.upper():12}: MISSING")

    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
