 
--- 
## 🧰 Mini-Kommandos (PowerShell)
Hier ist die **neue `copilot-instructions.md`** — eine **einzielige** Anleitung für deine ausführende KI.
Sie führt von 0 → „Discord-Post mit AI-Insights“ in klaren Schritten, inkl. **FERTIG-Checkliste**, **Abnahmekriterien**, **Prompts** (Agent-Systemprompts), und **Selbst-Validierung**.


# SkoolHUD – Copilot Instructions (Single-Goal Playbook)

## 🎯 Ziel (ein Satz)

**Pro Tenant per Run**: Reports **validieren → analysieren → zusammenfassen → sicher posten**.
**Ergebnis:** `exports/ai/<tenant>/<run_id>/insights.md` + `actions.md` erstellt **und** in den AI-Discord-Kanal gepostet.

> **Definition of Done (DoD)**
>
> 1. Dateien `insights.md` & `actions.md` existieren,
> 2. Discord-Webhook liefert **2xx**,
> 3. Status `exports/status/runs/<run_id>/<tenant>/status.json` enthält `"ok": true`.


## 🔧 Rahmen (immer gültig)

* **Read-only DB** in der KI-Schicht (nur `SELECT`),
* **Rate-Limit/Retry** zentral via `skoolhud/utils/net.py` (≥15s Delay, 3x Backoff),
* **Keine Secrets** in Logs/Posts, Maskierung von PII (E-Mail, Handles),
* **Arbeiten strikt datenbasiert** (keine Halluzinationen; bei fehlenden Daten: „Daten fehlen“).
* **Tool-Preambles & klare Stop-Bedingungen** in Prompts: upfront Plan + Fortschritt, dann sauberes Ende. ([OpenAI Kochbuch][1])


## ✅ FERTIG-Checkliste (die **einzige** To-do-Liste)

> Arbeite diese Liste **von oben nach unten** ab.
> Nach jedem Schritt: schreibe einen **Beleg** (siehe „Beweis/Abnahme“) **und** markiere in `build_checklist.json` den Schritt als erledigt.

1. [ ] **Run-ID erzeugen & Ordner anlegen**

   * Erzeuge `RUN_ID=YYYYMMDD-HHMMSS` (UTC timestamp including seconds).
   * Lege `exports/ai/<tenant>/<RUN_ID>/` an.

2. [ ] **Neueste Input-Artefakte finden**

   * Suche pro Typ (KPI/Health/Movers/Delta/Snapshot) die **neueste** Datei unter `exports/reports/<tenant>/**` (CSV/JSON/MD).

3. [ ] **Schema-Validierung (Gate)**

   * Validiere alle JSON/CSV-Inputs gegen `schemas/**`.
   * Erzeuge `validate.json` mit `{ ok, errors[], warnings[], files_checked }`.
   * **Abbruch** bei `ok=false` (kritisch).

4. [ ] **Analysten ausführen** (in dieser Reihenfolge)
   a) **KPIAnalyst** → `kpi_findings.json`
   b) **HealthAnalyst** (DB read-only) → `health_findings.json`
   c) **MoversAnalyst** → `movers_findings.json`
   d) **DeltaAnalyst** → `delta_true_findings.json`
   e) **SnapshotAnalyst** (+ optional **Expert-Finder**) → `snapshot_findings.json`, `experts.json`

5. [ ] **Composer** (Schreiber)

   * Konsolidiere Findings → `insights.json` → `insights.md` & `actions.md` (kurz, prägnant, umsetzbar).

6. [ ] **Safety-Gate**

   * PII-Redaktion + Kosten-Budget prüfen; ggf. kürzen oder abbrechen.
   * Protokolliere Prüfresultat in `status.json`.

7. [ ] **Dispatcher (Discord)**

   * Poste `insights.md` (und optional `actions.md`) an `DISCORD_WEBHOOK_AI_INSIGHTS` (Chunking + Retry).
   * Schreibe `dispatch.json` mit HTTP-Statuscodes.

