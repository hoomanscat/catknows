from skoolhud.db import engine
from sqlalchemy import text

with engine.begin() as conn:
    print("== PRAGMA table_info(member_daily_snapshot)")
    for row in conn.execute(text("PRAGMA table_info(member_daily_snapshot)")):
        print(row)
    print("\n== CREATE SQL")
    row = conn.execute(text(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='member_daily_snapshot'"
    )).fetchone()
    print(row[0] if row else "(not found)")
