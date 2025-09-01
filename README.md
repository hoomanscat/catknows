# SkoolHUD

Ein CLI-Tool für **Mitglieder- und Leaderboard-Daten von Skool Communities**.  
Es sammelt Daten täglich, normalisiert sie in eine SQL-Datenbank und erstellt Reports & Zeitreihen.

---

## 🚀 Features
- Mitglieder-Import mit Pagination
- Leaderboard (All-Time, 30 Tage, 7 Tage)
- Normalisierung + Zeitreihen (`LeaderboardSnapshot`, `MemberDailySnapshot`)
- Daily Runner mit Reports:
  - KPI Report
  - Health Score (Advocates / At Risk)
  - Leaderboard Movers
  - True Delta Leaderboards (echte Historie)
- Data Lake Export (`data_lake/members/dt=YYYY-MM-DD/members.csv`)
- Automatisches Reporting (`exports/reports/*.md`)

---

## 📦 Installation
```powershell
git clone https://github.com/hoomanscat/catknows.git
cd catknows
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

---

## ⚙️ Setup
1. **DB anlegen**
```powershell
skoolhud init-db
```

2. **Cookie speichern**  
   `cookie.txt` ins Projektroot legen (vollständiger Cookie-Header).

3. **Tenant einrichten**
```powershell
$cookie = Get-Content .\cookie.txt -Raw
skoolhud add-tenant --slug hoomans --group hoomans --cookie $cookie
skoolhud test-tenant --slug hoomans
```

---

## 📊 Daily Run
```powershell
python daily_runner.py
```
Ablauf:
1. Mitglieder & Leaderboards ziehen  
2. Leaderboards normalisieren  
3. MemberDailySnapshot schreiben  
4. Agents ausführen (Reports + Data Lake Export)  

Ergebnisse:
- **Reports**: `exports/reports/*.md`, `exports/reports/*.csv`
- **Snapshots**: `data_lake/members/dt=YYYY-MM-DD/`

---

## 🔎 Reports
- `kpi_YYYY-MM-DD.md` → Mitgliederzahlen + Top-Performer
- `member_health_summary.md` → Advocates vs. At Risk
- `leaderboard_movers.md` → heuristische Movers
- `leaderboard_delta_true.md` → echte Deltas zwischen Snapshots
- `member_health.csv` → Health Scores pro User
- `members.csv` im Data Lake → täglicher Export aller Member-Felder

---

## 🧪 Development
Tests / Smoke:
```powershell
skoolhud --help
python update_all.py
python verify_system.py
```

CI läuft über GitHub Actions (`.github/workflows/ci.yml`).

---

## 🛣️ Fahrplan (Next Steps)
1. **Stabilisieren**
   - Migrations-Skripte für DB (Alembic einführen)  
   - Encoding fix in allen Reports (`encoding="utf-8"`)  

2. **Analytics erweitern**
   - Trend-Reports (7d/30d Health Trend pro Member)  
   - Community Growth Rate (Neuzugänge vs. Abgänge)  
   - Engagement Funnel (aktive % → Post/Kommentar-Rate, wenn Daten vorliegen)

3. **Export & Dashboard**
   - CSV/Parquet-Exports automatisieren  
   - Mini-Dashboard (Streamlit oder statisches HTML mit Charts aus Reports)  

4. **Multi-Tenant Support**
   - `tenants.json` einlesen  
   - Runner für alle Communities laufen lassen  

5. **Deployment**
   - Dockerfile hinzufügen  
   - Optional Cronjob / GitHub Action für Daily Run  

---

## ✅ Quick Verify
```powershell
python verify_system.py
```
Ausgabe zeigt:
- `Members: N (with points_all: X) | LeaderboardSnapshots: Y`
- `MemberDailySnapshot: today > 0`
