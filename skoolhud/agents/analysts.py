from __future__ import annotations
from typing import Any, Dict
from datetime import datetime
from skoolhud.db import SessionLocal
from skoolhud.models import Member
import os
from skoolhud.ai.tools import llm_complete


class BaseAnalyst:
    name = 'base'

    def analyze(self, tenant: str) -> Dict[str, Any]:
        raise NotImplementedError()


class KPIAnalyst(BaseAnalyst):
    name = 'kpi'

    def analyze(self, tenant: str) -> Dict[str, Any]:
        s = SessionLocal()
        try:
            total = s.query(Member).filter(Member.tenant == tenant).count()
            active7 = s.query(Member).filter((Member.points_7d != None) & (Member.points_7d > 0) & (Member.tenant == tenant)).count()
            active30 = s.query(Member).filter((Member.points_30d != None) & (Member.points_30d > 0) & (Member.tenant == tenant)).count()
        finally:
            s.close()

        insights = {
            'summary': f"{total} members; active7={active7}; active30={active30}",
            'metrics': {'total': total, 'active7': active7, 'active30': active30}
        }

        provider = os.getenv('LLM_PROVIDER', 'ollama')
        insights['actions'] = [llm_complete(f"Suggest 3 actions to improve active7 for tenant {tenant}", provider=provider, purpose=self.name)]
        return insights


class HealthAnalyst(BaseAnalyst):
    name = 'health'

    def analyze(self, tenant: str) -> Dict[str, Any]:
        s = SessionLocal()
        try:
            rows = s.query(Member.user_id, Member.name, Member.points_30d, Member.points_all, Member.last_active_at_utc).filter(Member.tenant == tenant).all()
        finally:
            s.close()
        at_risk = [r for r in rows if (r[2] or 0) < 5 and (r[3] or 0) > 50]
        insights = {
            'summary': f'Found {len(at_risk)} at-risk members',
            'at_risk_count': len(at_risk),
            'samples': [{'user_id': r[0], 'name': r[1]} for r in at_risk[:10]]
        }
        provider = os.getenv('LLM_PROVIDER', 'ollama')
        insights['actions'] = [llm_complete(f"Create re-engagement steps for {len(at_risk)} users", provider=provider, purpose=self.name)]
        return insights
