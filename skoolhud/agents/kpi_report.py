from __future__ import annotations
from typing import Any, Dict
from skoolhud.db import SessionLocal
from skoolhud.models import Member

def generate_kpi(tenant: str) -> Dict[str, Any]:
    s = SessionLocal()
    try:
        total = s.query(Member).filter(Member.tenant==tenant).count()
        active7 = s.query(Member).filter((Member.points_7d!=None) & (Member.points_7d>0) & (Member.tenant==tenant)).count()
    finally:
        s.close()
    return {'total': total, 'active7': active7}
