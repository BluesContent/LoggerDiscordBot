"""Armazenamento 100% local (arquivos JSON em data/) — projetos, historico de
avisos e configuracoes. Mesma interface que outros modulos (checker.py,
webapp/app.py, bot.py, diagnostico.py) ja esperam, entao nada mais precisa
mudar caso um dia isso volte a ser backed por um banco na nuvem."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_FILE = DATA_DIR / "projects.json"
NOTIFIED_FILE = DATA_DIR / "notified_folders.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

_DEFAULT_SETTINGS = {
    "poll_interval_seconds": "300",
    "timezone": "America/Sao_Paulo",
    "date_format": "%Y%m%d",
    "monitoring_enabled": "true",
}

_lock = threading.Lock()


class DBError(Exception):
    pass


def _ensure_files() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not PROJECTS_FILE.exists():
        PROJECTS_FILE.write_text("[]", encoding="utf-8")
    if not NOTIFIED_FILE.exists():
        NOTIFIED_FILE.write_text("{}", encoding="utf-8")
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(json.dumps(_DEFAULT_SETTINGS, indent=2), encoding="utf-8")


def _read(path: Path, default):
    _ensure_files()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _write(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _now_iso(tz: str = "America/Sao_Paulo") -> str:
    return datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M:%S")


# ----------------------------- projects -----------------------------
def list_projects() -> list[dict]:
    with _lock:
        return _read(PROJECTS_FILE, [])


def get_project(project_id: str) -> dict | None:
    for row in list_projects():
        if row["id"] == project_id:
            return row
    return None


def create_project(data: dict) -> dict:
    with _lock:
        rows = _read(PROJECTS_FILE, [])
        row = dict(data)
        row["id"] = str(uuid.uuid4())
        row["created_at"] = _now_iso()
        row["updated_at"] = row["created_at"]
        rows.append(row)
        _write(PROJECTS_FILE, rows)
        return row


def update_project(project_id: str, data: dict) -> dict:
    with _lock:
        rows = _read(PROJECTS_FILE, [])
        for row in rows:
            if row["id"] == project_id:
                row.update(data)
                row["updated_at"] = _now_iso()
                _write(PROJECTS_FILE, rows)
                return row
        raise DBError(f"Projeto {project_id} não encontrado.")


def delete_project(project_id: str) -> None:
    with _lock:
        rows = _read(PROJECTS_FILE, [])
        rows = [r for r in rows if r["id"] != project_id]
        _write(PROJECTS_FILE, rows)


# ----------------------------- notified_folders -----------------------------
def is_notified(folder_id: str) -> bool:
    with _lock:
        return folder_id in _read(NOTIFIED_FILE, {})


def mark_notified(folder_id: str, project_id: str, project_name: str, path: str, date: str, channel_id: int) -> None:
    with _lock:
        rows = _read(NOTIFIED_FILE, {})
        rows[folder_id] = {
            "folder_id": folder_id, "project_id": project_id, "project_name": project_name,
            "path": path, "date": date, "channel_id": channel_id, "sent_at": _now_iso(),
        }
        _write(NOTIFIED_FILE, rows)


def forget_notified(folder_id: str) -> bool:
    with _lock:
        rows = _read(NOTIFIED_FILE, {})
        if folder_id in rows:
            del rows[folder_id]
            _write(NOTIFIED_FILE, rows)
            return True
        return False


def history(limit: int = 200) -> list[dict]:
    with _lock:
        rows = list(_read(NOTIFIED_FILE, {}).values())
    rows.sort(key=lambda r: r.get("sent_at", ""), reverse=True)
    return rows[:limit]


# ----------------------------- settings -----------------------------
def get_settings() -> dict:
    with _lock:
        s = dict(_DEFAULT_SETTINGS)
        s.update(_read(SETTINGS_FILE, {}))
        return s


def set_setting(key: str, value: str) -> None:
    with _lock:
        s = _read(SETTINGS_FILE, dict(_DEFAULT_SETTINGS))
        s[key] = str(value)
        _write(SETTINGS_FILE, s)
