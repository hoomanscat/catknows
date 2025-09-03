import typer, sys, json, time
from sqlalchemy import select
from .db import Base, engine, SessionLocal
from .models import Tenant
from .config import settings
from .fetcher import SkoolFetcher
from .normalizer import normalize_members_json
from skoolhud.vector.ingest import ingest_members_to_vector as ingest_vectors
from skoolhud.vector.query import search as search_vectors

app = typer.Typer(help="Skool HUD CLI")

@app.command()
def init_db():
    # Create SQLite tables.
    Base.metadata.create_all(bind=engine)
    typer.echo("DB initialisiert: tables created.")

@app.command()
def count_members(slug: str = typer.Option(..., help="Tenant Slug")):
    """Zähle wie viele Member für einen Tenant in der DB stehen."""
    from .models import Member
    with SessionLocal() as s:
        t = s.execute(select(Tenant).where(Tenant.slug==slug)).scalar_one_or_none()
        if not t:
            typer.echo("Unbekannter Tenant. Erst add-tenant ausführen.")
            raise typer.Exit(code=1)
        count = s.query(Member).filter(Member.tenant==slug).count()
        typer.echo(f"Tenant '{slug}' hat {count} Member in der DB.")

@app.command("vectors-ingest")
def vectors_ingest(tenant: str = typer.Option("hoomans", "--tenant")):
    """Vektor-Store mit Reports/CSVs füttern."""
    import os
    os.environ["TENANT"] = tenant
    ingest_vectors(tenant)

@app.command("vectors-search")
def vectors_search(
    query: str = typer.Argument(...),
    tenant: str = typer.Option("hoomans", "--tenant"),
    k: int = typer.Option(5, "--k"),
):
    """Semantische Suche im Vektor-Store (tenant-isoliert)."""
    search_vectors(query=query, tenant=tenant, k=k)

@app.command()
def add_tenant(slug: str = typer.Option(..., help="Kurzname, z. B. 'hoomans'"),
               group: str = typer.Option(..., help="Skool Gruppenpfad, z. B. 'the-alley'"),
               cookie: str = typer.Option(..., help="Kompletter Cookie Header (aus DevTools)")):
    with SessionLocal() as s:
        exists = s.execute(select(Tenant).where(Tenant.slug==slug)).scalar_one_or_none()
        if exists:
            typer.echo("Slug existiert schon. Aktualisiere Cookie/Group.")
            exists.group_path = group
            exists.cookie_header = cookie
            s.add(exists)
        else:
            s.add(Tenant(slug=slug, group_path=group, cookie_header=cookie))
        s.commit()
        typer.echo(f"Tenant '{slug}' gespeichert.")

@app.command()
def test_tenant(slug: str = typer.Option(..., help="Tenant Slug, z. B. 'hoomans'")):
    with SessionLocal() as s:
        t = s.execute(select(Tenant).where(Tenant.slug==slug)).scalar_one_or_none()
        if not t:
            typer.echo("Unbekannter Tenant. Erst add-tenant ausführen.")
            raise typer.Exit(code=1)
        f = SkoolFetcher(settings.base_url, t.group_path, t.cookie_header, t.slug)
        try:
            build = f.discover_build_id()
            typer.echo(f"OK: buildId gefunden: {build}")
        except Exception as e:
            typer.echo(f"FEHLER: {e}")
            raise typer.Exit(code=1)

@app.command()
def fetch_members(slug: str = typer.Option(..., help="Tenant Slug")):
    with SessionLocal() as s:
        t = s.execute(select(Tenant).where(Tenant.slug==slug)).scalar_one_or_none()
        if not t:
            typer.echo("Unbekannter Tenant. Erst add-tenant ausführen.")
            raise typer.Exit(code=1)
        f = SkoolFetcher(settings.base_url, t.group_path, t.cookie_header, t.slug)
        build = f.discover_build_id()
        typer.echo(f"buildId: {build} – warte {settings.min_interval_seconds}s (Rate-Limit)...")
        time.sleep(settings.min_interval_seconds)
        data, route, fpath = f.fetch_members_json(build)
        typer.echo(f"RAW gespeichert: {fpath}")
        res = normalize_members_json(s, t.slug, build, data, fpath)
        s.commit()
        typer.echo(f"Normalisiert: inserted={res['inserted']}, updated={res['updated']} (scanned_nodes={res['scanned_nodes']})")

