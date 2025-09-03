# AI Agent Instructions for SkoolHUD

## Purpose
This file provides live, actionable instructions and status updates for any AI agent building or maintaining the SkoolHUD system. It is designed to be updated continuously as the codebase evolves.

## How to Use
- Always read this file before starting any coding or automation task.
- Update this file after major changes, refactors, or new feature additions.
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

This file is the single source of truth for AI agents. Keep it up to date for maximum productivity and reliability.
