from pathlib import Path
import argparse
from skoolhud.db import SessionLocal
from skoolhud.models import Member
from skoolhud.utils import reports_dir_for


def top_movers(session, window: str, topn: int = 15):
    # window in {"7d","30d","all"}
    if window == "7d":
        q = session.query(Member.name, Member.points_7d).filter(Member.points_7d != None)
        order_key = lambda row: row[1]
    elif window == "30d":
        q = session.query(Member.name, Member.points_30d).filter(Member.points_30d != None)
        order_key = lambda row: row[1]
    else:
        q = session.query(Member.name, Member.points_all).filter(Member.points_all != None)
        order_key = lambda row: row[1]

    rows = q.all()
    rows = sorted(rows, key=order_key, reverse=True)[:topn]
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="hoomans")
    args = ap.parse_args()

    out_dir = reports_dir_for(args.slug)
    s = SessionLocal()
    try:
        movers7 = top_movers(s, "7d")
        movers30 = top_movers(s, "30d")
        moversAll = top_movers(s, "all")

        lines = []
        lines.append("# Leaderboard Movers (Heuristic)")
        lines.append("")
        lines.append("## Top 15  past 7 days")
        for i,(n,p) in enumerate(movers7, start=1):
            lines.append(f"{i:>2}. {n}  {p or 0} pts")
        lines.append("")
        lines.append("## Top 15  past 30 days")
        for i,(n,p) in enumerate(movers30, start=1):
            lines.append(f"{i:>2}. {n}  {p or 0} pts")
        lines.append("")
        lines.append("## Top 15  all time")
        for i,(n,p) in enumerate(moversAll, start=1):
            lines.append(f"{i:>2}. {n}  {p or 0} pts")

        out = out_dir / "leaderboard_movers.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"geschrieben: {out}")
    finally:
        s.close()

if __name__ == "__main__":
    main()
