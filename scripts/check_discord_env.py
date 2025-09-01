# scripts/check_discord_env.py
from pathlib import Path
import os, textwrap, json
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def mask(s: str) -> str:
    if not s: return "<empty>"
    return (s[:6] + "..." + s[-6:]) if len(s) > 14 else "*" * len(s)

bot = (os.getenv("DISCORD_BOT_TOKEN") or "").strip()
webhook_any = (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()

print("DISCORD_BOT_TOKEN.len:", len(bot), " sample:", mask(bot))
print("DISCORD_BOT_TOKEN.has_2_dots:", bot.count(".") >= 2)
print("DISCORD_BOT_TOKEN_looks_like_webhook:", bot.startswith("https://discord.com/api/webhooks"))
print("DISCORD_WEBHOOK_URL.set:", bool(webhook_any), " sample:", mask(webhook_any))

if not bot:
    raise SystemExit("❌ Kein Bot-Token gefunden.")
if bot.startswith("https://discord.com/api/webhooks"):
    raise SystemExit("❌ Du hast einen WEBHOOK anstelle eines BOT TOKENS hinterlegt.")

# Minimal-API-Check: Wer bin ich?
headers = {"Authorization": f"Bot {bot}"}
r = requests.get("https://discord.com/api/v10/users/@me", headers=headers, timeout=15)

print("GET /users/@me ->", r.status_code)
if r.status_code == 200:
    data = r.json()
    print("OK. Logged in as:", f"{data.get('username')}#{data.get('discriminator')}", "id:", data.get("id"))
else:
    print("Body:", textwrap.shorten(r.text, width=200))
    raise SystemExit("❌ Discord-Login fehlgeschlagen. Token prüfen / neu generieren.")