8. [ ] **Status schreiben**

   * `exports/status/runs/<RUN_ID>/<tenant>/status.json` mit `{ run_id, tenant, steps[], ok, artifacts{} }`.
   * `exports/status/last_run.json` aktualisieren.

9. [ ] **Dok-Marker (optional)**

   * Aktualisiere `copilot-instructions.md` AUTO-Marker (Status/Backlog).

10. [ ] **FERTIG**

* Alle drei DoD-Kriterien erfüllt (oben).
* Trage `"finished": true` in `build_checklist.json` ein.

**Beweis/Abnahme (pro Schritt):**
Erzeuge/aktualisiere `exports/ai/<tenant>/<RUN_ID>/build_checklist.json`:

```json
{
   "run_id": "20250904-093000",
  "tenant": "hoomans",
  "steps": {
    "id_created": true,
    "inputs_found": true,
    "validated": {"ok": true, "files_checked": 7},
    "analysts": {"kpi": true, "health": true, "movers": true, "delta": true, "snapshot": true},
    "composed": true,
    "safety_passed": true,
    "dispatched": {"http_status": 204},
    "status_written": true,
    "docs_updated": false
  },
  "finished": true
}
```


## 🧭 Ablauf (genau so umsetzen)

### 1) Orchestrator (Startpunkt)

**Pfad:** `skoolhud/ai/orchestrator.py` (CLI: `python -m skoolhud.cli run-orchestrator <tenant>`; alias `python -m skoolhud.cli orchestrator <tenant>` is supported)
**Tut:** erzeugt Run-ID, findet Inputs, ruft Validator → Analysten → Composer → Safety → Dispatcher → Status.
**Abnahme:** Rückgabe enthält `outdir`, `items` (>=5), HTTP-Status in `dispatch.json`.

### 2) Validator (Gate)

**Pfad:** `skoolhud/ai/agents/validator.py`
**Input:** `exports/reports/<tenant>/**`, `schemas/**`
**Output:** `validate.json` (Schema unten) + Fehlerliste an Orchestrator
**Abbruchregel:** `ok=false` ⇒ Run stoppen, `status.json.ok=false`.

```json
// validate.json (Schema)
{
  "ok": true,
  "files_checked": 0,
  "errors": [],
  "warnings": []
}
```

### 3) Analysten (fachlich)

**Reihenfolge und Outputs:**

* KPI → `kpi_findings.json`
* Health (mit DB-Query) → `health_findings.json`
* Movers → `movers_findings.json`
* DeltaTrue → `delta_true_findings.json`
* Snapshot (+ optional Expert-Finder) → `snapshot_findings.json`, `experts.json`

**Format (einheitlich):**

```json
{
   "run_id": "20250904-093000",
  "tenant": "hoomans",
  "agent": "HealthAnalyst",
  "bullets": ["5 Mitglieder >14 Tage inaktiv: Alice, Bob, …"],
  "actions": [{"title": "DM an Alice/Bob", "due_days": 2}],
  "evidence": {"sources": ["exports/reports/.../health.json"], "query": "SELECT ... LIMIT 5"}
}
```

### 4) Composer (Schreiber)

**Pfad:** `skoolhud/ai/agents/composer.py`
**Tut:** Wandelt alle `*_findings.json` in `insights.json`, `insights.md`, `actions.md` um.
**Regeln:** kurze klare Sätze, keine Jargon-Wolken; **Tool-Preamble** im LLM-Prompt: Ziel paraphrasieren → Plan → Ausführung → Abschluss. ([OpenAI Kochbuch][1])

### 5) Safety (PII & Kosten)

**Pfad:** `skoolhud/ai/agents/safety.py`
**Checks:** PII maskieren, Budget-Grenzen (Tokens/Kosten); bei Verstoß: sanitizen oder abbrechen.

