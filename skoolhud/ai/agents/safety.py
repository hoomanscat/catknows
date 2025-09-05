from __future__ import annotations
import re
import os
from typing import Tuple


def mask_pii(text: str) -> str:
    text = re.sub(r"[\w\.-]+@[\w\.-]+", "[redacted-email]", text)
    text = re.sub(r"@(\w{2,32})", r"[redacted-handle]", text)
    return text


def check_for_secrets(text: str) -> Tuple[bool, str]:
    # simple heuristics: look for long base64-like strings or 'api_key' words
    if 'api_key' in text.lower() or 'secret' in text.lower():
        return False, 'contains secret-like term'
    if re.search(r"[A-Za-z0-9\-/+]{40,}", text):
        return False, 'contains long token-like string'
    return True, 'ok'


def cost_guard_allowed() -> Tuple[bool, str]:
    # mirror existing orchestrator policy: passive by default
    if os.getenv('AI_ENABLE_COST_GUARD', '0') != '1':
        return True, 'passive'
    # otherwise check simple budget env
    try:
        max_eur = float(os.getenv('AI_MAX_COST_EUR', '1.0'))
    except Exception:
        max_eur = 1.0
    # No runtime accounting implemented yet; allow but note budget
    return True, f'active-budget={max_eur}'