@app.command()
def fetch_members_all(slug: str = typer.Option(..., help="Tenant Slug"),
                      max_pages: int = typer.Option(20, help="Sicherheitslimit (z. B. 20)"),
                      min_wait: int = typer.Option(11, help="Min. Pause zwischen Seiten (Sek.)"),
                      max_wait: int = typer.Option(24, help="Max. Pause zwischen Seiten (Sek.)")):
    """
    Holt alle Members-Seiten mit dem bestätigten Param 'p=1..N' und normalisiert sie.
    Stoppt bei 0 neuen IDs, weniger als 30 Einträgen (letzte Seite), wiederholter Route oder nach max_pages.
    """
    import random, time
    from .utils import get_in

    with SessionLocal() as s:
        t = s.execute(select(Tenant).where(Tenant.slug==slug)).scalar_one_or_none()
        if not t:
            typer.echo("Unbekannter Tenant. Erst add-tenant ausführen.")
            raise typer.Exit(code=1)

        f = SkoolFetcher(settings.base_url, t.group_path, t.cookie_header, t.slug)
        build = f.discover_build_id()
        typer.echo(f"buildId: {build} – starte Pagination mit Param 'p'…")

        total_inserted = 0
        total_updated = 0
        page = 1
        seen_routes = set()
        seen_ids = set()

        while page <= max_pages:
            params = None if page == 1 else {"p": page}
            typer.echo(f"Seite {page} abrufen… (params={params})")
            data, route, fpath = f.fetch_members_json_with_params(build, params)

            # Doppel-Route-Schutz
            if route in seen_routes:
                typer.echo(f"Stoppe: Route wiederholt sich ({route}).")
                break
            seen_routes.add(route)

            # Einträge zählen & neue IDs bestimmen
            users = get_in(data, "pageProps.users") or []
            entries_count = len(users) if isinstance(users, list) else 0
            new_ids = set()
            for u in (users if isinstance(users, list) else []):
                uid = get_in(u, "user.id") or u.get("id")
                if uid and str(uid) not in seen_ids:
                    new_ids.add(str(uid))

            # Normalisieren
            # build ist direkt darüber definiert: build = f.discover_build_id()
            build_id_val = build if 'build' in locals() and build is not None else ""
            res = normalize_members_json(s, t.slug, build if build is not None else "", data, fpath)
            s.commit()
            total_inserted += res["inserted"]
            total_updated += res["updated"]

            typer.echo(f"  -> RAW: {fpath}")
            typer.echo(f"  -> Normalisiert: +{res['inserted']}/~{res['updated']} (scanned={res['scanned_nodes']}, entries={entries_count}, neueIDs={len(new_ids)})")

            # Abbruchkriterien
            if entries_count == 0:
                typer.echo("Stoppe: 0 Einträge auf dieser Seite.")
                break
            if len(new_ids) == 0:
                typer.echo("Stoppe: keine neuen IDs mehr (wir sind durch).")
                break
            if entries_count < 30:
                typer.echo("Stoppe: letzte Seite erkannt (weniger als 30 Einträge).")
                break

            # nächste Seite
            seen_ids.update(new_ids)
            page += 1

            # Pause (zufällig 11–24s)
            wait_s = random.randint(min_wait, max_wait)
            typer.echo(f"Warte {wait_s}s (zufällig) vor nächster Seite…")
            time.sleep(wait_s)

        typer.echo(f"FERTIG. Gesamt: inserted={total_inserted}, updated={total_updated}.")

        # Nach erfolgreichem Fetch: Vector-Ingest für diesen Tenant
        try:
            typer.echo(f"Starte automatischen Vector-Ingest für Tenant '{slug}'...")
            ingest_members_to_vector(slug, collection_name="skool_members")
            typer.echo("Vector-Ingest abgeschlossen.")
        except Exception as e:
            typer.echo(f"Fehler beim Vector-Ingest: {e}")



# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# INSPECTOR COMMAND – MUSS ÜBER DEM MAIN-BLOCK STEHEN
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
@app.command()
def inspect_members_raw(slug: str = typer.Option(..., help="Tenant Slug")):
    """
    Inspektor: zeigt die neueste RAW-JSON (members) und rät:
      - Wo die Members-Liste steckt (Pfad + Länge)
      - Welche Pagination-Hinweise es gibt (cursor/next/page)
    """
    from .utils import latest_raw_file, guess_members_arrays, guess_pagination_hints
    import orjson

    # RAW-Datei finden
    fpath = latest_raw_file("exports/raw", slug, route_keyword="members")
    if not fpath:
        typer.echo("Keine members-RAW-Datei gefunden. Erst 'fetch-members' ausführen.")
        raise typer.Exit(code=1)

    # JSON laden
    try:
        with open(fpath, "rb") as f:
            data = orjson.loads(f.read())
    except Exception as e:
        typer.echo(f"Fehler beim Lesen von {fpath}: {e}")
        raise typer.Exit(code=1)

    typer.echo(f"RAW-Datei: {fpath}")

    # Kandidaten-Liste(n) erkennen
    arrays = guess_members_arrays(data)
    if arrays:
        typer.echo("Mögliche Members-Listen (Pfad → Länge):")
        for p, ln in arrays[:5]:
            typer.echo(f"  - {p}  →  {ln}")
    else:
        typer.echo("Keine offensichtliche Members-Liste gefunden.")

    # Pagination-Hinweise zeigen
    hints = guess_pagination_hints(data)
    if hints:
        typer.echo("Mögliche Pagination-Hinweise:")
        for p, v in hints[:10]:
            typer.echo(f"  - {p} = {v}")
    else:
        typer.echo("Keine offensichtlichen Pagination-Hinweise gefunden.")

    typer.echo("Tipp: Kopiere mir die obigen Pfade, dann baue ich 'fetch-members-all' exakt passend.")

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

@app.command()
def probe_members_pages(slug: str = typer.Option(..., help="Tenant Slug"),
                        target_page: int = typer.Option(2, help="Welche Seite prüfen (z.B. 2)"),
                        min_wait: int = typer.Option(1),
                        max_wait: int = typer.Option(2)):
    """
    Probiert verschiedene Query-Param-Varianten aus, um Seite target_page zu laden.
    Zeigt an, welche Variante wirklich eine neue Seite bringt.
    """
    import random, time
    from .utils import get_in

    variants = [
        lambda p: {"page": p},
        lambda p: {"pageNum": p},
        lambda p: {"p": p},
        lambda p: {"index": p},
        lambda p: {"offset": (p-1)*30},
        lambda p: {"skip": (p-1)*30},
        lambda p: {"start": (p-1)*30},
    ]

    with SessionLocal() as s:
        t = s.execute(select(Tenant).where(Tenant.slug==slug)).scalar_one_or_none()
        if not t:
            typer.echo("Unbekannter Tenant. Erst add-tenant ausführen.")
            raise typer.Exit(code=1)

        f = SkoolFetcher(settings.base_url, t.group_path, t.cookie_header, t.slug)
        build = f.discover_build_id()

        # Seite 1 holen
        base1, _, _ = f.fetch_members_json_with_params(build, None)
        ref_ids = set()
        users1 = get_in(base1, "pageProps.users") or []
        for u in (users1 if isinstance(users1, list) else []):
            uid = get_in(u, "user.id") or u.get("id")
            if uid: ref_ids.add(str(uid))

        typer.echo(f"Referenz: users={len(users1)}")

        # Varianten testen
        for maker in variants:
            params = maker(target_page)
            data, route, _ = f.fetch_members_json_with_params(build, params)
            users = get_in(data, "pageProps.users") or []
            ids = set()
            for u in (users if isinstance(users, list) else []):
                uid = get_in(u, "user.id") or u.get("id")
                if uid: ids.add(str(uid))
            diff = "DIFF" if ids and ids != ref_ids else "same"
            typer.echo(f"Test {params} -> users={len(users)}, compare={diff}")
            time.sleep(random.randint(min_wait, max_wait))

@app.command()
def fetch_leaderboard(
    slug: str = typer.Option(..., help="Tenant Slug"),
    window: str = typer.Option(None, help="Optional: 7 | 30 | all. Wenn leer: holt komplettes Leaderboard.")
):
    """
    Holt Leaderboard-JSON (direkte Route /leaderboards.json) und speichert RAW.
    """
    from sqlalchemy import select
    with SessionLocal() as s:
        t = s.execute(select(Tenant).where(Tenant.slug==slug)).scalar_one_or_none()
        if not t:
            typer.echo("Unbekannter Tenant. Erst add-tenant ausführen.")
            raise typer.Exit(code=1)

        f = SkoolFetcher(settings.base_url, t.group_path, t.cookie_header, t.slug)

        # buildId nur als Log (nicht an fetch_leaderboard_json übergeben!)
        build = f.discover_build_id()
        typer.echo(f"buildId: {build} – hole Leaderboard…")

        if window:
            data, route, fpath = f.fetch_leaderboard_json(window=window)
            typer.echo(f"  -> RAW gespeichert: {fpath} (window={window})")
        else:
            # alles in einem Rutsch (Server liefert i.d.R. alle Fenster in einem JSON)
            data, route, fpath = f.fetch_leaderboard_json()
            typer.echo(f"  -> RAW gespeichert: {fpath}")

        s.commit()

