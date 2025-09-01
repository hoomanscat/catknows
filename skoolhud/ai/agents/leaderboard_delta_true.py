# REPLACE FILE: skoolhud/ai/agents/leaderboard_delta_true.py
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

from skoolhud.db import SessionLocal
from skoolhud.models import Member, LeaderboardSnapshot

OUT_DIR = Path("exports/reports")
WINDOWS = [("all", "All-Time"), ("30", "Past 30 Days"), ("7", "Past 7 Days")]

def _rank_int(r): return r if isinstance(r, int) else 10**9
def _fmt(v): return f"+{v}" if v > 0 else str(v)

def _latest_two(session, window: str):
    q = (session.query(LeaderboardSnapshot.captured_at)
         .filter(LeaderboardSnapshot.window == window)
         .order_by(LeaderboardSnapshot.captured_at.desc()))
    seen = []
    last = None
    for (ts,) in q:
        if last is None or ts != last:
            seen.append(ts)
            last = ts
        if len(seen) == 2:
            break
    return (seen[0], seen[1]) if seen else (None, None)

def _snap_map(session, window: str, ts):
    if not ts: return {}
    rows = (session.query(LeaderboardSnapshot.user_id, LeaderboardSnapshot.points, LeaderboardSnapshot.rank)
            .filter(LeaderboardSnapshot.window == window)
            .filter(LeaderboardSnapshot.captured_at == ts).all())
    return {uid: (pts or 0, rk) for uid, pts, rk in rows}

def _name_map(session, ids):
    if not ids: return {}
    rows = session.query(Member.user_id, Member.name).filter(Member.user_id.in_(list(ids))).all()
    return {u: (n or f"user:{u}") for u, n in rows}

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    s = SessionLocal()
    try:
        combined = ["# Leaderboard Deltas (true history)\n"]
        for key, label in WINDOWS:
            latest, prev = _latest_two(s, key)
            if not latest or not prev:
                combined.append(f"## {label}\n(zu wenig Snapshots)\n")
                continue

            cur = _snap_map(s, key, latest)
            old = _snap_map(s, key, prev)
            users = set(cur) | set(old)
            names = _name_map(s, users)

            up, down, new_in, dropped = [], [], [], []
            for uid in users:
                nm = names.get(uid, f"user:{uid}")
                if uid in cur and uid not in old:
                    p, r = cur[uid]
                    new_in.append((nm, p, r)); continue
                if uid in old and uid not in cur:
                    p, r = old[uid]
                    dropped.append((nm, p, r)); continue

                p_new, r_new = cur.get(uid, (0, None))
                p_old, r_old = old.get(uid, (0, None))
                dr = _rank_int(r_old) - _rank_int(r_new)
                dp = (p_new or 0) - (p_old or 0)
                if dr > 0 or dp > 0: up.append((nm, dr, dp, r_old, r_new, p_old, p_new))
                elif dr < 0 or dp < 0: down.append((nm, dr, dp, r_old, r_new, p_old, p_new))

            up = sorted(up, key=lambda t: (t[1], t[2]), reverse=True)[:20]
            down = sorted(down, key=lambda t: (t[1], t[2]))[:20]

            lines = []
            lines.append(f"# {label} — Δ (latest {latest} vs prev {prev})\n")
            lines.append("## Up-Movers")
            lines += ["- (keine)"] if not up else [
                f"- {n} — rank {ro}→{rn} ({_fmt(dr)}) | pts {po}→{pn} ({_fmt(dp)})"
                for n, dr, dp, ro, rn, po, pn in up
            ]
            lines.append("\n## Down-Movers")
            lines += ["- (keine)"] if not down else [
                f"- {n} — rank {ro}→{rn} ({_fmt(dr)}) | pts {po}→{pn} ({_fmt(dp)})"
                for n, dr, dp, ro, rn, po, pn in down
            ]
            lines.append("\n## Neueinsteiger")
            lines += ["- (keine)"] if not new_in else [
                f"- {n} — rank {r} | pts {p}" for n, p, r in new_in
            ]
            lines.append("\n## Dropouts")
            lines += ["- (keine)"] if not dropped else [
                f"- {n} — rank {r} | pts {p}" for n, p, r in dropped
            ]

            (OUT_DIR / f"leaderboard_delta_true_{key}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
            combined.append("\n".join(lines) + "\n")

        (OUT_DIR / "leaderboard_delta_true.md").write_text("\n".join(combined), encoding="utf-8")
        print("OK: leaderboard_delta_true")
    finally:
        s.close()

if __name__ == "__main__":
    main()
