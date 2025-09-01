# skoolhud/cleanup_repo.py
from __future__ import annotations
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # Projektroot
EXPORTS = ROOT / "exports" / "reports"
DATALAKE = ROOT / "data_lake"
TENANTS_FILE = ROOT / "tenants.json"

def load_tenants() -> list[str]:
    if TENANTS_FILE.exists():
        try:
            data = json.loads(TENANTS_FILE.read_text(encoding="utf-8"))
            # Erlaubt entweder {"tenants":[{"slug":"..."}, ...]} ODER [{"slug":"..."}]
            if isinstance(data, dict) and "tenants" in data:
                return [t["slug"] for t in data["tenants"] if "slug" in t]
            if isinstance(data, list):
                return [t["slug"] for t in data if isinstance(t, dict) and "slug" in t]
        except Exception:
            pass
    # Fallback: Wenn keine tenants.json → aus DB/Repo können wir hier nicht lesen.
    # Dann versuchen wir, vorhandene Strukturen zu mappen:
    slugs = set()
    # existierende tenantisierte Ordner erkennen
    if EXPORTS.exists():
        for p in EXPORTS.iterdir():
            if p.is_dir() and p.name not in (".gitkeep",):
                slugs.add(p.name)
    if (DATALAKE).exists():
        for p in DATALAKE.iterdir():
            if p.is_dir() and p.name not in ("members",):
                slugs.add(p.name)
    # letzter Fallback: gängigster Dev-Slug
    return sorted(slugs) or ["hoomans"]

def ensure_dirs(slugs: list[str]) -> None:
    for slug in slugs:
        (EXPORTS / slug).mkdir(parents=True, exist_ok=True)
        (DATALAKE / slug / "members").mkdir(parents=True, exist_ok=True)
    print("OK: ensured folder structure for tenants:", ", ".join(slugs))

def _move_file(src: Path, dst: Path) -> None:
    """Verschiebt sicher, ohne zu überschreiben (fügt Suffix .1, .2 ... an)."""
    target = dst
    if target.exists():
        i = 1
        stem, suffix = target.stem, target.suffix
        while target.exists():
            target = target.with_name(f"{stem}.{i}{suffix}")
            i += 1
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(target))

def tenantize_reports(slugs: list[str]) -> None:
    # untenantisierte Reports (direkt in exports/reports) in den "best guess" Tenant verschieben
    # Heuristik: wenn genau 1 Tenant → dahin; sonst liegen lassen und melden.
    dest_slug = slugs[0] if len(slugs) == 1 else None

    if not EXPORTS.exists():
        return

    moved = 0
    for pattern in ("*.md", "*.csv", "*.parquet"):
        for f in EXPORTS.glob(pattern):
            # bereits tenantisiert?
            if f.parent != EXPORTS:
                continue
            if f.name == ".gitkeep":
                continue
            if dest_slug is None:
                print(f"SKIP (multi-tenant): {f} cannot guess destination tenant")
                continue
            target = EXPORTS / dest_slug / f.name
            print(f"MOVE report: {f} -> {target}")
            _move_file(f, target)
            moved += 1

    if moved == 0:
        print("OK: no untenantized reports to move")
    else:
        print(f"OK: moved {moved} reports into exports/reports/{dest_slug}/")

def tenantize_datalake(slugs: list[str]) -> None:
    # untenantisierter Data Lake: data_lake/members → data_lake/<slug>/members
    src = DATALAKE / "members"
    if not src.exists():
        print("OK: no untenantized data_lake/members")
        return
    dest_slug = slugs[0] if len(slugs) == 1 else None
    if dest_slug is None:
        print(f"SKIP (multi-tenant): {src} cannot guess destination tenant")
        return

    dst_root = DATALAKE / dest_slug / "members"
    dst_root.mkdir(parents=True, exist_ok=True)

    moved = 0
    for item in src.iterdir():
        target = dst_root / item.name
        print(f"MOVE datalake: {item} -> {target}")
        if item.is_dir():
            # verschiebe ganzen Ordner (z. B. dt=YYYY-MM-DD)
            if target.exists():
                # merge: move Inhalt rein
                for sub in item.iterdir():
                    _move_file(sub, target / sub.name)
                item.rmdir()
            else:
                shutil.move(str(item), str(target))
        else:
            _move_file(item, target)
        moved += 1

    # leeren src-Ordner entfernen
    try:
        src.rmdir()
    except OSError:
        pass

    print(f"OK: moved {moved} items into data_lake/{dest_slug}/members/")

def clean_empty_shells(slugs: list[str]) -> None:
    # lösche leere Platzhalter in exports/reports (außer tenantisierte)
    for p in EXPORTS.iterdir() if EXPORTS.exists() else []:
        if p.is_file() and p.name != ".gitkeep":
            continue
        if p.is_dir() and p.name not in slugs:
            # wenn leer, löschen
            try:
                next(p.iterdir())
            except StopIteration:
                try:
                    p.rmdir()
                    print(f"RM empty folder: {p}")
                except OSError:
                    pass

def main():
    slugs = load_tenants()
    print("Tenants detected:", ", ".join(slugs))
    ensure_dirs(slugs)
    tenantize_reports(slugs)
    tenantize_datalake(slugs)
    clean_empty_shells(slugs)
    print("Cleanup finished.")

if __name__ == "__main__":
    main()
