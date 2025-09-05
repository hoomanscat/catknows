from __future__ import annotations
from typing import List, Dict
from skoolhud.config import get_tenant_slug

# Prefer the higher-level vector_search from ai.tools which returns structured hits
try:
    from skoolhud.ai.tools import vector_search as _vector_search
except Exception:
    _vector_search = None
    try:
        from skoolhud.vector.query import search as _legacy_search
    except Exception:
        _legacy_search = None


def find_experts(topic: str, tenant: str | None = None, k: int = 3) -> List[Dict]:
    """Return top-k member docs from skool_members collection with simple rationale.

    Returns an empty list if no search implementation is available.
    """
    hits = None
    resolved = get_tenant_slug(tenant)

    if _vector_search:
        try:
            hits = _vector_search(topic, tenant=resolved, k=k)
        except Exception:
            hits = None
    elif _legacy_search:
        try:
            # legacy search prints results and returns None; guard against that
            res = _legacy_search(query=topic, tenant=resolved, k=k, collection_name="skool_members")
            hits = res
        except Exception:
            hits = None

    if not hits:
        return []

    out = []
    for h in hits[:k]:
        meta = h.get('meta') if isinstance(h, dict) else {}
        name = (meta or {}).get('name') or (meta or {}).get('display_name') or (meta or {}).get('filename')
        handle = (meta or {}).get('handle') or (meta or {}).get('skool_tag') or (meta or {}).get('id')
        reason = (h.get('doc') or '')[:200] if isinstance(h, dict) else ''
        out.append({'name': name, 'handle': handle, 'score': h.get('score') if isinstance(h, dict) else None, 'reason': reason})
    return out

