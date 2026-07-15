"""Configuracoes globais. Le do .env localmente e das variaveis de ambiente na Vercel.
A configuracao dos PROJETOS (pasta, canal, mensagem, agenda) vive no Supabase (db.py),
nao mais em arquivos locais - assim funciona igual local e na nuvem."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from window import ActiveWindow

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# ----- Segredos / globais -----
DISCORD_TOKEN = env("DISCORD_TOKEN")
SUPABASE_URL = env("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = env("SUPABASE_SERVICE_ROLE_KEY")

# Credencial do Google: em produção (Vercel) vem como o JSON inteiro numa env var
# (não dá para gravar arquivo). Localmente também aceitamos um arquivo em disco.
GOOGLE_SERVICE_ACCOUNT_JSON = env("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_CREDENTIALS_FILE = str(BASE_DIR / env("GOOGLE_CREDENTIALS_FILE", "credentials/service_account.json"))

# Protege o painel web (login simples) e o endpoint de checagem (chamado pelo GitHub Actions)
PANEL_PASSWORD = env("PANEL_PASSWORD")
CRON_SECRET = env("CRON_SECRET")


def google_credentials():
    """Retorna as credenciais do Google: um dict (se veio de env var JSON) ou um
    caminho de arquivo (fallback local)."""
    if GOOGLE_SERVICE_ACCOUNT_JSON.strip():
        import json
        return json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    return GOOGLE_CREDENTIALS_FILE


def credentials_ok() -> bool:
    if GOOGLE_SERVICE_ACCOUNT_JSON.strip():
        return True
    return Path(GOOGLE_CREDENTIALS_FILE).exists()


class Project:
    """Envolve uma linha da tabela `projects` do Supabase com a mesma interface
    que o resto do codigo (checker.py, webapp) ja espera."""

    def __init__(self, row: dict, timezone: str):
        self.row = row
        self.id = row["id"]
        self.name = row.get("name", "Sem nome")
        self.midias_folder_id = (row.get("midias_folder_id") or "").strip()
        self.required_indices = set(int(n) for n in (row.get("required_indices") or []))
        self.channel_id = int(row.get("discord_channel_id") or 0)
        self.message_text = row.get("message_text", "")
        self.window = ActiveWindow(
            timezone,
            row.get("active_days", ""),
            row.get("active_start", ""),
            row.get("active_end", ""),
        )

    def read_message(self) -> str:
        return self.message_text

    def is_configured(self) -> bool:
        return (
            self.channel_id > 0
            and bool(self.midias_folder_id)
            and len(self.required_indices) > 0
        )


def load_projects(timezone: str) -> list[Project]:
    import db
    return [Project(row, timezone) for row in db.list_projects()]
