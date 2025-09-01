
"""
Entry-Point für das skoolhud-Paket, wenn es als Skript ausgeführt wird.
Importiert die Typer-CLI und startet die Kommandozeilenanwendung.
"""
from .cli import app

if __name__ == "__main__":
    app()