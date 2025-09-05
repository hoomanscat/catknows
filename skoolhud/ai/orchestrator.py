from __future__ import annotations
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional
from skoolhud.ai.mvp_actors import SchemaValidator, KPIAnalyst, HealthAnalyst, MoversAnalyst, InsightComposer, Dispatcher
import os
import re

# Prefer safety helpers if present
try:
    from skoolhud.ai.agents.safety import mask_pii as agent_mask_pii, cost_guard_allowed as agent_cost_guard_allowed
except Exception:
    agent_mask_pii = None
    agent_cost_guard_allowed = None


def _sanitize_pii(text: str) -> str:
    # prefer agent-provided sanitizer
    if agent_mask_pii:
        try:
            return agent_mask_pii(text)
        except Exception:
            pass
    # fallback: mask emails and simple handles
    text = re.sub(r"[\w\.-]+@[\w\.-]+", "[redacted-email]", text)
    text = re.sub(r"@(\w{2,32})", r"[redacted-handle]", text)
    return text


def _cost_guard_allowed() -> Tuple[bool, str]:
    # prefer agent-level cost guard if available
    if agent_cost_guard_allowed:
        try:
            return agent_cost_guard_allowed()
        except Exception:
            pass

    # Passive default: do not actively block (useful for local Ollama).
    enable = os.getenv("AI_ENABLE_COST_GUARD", "0")
    if enable != "1":
        max_cost = os.getenv("AI_MAX_COST_EUR", "1.0")
        return True, f"passive (max_cost={max_cost})"

    # Active guard path (legacy): check AI_MAX_CALLS env var counting llm_calls.log entries
    max_calls = os.getenv("AI_MAX_CALLS")
    if not max_calls:
        return True, "active guard enabled but no AI_MAX_CALLS set"
    try:
        max_calls_i = int(max_calls)
    except Exception:
        return True, "invalid limit"
    logp = Path("exports") / "status" / "llm_calls.log"
    if not logp.exists():
        return True, "no log"
    cnt = 0
    try:
        with logp.open("r", encoding="utf-8", errors="ignore") as fh:
            for _ in fh:
                cnt += 1
    except Exception:
        return True, "log read error"
    if cnt >= max_calls_i:
        return False, f"limit reached: {cnt}/{max_calls_i}"
    return True, f"ok {cnt}/{max_calls_i}"


