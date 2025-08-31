# update_all.ps1
# Hält die SkoolHUD-Datenbank auf dem neuesten Stand

Write-Host "==== SkoolHUD Update gestartet ====" -ForegroundColor Cyan

# 1. Prüfen ob cookie.txt existiert
$cookiePath = Join-Path $PSScriptRoot "cookie.txt"
if (-Not (Test-Path $cookiePath)) {
    Write-Host "FEHLER: cookie.txt fehlt in $cookiePath" -ForegroundColor Red
    exit 1
}

# 2. Tenant-Infos
$slug = "hoomans"

# 3. Mitglieder abrufen (alle Seiten)
Write-Host ">>> Fetch members (alle Seiten)..." -ForegroundColor Yellow
skoolhud fetch-members-all --slug $slug

# 4. Leaderboards abrufen
Write-Host ">>> Fetch leaderboard RAW..." -ForegroundColor Yellow
skoolhud fetch-leaderboard --slug $slug

# 5. Normalisieren für alle Fenster
foreach ($w in "all","30","7") {
    Write-Host ">>> Normalisiere Leaderboard (window=$w)..." -ForegroundColor Yellow
    skoolhud normalize-leaderboard --slug $slug --window $w
}

# 6. Status-Report
Write-Host ">>> Mitglieder-Count prüfen..." -ForegroundColor Yellow
skoolhud count-members --slug $slug

Write-Host "==== SkoolHUD Update fertig ====" -ForegroundColor Green
