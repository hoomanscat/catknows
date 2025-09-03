from __future__ import annotations
import os
import time
import requests
from typing import Any

_MIN_DELAY = float(os.getenv("RATE_LIMIT_MIN_DELAY", "15"))
_MAX_RETRY = int(os.getenv("RETRY_MAX", "3"))
_last_ts = 0.0

def _respect_rate_limit():
    global _last_ts
    now = time.time()
    wait = _MIN_DELAY - (now - _last_ts)
    if wait > 0:
        time.sleep(wait)
    _last_ts = time.time()

def _with_retry(method: str, url: str, **kw) -> requests.Response:
    max_retry = int(kw.pop("max_retries", _MAX_RETRY))
    for attempt in range(max_retry + 1):
        _respect_rate_limit()
        try:
            r = requests.request(method, url, timeout=kw.pop("timeout", 60), **kw)
            if r.status_code >= 500:
                r.raise_for_status()
            return r
        except Exception:
            if attempt >= max_retry:
                raise
            backoff = min(60, 2 ** attempt)
            time.sleep(backoff)

def get_with_retry(url: str, **kw) -> requests.Response:
    return _with_retry("GET", url, **kw)

def post_with_retry(url: str, json: Any = None, data: Any = None, files: Any = None, **kw) -> requests.Response:
    return _with_retry("POST", url, json=json, data=data, files=files, **kw)
