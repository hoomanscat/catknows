import argparse, shutil, os
from datetime import date
from pathlib import Path
from skoolhud.utils import reports_dir_for, datalake_members_dir_for

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="hoomans")
    args = ap.parse_args()

    out_dir = reports_dir_for(args.slug)
    today = date.today()
    src_dir = datalake_members_dir_for(args.slug, today)
    src = src_dir / "members.csv"
    if src.exists():
        dest = out_dir / f"snapshot_members_{today.isoformat()}.csv"
        shutil.copy2(src, dest)
        # small md summary
        md = out_dir / f"snapshot_{today.isoformat()}.md"
        md.write_text(f"# Snapshot — {args.slug} — {today.isoformat()}\n\nMembers snapshot CSV attached.\n", encoding="utf-8")
        print(f"Wrote snapshot files: {dest} and {md}")
    else:
        print("No members.csv in datalake for today; skipping snapshot report")

if __name__ == '__main__':
    main()