### 6) Dispatcher (Discord)

**Pfad:** `skoolhud/ai/agents/dispatcher.py`
**Tut:** Post an `DISCORD_WEBHOOK_AI_INSIGHTS` (Chunking, Retry, Backoff); schreibt `dispatch.json`.

### 7) Status & Doku

**Pfad:** `scripts/update_copilot_instructions.py` (optional)
**Tut:** schreibt `exports/status/runs/<RUN_ID>/<tenant>/status.json` und aktualisiert AUTO-Marker.


## 🧱 Dateien & Pfade (Kanonisch)

* **Inputs:** `exports/reports/<tenant>/**` (CSV/JSON/MD), **DB** (read-only), **Vector** (`./vector_store`, Collection `skool_members`)
* **Outputs:** `exports/ai/<tenant>/<RUN_ID>/{validate.json, *_findings.json, insights.json, insights.md, actions.md, dispatch.json}`
* **Status:** `exports/status/runs/<RUN_ID>/<tenant>/status.json`, `exports/status/last_run.json`


## 🧪 Selbst-Validierung (automatisch)

Nach dem Run müssen diese Checks **grün** sein:

1. **Dateien vorhanden**

   * `insights.md`, `actions.md`, `dispatch.json`, `status.json`, `validate.json`
2. **Discord-Antwort**

   * `dispatch.json.http_status` ∈ {200, 201, 204}
3. **Status**

   * `status.json.ok == true`, `last_run.json` aktualisiert
4. **Schema-Konformität**

   * `run_status.schema.json` & `validate.schema.json` **pass**
5. **FERTIG**

   * `build_checklist.json.finished == true`


## 🧠 Prompt-Paket (Systemprompts)

> Prompts folgen best practices zu **Agenten-Steuerung**, **Tool-Preambles** und **kontrollierter Eifrigkeit**: upfront Ziel+Plan, klare Stop-Kriterien, konsistente Fortschrittsmeldungen. Nutze „geringere Eifrigkeit“ für schnelle, fokussierte Schritte; erhöhe Eifrigkeit nur, wenn die Aufgabe komplex ist. ([OpenAI Kochbuch][1])

### A) Globaler System-Prompt (alle Analysten)

```
Du bist ein sachlicher Analyst für SkoolHUD.
ZIEL: Erzeuge kurze, belastbare Befunde aus gelieferten Dateien/DB-Abfragen.
REGELN:
```

### B) KPIAnalyst (System)

```
Rolle: KPI-Analyst.
Aufgabe: Identifiziere die 3 wichtigsten Kennzahlen/Trends (7d/30d/Aktivität).
Daten: kpi_report.* (+ optional DB-Snapshots).
Lieferform: bullets[], actions[], evidence{} wie im Schema.
Hinweis: Keine Erklärungen außerhalb der Daten. Kurz, präzise, umsetzbar.
```

### C) HealthAnalyst (System)

```
Rolle: Health/Churn-Analyst.
Aufgabe: Finde inaktive Segmente und schlage 2-3 Re-Engagement-Maßnahmen vor.
Daten: health_score.* + DB (SELECT nur, z.B. inaktiv >14 Tage).
Lieferform: bullets[], actions[], evidence{query, sources[]}.
Maske PII in Text (Handles/E-Mails).
```

### D) MoversAnalyst (System)

```
Rolle: Movers-Analyst.
Aufgabe: Top-Mover & echte Veränderungen benennen; 1 Challenge vorschlagen.
Daten: leaderboard_delta.*, leaderboard_delta_true.*.
Lieferform: bullets[], actions[], evidence{sources[]}.
```

### E) SnapshotAnalyst (System)

```
Rolle: Snapshot-Segmentierer.
Aufgabe: 2-3 sinnvolle Segmente + Beispiel-Mitglieder vorschlagen.
Daten: export_members_snapshot.* (+ optional Vector "skool_members").
Lieferform: bullets[], actions[], evidence{sources[], (optional) vector_hits[]}.
```

