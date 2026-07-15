"""Ponto de entrada da Vercel para o painel web. Apenas reexporta o app Flask
definido em webapp/app.py (mesma logica usada localmente)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from webapp.app import app  # noqa: E402,F401
