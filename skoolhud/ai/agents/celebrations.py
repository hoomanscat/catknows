import argparse
from datetime import date
from skoolhud.db import SessionLocal
from skoolhud.models import Member
from skoolhud.utils import reports_dir_for

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="hoomans")
    args = ap.parse_args()

    out_dir = reports_dir_for(args.slug)
    s = SessionLocal()
    try:
        # simple celebrations: top 5 by 7d points and up to 5 most recent members (joined_date exists)
        movers = s.query(Member.name, Member.points_7d).filter(Member.points_7d!=None).order_by(Member.points_7d.desc()).limit(5).all()
        recent = []
        try:
            recent = s.query(Member.name).filter(Member.joined_date!=None).order_by(Member.joined_date.desc()).limit(5).all()
        except Exception:
            recent = []

        lines = [f"# 🎉 Celebrations — {args.slug}", "", "## Top Movers (7d)"]
        for n,p in movers:
            lines.append(f"- {n} — {p or 0} pts")

        lines.append("")
        lines.append("## New Joiners")
        if recent:
            for (n,) in recent:
                lines.append(f"- {n}")
        else:
            lines.append("- (keine)")

        fn = out_dir / f"celebrations_{date.today().isoformat()}.md"
        fn.write_text("\n".join(lines)+"\n", encoding="utf-8")
        print(f"Wrote celebrations: {fn}")
    finally:
        s.close()

if __name__ == '__main__':
    main()
