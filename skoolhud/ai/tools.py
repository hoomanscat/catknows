from __future__ import annotations
import json, csv, os
from pathlib import Path
import subprocess
import time
from datetime import datetime
from typing import Any, List, Dict, Optional

from skoolhud.db import SessionLocal
from sqlalchemy import text
from skoolhud.vector.db import get_collection, get_client
import requests
from requests.adapters import HTTPAdapter, Retry
from sentence_transformers import SentenceTransformer
from skoolhud.utils import reports_dir_for
from skoolhud.config import get_tenant_slug
from skoolhud.utils.net import post_with_retry

ROOT = Path("exports") / "reports"

# simple in-process cache for `ollama list`
_OLLAMA_LIST_CACHE: dict = {"ts": 0, "models": []}
_OLLAMA_LIST_TTL = 60  # seconds

STATUS_DIR = Path("exports") / "status"
STATUS_DIR.mkdir(parents=True, exist_ok=True)
LLM_LOG = STATUS_DIR / "llm_calls.log"

def find_latest(tenant: str, *patterns: str) -> Optional[Path]:
    base = ROOT / tenant
    for pat in patterns:
        matches = sorted(base.glob(pat), reverse=True)
        if matches:
            return matches[0]
    # fallback to root
    for pat in patterns:
        matches = sorted((Path("exports") / "reports").glob(pat), reverse=True)
        if matches:
            return matches[0]
    return None


def get_model_for(model_override: Optional[str] = None, purpose: Optional[str] = None) -> Optional[str]:
    """Resolve a model name to use for Ollama calls.

    Order:
      1) explicit model_override
      2) env OLLAMA_MODEL_{PURPOSE}
      3) env OLLAMA_MODEL
      4) first model from `ollama list`
    """
    if model_override:
        return model_override
    if purpose:
        env = os.getenv(f'OLLAMA_MODEL_{purpose.upper()}')
        if env:
            return env
    env = os.getenv('OLLAMA_MODEL')
    if env:
        return env

    # fallback: query local ollama binary for available models
    ollama_bin = os.getenv('OLLAMA_BIN', 'ollama')
    try:
        now = time.time()
        if _OLLAMA_LIST_CACHE.get('ts', 0) + _OLLAMA_LIST_TTL > now and _OLLAMA_LIST_CACHE.get('models'):
            models = _OLLAMA_LIST_CACHE['models']
        else:
            proc = subprocess.run([ollama_bin, 'list'], capture_output=True, text=True, timeout=10)
            out = proc.stdout or ''
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            models = []
            # skip header if present
            start = 0
            if lines and lines[0].lower().startswith('name'):
                start = 1
            for l in lines[start:]:
                parts = l.split()
                if parts:
                    models.append(parts[0])
            _OLLAMA_LIST_CACHE['ts'] = now
            _OLLAMA_LIST_CACHE['models'] = models

        if models:
            return models[0]
    except Exception:
        return None
    return None


def _log_llm_call(prompt: str, provider: str, model: Optional[str], purpose: Optional[str], result: str, duration_ms: int) -> None:
    try:
        entry = {
            'ts': datetime.utcnow().isoformat() + 'Z',
            'provider': provider,
            'model': model,
            'purpose': purpose,
            'prompt_preview': (prompt[:200] + '...') if len(prompt) > 200 else prompt,
            'result_preview': (result[:500] + '...') if len(result) > 500 else result,
            'duration_ms': duration_ms,
        }
        with LLM_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _normalize_llm_output(raw: Any) -> str:
    """Normalize various LLM response shapes to plain text for agent consumption.

    Accepts dicts or strings. Tries common fields in order:
      - response
      - text
      - output (string)
      - outputs[0].content
      - choices[0].message.content (OpenAI-like)
      - choices[0].text
    Falls back to stringifying the input.
    """
    try:
        if raw is None:
            return ''
        # If it's a JSON string, try to parse it
        if isinstance(raw, str):
            s = raw.strip()
            # quick heuristic: if looks like json, parse
            if s.startswith('{') or s.startswith('['):
                try:
                    parsed = json.loads(s)
                    return _normalize_llm_output(parsed)
                except Exception:
                    return s
            return s

        if isinstance(raw, dict):
            # common Ollama-style
            if 'response' in raw and isinstance(raw['response'], str):
                return raw['response']
            if 'text' in raw and isinstance(raw['text'], str):
                return raw['text']
            if 'output' in raw and isinstance(raw['output'], str):
                return raw['output']
            if 'outputs' in raw and isinstance(raw['outputs'], list) and raw['outputs']:
                first = raw['outputs'][0]
                if isinstance(first, dict) and 'content' in first:
                    return first['content']
                if isinstance(first, str):
                    return first

            # OpenAI-like
            if 'choices' in raw and isinstance(raw['choices'], list) and raw['choices']:
                c = raw['choices'][0]
                if isinstance(c, dict):
                    # chat format
                    if 'message' in c and isinstance(c['message'], dict) and 'content' in c['message']:
                        return c['message']['content']
                    if 'text' in c and isinstance(c['text'], str):
                        return c['text']

            # fallback: stringify
            try:
                return json.dumps(raw, ensure_ascii=False)
            except Exception:
                return str(raw)

        # other types -> stringify
        return str(raw)
    except Exception:
        try:
            return str(raw)
        except Exception:
            return ''

