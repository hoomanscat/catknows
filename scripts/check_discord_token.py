from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
tok = (os.getenv("DISCORD_BOT_TOKEN") or "").strip()

def mask(t: str) -> str:
    if not t:
        return "<empty>"
    if len(t) <= 10:
        return "*" * len(t)
    return t[:6] + "..." + t[-6:]

print("len:", len(tok), " sample:", mask(tok))
print("looks_like_webhook:", tok.startswith("https://discord.com/api/webhooks"))
print("dot_parts:", tok.count("."))