import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Member, RawSnapshot, LeaderboardSnapshot
from .utils import get_in, to_utc_str, find_member_entries

# -------------------- Feld-Mapping für Member-Normalisierung --------------------
FIELDS = {
    "user_id": "user.id",
    "member_id": "member.id",
    "handle": "user.name",
    "first_name": "user.firstName",
    "last_name": "user.lastName",
    "name": "user.firstName|member.firstName",
    "email": "member.searchAnswer|member.metadata.survey.answer|user.email",
    "joined_date": "member.createdAt|user.createdAt",
    "approved_at": "member.approvedAt",
    "role": "member.role",
    "bio": "user.metadata.bio",
    "location": "user.metadata.location|member.metadata.requestLocation",
    "link_website": "user.metadata.linkWebsite",
    "link_instagram": "user.metadata.linkInstagram",
    "link_linkedin": "user.metadata.linkLinkedin",
    "link_facebook": "user.metadata.linkFacebook",
    "link_youtube": "user.metadata.linkYoutube",
    "last_active_raw": "member.lastOffline|user.metadata.lastOffline",
    "updated_at_raw": "user.updatedAt",
}


# -------------------- Upsert-Helfer --------------------
def upsert_member(session: Session, tenant: str, record: dict, build_id: str):
    # leere E-Mails als None behandeln
    if record.get("email") in ("", None):
        record["email"] = None

    # 1) Erst nach user_id suchen (stabil & eindeutig)
    existing = None
    if record.get("user_id"):
        existing = session.execute(
            select(Member).where(
                Member.tenant == tenant,
                Member.user_id == record.get("user_id"),
            )
        ).scalar_one_or_none()

    # 2) Falls nicht gefunden, nach email suchen (kann mehrfach vorkommen)
    if not existing and record.get("email"):
        existing = session.execute(
            select(Member).where(
                Member.tenant == tenant,
                Member.email == record.get("email"),
            )
        ).scalar_one_or_none()

    if existing:
        # Merge-Policy (Emails können gleich sein, user_id ist Master)
        for k, v in record.items():
            if v in (None, "", []):
                continue  # leere Werte überschreiben nicht
            if k in ("name", "email", "joined_date"):
                # Stammdaten aus erster Quelle nicht blind überschreiben
                continue
            if k == "last_active_raw":
                cand = to_utc_str(v)
                old = to_utc_str(existing.last_active_raw) if existing.last_active_raw else None
                if not old or (cand and cand > old):
                    existing.last_active_raw = v
                    existing.last_active_at_utc = cand
                continue
            setattr(existing, k, v)
        existing.source_last_update = "members"
        existing.source_build_id = build_id
        session.add(existing)
        return "updated"
    else:
        m = Member(tenant=tenant, **record)
        m.last_active_at_utc = to_utc_str(record.get("last_active_raw"))
        m.source_last_update = "members"
        m.source_build_id = build_id
        session.add(m)
        # wichtig: flush, damit Folgeläufe in derselben Session den Datensatz sehen
        session.flush()
        return "inserted"


