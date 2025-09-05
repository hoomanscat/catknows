"""Simple shoutout generator for local runs.
Creates `exports/reports/<tenant>/shoutout_<date>.md` with a short list of candidates.
"""
from datetime import date
from pathlib import Path
import sys

from skoolhud.utils import reports_dir_for

def main():
    from skoolhud.config import get_tenant_slug
    tenant = sys.argv[1] if len(sys.argv) > 1 else None
    tenant = get_tenant_slug(tenant)
    out = reports_dir_for(tenant)
    today = date.today().isoformat()
    p = out / f"shoutout_{today}.md"
    content = [f"# Shoutouts — {tenant} — {today}", "", "Recognizing top movers and engaged members:", ""]
    sample = [
        "• Alice — great onboarding help",
        "• Bob — top contributor this week",
        "• Carol — awesome feedback on the course",
    ]
    content.extend(sample)
    p.write_text("\n".join(content), encoding='utf-8')
    print("Wrote shoutout file:", p)

if __name__ == '__main__':
    main()
