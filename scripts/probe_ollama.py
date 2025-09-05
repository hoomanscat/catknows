#!/usr/bin/env python3
"""Probe common Ollama endpoints to help discover the correct API path.

Usage: python scripts/probe_ollama.py
"""
from __future__ import annotations
import os
import sys
import requests
from urllib.parse import urljoin

BASE = os.getenv('OLLAMA_BASE', os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434'))
MODEL = os.getenv('OLLAMA_MODEL', 'gorilla')

paths = [
    '/',
    '/api',
    '/api/generate',
    f'/api/models/{MODEL}/generate',
    '/v1/generate',
    '/openapi.json',
    '/api/models',
]


def probe():
    print(f"Probing base: {BASE}")
    for p in paths:
        url = urljoin(BASE if BASE.endswith('/') else BASE + '/', p.lstrip('/'))
        try:
            r = requests.get(url, timeout=3)
            code = r.status_code
            text = r.text[:2048]
            print(f"{url} -> {code}")
            if text:
                print(text[:1024])
            print('-' * 60)
        except Exception as e:
            print(f"{url} -> ERROR: {e}")
            print('-' * 60)


if __name__ == '__main__':
    try:
        probe()
    except KeyboardInterrupt:
        sys.exit(1)
