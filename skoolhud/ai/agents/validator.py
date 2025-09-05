from __future__ import annotations
import json
from pathlib import Path
from typing import List, Tuple, Any
import os

try:
    import jsonschema
    _HAS_JSONSCHEMA = True
except Exception:
    _HAS_JSONSCHEMA = False


class SchemaValidator:
    def __init__(self, schemas_dir: str | Path | None = None):
        self.schemas_dir = Path(schemas_dir) if schemas_dir else Path("project-status") / "schemas"

    def _load_schema(self, name: str) -> Any | None:
        p = self.schemas_dir / name
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            return None

    def validate_reports(self, tenant: str) -> Tuple[bool, List[str]]:
        """Validate exports/reports/<tenant> using available schemas.

        - If jsonschema is available and matching schema files exist, validate JSON files.
        - For CSV, perform basic header checks if a schema with `required_columns` is present as JSON.
        """
        base = Path("exports") / "reports" / tenant
        errors: List[str] = []
        warnings: List[str] = []
        if not base.exists():
            errors.append(f"reports dir missing: {base}")
            return False, errors

        files = list(base.glob("**/*"))
        if not files:
            errors.append("no report files found for tenant")
            return False, errors

        # Basic checks: try to validate JSON files against schema by filename match
        if _HAS_JSONSCHEMA and self.schemas_dir.exists():
            for p in base.glob("*.json"):
                # try to find a schema file with same stem
                schema = self._load_schema(p.name)
                if schema is None:
                    # try <stem>.schema.json
                    schema = self._load_schema(f"{p.stem}.schema.json")
                if schema is None:
                    warnings.append(f"no schema for {p.name}")
                    continue
                try:
                    inst = json.loads(p.read_text(encoding='utf-8'))
                    jsonschema.validate(instance=inst, schema=schema)
                except Exception as e:
                    errors.append(f"schema validation failed for {p.name}: {e}")

        # CSV heuristics: if there's a matching schema file like name.csv.schema.json with required_columns
        for p in base.glob("*.csv"):
            schema = self._load_schema(f"{p.name}.schema.json")
            if schema and isinstance(schema, dict) and schema.get("required_columns"):
                try:
                    txt = p.read_text(encoding='utf-8')
                    hdr = txt.splitlines()[0].split(',')
                    missing = [c for c in schema.get("required_columns", []) if c not in hdr]
                    if missing:
                        errors.append(f"csv {p.name} missing columns: {missing}")
                except Exception as e:
                    errors.append(f"could not read csv {p.name}: {e}")

        # Non-file-specific checks: ensure there is at least one .md or .json report
        md_or_json = list(base.glob("*.md")) + list(base.glob("*.json"))
        if not md_or_json:
            warnings.append("no markdown or json reports found; pipeline may have produced only CSVs")

        result_errors = errors[:]
        for w in warnings:
            result_errors.append("WARNING: " + w)

        return (len(errors) == 0), result_errors

    def validate_summary(self, tenant: str) -> dict:
        """Return a richer summary dict: {ok, errors, warnings, files_checked}."""
        base = Path("exports") / "reports" / tenant
        errors: List[str] = []
        warnings: List[str] = []
        files_checked = 0
        if not base.exists():
            errors.append(f"reports dir missing: {base}")
            return {"ok": False, "errors": errors, "warnings": warnings, "files_checked": files_checked}

        # count only report files of interest
        files = [p for p in base.glob("**/*") if p.is_file() and p.suffix.lower() in ('.md', '.json', '.csv')]
        files_checked = len(files)
        if not files:
            errors.append("no report files found for tenant")
            return {"ok": False, "errors": errors, "warnings": warnings, "files_checked": files_checked}

        # reuse existing validation logic path by calling validate_reports
        ok, result_errors = self.validate_reports(tenant)
        # split warnings from result_errors
        for e in result_errors:
            if isinstance(e, str) and e.startswith("WARNING:"):
                warnings.append(e[len("WARNING: "):])
            else:
                errors.append(e)

        return {"ok": ok, "errors": errors, "warnings": warnings, "files_checked": files_checked}
