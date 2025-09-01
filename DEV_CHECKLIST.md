# Dev Checklist – SkoolHUD

## ✅ Core Setup
- [x] Repo-Struktur clean (`skoolhud/`, `exports/`, `.github/`)  
- [x] `.env` mit SKOOL_COOKIE + Discord Webhooks  
- [x] Alembic DB-Init (`alembic upgrade head`)  
- [x] `daily_runner.py` orchestriert Pipelines

## 🛠️ Local Development
- [ ] `python update_all.py` → Fetch + Normalize  
- [ ] `skoolhud snapshot-members-daily hoomans`  
- [ ] `python skoolhud/ai/agents/run_all_agents.py`  
- [ ] `python skoolhud/vector/ingest.py` (falls Embeddings aktiv)  
- [ ] `python skoolhud/discord/bot.py` (für Bot-Integration)

## 📊 Exports & Reports
- [x] Raw JSON unter `exports/raw/<tenant>/`  
- [x] Normalized CSV unter `exports/normalized/`  
- [x] Reports unter `exports/reports/` (Health, KPI, Movers, etc.)  
- [x] Discord Notify → Channels

## 🚀 CI/CD
- [x] `.github/workflows/daily.yml` → Täglicher Run  
- [x] `.github/workflows/notify_test.yml` → Test Webhooks  
- [ ] Multi-Tenant Runner (serienweise)  
- [ ] Rate-Limit Safety (>=15s Delay zwischen API Calls)

## 🧩 Vector Store
- [x] `chromadb` Integration (`vector_store/`)  
- [x] Collection `skool_members`  
- [ ] Automatischer Ingest beim Daily Run  
- [ ] Embeddings statt Rohtext (`sentence-transformers`)

## 🤖 Discord Bot
- [ ] `DISCORD_BOT_TOKEN` im `.env`  
- [ ] Bot mit OAuth2 Link zum Server hinzufügen  
- [ ] Slash-Commands (`!who-knows <topic>`)  
- [ ] Query → Vector Store → Antwort mit Member-Infos

## 🔮 Roadmap
- Embeddings einbinden (lokal: `sentence-transformers`, remote: OpenAI)  
- Bot Q&A für Knowledge Discovery  
- Multi-Tenant Runner (`tenants.json`)  
- Dashboard (Streamlit/FastAPI) für KPIs & Health  
