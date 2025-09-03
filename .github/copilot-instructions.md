## Advanced Project Conventions & Templates

- **Data-Contracts (JSON-Schemas):**
	- All reports and snapshots must follow a defined JSON schema (see `project-status/schemas/` for templates).
	- Example: `member_daily_snapshot.schema.json`, `kpi_report.schema.json`.

- **Run-ID & Status-Artefacts:**
	- Every pipeline run writes a unique run ID and status file to `exports/status/` (e.g. `last-run.txt`, `run-YYYYMMDD-HHMM.json`).

- **Rate-Limit/Retry-Wrapper:**
	- Use `skoolhud/utils/net.py` for all network calls. Centralizes rate-limiting, retries, and error handling.

- **Testing-Mindeststandard:**
	- Run smoke tests and fixtures before every push. See `TESTING.md` for details.
	- Use `verify_system.py` for basic health checks.

- **Bot-Spezifikation & Channel-Mapping:**
	- All bot commands and Discord channel mappings are documented in `BOT_COMMANDS.md`.
	- Webhook env variables must match channel names (see `.env` and `notify_reports_local.py`).

- **Security/PII-Leitplanken:**
	- Never log or export sensitive user data (PII) outside the system.
	- See `SECURITY.md` for rules and audit checklist.

- **Konfig & Feature-Flags:**
	- All config is in `config/app.yaml`. Use feature flags for experimental features.

- **CI-Polish:**
	- Use matrix builds, concurrency limits, and artifact retention in workflows. See `.github/workflows/ci.yml` for examples.

- **Tenants-Onboarding:**
	- All tenants are listed in `tenants.json` and described in `TENANTS.md`.
	- Onboarding steps and requirements are documented for each tenant.

- **Prompts & AI-Guardrails:**
	- All AI prompts and guardrails are versioned in `project-status/prompts/`.

- **Optionale Containerisierung:**
	- Dockerfile and container setup are available for easy deployment. See `Dockerfile` and `README.md`.

- **.env-Extras:**
	- Additional env variables: `RATE_LIMIT_MIN_DELAY`, `RETRY_MAX`, `RETENTION_DAYS`, `AI_MAX_COST_EUR` for fine-tuning system behavior.

---

Refer to the listed files for ready-to-use templates and further details. Always keep this section up to date as new conventions and templates are added.
# Step-by-Step Instructions & Live Roadmap for SkoolHUD

## Roles & Workflow
You are now the developer in charge of SkoolHUD/CatKnows. Follow these instructions step by step. The 'Master' (user) gives you tasks and information, you execute and report back. Always use simple language and PowerShell commands for every action.

## Handover & Checklist
Refer to `PROJECT_HANDOVER.md` and `DEV_CHECKLIST.md` for current status and next To-Dos. These files are your starting point for every new task.

## Step 1: Prepare Development Environment
- Ensure `.env` exists in the project root. If missing, create it:
	```powershell
	New-Item -ItemType File -Path .\.env
	notepad .\.env
	```
- Add all required secrets:
	- `SKOOL_COOKIE` (Skool login cookie)
	- Discord webhook URLs: `DISCORD_WEBHOOK_STATUS`, `DISCORD_WEBHOOK_ALERTS`, `DISCORD_WEBHOOK_KPIS`, `DISCORD_WEBHOOK_MOVERS`, `DISCORD_WEBHOOK_HEALTH`, `DISCORD_WEBHOOK_NEWJOINERS`
	- `DISCORD_BOT_TOKEN` (Discord bot token, 3 parts, not a webhook)
- Install Python dependencies:
	```powershell
	pip install -r requirements.txt
	```

## Step 2: Update Codebase & Fix Bugs
- Open `skoolhud/models.py` and update all models to use SQLAlchemy 2.0 style (`Mapped[...] = mapped_column(...)`).
- Remove any test code at the end of `skoolhud/vector/ingest.py` that runs ingest on import.
- Ensure all ENV variable names are consistent in `.env` and code.

## Step 3: Test Vector Store Integration
- Run vector ingest manually:
	```powershell
	python -m skoolhud.cli vector-ingest hoomans
	```
- Check for output like "Embeddings erzeugt: ..." and no errors.

## Step 4: Run Full Pipeline
- Start the daily runner:
	```powershell
	python daily_runner.py
	```
- Watch for errors and check Discord for posted reports.

## Step 5: Start & Test Discord Bot
- Start the bot:
	```powershell
	python skoolhud/discord/bot.py
	```