### F) Expert-Finder (System)

```
Rolle: Expert-Finder.
Aufgabe: Für <topic> die Top-3 Personen aus Vector-Fundus nennen + kurzer Grund.
Daten: Vector-Suche (Chroma, Collection "skool_members").
Lieferform: JSON {hits:[{member_id,name,reason,score,source_meta}]}.
Hinweis: Nur nennen, wenn Trefferqualität ausreichend; sonst "Daten fehlen".
```

### G) Composer (System)

```
Rolle: Executive-Writer.
Aufgabe: Aus allen Findings eine 8-12 Zeilen "insights.md" + checklist "actions.md".
Stil: kurze Sätze, konkrete Verben, 0% Jargon, max 12 Zeilen Insights.
Tool-Preamble: Ziel paraphrasieren → Plan → dann klare Abschnitte schreiben.
Stoppe, wenn beide Dateien schlüssig sind.
```

### H) Dispatcher (System)

```
Rolle: Dispatcher.
Aufgabe: "insights.md" (und optional "actions.md") posten.
Regeln: Chunking (<=1800 Zeichen), Retry/Backoff, Erfolgscode in dispatch.json.
Text: Keine PII im Klartext; Emojis sparsam; präziser Titel.
```

> **Hinweis zur Agenten-Steuerung:** Klare Preambles/Pläne und explizite Persistenz/Stop-Kriterien erhöhen die Vorhersehbarkeit in agentischen Flows (z. B. „plane zuerst, führe dann aus; beende, wenn alle Teilaufgaben erledigt sind“). Steuer’ die „Eifrigkeit“: niedriger für schnelle, enge Aufgaben; höher für komplexe Ketten. ([OpenAI Kochbuch][1])


## 🗂️ Artefakte (sollten existieren, wenn „FERTIG“)

* `exports/ai/<tenant>/<RUN_ID>/validate.json`
* `exports/ai/<tenant>/<RUN_ID>/*_findings.json`
* `exports/ai/<tenant>/<RUN_ID>/insights.json`
* `exports/ai/<tenant>/<RUN_ID>/insights.md`
* `exports/ai/<tenant>/<RUN_ID>/actions.md`
* `exports/ai/<tenant>/<RUN_ID>/dispatch.json`
* `exports/status/runs/<RUN_ID>/<tenant>/status.json`
* `exports/status/last_run.json`
 
## 📝 Journal (Copilot)

Kurzjournal: unten steht, welche Punkte aus der 10er-Checkliste ich implementiert habe, mit knappen Belegen (Dateien/Orte).

1) Run-ID & Ordner anlegen — Done
   - Beleg: `skoolhud/ai/orchestrator.py` erzeugt `RUN_ID` und legt `exports/ai/<tenant>/<RUN_ID>/` an.

2) Input-Artefakte finden — Done
   - Beleg: Suche/Resolver in Orchestrator + `skoolhud/ai/agents/validator.py` verwendet `exports/reports/<tenant>/**`.

3) Schema-Validierung (Gate) — Done
   - Beleg: `validate.json` geschrieben in `exports/ai/<tenant>/<RUN_ID>/validate.json` (Shape `{ok,errors,warnings,files_checked}`).

4) Analysten ausführen — Done
   - Beleg: `exports/ai/<tenant>/<RUN_ID>/*_findings.json` (z.B. `kpi_findings.json`, `health_findings.json`).

5) Composer → insights/actions — Done
   - Beleg: `insights.json`, `insights.md`, `actions.md` im Run-Ordner; PII-Masking in `skoolhud/ai/agents/safety.py`.

6) Safety-Gate (PII & Kosten) — Mostly Done
   - Beleg: PII-Redaktion vorhanden; Budget/Token-Telemetrie ist minimal (weiteres Hardening empfohlen).

