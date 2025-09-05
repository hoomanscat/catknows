from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, Any, List

# Prefer new agent modules if available
try:
    from skoolhud.ai.agents.validator import SchemaValidator as ExternalSchemaValidator
except Exception:
    ExternalSchemaValidator = None

try:
    from skoolhud.ai.agents.composer import compose_insights as external_compose
except Exception:
    external_compose = None

try:
    from skoolhud.ai.agents.dispatcher import Dispatcher as ExternalDispatcher
except Exception:
    ExternalDispatcher = None

try:
    from skoolhud.ai.agents.safety import mask_pii as external_mask_pii
except Exception:
    external_mask_pii = None


class SchemaValidator:
    def __init__(self):
        if ExternalSchemaValidator:
            # wrap external validator
            self._impl = ExternalSchemaValidator()
        else:
            self._impl = None

    def validate_reports(self, tenant: str) -> Tuple[bool, List[str]]:
        if self._impl:
            return self._impl.validate_reports(tenant)

        base = Path("exports") / "reports" / tenant
        errors: List[str] = []
        warnings: List[str] = []
        if not base.exists():
            errors.append(f"reports dir missing: {base}")
            return False, errors

        files = list(base.glob("*.md"))
        if not files:
            errors.append("no .md report files found")
            return False, errors

        for p in files:
            try:
                txt = p.read_text(encoding="utf-8").strip()
            except Exception as e:
                errors.append(f"could not read {p}: {e}")
                continue
            if not txt:
                # Treat empty files as warnings (non-blocking) in MVP mode
                warnings.append(f"empty file: {p}")

        # Return ok if no critical errors; include warnings in the error list prefixed
        result_errors = errors[:]
        for w in warnings:
            result_errors.append("WARNING: " + w)

        return (len(errors) == 0), result_errors

    def validate_summary(self, tenant: str) -> dict:
        """Compatibility shim: return {ok, errors, warnings, files_checked}.

        If an external validator implementation provides a richer summary, prefer it.
        """
        if self._impl and hasattr(self._impl, "validate_summary"):
            try:
                return self._impl.validate_summary(tenant)
            except Exception:
                pass

        ok, result_errors = self.validate_reports(tenant)
        errors: List[str] = []
        warnings: List[str] = []
        # split warnings from result_errors
        for e in result_errors:
            if isinstance(e, str) and e.startswith("WARNING:"):
                warnings.append(e[len("WARNING: "):])
            else:
                errors.append(e)

        # count files of interest
        base = Path("exports") / "reports" / tenant
        files_checked = 0
        if base.exists():
            files_checked = len([p for p in base.glob("**/*") if p.is_file() and p.suffix.lower() in ('.md', '.json', '.csv')])

        return {"ok": ok, "errors": errors, "warnings": warnings, "files_checked": files_checked}


class KPIAnalyst:
    def run(self, tenant: str) -> Dict[str, Any]:
        base = Path("exports") / "reports" / tenant
        out = {"run_id": datetime.utcnow().isoformat(), "tenant": tenant, "agent": "KPIAnalyst", "priority": "medium", "bullets": [], "actions": []}
        for p in base.glob("ai_kpi_summary_*.md"):
            text = p.read_text(encoding="utf-8")
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            out["bullets"].extend(lines[:6])
        if not out["bullets"]:
            out["bullets"].append("No KPI summary found; run ingest or check agent.")
        out["actions"].append({"title": "Review KPIs", "owner": "community-team", "due_days": 2})
        return out


class HealthAnalyst:
    def run(self, tenant: str) -> Dict[str, Any]:
        base = Path("exports") / "reports" / tenant
        out = {"run_id": datetime.utcnow().isoformat(), "tenant": tenant, "agent": "HealthAnalyst", "priority": "high", "bullets": [], "actions": []}
        for p in base.glob("ai_health_plan_*.md"):
            text = p.read_text(encoding="utf-8")
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            out["bullets"].extend(lines[:6])
        if not out["bullets"]:
            out["bullets"].append("No health plan found; ensure health agent ran.")
        out["actions"].append({"title": "Target re-engagement list", "owner": "community-team", "due_days": 3})
        return out


class MoversAnalyst:
    def run(self, tenant: str) -> Dict[str, Any]:
        base = Path("exports") / "reports" / tenant
        out = {"run_id": datetime.utcnow().isoformat(), "tenant": tenant, "agent": "MoversAnalyst", "priority": "low", "bullets": [], "actions": []}
        for p in base.glob("leaderboard_movers*.md"):
            text = p.read_text(encoding="utf-8")
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            out["bullets"].extend(lines[:8])
        if not out["bullets"]:
            out["bullets"].append("No movers report found.")
        out["actions"].append({"title": "Prepare shoutouts", "owner": "community-team", "due_days": 1})
        return out


class InsightComposer:
    def compose(self, findings: List[Dict[str, Any]], tenant: str, run_id: str) -> Dict[str, Any]:
        if external_compose:
            return external_compose(findings, tenant, run_id)

        insights_md_lines: List[str] = [f"# Insights — {tenant} — {run_id}", ""]
        actions_md_lines: List[str] = [f"# Actions — {tenant} — {run_id}", ""]
        for f in findings:
            insights_md_lines.append(f"## {f.get('agent')}")
            for b in f.get("bullets", []):
                insights_md_lines.append(f"- {b}")
            insights_md_lines.append("")
            for a in f.get("actions", []):
                actions_md_lines.append(f"- {a.get('title')} (owner={a.get('owner')}, due_days={a.get('due_days')})")

        return {
            "insights_md": "\n".join(insights_md_lines),
            "actions_md": "\n".join(actions_md_lines),
            "summary": {"agents": [f.get('agent') for f in findings]},
        }


class Dispatcher:
    def dispatch(self, tenant: str, out_dir: Path, force: bool = False) -> Dict[str, Any]:
        # prefer external dispatcher if available
        if ExternalDispatcher:
            d = ExternalDispatcher()
            try:
                return d.dispatch(tenant, out_dir, force=force)
            except TypeError:
                # older external dispatcher may not accept force
                return d.dispatch(tenant, out_dir)

        insights = ""
        actions = ""
        try:
            if (out_dir / "insights.md").exists():
                insights = (out_dir / "insights.md").read_text(encoding="utf-8", errors="replace")
        except Exception:
            insights = ""
        try:
            if (out_dir / "actions.md").exists():
                actions = (out_dir / "actions.md").read_text(encoding="utf-8", errors="replace")
        except Exception:
            actions = ""

        plan = {"tenant": tenant, "preview": insights[:200], "actions_preview": actions[:200], "posted": False}
        return plan