def load_any(p: Path) -> Any:
    if not p or not p.exists():
        return None
    if p.suffix.lower() in ('.json',):
        return json.loads(p.read_text(encoding='utf-8'))
    if p.suffix.lower() in ('.csv',):
        with p.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    # fallback to text
    return p.read_text(encoding='utf-8')

def db_query(sql: str, params: Optional[Dict[str, Any]] = None):
    # Allow only SELECT statements for safety
    if not sql.strip().lower().startswith('select'):
        raise ValueError('db_query only supports read-only SELECT statements')
    s = SessionLocal()
    try:
        # SQLAlchemy 1.4+ recommends using text() for raw SQL strings
        res = s.execute(text(sql), params or {})
        # use .mappings() to get dict-like rows
        mapped = res.mappings().all()
        return [dict(r) for r in mapped]
    finally:
        s.close()

def vector_search(query: str, tenant: str | None = None, k: int = 5):
    tenant = get_tenant_slug(tenant)
    model_name = os.getenv('EMBED_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    model = SentenceTransformer(model_name)
    q_emb = model.encode([query], normalize_embeddings=True).tolist()[0]
    client = get_client()
    col = get_collection('skoolhud')
    res = col.query(query_embeddings=[q_emb], n_results=k, where={'tenant': tenant}, include=['metadatas','documents','distances'])
    ids = (res.get('ids') or [[]])[0]
    docs = (res.get('documents') or [[]])[0]
    metas = (res.get('metadatas') or [[]])[0]
    dists = (res.get('distances') or [[]])[0]
    out = []
    for id_, doc, meta, dist in zip(ids, docs, metas, dists):
        out.append({'id': id_, 'doc': doc, 'meta': meta, 'score': 1 - dist})
    return out

def llm_complete(prompt: str, max_tokens: int = 256, provider: str = 'stub', model: Optional[str] = None, purpose: Optional[str] = None) -> str:
    # Minimal stub: returns first 2 lines or a short echo. Replace with OpenAI/Ollama integrations as needed.
    if provider == 'stub':
        lines = [l.strip() for l in prompt.splitlines() if l.strip()]
        out = '\n'.join(lines[:3]) if lines else prompt[:max_tokens]
        _log_llm_call(prompt, provider, None, purpose, out, 0)
        return out

    if provider == 'ollama':
        # Resolve model using helper (overrides, purpose-specific env, global env, or local list)
        resolved = get_model_for(model_override=model, purpose=purpose)
        if not resolved:
            # no model available; fall back to stub behavior
            return "[ollama-error] no model available"
        model = resolved

        # Try a set of candidate endpoints to support multiple Ollama versions
        base = os.getenv('OLLAMA_BASE', os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434'))
        api_key = os.getenv('OLLAMA_API_KEY')
        # Allow an explicit API path override e.g. '/api/models/gpt-4/generate'
        api_path = os.getenv('OLLAMA_API_PATH')
        if api_path:
            api_path = api_path.lstrip('/')
            candidates = [f"{base.rstrip('/')}/{api_path}"]
        else:
            candidates = [
                f"{base.rstrip('/')}/api/generate",
                f"{base.rstrip('/')}/api/models/{model}/generate",
                f"{base.rstrip('/')}/v1/generate",
            ]

        # ensure model is a string
        model = model or os.getenv('OLLAMA_MODEL', 'gorilla')
        payload = {
            'model': model,
            'prompt': prompt,
            'max_tokens': max_tokens,
            'stream': False,
        }

        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        sess = requests.Session()
        retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 502, 503, 504])
        sess.mount('http://', HTTPAdapter(max_retries=retries))
        sess.mount('https://', HTTPAdapter(max_retries=retries))

    start_ts = time.time()
    last_err = None
    # Try HTTP endpoints first
    for url in candidates:
        try:
            r = sess.post(url, json=payload, headers=headers, timeout=20)
            status = getattr(r, 'status_code', None)
            text = (r.text or '')[:4096]
            if r.ok:
                # try parse JSON, otherwise return raw text
                try:
                    data = r.json()
                except Exception:
                    out = text
                    normalized = _normalize_llm_output(out)
                    _log_llm_call(prompt, provider, model, purpose, normalized, int((time.time() - start_ts) * 1000))
                    return normalized

                # Normalize the parsed object to plain text for agents
                normalized = _normalize_llm_output(data)
                _log_llm_call(prompt, provider, model, purpose, normalized, int((time.time() - start_ts) * 1000))
                return normalized
            else:
                last_err = f"[{status}] {text}"
        except Exception as e:
            last_err = str(e)

    # none of the endpoints returned a usable result -> try CLI fallback
    ollama_bin = os.getenv('OLLAMA_BIN', 'ollama')
    try:
        model_str = str(model)
        try:
            proc = subprocess.run([ollama_bin, 'run', model_str], input=prompt, capture_output=True, text=True, timeout=20)
        except Exception:
            proc = subprocess.run([ollama_bin, 'generate', model_str, prompt], capture_output=True, text=True, timeout=20)

        if proc.returncode == 0 and proc.stdout:
            out = proc.stdout.strip()
            _log_llm_call(prompt, provider, model, purpose, out, int((time.time() - start_ts) * 1000))
            return out
        else:
            cli_err = (proc.stderr or proc.stdout or '').strip()
            out = f"[ollama-error] no successful HTTP response; last: {last_err}; cli: {cli_err}"
            _log_llm_call(prompt, provider, model, purpose, out, int((time.time() - start_ts) * 1000))
            return out
    except Exception as e:
        out = f"[ollama-error] no successful response; last: {last_err}; cli-exc: {e}"
        _log_llm_call(prompt, provider, model, purpose, out, int((time.time() - start_ts) * 1000))
        return out

    raise NotImplementedError('No LLM provider configured')