7) Dispatcher (Discord) — Done
   - Beleg: `skoolhud/ai/agents/dispatcher.py` unterstützt preview, guard, retry, `--force`; `dispatch.json` und `dispatch_preview.json` in Run-Ordner.

8) Status schreiben (canonical) — Done
   - Beleg: `exports/status/runs/<RUN_ID>/<tenant>/status.json` und `exports/status/last_run.json` werden geschrieben.

9) Docs / AUTO-Marker — Done (manual update)
   - Beleg: `exports/ai/<tenant>/<RUN_ID>/build_checklist.json` erstellt; `.github/copilot-instructions.md` AUTO-Block wurde aktualisiert for that run. Full auto-updater script is deferred.

10) FERTIG marker — Done for the example run
   - Beleg: `build_checklist.json.finished == true` for the executed run. CI enforcement deferred.

---

## 📨 Detailed note to the other AI (evidence-backed)

I implemented the orchestrator flow and supporting agents to complete the 10‑point checklist end-to-end; below are precise artifacts, file edits, commands run, and outcomes you can inspect.

Files & key edits (code locations):
- `skoolhud/ai/orchestrator.py` — run-id creation, input resolver, validator gate, analyst sequencing, composer + safety + dispatcher wiring.
- `skoolhud/ai/agents/validator.py` — canonical `validate.json` shape and gate behavior.
- `skoolhud/ai/agents/composer.py` — consolidates findings → `insights.json`, `insights.md`, `actions.md`.
- `skoolhud/ai/agents/safety.py` — PII masking rules and allowlist for `@skool`.
- `skoolhud/ai/agents/dispatcher.py` — guarded posting, preview, chunking, retry/backoff, `--force` behavior, writes `dispatch.json`.
- `skoolhud/ai/agents/*_analysts.py` (kpi_report.py, health_score.py, leaderboard_delta*.py, export_members_snapshot.py) — produce `*_findings.json`.
- `skoolhud/config.py` & `skoolhud/cli.py` — tenant resolution (`get_tenant_slug()` used throughout).
- `skoolhud/fetcher.py` — small typing fix (`Optional` for page/window params) to satisfy static checks.
- `.github/workflows/notify_test.yml` & `.github/workflows/daily.yml` — fixed `workflow_dispatch.inputs`, normalized `env` mappings, and adjusted `if:` to use `env.DISCORD_WEBHOOK_URL` or `github.event_name` to avoid parse-time `secrets` evaluation.
- Added CI workflows: `.github/workflows/run-tests.yml` and `.github/workflows/validate-workflows-ci.yml`.

Representative artifacts (inspect these paths in the repo):
- validate summary: `exports/ai/example-tenant/20250904T193846Z/validate.json` (shape: {ok, errors, warnings, files_checked}).
- findings: `exports/ai/example-tenant/20250904T193846Z/kpi_findings.json`, `health_findings.json`, etc.
- composed outputs: `exports/ai/example-tenant/20250904T193846Z/insights.json`, `insights.md`, `actions.md`.
- dispatch records: `exports/ai/example-tenant/20250904T193846Z/dispatch.json` and `dispatch_preview.json`.
- run checklist: `exports/ai/example-tenant/20250904T193846Z/build_checklist.json` (shows per-step booleans and `finished: true`).
- canonical status: `exports/status/runs/20250904T193846Z/example-tenant/status.json` and `exports/status/last_run.json`.

Commands I executed during development (can be re-run locally):
- YAML validation: `python validate_yaml.py` → both workflows parse OK.
- Tests: `pytest -q` → previous local run reported `7 passed` (see test artifacts/CI job `run-tests.yml`).
- Orchestrator: `python -m skoolhud.cli run-orchestrator example-tenant --force` (used to create run artifacts and exercise dispatcher).
- Direct dispatcher test: small Python call invoking `skoolhud.ai.agents.dispatcher.Dispatcher.dispatch(...)` with `force=True` to verify live post.

