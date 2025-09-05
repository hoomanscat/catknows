"""AI package shim for backwards compatibility.

Re-exports the new `skoolhud.agents` package so old imports like
`from skoolhud.ai.agents import ...` continue to work.
"""
from .. import agents as agents

__all__ = ['agents']