def run_orchestrator(tenant: str, run_id: Optional[str] = None, force: bool = False) -> int:
    run_id = run_id or datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_dir = Path("exports") / "ai" / tenant / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    ctx = {"tenant": tenant, "run_id": run_id, "out_dir": str(out_dir)}

    # 1) Validate schemas
    validator = SchemaValidator()
    # call validate_summary if available (use getattr to avoid static attribute check warnings)
    _vs = getattr(validator, "validate_summary", None)
    if callable(_vs):
        try:
            summary = _vs(tenant)
        except Exception:
            ok, errors = validator.validate_reports(tenant)
            summary = {"ok": ok, "errors": errors, "warnings": [], "files_checked": 0}
    else:
        # fallback to legacy tuple return
        ok, errors = validator.validate_reports(tenant)
        summary = {"ok": ok, "errors": errors, "warnings": [], "files_checked": 0}
    (out_dir / "validate.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    # Ensure summary is a dict (some validators may return tuples, lists or custom objects)
    if not isinstance(summary, dict):
        if isinstance(summary, (list, tuple)) and len(summary) >= 2:
            ok, errors = summary[0], summary[1]
            summary = {"ok": bool(ok), "errors": errors or [], "warnings": [], "files_checked": 0}
        else:
            # Try to read attributes 'ok' and 'errors' if it's an object
            ok_attr = getattr(summary, "ok", None)
            errors_attr = getattr(summary, "errors", None)
            if ok_attr is not None:
                summary = {"ok": bool(ok_attr), "errors": errors_attr or [], "warnings": [], "files_checked": 0}
            else:
                summary = {"ok": False, "errors": ["invalid validate result"], "warnings": [], "files_checked": 0}
    # write status files on validation failure
    STATUS_DIR = Path("exports") / "status"
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    last_run = STATUS_DIR / "last_run.json"
    run_status_dir = STATUS_DIR / "runs" / run_id / tenant
    run_status_dir.mkdir(parents=True, exist_ok=True)
    status_payload = {"ok": summary.get("ok", False), "tenant": tenant, "run_id": run_id, "errors": summary.get("errors", [])}
    # canonical status location
    (run_status_dir / "status.json").write_text(json.dumps(status_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    last_run.write_text(json.dumps(status_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    # also write a run-local copy so tools that inspect the run folder find it
    try:
        (out_dir / "status.json").write_text(json.dumps(status_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    if not summary.get("ok", False):
        print("Schema validation failed, aborting. See:", out_dir / "validate.json")
        return 2

    # 2) Run analysts
    findings = []
    # Prefer existing agents runner if available (dynamic import)
    try:
        import importlib
        mod = importlib.import_module('skoolhud.ai.agents.run_all_agents')
        run_for_tenant = getattr(mod, 'run_for_tenant', None)
        if callable(run_for_tenant):
            try:
                runner_out = run_for_tenant(tenant)
                # runner_out may be a Path or a string path with outputs; try to load any produced JSONs
                if isinstance(runner_out, (str, Path)):
                    runner_path = Path(runner_out)
                    for p in runner_path.glob('*.json'):
                        try:
                            data = json.loads(p.read_text(encoding='utf-8', errors='replace'))
                            findings.append(data)
                        except Exception:
                            continue
                else:
                    # unexpected return; ignore and fallback
                    pass
            except Exception:
                # fallback to MVP actors below
                run_for_tenant = None
        else:
            run_for_tenant = None
    except Exception:
        run_for_tenant = None

    if not run_for_tenant:
        for actor in [KPIAnalyst(), HealthAnalyst(), MoversAnalyst()]:
            res = actor.run(tenant)
            findings.append(res)
            (out_dir / f"{res['agent']}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

    # 3) Compose insights
    composer = InsightComposer()
    insights = composer.compose(findings, tenant, run_id)
    (out_dir / "insights.json").write_text(json.dumps(insights, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "insights.md").write_text(insights.get("insights_md", ""), encoding="utf-8")
    (out_dir / "actions.md").write_text(insights.get("actions_md", ""), encoding="utf-8")

    # 4) Sanitize & cost-guard then Dispatch (Dispatcher will post when configured)
    # sanitize insights text
    try:
        md = (out_dir / "insights.md").read_text(encoding="utf-8", errors="replace")
        (out_dir / "insights.md").write_text(_sanitize_pii(md), encoding="utf-8")
    except Exception:
        pass

    allowed, reason = _cost_guard_allowed()
    if not allowed:
        dispatch_res = {"posted": False, "reason": f"cost guard blocked: {reason}"}
    else:
        dispatcher = Dispatcher()
        dispatch_res = dispatcher.dispatch(tenant, out_dir, force=force)
    (out_dir / "dispatch.json").write_text(json.dumps(dispatch_res, indent=2, ensure_ascii=False), encoding="utf-8")

    # write final status files
    artifacts = [str(p.relative_to(Path('.'))) for p in sorted(out_dir.glob('*'))]
    status_payload = {"ok": True, "tenant": tenant, "run_id": run_id, "artifacts": artifacts, "dispatch": dispatch_res}
    # canonical status
    (run_status_dir / "status.json").write_text(json.dumps(status_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    last_run.write_text(json.dumps(status_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    # also copy to run folder for easier local inspection
    try:
        (out_dir / "status.json").write_text(json.dumps(status_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    print("Orchestrator finished. Artifacts written to:", out_dir)
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tenant")
    p.add_argument("--run-id")
    args = p.parse_args()
    code = run_orchestrator(args.tenant, args.run_id)
    raise SystemExit(code if isinstance(code, int) else 0)


if __name__ == "__main__":
    main()

