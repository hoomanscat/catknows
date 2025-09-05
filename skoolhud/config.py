
"""
Konfigurationsmodul für skoolhud.
Lädt Einstellungen aus Umgebungsvariablen und stellt sie als Settings-Objekt bereit.
"""
from pydantic import BaseModel
import os

class Settings(BaseModel):
    """
    Settings-Objekt, das alle relevanten Konfigurationswerte aus Umgebungsvariablen lädt.
    """
    base_url: str = os.environ.get("SKOOL_BASE", "https://www.skool.com")
    user_agent: str = os.environ.get("SKOOL_UA", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SkoolHUD/0.1")
    raw_dir: str = os.environ.get("RAW_DIR", "exports/raw")
    db_path: str = os.environ.get("DB_PATH", "skool.db")
    min_interval_seconds: int = int(os.environ.get("MIN_INTERVAL_SECONDS", "15"))

# Instanz der Settings, wird von anderen Modulen importiert
settings = Settings()

def get_tenant_slug(provided: str | None = None) -> str:
    """Resolve tenant slug from provided value, env, tenants.json, or fallback.

    Order of precedence:
    1. provided (non-empty)
    2. environment variable TENANT_SLUG
    3. tenants.json first entry
    4. fallback to 'hoomans'
    """
    if provided:
        return provided
    env = os.environ.get("TENANT_SLUG")
    if env:
        return env
    # try tenants.json
    try:
        import json
        from pathlib import Path
        p = Path("tenants.json")
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and data[0].get("slug"):
                return data[0]["slug"]
    except Exception:
        pass
    return "hoomans"