@app.command()
def inspect_leaderboard_raw(slug: str = typer.Option(..., help="Tenant Slug")):
    """
    Zeigt die neueste RAW-Leaderboard-JSON und verrät, wo die Datenblöcke stecken.
    """
    from .utils import latest_raw_file, deep_iter
    import orjson

    fpath = latest_raw_file("exports/raw", slug, route_keyword="leaderboards")
    if not fpath:
        typer.echo("Keine Leaderboard-RAW-Datei gefunden. Erst 'fetch-leaderboard' ausführen.")
        raise typer.Exit(code=1)

    with open(fpath, "rb") as f:
        data = orjson.loads(f.read())
    typer.echo(f"RAW-Datei: {fpath}")

    found = 0
    for node in deep_iter(data):
        if isinstance(node, dict):
            keys = set(node.keys())
            if any(k in keys for k in ["points", "rank", "userId", "user", "member"]):
                typer.echo(f"- Dict mit Keys: {list(keys)[:10]}")
                found += 1
                if found >= 20:
                    break

    if found == 0:
        typer.echo("Keine offensichtlichen Leaderboard-Einträge gefunden.")

@app.command()
def normalize_leaderboard(
    slug: str = typer.Option(..., help="Tenant Slug"),
    window: str = typer.Option(..., help="Fenster: 7, 30 oder all")
):
    """
    Normalisiert die letzte Leaderboard-RAW-Datei in DB + Snapshots.
    """
    from .utils import latest_raw_file
    from .normalizer import normalize_leaderboard_json
    import orjson
    from .models import Tenant

    with SessionLocal() as s:
        t = s.execute(select(Tenant).where(Tenant.slug == slug)).scalar_one_or_none()
        if not t:
            typer.echo("Unbekannter Tenant. Erst add-tenant ausführen.")
            raise typer.Exit(code=1)

        fpath = latest_raw_file("exports/raw", slug, route_keyword="leaderboards")
        if not fpath:
            typer.echo("Keine Leaderboard-RAW-Datei gefunden. Erst 'fetch-leaderboard' ausführen.")
            raise typer.Exit(code=1)

        with open(fpath, "rb") as f:
            data = orjson.loads(f.read())

        # Fix: build is not defined here, use a static/manual value or pass empty string
        res = normalize_leaderboard_json(s, t.slug, "manual", data, fpath, window)
        s.commit()
        typer.echo(
            f"Leaderboard normalisiert (window={window}): "
            f"inserted={res['inserted']}, updated={res['updated']}, scanned={res['scanned']}"
        )

@app.command("fetch-leaderboard-all")
def fetch_leaderboard_all(slug: str, window: str = typer.Option("all", help="all|30|7"), limit: int = 100):
    from .db import SessionLocal
    from .models import Tenant
    from .normalizer import normalize_leaderboard_json

    s = SessionLocal()
    t = s.query(Tenant).filter(Tenant.slug == slug).one_or_none()
    if not t:
        typer.echo("Unbekannter Tenant. Erst add-tenant ausführen."); raise typer.Exit(1)

    f = SkoolFetcher(settings.base_url, t.group_path, t.cookie_header, slug)

    offset = 0
    total_ins = total_upd = total_scanned = 0
    while True:
        data, route, fpath = f.fetch_leaderboard_page(window=window, offset=offset, limit=limit)
        res = normalize_leaderboard_json(s, slug, build_id="", data=data, fpath=fpath, window=window)
        s.commit()
        typer.echo(f"[{window}] offset={offset} -> inserted={res['inserted']}, updated={res['updated']}, scanned={res['scanned']}")
        total_ins += res["inserted"]; total_upd += res["updated"]; total_scanned += res["scanned"]

        # Break: weniger als limit Einträge → letzte Seite
        try:
            users = (data.get("pageProps", {}).get("s", {})
                           .get({"all":"allTime","30":"past30Days","7":"past7Days"}[window], {})
                           .get("users", [])) or []
        except Exception:
            users = []
        if len(users) < limit:
            break
        offset += limit

    typer.echo(f"FERTIG [{window}]. Summe inserted={total_ins}, updated={total_upd}, scanned={total_scanned}")

import typer
from datetime import datetime, timezone, date
from typing import Optional

def _to_dt_utc(x):
    if not x:
        return None
    if isinstance(x, datetime):
        return x.astimezone(timezone.utc) if x.tzinfo else x.replace(tzinfo=timezone.utc)
    s = str(x).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

