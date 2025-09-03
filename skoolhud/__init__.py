"""
Initialisiert das skoolhud-Paket und legt fest, welche Submodule beim Import sichtbar sind.
Die __all__-Liste definiert die öffentlichen Schnittstellen des Pakets.
"""
__all__ = ["config","db","models","utils","fetcher","normalizer","cli"]

# NOTE: Avoid importing heavy submodules (like `cli`) at package import time.
# Importing `cli` here caused a warning and unpredictable behaviour when
# executing `python -m skoolhud.cli` because the package is imported before
# the module execution finishes. Import submodules lazily where needed.

# If you need package-level convenience imports, import them explicitly in
# runtime code (e.g., `from skoolhud import cli`) rather than here.
