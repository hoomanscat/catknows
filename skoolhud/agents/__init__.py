"""Top-level agents package for skoolhud.

This package collects AI agent implementations. It is the new canonical
location for agents; old imports under `skoolhud.ai.agents` are forwarded
via the shim in `skoolhud/ai/__init__.py`.
"""
from .analysts import *
from .joiners import *
from .kpi_report import *

__all__ = [k for k in globals().keys() if not k.startswith('_')]
