<# =========================
   update_skoolhud.ps1
   =========================
   Nutzt die installierte skoolhud-CLI.
   Parameter:
     -Slug   : z.B. hoomans
     -Group  : z.B. hoomans
     -Cookie : (optional) kompletter Cookie-String; wenn leer, wird ./cookie.txt gelesen
#>

param(
  [string]$Slug  = "hoomans",
  [string]$Group = "hoomans",
  [string]$Cookie = ""
)

$ErrorActionPreference = "Stop"
function Stamp { param([string]$msg) Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $msg) -ForegroundColor Cyan }

# 0) In Projektordner wechseln
Set-Location -Path "C:\skool-hud-starter"

# 1) Cookie laden
if (-not $Cookie -or $Cookie.Trim() -eq "") {
  $cookieFile = Join-Path (Get-Location) "cookie.txt"
  if (Test-Path $cookieFile) {
    $Cookie = Get-Content $cookieFile -Raw
    Stamp "Cookie aus cookie.txt geladen."
  } else {
    throw "Kein Cookie übergeben und keine cookie.txt gefunden. Bitte -Cookie setzen ODER cookie.txt anlegen."
  }
}

# 2) Tenant aktualisieren/setzen
Stamp "Tenant updaten…"
skoolhud add-tenant --slug $Slug --group $Group --cookie $Cookie

# 3) Alle Member ziehen (mit Pagination) & normalisieren
Stamp "Members (alle Seiten) abrufen & normalisieren…"
skoolhud fetch-members-all --slug $Slug

# 4) Leaderboards normalisieren (all → 30 → 7)
Stamp "Leaderboards normalisieren…"
# (optional) neueste Leaderboard-RAW zuerst ziehen – falls du sicherstellen willst, dass die Datei aktuell ist:
# skoolhud fetch-leaderboard --slug $Slug

skoolhud normalize-leaderboard --slug $Slug --window all
skoolhud normalize-leaderboard --slug $Slug --window 30
skoolhud normalize-leaderboard --slug $Slug --window 7

# 5) Schnell-Report (Python Inline)
Stamp "DB-Report erzeugen…"
$py = @'
from skoolhud.db import SessionLocal
from skoolhud.models import Member

s = SessionLocal()

total = s.query(Member).count()
with_any = s.query(Member).filter(
    (Member.points_all  != None) |
    (Member.points_30d  != None) |
    (Member.points_7d   != None)
).count()

print(f"Members total: {total}")
print(f"Members mit irgendeinem Leaderboard-Feld: {with_any}")

def top(window, points_attr, rank_attr):
    print(f"\nTop 10 ({window}):")
    rows = (
        s.query(Member.name, getattr(Member, points_attr), getattr(Member, rank_attr))
         .filter(getattr(Member, points_attr) != None)
         .order_by(getattr(Member, points_attr).desc())
         .limit(10)
         .all()
    )
    if not rows:
        print("  (keine Daten)")
        return
    for n,p,r in rows:
        r_disp = "-" if r is None else r
        p_disp = "-" if p is None else p
        print(f"{str(r_disp).rjust(3)} | {str(p_disp).rjust(5)} | {n}")

top("ALL",  "points_all",  "rank_all")
top("30d",  "points_30d",  "rank_30d")
top("7d",   "points_7d",   "rank_7d")
'@

$tf = Join-Path $env:TEMP "skhud_daily_report.py"
$py | Set-Content $tf -Encoding UTF8
python $tf

Stamp "Fertig. DB ist auf tagesaktuellem Stand."
