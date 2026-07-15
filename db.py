"""Acesso ao Supabase (Postgres na nuvem) via API REST (PostgREST).
Substitui os antigos projects.json / state.json — funciona tanto local quanto
na Vercel, já que o estado fica no banco, nao em arquivos."""
from __future__ import annotations

import os

import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


class DBError(Exception):
    pass


def _headers(prefer: str | None = None) -> dict:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise DBError(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY não configurados. "
            "Preencha essas variáveis (.env local ou variáveis de ambiente na Vercel)."
        )
    h = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def _url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"


def _check(r: requests.Response):
    if not r.ok:
        raise DBError(f"Supabase {r.request.method} {r.url} -> {r.status_code}: {r.text[:300]}")
    return r


# ----------------------------- projects -----------------------------
def list_projects() -> list[dict]:
    r = _check(requests.get(_url("projects"), headers=_headers(), params={"select": "*", "order": "created_at.asc"}, timeout=15))
    return r.json()


def get_project(project_id: str) -> dict | None:
    r = _check(requests.get(_url("projects"), headers=_headers(), params={"select": "*", "id": f"eq.{project_id}"}, timeout=15))
    rows = r.json()
    return rows[0] if rows else None


def create_project(data: dict) -> dict:
    r = _check(requests.post(_url("projects"), headers=_headers("return=representation"), json=data, timeout=15))
    return r.json()[0]


def update_project(project_id: str, data: dict) -> dict:
    data = dict(data)
    data["updated_at"] = "now()"
    r = _check(requests.patch(_url("projects"), headers=_headers("return=representation"),
                               params={"id": f"eq.{project_id}"}, json=data, timeout=15))
    rows = r.json()
    if not rows:
        raise DBError(f"Projeto {project_id} não encontrado.")
    return rows[0]


def delete_project(project_id: str) -> None:
    _check(requests.delete(_url("projects"), headers=_headers(), params={"id": f"eq.{project_id}"}, timeout=15))


# ----------------------------- notified_folders -----------------------------
def is_notified(folder_id: str) -> bool:
    r = _check(requests.get(_url("notified_folders"), headers=_headers(),
                             params={"select": "folder_id", "folder_id": f"eq.{folder_id}"}, timeout=15))
    return len(r.json()) > 0


def mark_notified(folder_id: str, project_id: str, project_name: str, path: str, date: str, channel_id: int) -> None:
    payload = {
        "folder_id": folder_id, "project_id": project_id, "project_name": project_name,
        "path": path, "date": date, "channel_id": channel_id,
    }
    _check(requests.post(_url("notified_folders"), headers=_headers("resolution=merge-duplicates"), json=payload, timeout=15))


def forget_notified(folder_id: str) -> bool:
    r = _check(requests.delete(_url("notified_folders"), headers=_headers("return=representation"),
                                params={"folder_id": f"eq.{folder_id}"}, timeout=15))
    return len(r.json()) > 0


def history(limit: int = 200) -> list[dict]:
    r = _check(requests.get(_url("notified_folders"), headers=_headers(),
                             params={"select": "*", "order": "sent_at.desc", "limit": str(limit)}, timeout=15))
    return r.json()


# ----------------------------- settings -----------------------------
def get_settings() -> dict:
    r = _check(requests.get(_url("settings"), headers=_headers(), params={"select": "*"}, timeout=15))
    return {row["key"]: row["value"] for row in r.json()}


def set_setting(key: str, value: str) -> None:
    _check(requests.post(_url("settings"), headers=_headers("resolution=merge-duplicates"),
                          json={"key": key, "value": str(value)}, timeout=15))
