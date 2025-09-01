
"""
Initialisiert die Datenbankverbindung und stellt die SQLAlchemy-Basisobjekte bereit.
Verwendet SQLite als Backend, Pfad wird aus den Settings geladen.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# Engine und Session für die Datenbank
engine = create_engine(f"sqlite:///{settings.db_path}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()