- Test commands in Discord: `!ping`, `!who <Thema>`

## Step 6: Extend Bot Features
- Implement real search for `!who`, `!whois`, and `!health` using the vector store and reports.

## Roadmap (as of 2025-09-03)
- Immediate: Setup script, better CLI errors, automated status reporting, last-run status file
- Short-Term: Refactor layers, move notification logic, make agent outputs accessible, document workflows
- Medium-Term: Integrate AI agents for report analysis/action items, modular agent system, smarter Discord bot, more analytics
- Long-Term: Full automation, proactive AI suggestions, extensibility for new sources/analytics/integrations

## Update Protocol
- After any major change, add a bullet to "Recent Changes" and update "Known Issues" if needed.
- If new workflows or conventions are introduced, document them here.
- If a bug is fixed or a new integration is added, note it here.

## Example Update
- **2025-09-03:** Fixed embedding conversion bug in vector ingest. All upserts now use Python lists.

---

If any section is unclear or missing important conventions, please provide feedback for further refinement. This file should always reflect the current state and rules of the project.

<!-- AUTO:STATUS START -->
- Letzter Run: `n/a`
- Runs total: 0
<!-- AUTO:STATUS END -->

<!-- AUTO:BACKLOG START -->
- [ ] Strict JSON Schema Validation in CI anschalten
- [ ] Smoke-Runner als CI-Job (PR-Gates)
- [ ] Net-Wrapper flächendeckend verwenden
<!-- AUTO:BACKLOG END -->
 
## Recent edits by Copilot (summary)

- Added tenant-aware `joiners` agent and small agents: `alerts.py`, `celebrations.py`, `snapshot_report.py`.
- Notifier `scripts/notify_reports_local.py` now prefers tenantized joiners files and skips placeholder posts; uses `skoolhud/utils/net.py` for retries.
- DB: added `skool_tag` to `skoolhud/models.py`, created Alembic revision `20250903_add_skool_tag_to_members.py`, and applied the column locally (Alembic stamped head).
- Added `skoolhud/utils/schema_utils.py` and JSON schemas (`kpi_report`, `member_daily_snapshot`); KPI agent and daily snapshot CLI now perform runtime validation (warnings only).
- Testing: added `scripts/run_smoke_tests.py` to run agents and assert expected artifacts; fixed Windows console emoji issue in `run_all_agents.py`.

Run: To re-check quickly, run `python scripts/run_smoke_tests.py` locally (requires environment and `.env` configured).

If you prefer stricter validation, I can make schema failures abort runs and write failure summaries to `exports/reports/<slug>/verify.txt` or add a CI job to run the smoke tests.

## Notes for AI agents — current status & conventions

- Repos & reported artifacts
	- Agents write tenantized artifacts into `exports/reports/<slug>/` (markdown, CSV). Use `skoolhud.utils.reports_dir_for(slug)` to locate/create dirs.
	- Raw snapshots land under `data_lake/<slug>/members/dt=YYYY-MM-DD/`.

- Schemas & validation
	- JSON schemas are under `project-status/schemas/` (currently: `kpi_report.schema.json`, `member_daily_snapshot.schema.json`).
	- `skoolhud/utils/schema_utils.py` provides `validate_json(instance, schema)` returning (ok, err). Validation is currently non-blocking (prints warnings); consider updating policy if you need strictness.

- Database & migrations
	- `skoolhud/models.py` contains SQLAlchemy models. `Member` includes `skool_tag` column; an Alembic revision `alembic/versions/20250903_add_skool_tag_to_members.py` was added and Alembic was stamped head during dev.
	- Local dev run also applied a one-off `ALTER TABLE` to add `skool_tag` to `skool.db`; CI should run `alembic upgrade head` instead of relying on the manual ALTER.

- Network & notifications
	- Use `skoolhud/utils/net.py::post_with_retry` for HTTP POSTs (rate-limit/retry wrapper). Local notifier `scripts/notify_reports_local.py` uses it; prefer it over ad-hoc requests.
	- Notifier will skip posting when files are missing or placeholders; it prefers explicit joiners files then falls back to KPI-extracted sections.

- Vector store
	- Vector ingest helper: `skoolhud/vector/ingest.py` and CLI `skoolhud.cli vector-ingest` (or `vectors-ingest`) exist. Ingest converts embeddings to Python lists before upsert.

