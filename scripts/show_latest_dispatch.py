from pathlib import Path
import sys

def main(tenant=None):
    from skoolhud.config import get_tenant_slug
    tenant = get_tenant_slug(tenant)
    base = Path('exports') / 'ai' / tenant
    if not base.exists():
        print('NO_RUNS: exports/ai/{tenant} missing'.format(tenant=tenant))
        return 2
    dirs = [d for d in base.iterdir() if d.is_dir()]
    if not dirs:
        print('NO_RUNS: no run dirs under', str(base))
        return 2
    latest = sorted(dirs, key=lambda d: d.stat().st_mtime, reverse=True)[0]
    print('LATEST_DIR:', latest)
    for name in ('dispatch_preview.json', 'dispatch.json', 'status.json'):
        p = latest / name
        if p.exists():
            print('\n---', name, '---')
            try:
                print(p.read_text(encoding='utf-8'))
            except Exception as e:
                print('ERR reading', name, e)
        else:
            print('\nMISSING', name)
    return 0

if __name__ == '__main__':
    tenant = sys.argv[1] if len(sys.argv) > 1 else None
    raise SystemExit(main(tenant))
