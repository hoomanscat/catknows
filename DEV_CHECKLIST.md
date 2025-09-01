# DEV Checkliste — Catknows / SkoolHUD

## 1. Setup & Installation
- [ ] Repo geklont und `.venv` eingerichtet
- [ ] `requirements.txt` installiert

## 2. Datenbank & Migration
- [ ] `init-db` ausgeführt
- [ ] `alembic upgrade head` ohne Fehler durchgelaufen

## 3. Tenant-Konfiguration
- [ ] Cookie erfolgreich über CLI hinzugefügt (`add-tenant`)
- [ ] `test-tenant` schlägt nicht fehl

## 4. Agenten laufen lokal
- [ ] `run_all_agents.py --slug hoomans` erstellt alle Reports
- [ ] Inhalte in `exports/reports/hoomans/` sichtbar

## 5. Backfill (falls benötigt)
- [ ] `backfill_member_daily_from_datalake.py` ausgeführt
- [ ] `backfill_member_daily_from_leaderboards.py` ohne DateTime-Fehler
- [ ] `verify_system.py` zeigt valide tägliche Snapshots

## 6. CI & Discord (GitHub Actions)
- [ ] Secrets für Discord-Webhooks gesetzt
- [ ] `daily.yml` läuft fehlerfrei (Notify-Test ok)
- [ ] Artefakte (`reports/{slug}`) werden im CI hochgeladen
- [ ] Discord-Kanäle empfangen korrekte Embeds (Status, KPI, Movers etc.)

## 7. Struktur & Cleanup
- [ ] Agenten schreiben in tenant-spezifische Verzeichnisse
- [ ] `.gitignore` aktualisiert (keine lokalen .db oder exports gepusht)
- [ ] Alembic-Versionen committed für Schema-Konsistenz

## 8. Zusätzliche Features (optional)
- [ ] `notify_test.yml` bereit für manuelle Discord-Tests
- [ ] Summary‑Embed implementieren (falls gewünscht)
- [ ] Dashboard (z. B. Streamlit) zur Live-Visualisierung

---

##  Tipps
- Bei Alembic-Fail wegen SQLite‑Limitierung → Migration auf No-Op setzen
- DateTime-Fehler = String ↔ datetime-Konflikt → immer `datetime` verwenden
- Bei CI-Fehlern → Discord‑Webhook über `curl` testen
- `verify_system.py --slug <slug>` schnellster Indikator, ob alles funzt

Let’s keep this dev flow smooth and reliable! 🚀