- Testing & CI
	- Lightweight smoke runner: `scripts/run_smoke_tests.py` — runs `run_all_agents.py --slug hoomans` and checks expected artifacts (no pytest dependency). Add CI job to run it on PRs.
	- `verify_system.py` prints DB counts and checks for presence of joiner files; CI workflows read `verify.txt` for diagnostics.

- Console & environment notes
	- Windows consoles may not accept emoji (cp1252); avoid emoji in agent stdout. Use ASCII messages for status logs.
	- All secrets are expected in `.env` (Discord webhooks, SKOOL_COOKIE, DISCORD_BOT_TOKEN). Do not write secrets to repo.

- If you change DB schema during runtime
	- Prefer adding an Alembic revision and call `alembic upgrade head` in CI; if you must ALTER local sqlite for dev, also `alembic stamp head` to keep migration history consistent.

- Quick commands for local dev
	- Run agents for tenant `hoomans`: `python skoolhud/ai/agents/run_all_agents.py --slug hoomans`
	- Run smoke test harness: `python scripts/run_smoke_tests.py`
	- Run notifier locally: `python scripts/notify_reports_local.py hoomans`

These notes should help downstream agents discover conventions and avoid common pitfalls. Update them if you introduce new agents, schemas, or CI steps.
## Recent changes & Copilot status (2025-09-03)

This project has been actively edited by the automated assistant. Below is a concise record of edits I applied, verification performed, and remaining recommended next steps.

- Agent & reports
	- Added tenant-aware `joiners` agent: writes `exports/reports/<slug>/new_joiners_week.md`, `new_joiners_last_week.md`, `new_joiners_30d.md` with lines like:
		- "Linda - @skooltag - joined on 02.09.2025 ( <8 Hours ago ) [user_id]"
	- Added resilience when DB lacks `skool_tag`.
	- Registered `joiners` in `skoolhud/ai/agents/run_all_agents.py`.
	- Added new agents earlier in the session: `alerts.py`, `celebrations.py`, `snapshot_report.py` (produce verify.txt / alerts / celebrations / snapshot files tenantized).

- Notifier & CI
	- `scripts/notify_reports_local.py` updated to prefer explicit joiners files and post three separate embeds (This Week / Last Week / Last 30 days), falling back to KPI extraction.
	- Notifiers now skip posting placeholder messages when files are absent (local + CI pattern applied earlier).
	- CI `daily.yml` already parses `verify.txt` and posts a summary embed; verify step now captures `verify.txt` output.

- DB & migrations
	- Added `skool_tag` Column to SQLAlchemy model (`skoolhud/models.py`).
	- Created Alembic revision `alembic/versions/20250903_add_skool_tag_to_members.py` to add `skool_tag`.
	- Applied a one-off `ALTER TABLE members ADD COLUMN skool_tag TEXT` to the local `skool.db` (so runtime now has column). If you prefer tracked migration state, run `alembic stamp head` or `alembic upgrade head`.

- Utilities & verification
	- `skoolhud/utils.py` contains `reports_dir_for()` and `datalake_members_dir_for()` helpers (used by agents).
	- `verify_system.py` was enhanced with DB-fallback raw-SQL counts and a smoke-check that prints whether joiners files exist for a sample tenant.

- Files added/edited (high level)
	- Added: `skoolhud/ai/agents/joiners.py`
	- Edited: `skoolhud/models.py` (added `skool_tag`), `scripts/notify_reports_local.py`, `skoolhud/ai/agents/run_all_agents.py`, `verify_system.py`
	- Added Alembic revision: `alembic/versions/20250903_add_skool_tag_to_members.py`
	- Added helper script: `scripts/add_skool_tag_column.py` (ran locally to add column)

- Verification performed
	- Ran `python skoolhud/ai/agents/joiners.py --slug hoomans` — files produced and counts printed.
	- Ran `python scripts/notify_reports_local.py hoomans` — notifier posted available embeds and printed HTTP statuses.
	- Ran `python verify_system.py` — DB diagnostics printed and joiners files presence reported.

- Pending / recommended next steps
	1. Migrations: run one of:
		 - `alembic stamp head` (if you already applied the column manually) OR
		 - `alembic upgrade head` (to let Alembic apply the revision). Keeping Alembic state consistent is recommended.
	2. Add `project-status/schemas/` JSON schemas for `kpi_report` and `member_daily_snapshot` and validate agent outputs against them.
	3. Create `skoolhud/utils/net.py` — central rate-limit/retry wrapper and replace direct requests/urllib calls.
	4. Add CI smoke-tests (pytest) that run `run_all_agents.py --slug hoomans` and assert `exports/reports/hoomans/new_joiners_*.md` exist.

