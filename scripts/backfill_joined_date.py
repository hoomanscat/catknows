"""Backfill script: normalize Member.joined_date into a new column `joined_at_utc`.

Usage:
    python scripts/backfill_joined_date.py [--dry-run]

This will:
 - add a TEXT column `joined_at_utc` to the `members` table if it doesn't exist
 - parse existing `joined_date` strings and write an ISO-8601 UTC string into `joined_at_utc`

This is a safe, idempotent helper for local dev. For production DB schema changes, create an Alembic
revision and run `alembic upgrade head` instead.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from skoolhud.db import engine
from skoolhud.utils import to_utc_str

def column_exists(conn, table: str, column: str) -> bool:
    cur = conn.exec_driver_sql(f"PRAGMA table_info('{table}')")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    args = ap.parse_args()

    tbl = "members"
    col = "joined_at_utc"

    with engine.begin() as conn:
        has_col = column_exists(conn, tbl, col)
        if not has_col:
            if args.dry_run:
                print(f"DRY RUN: would add column {col} to {tbl}")
            else:
                print(f"Adding column {col} to {tbl}...")
                conn.exec_driver_sql(f"ALTER TABLE {tbl} ADD COLUMN {col} TEXT")
                has_col = True
        else:
            print(f"Column {col} already exists in {tbl}")

        # Read all rows and parse
        if has_col:
            res = conn.exec_driver_sql(f"SELECT id, joined_date, {col} FROM {tbl}")
        else:
            # column absent -> only select id and joined_date; treat existing as None
            res = conn.exec_driver_sql(f"SELECT id, joined_date FROM {tbl}")
        rows = res.fetchall()
        total = len(rows)
        parsed = 0
        skipped = 0
        updated = 0

        for r in rows:
            _id = r[0]
            joined_raw = r[1]
            existing = r[2] if has_col and len(r) > 2 else None
            if existing:
                skipped += 1
                continue
            if not joined_raw:
                skipped += 1
                continue
            norm = to_utc_str(joined_raw)
            if not norm:
                skipped += 1
                continue
            parsed += 1
            if args.dry_run:
                print(f"DRY: would UPDATE {tbl} set {col}='{norm}' WHERE id={_id}")
            else:
                conn.exec_driver_sql(f"UPDATE {tbl} SET {col} = :v WHERE id = :id", {"v": norm, "id": _id})
                updated += 1

        print("Backfill complete:")
        print(f"  total rows: {total}")
        print(f"  parsed (to write): {parsed}")
        print(f"  updated: {updated}")
        print(f"  skipped (already present or empty/unparsable): {skipped}")

if __name__ == '__main__':
    main()
