from __future__ import annotations
import re, glob, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / ".github" / "copilot-instructions.md"

S1, E1 = "<!-- AUTO:STATUS START -->", "<!-- AUTO:STATUS END -->"
S2, E2 = "<!-- AUTO:BACKLOG START -->", "<!-- AUTO:BACKLOG END -->"

def replace_block(text, start, end, payload):
    return re.sub(re.escape(start)+r"(?:.|\n)*?"+re.escape(end), f"{start}\n{payload}\n{end}", text, flags=re.DOTALL)

def main():
    text = DOC.read_text(encoding="utf-8")
    runs = sorted(glob.glob(str(ROOT/"exports"/"status"/"runs"/"*" )), reverse=True)
    latest = runs[0].split("\\")[-1] if runs else "n/a"

    status = [
        f"Letzter Run: `{latest}`",
        f"Runs total: {len(runs)}",
    ]
    status_md = "\n".join(f"- {x}" for x in status)

    backlog = [
        "Strict JSON Schema Validation in CI anschalten",
        "Smoke-Runner als CI-Job (PR-Gates)",
        "Net-Wrapper flächendeckend verwenden",
    ]
    backlog_md = "\n".join(f"- [ ] {x}" for x in backlog)

    text = replace_block(text, S1, E1, status_md)
    text = replace_block(text, S2, E2, backlog_md)
    DOC.write_text(text, encoding="utf-8")
    print("copilot-instructions.md aktualisiert.")

if __name__ == '__main__':
    main()
