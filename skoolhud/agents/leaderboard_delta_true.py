# REPLACE FILE: copied from ai/agents
import argparse
from skoolhud.db import SessionLocal
from skoolhud.models import Member, LeaderboardSnapshot
from skoolhud.utils import reports_dir_for

WINDOWS = [("all","All-Time"), ("30","Past 30 Days"), ("7","Past 7 Days")]
_rank = lambda r: r if isinstance(r,int) else 10**9
_fmt  = lambda v: f"+{v}" if v>0 else str(v)

def _latest_two(s, slug, window):
    q=(s.query(LeaderboardSnapshot.captured_at)
        .filter(LeaderboardSnapshot.tenant==slug)
        .filter(LeaderboardSnapshot.window==window)
        .order_by(LeaderboardSnapshot.captured_at.desc()))
    seen=[]; last=None
    for (ts,) in q:
        if last is None or ts!=last: seen.append(ts); last=ts
        if len(seen)==2: break
    return (seen[0], seen[1]) if seen else (None, None)

def _snap_map(s, slug, window, ts):
    if not ts: return {}
    rows=(s.query(LeaderboardSnapshot.user_id, LeaderboardSnapshot.points, LeaderboardSnapshot.rank)
           .filter(LeaderboardSnapshot.tenant==slug)
           .filter(LeaderboardSnapshot.window==window)
           .filter(LeaderboardSnapshot.captured_at==ts).all())
    return {u:(p or 0, r) for u,p,r in rows}

def _names(s, ids):
    if not ids: return {}
    rows=s.query(Member.user_id, Member.name).filter(Member.user_id.in_(list(ids))).all()
    return {u:(n or f"user:{u}") for u,n in rows}

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--slug", default=None)
    args=ap.parse_args()
    from skoolhud.config import get_tenant_slug
    args.slug = get_tenant_slug(args.slug)

    out_dir = reports_dir_for(args.slug)
    s=SessionLocal()
    try:
        combined=[f"# Leaderboard Deltas (true history) — {args.slug}\n"]
        for key,label in WINDOWS:
            latest, prev = _latest_two(s, args.slug, key)
            if not latest or not prev:
                combined.append(f"## {label}\n(zu wenig Snapshots)\n"); continue
            cur=_snap_map(s,args.slug,key,latest)
            old=_snap_map(s,args.slug,key,prev)
            users=set(cur)|set(old); names=_names(s, users)
            up,down,new_in,dropped=[],[],[],[]
            for uid in users:
                nm=names.get(uid, f"user:{uid}")
                if uid in cur and uid not in old:  new_in.append((nm, *cur[uid]));  continue
                if uid in old and uid not in cur:  dropped.append((nm, *old[uid])); continue
                p_new,r_new=cur.get(uid,(0,None))
                p_old,r_old=old.get(uid,(0,None))
                dr=_rank(r_old)-_rank(r_new); dp=(p_new or 0)-(p_old or 0)
                (up if (dr>0 or dp>0) else down if (dr<0 or dp<0) else up).append((nm,dr,dp,r_old,r_new,p_old,p_new))
            up=sorted(up,key=lambda t:(t[1],t[2]),reverse=True)[:20]
            down=sorted(down,key=lambda t:(t[1],t[2]))[:20]

            lines=[f"# {label} — Δ (latest {latest} vs prev {prev})\n","## Up-Movers"]
            lines += ["- (keine)"] if not up else [f"- {n} — rank {ro}→{rn} ({_fmt(dr)}) | pts {po}→{pn} ({_fmt(dp)})" for n,dr,dp,ro,rn,po,pn in up]
            lines += ["", "## Down-Movers"]
            lines += ["- (keine)"] if not down else [f"- {n} — rank {ro}→{rn} ({_fmt(dr)}) | pts {po}→{pn} ({_fmt(dp)})" for n,dr,dp,ro,rn,po,pn in down]
            lines += ["", "## Neueinsteiger"]
            lines += ["- (keine)"] if not new_in else [f"- {n} — rank {r} | pts {p}" for n,p,r in new_in]
            lines += ["", "## Dropouts"]
            lines += ["- (keine)"] if not dropped else [f"- {n} — rank {r} | pts {p}" for n,p,r in dropped]
            (out_dir / f"leaderboard_delta_true_{key}.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
            combined.append("\n".join(lines)+"\n")
        (out_dir / "leaderboard_delta_true.md").write_text("\n".join(combined), encoding="utf-8")
        print("OK: leaderboard_delta_true")
    finally:
        s.close()

if __name__=="__main__":
    main()
