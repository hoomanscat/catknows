from skoolhud.db import SessionLocal
from skoolhud.models import Member

def main():
    s = SessionLocal()
    try:
        rows = (
            s.query(Member.name, Member.points_all, Member.rank_all)
             .filter(Member.points_all != None)
             .order_by(Member.points_all.desc(), Member.rank_all.asc().nulls_last())
             .limit(5)
             .all()
        )
        for n, p, r in rows:
            rank = r if r is not None else "-"
            pts  = p if p is not None else 0
            print(f"{rank:>2} | {pts:>5} | {n}")
    finally:
        s.close()

if __name__ == "__main__":
    main()
