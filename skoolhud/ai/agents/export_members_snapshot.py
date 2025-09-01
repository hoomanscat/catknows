from datetime import datetime, timezone
from pathlib import Path
import csv

from skoolhud.db import SessionLocal
from skoolhud.models import Member

# Data-Lake Ordner (außerhalb von exports/reports)
BASE_DIR = Path("data_lake/members")

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def write_csv(path: Path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def try_write_parquet(path: Path, rows, fieldnames):
    try:
        import pandas as pd  # pyarrow optional
        df = pd.DataFrame(rows, columns=fieldnames)
        df.to_parquet(path, index=False)   # nutzt pyarrow/fastparquet, falls vorhanden
        return True
    except Exception:
        return False

def main():
    now = datetime.now(timezone.utc)
    dt = now.strftime("%Y-%m-%d")
    # Partition wie: data_lake/members/dt=2025-09-01/
    part_dir = BASE_DIR / f"dt={dt}"
    ensure_dir(part_dir)

    s = SessionLocal()
    rows = []
    try:
        for m in s.query(Member).all():
            rows.append({
                "tenant": getattr(m, "tenant", None),
                "user_id": m.user_id,
                "name": m.name or "",
                "email": m.email or "",
                "level_current": m.level_current or 0,
                "points_7d": m.points_7d or 0,
                "points_30d": m.points_30d or 0,
                "points_all": m.points_all or 0,
                "rank_7d": m.rank_7d,
                "rank_30d": m.rank_30d,
                "rank_all": m.rank_all,
                "joined_date": m.joined_date.isoformat() if getattr(m, "joined_date", None) else "",
                "last_active_at_utc": m.last_active_at_utc.isoformat() if m.last_active_at_utc else "",
                "captured_at_utc": now.isoformat(),
            })
    finally:
        s.close()

    fieldnames = list(rows[0].keys()) if rows else [
        "tenant","user_id","name","email","level_current",
        "points_7d","points_30d","points_all",
        "rank_7d","rank_30d","rank_all",
        "joined_date","last_active_at_utc","captured_at_utc"
    ]

    csv_path = part_dir / "members.csv"
    write_csv(csv_path, rows, fieldnames)

    # Optional Parquet (nur, wenn libs vorhanden)
    parquet_ok = try_write_parquet(part_dir / "members.parquet", rows, fieldnames)

    # ein kleines Manifest mit Metadaten
    (part_dir / "_SUCCESS").write_text("", encoding="utf-8")
    (part_dir / "manifest.txt").write_text(
        f"rows={len(rows)}\nparquet={parquet_ok}\ncreated_utc={now.isoformat()}\n",
        encoding="utf-8"
    )

    print(f"Snapshot geschrieben: {csv_path}  (rows={len(rows)}, parquet={parquet_ok})")

if __name__ == "__main__":
    main()