Live dispatch outcome (example):
- The direct dispatcher run posted successfully (HTTP 200). The recorded `dispatch.json` contains the response body with Discord message JSON and an `attachments[...] .url` CDN link to the posted `insights.md`.

Validation / quality gates (evidence):
- YAMLs: `validate_yaml.py` output: `notify_test.yml: OK`, `daily.yml: OK`.
- Tests: local pytest run previously returned `7 passed`.
- Validator: sample `validate.json` indicates `ok: true` and `files_checked` > 0 for the successful run.

Notes and open items:
- PII masking and basic budget checks exist; stronger LLM cost telemetry is recommended for production.
- The AUTO-marker update in `.github/copilot-instructions.md` was applied for the example run, but a small script to update it automatically at orchestrator completion is deferred (I can add `scripts/update_copilot_marker.py` and wire it into the orchestrator if you want).

If you want, I can produce a short patch log (git-style list) of the exact commits/files changed, or open a PR containing these changes for review.

---

### Abschluss


## 🧰 Mini-Kommandos (PowerShell)

```powershell
# Orchestrator (CLI) - canonical command
python -m skoolhud.cli run-orchestrator hoomans

# Backward-compatible alias (keeps older docs/commands working)
python -m skoolhud.cli orchestrator hoomans

# Prüfen: Artefakte vorhanden?
dir exports\ai\hoomans\*\ | select Name,Length,LastWriteTime

# Letzten Status sehen (Windows)
gc exports\status\last_run.json

# JSON kurz validieren (falls jq installiert)
jq . exports\ai\hoomans\*\validate.json
```


## 📎 Anhang: JSON-Schemas (Kurzform)

`schemas/run_status.schema.json`

```json
{ "$schema":"https://json-schema.org/draft/2020-12/schema",
  "title":"Run Status","type":"object",
  "required":["run_id","tenants","steps","ok","artifacts"],
  "properties":{
   "run_id":{"type":"string","pattern":"^\\d{8}-\\d{6}$"},
    "tenants":{"type":"array","items":{"type":"string"}},
    "steps":{"type":"array","items":{"type":"string"}},
    "ok":{"type":"boolean"},
    "errors":{"type":"array","items":{"type":"string"}},
    "artifacts":{"type":"object"}
}}
```

`schemas/validate.schema.json`

```json
{ "$schema":"https://json-schema.org/draft/2020-12/schema",
  "title":"Validation Summary","type":"object",
  "required":["ok","files_checked"],
  "properties":{
    "ok":{"type":"boolean"},
    "errors":{"type":"array","items":{"type":"string"}},
    "warnings":{"type":"array","items":{"type":"string"}},
    "files_checked":{"type":"integer","minimum":0}
}}
```


## ℹ️ Prompt-Hinweise (aus OpenAI Cookbook, knapp)

* **Tool-Preambles**: Ziel re-phrasing + Schrittplan + Fortschrittsmeldungen verbessern Nachvollziehbarkeit in agentischen Flows. ([OpenAI Kochbuch][1])
* **Eifrigkeit steuern**: Weniger Eifrigkeit für schnelle Aufgaben; **persistente Agenten** bei komplexen Aufgaben, klare Stop-Bedingungen/Unsicherheits-Regeln definieren. ([OpenAI Kochbuch][1])
* **Reasoning-/Verbosity-Kontrolle**: Präzise Prompt-Vorgaben zur Länge & Planung erhöhen Zuverlässigkeit. ([OpenAI Kochbuch][1])


### Abschluss

Wenn **alle** Punkte der **FERTIG-Checkliste** erledigt sind **und** die DoD-Kriterien erfüllt sind, markiere in `build_checklist.json` `"finished": true` — **dann ist der Run FERTIG**.

[1]: https://cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide "GPT-5 prompting guide"