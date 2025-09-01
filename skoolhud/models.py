from sqlalchemy import Column, Integer, String, DateTime, JSON, UniqueConstraint, Text
from sqlalchemy.sql import func
from .db import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    group_path = Column(String, nullable=False)
    cookie_header = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True)
    tenant = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=True)
    member_id = Column(String, index=True, nullable=True)
    handle = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    name = Column(String, nullable=True)
    email = Column(String, index=True, nullable=True)
    joined_date = Column(String, nullable=True)
    approved_at = Column(String, nullable=True)
    role = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    link_website = Column(String, nullable=True)
    link_instagram = Column(String, nullable=True)
    link_linkedin = Column(String, nullable=True)
    link_facebook = Column(String, nullable=True)
    link_youtube = Column(String, nullable=True)
    last_active_raw = Column(String, nullable=True)
    last_active_at_utc = Column(String, nullable=True)
    updated_at_raw = Column(String, nullable=True)
    level_current = Column(Integer, nullable=True)
    source_last_update = Column(String, nullable=True)
    source_build_id = Column(String, nullable=True)

    # Leaderboard Felder (immer aktuellster Stand)
    points_7d = Column(Integer, nullable=True)
    rank_7d = Column(Integer, nullable=True)
    points_30d = Column(Integer, nullable=True)
    rank_30d = Column(Integer, nullable=True)
    points_all = Column(Integer, nullable=True)
    rank_all = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant", "user_id", name="uq_member_tenant_userid"),
    )


class RawSnapshot(Base):
    __tablename__ = "raw_snapshots"
    id = Column(Integer, primary_key=True)
    tenant = Column(String, index=True, nullable=False)
    route = Column(String, nullable=False)
    build_id = Column(String, nullable=True)
    captured_at = Column(DateTime(timezone=True), server_default=func.now())
    path = Column(String, nullable=False)
    meta = Column(JSON, nullable=True)


class LeaderboardSnapshot(Base):
    __tablename__ = "leaderboard_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    tenant = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    window = Column(String, index=True, nullable=False)  # "7", "30", "all"
    points = Column(Integer, nullable=True)
    rank = Column(Integer, nullable=True)
    captured_at = Column(DateTime(timezone=True), server_default=func.now())
    source_file = Column(String, nullable=True)
    build_id = Column(String, nullable=True)

# PATCH: skoolhud/models.py  (MemberDailySnapshot ersetzen)
from sqlalchemy import Column, Integer, String, Date, DateTime, Index, UniqueConstraint

class MemberDailySnapshot(Base):
    __tablename__ = "member_daily_snapshot"

    # WICHTIG für SQLite: INTEGER primary_key + autoincrement
    id = Column(Integer, primary_key=True, autoincrement=True)

    tenant = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=False)
    day = Column(Date, nullable=False)

    level_current = Column(Integer)
    points_7d = Column(Integer)
    points_30d = Column(Integer)
    points_all = Column(Integer)

    rank_7d = Column(Integer)
    rank_30d = Column(Integer)
    rank_all = Column(Integer)

    last_active_at_utc = Column(DateTime)
    captured_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant", "user_id", "day", name="uq_member_daily"),
        Index("ix_mds_tenant_day", "tenant", "day"),
        Index("ix_mds_tenant_user_day", "tenant", "user_id", "day"),
    )

