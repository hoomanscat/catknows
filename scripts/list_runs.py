from pathlib import Path
import sys

def main(tenant=None):
    from skoolhud.config import get_tenant_slug
    tenant = get_tenant_slug(tenant)
    base = Path('exports') / 'ai' / tenant
    if not base.exists():
        print('NO_RUNS: exports/ai/{tenant} missing'.format(tenant=tenant))
        return 2
    runs = sorted([d for d in base.iterdir() if d.is_dir()], key=lambda d: d.stat().st_mtime, reverse=True)
    if not runs:
        print('NO_RUNS: no run dirs under', str(base))
        return 2

    for d in runs:
        print('RUN:', d.name)
        print('  mtime:', d.stat().st_mtime)
        for fname in ('insights.md','actions.md','dispatch.json','dispatch_preview.json','status.json'):
            f = d / fname
            print('   {name:18} → {status}'.format(name=fname, status=('EXISTS' if f.exists() else 'MISSING')))
        print('')
    return 0

if __name__ == '__main__':
    tenant = sys.argv[1] if len(sys.argv) > 1 else None
    raise SystemExit(main(tenant))
