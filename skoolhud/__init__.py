"""
Initialisiert das skoolhud-Paket und legt fest, welche Submodule beim Import sichtbar sind.
Die __all__-Liste definiert die öffentlichen Schnittstellen des Pakets.
"""
__all__ = ["config","db","models","utils","fetcher","normalizer","cli"]

# Importiere die Submodule, damit sie über skoolhud.* verfügbar sind
from . import config, db, models, utils, fetcher, normalizer, cli
