# Skool HUD & Knowledge Base — Starter

**Einfacher Start für Windows (auch für Anfänger geeignet).**

## Was ist hier drin?
- **Fetcher** (holt Skool-JSON über die offiziellen Next.js-Routen – ToS-konform)
- **Raw-Snapshots** (legt die Original-JSON-Dateien ab)
- **Erste Normalisierung** (schreibt Grunddaten in SQLite)
- **CLI** (Befehle: `init-db`, `add-tenant`, `test-tenant`, `fetch-members`)

> Hinweis: Diese Version konzentriert sich auf **Members**. Leaderboard & weitere Quellen kommen als nächster Schritt.

---

## 0) Voraussetzungen (einmalig)
1. **Python 3.11** installieren (Windows): https://www.python.org/downloads/
   - Während der Installation **"Add Python to PATH"** anhaken.
2. (Optional) **Git** installieren: https://git-scm.com/downloads

> Wenn du Python schon hast: Öffne PowerShell und tippe `python --version`. Es sollte `3.11.x` anzeigen.

---

## 1) Entpacken & Ordner öffnen
- Entpacke die ZIP (z. B. in `C:\skool-hud-starter`).
- Öffne **PowerShell** in diesem Ordner (Shift + Rechtsklick → *PowerShell hier öffnen*).

---

## 2) Virtuelle Umgebung & Abhängigkeiten
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3) Datenbank anlegen
```powershell
python -m skoolhud.cli init-db
```

---

## 4) Tenant anlegen (Cookie eintragen)
### 4.1 Cookie aus dem Browser holen
- Öffne `https://www.skool.com/<DEIN-GROUP-PFAD>/-/members` im **Chrome**-Browser (eingeloggt).
- `F12` → Tab **Network** → Seite neu laden (F5).
- Links einen Request anklicken (z. B. auf die Members-Seite).
- Rechts im Reiter **Headers** → **Request Headers** → **cookie**.
- **Den kompletten Cookie-String kopieren.** (Nichts verändern.)

### 4.2 Tenant in der DB anlegen
```powershell
python -m skoolhud.cli add-tenant --slug hoomans --group your-group-path --cookie "HIER_DEN_GESAMTEN_COOKIE_STRING_EINFÜGEN"
```
- `--slug`: frei wählbarer Kurzname (z. B. `hoomans`)
- `--group`: der Pfad im Skool-URL (z. B. `the-alley` oder dein eigener Group-Pfad)
- `--cookie`: exakt wie kopiert

**Sicherheit:** Gib deinen Cookie **niemandem**. Er bleibt lokal in deiner SQLite-DB. Du kannst ihn jederzeit austauschen.

---

## 5) Cookie prüfen
```powershell
python -m skoolhud.cli test-tenant --slug hoomans
```
- Der Befehl lädt die Members-Seite, sucht die `BUILD_ID` und meldet Erfolg/Fehler.

---

## 6) Mitglieder holen (raw + normalisieren)
```powershell
python -m skoolhud.cli fetch-members --slug hoomans
```
- Ablauf:
  1. BUILD_ID entdecken (HTML)
  2. 15s warten (Rate-Limit)
  3. JSON-Route abrufen
  4. Raw-JSON speichern (`exports/raw/`)
  5. Grunddaten in SQLite upserten (`skool.db`)

> Beim ersten Lauf kann es sein, dass die Normalisierung nur einen Teil der Felder füllt. Wir verbessern das nach Sichtung deiner echten JSON.

---

## 7) Daten ansehen
- **SQLite DB**: Datei `skool.db` (z. B. mit *DB Browser for SQLite* öffnen: https://sqlitebrowser.org/)
- **Rohdaten**: Ordner `exports/raw/`

---

## Nächste Schritte
- Leaderboard-Import ergänzen
- 6h-Scheduler hinzufügen
- Vektorstore + Chat
- HUD-Frontend

Bei Fragen einfach die Konsolenausgabe hier reinkopieren – ich sage dir dann genau, was zu tun ist.
