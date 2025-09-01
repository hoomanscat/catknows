# SkoolHUD & Community Insights — Starter Kit

Dieses Repository enthält die Basis für automatisierte Community‑Analysen (SkoolHUD), inkl. Multi‑Tenant‑Support, Daily‑Reporting und Discord‑Integrationen.

---

##  Übersicht

- **Datenfluss**: Skool-Daten abrufen → normalisieren → in SQLite speichern.
- **Agents** generieren tägliche Reports: KPIs, Health Scores, Leaderboard‑Deltas, Member‑Snapshots.
- **Alembic** verwaltet das Datenbankschema.
- **CI** (GitHub Actions) führt tägliche Runs durch, generiert Reports, lädt Artefakte hoch und verschickt Discord‑Benachrichtigungen.
- **Multi‑Tenant**: Jede Community hat eigene Tenant‑Slug, Daten & Reports.

---

##  Installation & Setup (Dev)

```bash
git clone https://github.com/hoomanscat/catknows.git
cd catknows

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

---

##  Datenbank initialisieren & Migration

```bash
python -m skoolhud.cli init-db
alembic upgrade head
```

Falls `skool.db` oder Schema sich ändert, migriere neu:

```bash
alembic revision --autogenerate -m "desc"
alembic upgrade head
```

---

##  Tenant registrieren

```bash
python -m skoolhud.cli add-tenant   --slug hoomans   --group your-group-path   --cookie "HIER_DEN_COOKIE_EINFÜGEN"
```

Zum Testen:

```bash
python -m skoolhud.cli test-tenant --slug hoomans
```

---

##  Agenten lokal ausführen

```bash
python skoolhud/ai/agents/run_all_agents.py --slug hoomans
```

Reports landen in: `exports/reports/hoomans/`

Datenbank‑Snapshot via:

```bash
python verify_system.py --slug hoomans
```

---

##  GitHub Actions & Discord‑Integration

- Täglicher Run: CI agiert über `daily.yml`
- Discord-Embeds für Status, KPI, Health, Movers & New Joiners
- Artefakte im CI-Tab verfügbar (Reports pro Tenant)

Channel-Konfiguration:
- DISCORD_WEBHOOK_STATUS
- DISCORD_WEBHOOK_KPI
- DISCORD_WEBHOOK_MOVERS
- DISCORD_WEBHOOK_HEALTH
- DISCORD_WEBHOOK_NEWJOINERS

---

##  Projektstruktur

```
catknows/
├── alembic/
├── exports/
│   └── reports/{slug}/
├── skoolhud/
│   ├── ai/agents/
│   └── models.py
├── daily_runner.py
├── verify_system.py
├── README.md
├── DEV_CHECKLIST.md
└── ...
```

---

##  Unterstützung & Debugging

- Fehlermeldungen einfach hier reinkopieren → ich sag dir Schritt-für-Schritt, was zu tun ist.
- Clean-Up:
  - `.gitignore` hält `skool.db`, `exports/`, `data_lake/` aus dem Repo
  - alembic-Versionen im Repo für Schema-Konsistenz

**Let’s get that data flowing!**