# -------------------- Members normalisieren --------------------
def normalize_members_json(session: Session, tenant: str, build_id: str, raw_json: dict, raw_path: str):
    session.add(
        RawSnapshot(
            tenant=tenant,
            route="members",
            build_id=build_id,
            path=raw_path,
            meta={"size": len(json.dumps(raw_json))},
        )
    )

    entries = list(find_member_entries(raw_json))
    if not entries:
        # Fallback: rohe Hinweise ausgeben
        try:
            top_keys = list(raw_json.keys())[:20]
            print(f"[DEBUG] Keine direkten Member-Einträge gefunden. Top-Level-Keys: {top_keys}")
        except Exception:
            pass

    inserted = updated = 0
    for node in entries:
        rec = {}
        # 1) Standardfelder mappen
        for field, path in FIELDS.items():
            rec[field] = get_in(node, path)

        # 2) spData: JSON-String mit All-Time Punkten & Level
        #    Beispiel: {"pts":2269,"lv":7,"pcl":2015,"pnl":8015,"role":3}
        sp_raw = get_in(node, "user.metadata.spData")
        if sp_raw:
            try:
                sp = json.loads(sp_raw) if isinstance(sp_raw, str) else sp_raw
                if isinstance(sp, dict):
                    # Level nur setzen, wenn noch nicht vorhanden
                    if sp.get("lv") is not None:
                        rec.setdefault("level_current", sp.get("lv"))
                    # All-time Punkte als aktueller Stand, nur setzen wenn noch leer
                    if sp.get("pts") is not None:
                        rec.setdefault("points_all", sp.get("pts"))
            except Exception:
                # falls mal kaputtes JSON kommt, ignorieren
                pass

        # 3) Upsert
        status = upsert_member(session, tenant, rec, build_id)
        if status == "inserted":
            inserted += 1
        else:
            updated += 1

    return {"inserted": inserted, "updated": updated, "scanned_nodes": len(entries)}


from .models import Member, LeaderboardSnapshot
from datetime import datetime
from .utils import get_in

def normalize_leaderboard_json(session, tenant: str, build_id: str, data: dict, fpath: str, window: str):
    """
    Normalisiert Leaderboard-JSON.
    Unterstützt sowohl:
      - pageProps.s.allTime/past7Days/past30Days.users
      - pageProps.allTime/past7Days/past30Days.users
    """
    if not data or "pageProps" not in data:
        return {"inserted": 0, "updated": 0, "scanned": 0}

    # gewünschtes Fenster → Bucket-Namen im JSON
    key_map = {"all": "allTime", "7": "past7Days", "30": "past30Days"}
    bucket_key = key_map.get(window)
    if not bucket_key:
        return {"inserted": 0, "updated": 0, "scanned": 0}

    # Kandidaten-Pfade in Reihenfolge der Wahrscheinlichkeit
    candidate_paths = [
        f"pageProps.s.{bucket_key}.users",
        f"pageProps.{bucket_key}.users",
        f"pageProps.{bucket_key}",  # falls direkt eine Liste ist
    ]

    entries = None
    for p in candidate_paths:
        val = get_in(data, p)
        if isinstance(val, list) and (not val or isinstance(val[0], dict)):
            entries = val
            break

    if not entries:
        # letzter Fallback: suche irgendeine List[dict] unter pageProps, die nach Leaderboard aussieht
        page = data.get("pageProps", {})
        for v in page.values():
            if isinstance(v, dict) and isinstance(v.get("users"), list):
                entries = v["users"]
                break

    if not entries:
        # Nichts gefunden → sauber aussteigen
        return {"inserted": 0, "updated": 0, "scanned": 0}

    inserted = updated = scanned = 0

    for e in entries:
        if not isinstance(e, dict):
            continue
        scanned += 1

        user = e.get("user") or {}
        user_id = str(e.get("userId") or user.get("id") or "")  # beides absichern
        if not user_id:
            continue

        points = e.get("points")
        rank = e.get("rank")

        # Member aktualisieren (nur wenn vorhanden)
        m = session.query(Member).filter(
            Member.tenant == tenant,
            Member.user_id == user_id
        ).one_or_none()

        if m:
            if window == "7":
                m.points_7d, m.rank_7d = points, rank
            elif window == "30":
                m.points_30d, m.rank_30d = points, rank
            elif window == "all":
                m.points_all, m.rank_all = points, rank
            updated += 1

        # Snapshot erfassen
        snap = LeaderboardSnapshot(
            tenant=tenant,
            user_id=user_id,
            window=window,
            points=points,
            rank=rank,
            captured_at=datetime.utcnow(),
            source_file=fpath,
            build_id=build_id,
        )
        session.add(snap)
        inserted += 1

    return {"inserted": inserted, "updated": updated, "scanned": scanned}
