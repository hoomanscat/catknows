from skoolhud.db import engine
from skoolhud.models import Base, MemberDailySnapshot
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS member_daily_snapshot"))
    print("Dropped table: member_daily_snapshot")

Base.metadata.create_all(bind=engine, tables=[MemberDailySnapshot.__table__])
print("Recreated table: member_daily_snapshot")