If you want, I can implement any of the pending steps now (run Alembic stamp/upgrade, scaffold JSON schemas, add the net wrapper, or add CI tests).
## Roadmap (as of 2025-09-03)

### Immediate Next Steps
- Add a setup script for easy local installation and environment setup
- Improve CLI error messages and help output for better usability
- Automate basic testing and status reporting after each pipeline run
- Write last-run status to a file for easy troubleshooting

### Short-Term Goals
- Refactor codebase for clearer separation of layers (data, logic, agents, notification)
- Move notification/reporting logic into a dedicated module for easier extension
- Make all agent outputs (reports, snapshots) easily accessible for other agents and bots
- Document all workflows and update instructions.md after every major change

### Medium-Term Goals
- Integrate AI agents that can analyze reports and data, generate action items, and post well-researched summaries to Discord
- Build a modular system for adding new analysis/reporting agents with minimal code changes
- Improve Discord bot to answer user queries with data-driven insights and recommendations
- Add more tenant-specific analytics and custom report types

### Long-Term Vision
- Fully automate data pipeline, reporting, and Discord integration for any Skool community
- Enable AI agents to proactively suggest improvements, flag anomalies, and guide users based on live data
- Make the system extensible for new data sources, analytics, and integrations

---

All agents and developers should use this roadmap to guide their work. Update this section as priorities shift or new ideas emerge.

# AI Agent Instructions & Project Status for SkoolHUD

## Purpose
This file is the single source of truth for all AI agents and developers. It contains live, actionable instructions and status updates for building, maintaining, and understanding the SkoolHUD system. Always keep it up to date!

## How to Use
- Read this file before starting any coding or automation task.
- Update after major changes, refactors, or new feature additions.
- Use it to communicate current architecture, conventions, and known issues to future agents.

## Current System Status (2025-09-03)
- **Architecture:**
	- Multi-tenant data pipeline for Skool communities
	- SQLite for classic DB, ChromaDB for vector store
	- Typer CLI (`skoolhud/cli.py`) for all pipeline steps
	- Agents in `skoolhud/ai/agents/` for analysis/reporting
	- Discord integration via webhooks (all secrets in `.env`)
	- Automation via `daily_runner.py` and GitHub workflows
- **Recent Changes:**
	- Vector ingest now robust: Embeddings always converted to Python lists before upsert
	- All secrets/cookies loaded from `.env`, never from files
	- All reports are tenant-specific; global reports removed
	- CI and daily workflows post to all Discord channels
	- All Pylance/type errors in CLI and ingest fixed
- **Known Issues:**
	- No dedicated test suite; rely on CLI smoke tests and `verify_system.py`
	- Discord notifications handled by separate scripts, not agents

- **Recent Changes (2025-09-03, delta):**
	- Fixed duplicate Discord notifications during a single daily run: removed duplicate notify call from `update_all.py` so `daily_runner.py` is the single notification trigger.
	- Notify scripts (`scripts/notify_reports_local.py` and `.github/scripts/discord_notify.py`) now skip posting placeholder "No ... file found." messages when a report file is absent or empty. Channels will remain quiet unless real content exists.
	- Local dry-run validation executed; recommendation: run `python daily_runner.py` to confirm no duplicates in your environment.
- **Key Workflows:**
	- Local: Activate venv, set up `.env`, run CLI commands
	- Full pipeline: `daily_runner.py` or sequence of CLI steps
	- Vector ingest: Automated after member updates
	- Reporting: Agents generate markdown/CSV, notification scripts post to Discord
- **Integration Points:**
	- Discord webhooks: All channels must be present in `.env` and GitHub secrets
	- ChromaDB: Ingest/search via `skoolhud/vector/ingest.py` and `skoolhud/vector/query.py`

## Update Protocol
- After any major change, add a bullet to "Recent Changes" and update "Known Issues" if needed.
- If new workflows or conventions are introduced, document them here.
- If a bug is fixed or a new integration is added, note it here.

## Example Update
- **2025-09-03:** Fixed embedding conversion bug in vector ingest. All upserts now use Python lists.

---

If any section is unclear or missing important conventions, please provide feedback for further refinement. This file should always reflect the current state and rules of the project.
