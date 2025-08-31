from pydantic import BaseModel
import os

class Settings(BaseModel):
    base_url: str = os.environ.get("SKOOL_BASE", "https://www.skool.com")
    user_agent: str = os.environ.get("SKOOL_UA", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SkoolHUD/0.1")
    raw_dir: str = os.environ.get("RAW_DIR", "exports/raw")
    db_path: str = os.environ.get("DB_PATH", "skool.db")
    min_interval_seconds: int = int(os.environ.get("MIN_INTERVAL_SECONDS", "15"))

settings = Settings()
