#!/usr/bin/env python3
"""Smoke test for Ollama integration.

Usage: python scripts/test_ollama.py

Reads .env for OLLAMA_URL / OLLAMA_MODEL / OLLAMA_API_KEY, then calls
`skoolhud.ai.tools.llm_complete(..., provider='ollama')` and prints the response.
"""
from __future__ import annotations
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from skoolhud.ai.tools import llm_complete
import importlib.util
from pathlib import Path

# Load ollama_manager.py as a module from the sibling scripts directory
try:
    spec = importlib.util.spec_from_file_location(
        "ollama_manager",
        str(Path(__file__).resolve().parent / "ollama_manager.py"),
    )
    if spec and spec.loader:
        _ollama_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_ollama_mod)  # type: ignore[attr-defined]
        ensure_ollama = getattr(_ollama_mod, "ensure")
    else:
        ensure_ollama = lambda: None
except Exception:
    ensure_ollama = lambda: None


def main() -> int:
    prompt = (
        "You are a helpful assistant. Reply with a one-line summary: "
        "What is the capital of France?"
    )
    provider = os.getenv("LLM_PROVIDER", os.getenv("SKOOL_LLM_PROVIDER", "ollama"))
    print(f"Using provider: {provider}")
    # ensure an Ollama server is available (will detect existing server)
    try:
        ensure_ollama()
    except Exception as e:
        print(f"Warning: ollama_manager.ensure() failed: {e}")

    try:
        out = llm_complete(prompt, max_tokens=64, provider=provider, purpose='test')
        print("--- RESPONSE ---")
        print(out)
        print("--- END ---")
        return 0
    except Exception as e:
        print(f"Ollama test failed: {e}", file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
