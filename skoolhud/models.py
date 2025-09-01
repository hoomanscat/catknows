# skoolhud/models.py
from __future__ import annotations

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


# -----------------------------
# Tenant (SQLAlchemy 2.0 typing)
# -----------------------------
class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    group_path: Mapped[str] = mapped_column(String(255))
    cookie_header: Mapped[str] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"Tenant(slug={self.slug!r}, group_path={self.group_path!r})"


# ---------------------------------
# Member (klassischer Column-Stil)
# ---------------------------------
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

    # Achtung: Hier lassen wir bewusst STRING,
    # weil die Ingestion historisch Strings schreibt.
    last_active_raw = Column(String, nullable=True)
    last_active_at_utc = Column(String, nullable=True)
    updated_at_raw = Column(String, nullable=True)

    level_current = Column(Integer, nullable=True)
    source_last_update = Column(String, nullable=True)
    source_build_id = Column(String, nullable=True)

    # Leaderboard Felder (aktueller Stand)
    points_7d = Column(Integer, nullable=True)
    rank_7d = Column(Integer, nullable=True)
    points_30d = Column(Integer, nullable=True)
    rank_30d = Column(Integer, nullable=True)
    points_all = Column(Integer, nullable=True)
    rank_all = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant", "user_id", name="uq_member_tenant_userid"),
    )


# -------------------
# Raw JSON Snapshots
# -------------------
class RawSnapshot(Base):
    __tablename__ = "raw_snapshots"

    id = Column(Integer, primary_key=True)
    tenant = Column(String, index=True, nullable=False)
    route = Column(String, nullable=False)
    build_id = Column(String, nullable=True)
    captured_at = Column(DateTime(timezone=True), server_default=func.now())
    path = Column(String, nullable=False)
    meta = Column(JSON, nullable=True)


# ------------------------
# Leaderboard Snapshots
# ------------------------
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


# -----------------------------
# Member Daily Snapshot (DWH)
# -----------------------------
class MemberDailySnapshot(Base):
    __tablename__ = "member_daily_snapshot"

    # Wichtig: autoincrement, damit kein NOT NULL-Fehler bei id
    id = Column(Integer, primary_key=True, autoincrement=True)

    tenant = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    day = Column(Date, nullable=False)

    level_current = Column(Integer)
    points_7d = Column(Integer)
    points_30d = Column(Integer)
    points_all = Column(Integer)

    rank_7d = Column(Integer)
    rank_30d = Column(Integer)
    rank_all = Column(Integer)

    # Hier echte DATETIME (UTC) – Backfill-/Writer müssen datetime-Objekte liefern
    last_active_at_utc = Column(DateTime)

    captured_at = Column(DateTime, server_default=func.now(), nullable=False)
