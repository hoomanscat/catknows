from pathlib import Path
from datetime import datetime, date, timezone
import csv
import re

from skoolhud.db import SessionLocal
from skoolhud.models import MemberDailySnapshot

BASE = Path("data_lake/members")

def _to_date_from_partition(part_dir: Path) -> date:
    # erwartet Ordner wie dt=2025-09-01
    m = re.match(r"dt=(\d{4}-\d{2}-\d{2})$", part_dir.name)
    if not m:
        return None
    y, mo, d = map(int, m.group(1).split("-"))
    return date(y, mo, d)

def _to_int(x):
    try:
        return int(x)
    except Exception:
        return None

def _to_dt(x):
    if not x:
        return None
    s = str(x).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def upsert_row(s, tenant, user_id, day, values):
    now = datetime.now(timezone.utc)
    row = (
        s.query(MemberDailySnapshot)
         .filter(MemberDailySnapshot.tenant == tenant)
         .filter(MemberDailySnapshot.user_id == user_id)
         .filter(MemberDailySnapshot.day == day)
         .one_or_none()
    )
    values = dict(values)
    values.update({"tenant": tenant, "user_id": user_id, "day": day, "captured_at": now})
    if row is None:
        row = MemberDailySnapshot(**values)
        s.add(row)
        return "insert"
    else:
        for k, v in values.items():
            setattr(row, k, v)
        return "update"

def main():
    parts = sorted([p for p in BASE.glob("dt=*") if p.is_dir()])
    if not parts:
        print("Keine Data-Lake-Partitionen gefunden unter", BASE)
        return

    s = SessionLocal()
    ins = upd = 0
    try:
        for part in parts:
            day = _to_date_from_partition(part)
            if not day:
                print("Überspringe unbekannte Partition:", part)
                continue
            csv_path = part / "members.csv"
            if not csv_path.exists():
                print("Keine CSV in", part)
                continue

            with csv_path.open("r", encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    tenant = (row.get("tenant") or "hoomans").strip()
                    user_id = (row.get("user_id") or "").strip()
                    if not user_id:
                        continue

                    vals = {
                        "level_current": _to_int(row.get("level_current")),
                        "points_7d": _to_int(row.get("points_7d")),
                        "points_30d": _to_int(row.get("points_30d")),
                        "points_all": _to_int(row.get("points_all")),
                        "rank_7d": _to_int(row.get("rank_7d")),
                        "rank_30d": _to_int(row.get("rank_30d")),
                        "rank_all": _to_int(row.get("rank_all")),
                        "last_active_at_utc": _to_dt(row.get("last_active_at_utc")),
                    }
                    res = upsert_row(s, tenant, user_id, day, vals)
                    if res == "insert": ins += 1
                    else: upd += 1
            s.commit()
            print(f"{part.name}: commit ok")
    finally:
        s.close()

    print(f"FERTIG — inserted={ins} updated={upd}")

if __name__ == "__main__":
    main()