def discord_post(webhook: str, content: str = '', username: Optional[str] = None, files: Optional[List[Path]] = None, chunk_size: int = 1800):
    if not webhook:
        return 0
    # chunk content
    parts = []
    if content:
        s = content
        while s:
            parts.append(s[:chunk_size])
            s = s[chunk_size:]
    else:
        parts = ['']

    status = 0
    for i, part in enumerate(parts):
        payload = {'content': part}
        if username:
            payload['username'] = username
        # only attach files on first chunk
        file_arg = None
        if files and i == 0:
            p = files[0]
            file_arg = {'file': (p.name, p.open('rb'))}
        try:
            resp = post_with_retry(webhook, json=payload, files=file_arg, timeout=15)
            status = getattr(resp, 'status_code', 0)
        finally:
            if file_arg:
                try: file_arg['file'][1].close()
                except: pass
    return status


def discord_report_post(webhook: str, md_path: Path, username: Optional[str] = None) -> int:
    """Post a markdown report to Discord. If file is large, send as attachment and include a short excerpt.

    Returns HTTP status code or 0 on failure.
    """
    if not webhook or not md_path or not md_path.exists():
        return 0
    text = md_path.read_text(encoding='utf-8')
    # send first 1500 chars as message and attach full file
    excerpt = text[:1500]
    try:
        status = discord_post(webhook, content=excerpt, username=username, files=[md_path], chunk_size=1500)
        return status
    except Exception:
        return 0


def discord_report_post_verbose(webhook: str, md_path: Path, username: Optional[str] = None) -> Dict[str, Any]:
    """Post markdown to Discord and return a verbose result dict: {'status':int,'text':str}.

    This uses the same chunking/attachment logic but preserves response text when available.
    """
    result = {'status': 0, 'text': ''}
    if not webhook or not md_path or not md_path.exists():
        return result
    text = md_path.read_text(encoding='utf-8')
    excerpt = text[:1500]
    # try to post and capture response
    try:
        # post the excerpt first (Discord will accept a json payload). If file is attached, use files param.
        # We use post_with_retry to get a requests.Response
        from skoolhud.utils.net import post_with_retry as _post
        # send payload with file as multipart for the first chunk
        with md_path.open('rb') as fh:
            files = {'file': (md_path.name, fh)}
            resp = _post(webhook, json={'content': excerpt, 'username': username} if username else {'content': excerpt}, files=files, timeout=20)
        code = getattr(resp, 'status_code', 0)
        body = getattr(resp, 'text', '')
        result['status'] = int(code or 0)
        result['text'] = (body or '')[:2000]
        return result
    except Exception as e:
        try:
            result['text'] = str(e)
        except Exception:
            result['text'] = 'error'
        return result


def _guard_file_for(name: str, slug: str) -> Path:
    return STATUS_DIR / f"{name}_last_post_{slug}.json"


def post_guard_allowed(slug: str, name: str, cooldown_env_var: Optional[str] = None, default: int = 3600) -> bool:
    """Return True if posting is allowed for (slug,name) based on a file-backed cooldown.

    cooldown_env_var: name of env var that contains seconds; if None use default.
    """
    try:
        cooldown = int(os.getenv(cooldown_env_var, str(default))) if cooldown_env_var else int(default)
    except Exception:
        cooldown = default

    guard = _guard_file_for(name, slug)
    now_ts = int(time.time())
    last_ts = 0
    try:
        if guard.exists():
            j = json.loads(guard.read_text(encoding='utf-8'))
            last_ts = int(j.get('last_post', 0))
    except Exception:
        last_ts = 0
    return (now_ts - last_ts) >= cooldown


def post_guard_mark(slug: str, name: str, ts: Optional[int] = None) -> None:
    """Write the current timestamp into the guard file for (slug,name)."""
    guard = _guard_file_for(name, slug)
    try:
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(json.dumps({'last_post': int(ts or time.time())}), encoding='utf-8')
    except Exception:
        pass
