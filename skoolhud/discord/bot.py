import os
import logging
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("skoolbot")

# .env laden (immer vom Projektroot)
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

def get_token() -> str:
    tok = (os.getenv("DISCORD_BOT_TOKEN") or "").strip()
    if tok.lower().startswith("bot "):
        tok = tok[4:].strip()
    if tok.startswith("https://discord.com/api/webhooks"):
        raise SystemExit("❌ WEBHOOK in DISCORD_BOT_TOKEN gefunden – bitte echten Bot-Token eintragen.")
    if tok.count(".") < 2 or len(tok) < 50:
        raise SystemExit("❌ DISCORD_BOT_TOKEN sieht ungültig aus. Im Dev Portal → Bot → Reset Token → Copy.")
    return tok

TOKEN = get_token()

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True  # im Dev-Portal aktivieren!

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    if bot.user is not None:
        log.info("Bot eingeloggt als %s (%s)", bot.user, bot.user.id)
    else:
        log.info("Bot eingeloggt, aber bot.user ist None")
    await bot.change_presence(activity=discord.Game(name="type !ping"))

@bot.command(name="ping")
async def ping(ctx: commands.Context):
    await ctx.reply("pong 🏓", mention_author=False)

@bot.command(name="who")
async def who(ctx: commands.Context, *, query: Optional[str] = None):
    if not query:
        await ctx.reply("Nutzung: `!who <Thema>` – ich suche dann in unserem Vector Store.", mention_author=False)
        return
    await ctx.reply(f"Du hast gefragt: **{query}**\n(Suche folgt 🔍)", mention_author=False)

@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CommandNotFound):
        return
    log.exception("Command error: %s", error)
    try:
        await ctx.reply(f"❌ Fehler: `{type(error).__name__}` – {error}", mention_author=False)
    except Exception:
        pass

def main():
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
