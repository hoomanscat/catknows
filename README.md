# SkoolHUD – Community Intelligence Hub

SkoolHUD ist ein Data-Pipeline- und Dashboard-System für Skool-Communities.  
Es automatisiert das Sammeln, Normalisieren, Analysieren und Reporten von Community-Daten – mit Discord-Integration und Vector-Search.

---

## Features

- **Fetcher & Normalizer**  
  - Holt Member- und Leaderboard-Daten über Skool-Web (Next.js JSON)  
  - Normalisiert in SQLite-DB (`skool.db`)  
  - Multi-Tenant-ready (`tenants.json`)

- **Snapshots & Reports**  
  - `MemberDailySnapshot` (Autoincrement-Fix, SQLite kompatibel)  
  - Leaderboard-Snapshots (7d, 30d, all)  
  - Health-/KPI-/Movers-/NewJoiner-Reports → Discord-Webhook

- **Agents (AI/Analysis)**  
  - Health Score, KPI-Report, Movers, New Joiners  
  - Alle Agenten in `skoolhud/ai/agents`  
  - Orchestriert durch `run_all_agents.py`

- **Discord Integration**  
  - GitHub Actions → Postet Status in Kanäle (Status, Alerts, KPIs, Movers, Health, NewJoiners)  
  - Optional: Discord Bot (`skoolhud/discord/bot.py`) für Queries wie `!who-knows AI?`

- **Vector Store (ChromaDB)**  
  - Persistenter Storage (`./vector_store`)  
  - `skool_members` Collection  
  - Automatischer Ingest beim Daily Run → Mitgliederprofile als Embeddings

- **Automation**  
  - `daily_runner.py` orchestriert alles:  
    1. `update_all.py` (fetch/normalize)  
    2. `snapshot-members-daily`  
    3. `run_all_agents.py`  
    4. Vector-Ingest

---

## Setup

### 1. Environment
`.env` im Projekt-Root:

```env
# Skool Cookie (nur lokal)
SKOOL_COOKIE=...

# Discord Webhooks
DISCORD_WEBHOOK_STATUS=...
DISCORD_WEBHOOK_ALERTS=...
DISCORD_WEBHOOK_KPIS=...
DISCORD_WEBHOOK_MOVERS=...
DISCORD_WEBHOOK_HEALTH=...
DISCORD_WEBHOOK_NEWJOINERS=...

# Discord Bot Token (für Bot-Integration)
DISCORD_BOT_TOKEN=...
```

### 2. Lokale DB
```bash
alembic upgrade head
```

### 3. Run Local
```bash
python daily_runner.py
```

### 4. Run GitHub Action
- `.github/workflows/daily.yml` (automatisch täglich)
- `.github/workflows/notify_test.yml` (manuell)

---

## Troubleshooting

- **SQLite `ALTER`**: Alembic erzeugt No-Op-Migration (safe).  
- **Windows Encoding**: `✅` → ersetzt durch `OK` falls Probleme.  
- **Discord Bot Token**: Token ≠ Webhook. Token muss 3 Teile (`xxx.yyy.zzz`) haben.  
- **Vector Store**: `chromadb` installieren (`pip install chromadb>=0.5.5`).

---

## Roadmap

- ✅ Datenpipeline (fetch/normalize/snapshot/agents)  
- ✅ Discord-Notify GitHub Actions  
- ✅ Vector Store init + ingest  
- 🚧 Embeddings (sentence-transformers oder OpenAI)  
- 🚧 Discord Bot Q&A (`!who-knows <topic>`)  
- 🚧 Multi-Tenant Runner (alle Communities)  
- 🚧 Dashboard (Streamlit/FastAPI)

---
