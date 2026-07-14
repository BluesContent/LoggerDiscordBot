"""Configuracoes globais (.env) e lista de projetos (projects.json).
Feito para ser lido E escrito pelo painel web, sem travar se algo faltar."""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv, set_key

from window import ActiveWindow

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
PROJECTS_FILE = BASE_DIR / "projects.json"
STATE_FILE = BASE_DIR / "state.json"
MESSAGES_DIR = BASE_DIR / "messages"
CREDENTIALS_DEFAULT = "credentials/service_account.json"

_DEFAULTS = {
    "POLL_INTERVAL_SECONDS": "300",
    "TIMEZONE": "America/Sao_Paulo",
    "DATE_FORMAT": "%Y%m%d",
    "GOOGLE_CREDENTIALS_FILE": CREDENTIALS_DEFAULT,
    "DISCORD_TOKEN": "",
}


def reload_env() -> None:
    load_dotenv(ENV_FILE, override=True)


reload_env()


# ---------- leitura/escrita de globais (.env) ----------
def get(key: str, default: str | None = None) -> str:
    val = os.getenv(key)
    if val is None or val == "":
        return _DEFAULTS.get(key, "") if default is None else default
    return val


def set_env(key: str, value: str) -> None:
    if not ENV_FILE.exists():
        ENV_FILE.write_text("", encoding="utf-8")
    set_key(str(ENV_FILE), key, value)
    reload_env()


def discord_token() -> str:
    return get("DISCORD_TOKEN", "")


def google_credentials_file() -> str:
    return str(BASE_DIR / get("GOOGLE_CREDENTIALS_FILE", CREDENTIALS_DEFAULT))


def credentials_ok() -> bool:
    return Path(google_credentials_file()).exists()


def poll_interval() -> int:
    try:
        return int(get("POLL_INTERVAL_SECONDS", "300"))
    except ValueError:
        return 300


def timezone() -> str:
    return get("TIMEZONE", "America/Sao_Paulo")


def date_format() -> str:
    return get("DATE_FORMAT", "%Y%m%d")


# ---------- projetos ----------
class Project:
    """Um projeto = uma pasta MIDIAS + regras proprias de deteccao, canal e mensagem."""

    def __init__(self, raw: dict):
        self.raw = raw
        self.name = raw.get("name", "Sem nome")
        self.midias_folder_id = str(raw.get("midias_folder_id", "")).strip()
        self.required_indices = set(int(n) for n in raw.get("required_indices", []))
        try:
            self.channel_id = int(raw.get("discord_channel_id", 0) or 0)
        except (TypeError, ValueError):
            self.channel_id = 0
        self.message_file = BASE_DIR / raw.get("message_file", "messages/default.txt")
        self.window = ActiveWindow(
            timezone(),
            raw.get("active_days", ""),
            raw.get("active_start", ""),
            raw.get("active_end", ""),
        )

    def read_message(self) -> str:
        if self.message_file.exists():
            return self.message_file.read_text(encoding="utf-8")
        return ""

    def is_configured(self) -> bool:
        return (
            self.channel_id > 0
            and bool(self.midias_folder_id)
            and not self.midias_folder_id.startswith("cole_")
            and len(self.required_indices) > 0
        )


def load_projects_raw() -> list[dict]:
    if not PROJECTS_FILE.exists():
        return []
    data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    return data.get("projects", [])


def save_projects_raw(projects: list[dict]) -> None:
    PROJECTS_FILE.write_text(
        json.dumps({"projects": projects}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_projects() -> list[Project]:
    return [Project(p) for p in load_projects_raw()]
