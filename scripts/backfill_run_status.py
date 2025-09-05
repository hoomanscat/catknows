#!/usr/bin/env python3
"""Backfill run-local status.json files.

For each run under exports/status/runs/<run_id>/<tenant>/status.json, copy it to
exports/ai/<tenant>/<run_id>/status.json if the destination is missing.
"""
from pathlib import Path
import shutil

STATUS_ROOT = Path('exports') / 'status' / 'runs'
AI_ROOT = Path('exports') / 'ai'

copied = []
missing_canonical = []
for run_dir in STATUS_ROOT.iterdir():
    if not run_dir.is_dir():
        continue
    for tenant_dir in run_dir.iterdir():
        if not tenant_dir.is_dir():
            continue
        canonical = tenant_dir / 'status.json'
        if not canonical.exists():
            missing_canonical.append(str(canonical))
            continue
        # target run folder
        run_id = run_dir.name
        tenant = tenant_dir.name
        dest_dir = AI_ROOT / tenant / run_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / 'status.json'
        if dest_file.exists():
            # skip existing
            continue
        try:
            shutil.copy2(canonical, dest_file)
            copied.append(str(dest_file))
        except Exception as e:
            print('ERROR copying', canonical, '->', dest_file, e)

print('Copied:', len(copied))
for p in copied:
    print('  ', p)
if missing_canonical:
    print('Runs missing canonical status.json:', len(missing_canonical))
    for p in missing_canonical[:10]:
        print('   ', p)
