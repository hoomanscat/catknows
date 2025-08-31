# DEV CHECKLIST — SkoolHUD

## Before changing anything
- [ ] `git pull origin main --rebase`
- [ ] `python -m pip install -U pip && pip install -e .`
- [ ] `skoolhud --help` (CLI smoke)
- [ ] `skoolhud test-tenant --slug hoomans` (buildId sichtbar)

## Changes
- [ ] Nur Feature-Branch: `git checkout -b feat/<kurzname>`
- [ ] Vorher Interfaces prüfen: `git diff`, Commit-Historie
- [ ] Heuristiken nur in `fetcher.py` anpassen (Headers/Referer/Cookie)
- [ ] Keine Stammdaten mit leeren Werten überschreiben (Normalizer-Regeln)

## Before merge
- [ ] `python update_all.py` lokal OK
- [ ] Agenten laufen: `python .\agents\run_all_agents.py`
- [ ] `exports/reports/*` entstehen (lokal), werden NICHT committed
