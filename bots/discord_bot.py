# bots/discord_bot.py
import os
import re
import asyncio
import discord
from discord.ext import commands

from skoolhud.vector.db import get_client, get_or_create_collection, similarity_search

INTENTS = discord.Intents.default()
INTENTS.message_content = True

BOT_PREFIX = os.getenv("DISCORD_BOT_PREFIX", "!")
TENANT_DEFAULT = os.getenv("DISCORD_DEFAULT_TENANT", "hoomans")

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=INTENTS)

from typing import Any, Dict, List, Optional

from typing import Any, Dict, List, Optional

def _search(query: str, tenant: Optional[str], top_k: int = 5) -> List[Dict[str, Any]]:
    client = get_client()
    col = get_or_create_collection(client, "skool_members")

    # Bail out early if the collection is empty
    if (getattr(col, "count", lambda: 0)() or 0) == 0:
        return []

    where = {"tenant": tenant} if tenant else {}

    # Run similarity search safely
    try:
        res = similarity_search(col, query, n_results=top_k, where=where) or {}
    except Exception as e:
        # TODO: replace with proper logging
        print(f"similarity_search failed: {e}")
        return []

    def _first_list(key: str) -> List[Any]:
        """
        Chroma returns dict-of-lists per query:
        {"ids": [[...]], "documents": [[...]], "metadatas": [[...]]}
        This unwraps the first list or returns [].
        """
        v = res.get(key)
        if isinstance(v, list) and v and isinstance(v[0], list):
            return v[0]
        return []

    ids   = _first_list("ids")
    docs  = _first_list("documents")
    metas = _first_list("metadatas")

    out: List[Dict[str, Any]] = []
    for i, (doc, meta) in enumerate(zip(docs, metas)):
        out.append({
            "id": ids[i] if i < len(ids) else None,
            "document": doc,
            "metadata": meta,
        })
    return out

@bot.event
async def on_ready():
    print(f"✅ Discord bot logged in as {bot.user} (prefix: {BOT_PREFIX})")

@bot.command(name="who")
async def who_knows(ctx, *args):
    """
    Beispiel:
    !who knows AI?
    !who knows funnel builder in berlin?
    """
    q = " ".join(args).strip()
    if q.lower().startswith("knows "):
        q = q[6:].strip()

    if not q:
        await ctx.reply("Bitte nutze: `!who knows <Thema>?`")
        return

    results = _search(q, TENANT_DEFAULT, top_k=5)
    if not results:
        await ctx.reply("Keine Treffer 😿")
        return

    lines = [f"**Top Matches für:** `{q}`"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['name']}** — points_all={r['points_all']} — `{r['user_id']}`")
        lines.append(f"    {r['snippet']}")
    await ctx.reply("\n".join(lines))

if __name__ == "__main__":
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Fehlt: DISCORD_BOT_TOKEN")
    bot.run(token)