@app.command("snapshot-members-daily")
def snapshot_members_daily(slug: str, day_str: Optional[str] = None):
    """
    Schreibt für alle Member einen Tages-Snapshot in member_daily_snapshot.
    day_str: YYYY-MM-DD (optional), Default = heute (UTC).
    """
    from skoolhud.db import SessionLocal
    from skoolhud.models import Member, MemberDailySnapshot
    from skoolhud.utils.schema_utils import validate_json
    import json
    from pathlib import Path

    # load member_daily_snapshot schema if available
    SCHEMA_PATH = Path(__file__).resolve().parents[1] / "project-status" / "schemas" / "member_daily_snapshot.schema.json"
    _MDS_SCHEMA = None
    try:
        _MDS_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except Exception:
        _MDS_SCHEMA = None

    s = SessionLocal()
    try:
        # Fix: Argument missing for parameter "tenant"
        if day_str is not None:
            y, m, d = map(int, day_str.split("-"))
            the_day = date(y, m, d)
        else:
            the_day = datetime.now(timezone.utc).date()

        now = datetime.now(timezone.utc)
        inserted = updated = 0

        members = s.query(Member).all()
        for m in members:
            tenant_val = getattr(m, "tenant", None) or slug
            row = (s.query(MemberDailySnapshot)
                    .filter(MemberDailySnapshot.tenant == tenant_val)
                    .filter(MemberDailySnapshot.user_id == m.user_id)
                    .filter(MemberDailySnapshot.day == the_day)
                    .one_or_none())

            values = dict(
                tenant=tenant_val,
                user_id=m.user_id,
                day=the_day,
                level_current=m.level_current,
                points_7d=m.points_7d,
                points_30d=m.points_30d,
                points_all=m.points_all,
                rank_7d=m.rank_7d,
                rank_30d=m.rank_30d,
                rank_all=m.rank_all,
                last_active_at_utc=_to_dt_utc(m.last_active_at_utc),
                captured_at=now,
            )

            # validate minimal snapshot dict against schema if available
            if _MDS_SCHEMA is not None:
                from datetime import date as _date, datetime as _dt
                the_day_val = values.get("day")
                if isinstance(the_day_val, (_date, _dt)):
                    day_iso = the_day_val.isoformat()
                elif isinstance(the_day_val, str):
                    day_iso = the_day_val
                else:
                    day_iso = None
                minimal = {"tenant": values.get("tenant"), "user_id": str(values.get("user_id")), "day": day_iso, "points_7d": values.get("points_7d"), "points_30d": values.get("points_30d"), "points_all": values.get("points_all")}
                ok, err = validate_json(minimal, _MDS_SCHEMA)
                if not ok:
                    print(f"MemberDailySnapshot schema validation failed for user {values.get('user_id')}: {err}")

            if row is None:
                s.add(MemberDailySnapshot(**values))
                inserted += 1
            else:
                for k, v in values.items():
                    setattr(row, k, v)
                updated += 1

        s.commit()
        typer.echo(f"member_daily_snapshot: inserted={inserted} updated={updated} day={the_day}")
    finally:
        s.close()
# --- NEU: Vector CLI Commands (am Ende der Datei oder bei den anderen Typer-Kommandos) ---
import typer
from skoolhud.vector.ingest import ingest_members_to_vector
from skoolhud.vector.db import get_client, get_or_create_collection, similarity_search

app = typer.Typer(add_completion=False) if 'app' not in globals() else app

@app.command("vector-ingest")
def vector_ingest(slug: str = typer.Argument(...), collection: str = typer.Option("skool_members", help="Chroma Collection Name")):
    """Ingest aller Members eines Tenants in den Vector Store (mit Embeddings)."""
    ingest_members_to_vector(slug, collection_name=collection)

@app.command("vector-search")
def vector_search(query: str = typer.Argument(...), slug: str = typer.Option(None, help="Optional: Tenant-Filter"), top_k: int = typer.Option(5, help="Anzahl Treffer")):
    """Semantische Suche im Vector Store."""
    client = get_client()
    col = get_or_create_collection(client, "skool_members")
    where = {"tenant": slug} if slug else None
    res = similarity_search(col, query, n_results=top_k, where=where)
    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]]) or [[]]
    docs = docs[0] if isinstance(docs, list) else []
    metas = res.get("metadatas", [[]]) or [[]]
    metas = metas[0] if isinstance(metas, list) else []
    for i, (id_, doc, meta) in enumerate(zip(ids, docs, metas), start=1):
        print(f"{i}. {meta.get('name','')} — user_id={meta.get('user_id','')} — points_all={meta.get('points_all',0)}")
        doc_short = doc[:180].replace('\n',' ')
        print(f"   {doc_short}{'...' if len(doc)>180 else ''}")
