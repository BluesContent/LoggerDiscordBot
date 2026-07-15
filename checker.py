"""Nucleo sincrono de verificacao: olha o Drive e (opcionalmente) envia no Discord.
Usado pelo painel web e pelo endpoint da Vercel (api/cron.py). Todo o estado
(projetos, quem ja foi avisado, configuracoes) vive no Supabase (db.py)."""
from __future__ import annotations

import config
import db
from drive import Drive
from notifier import Discord


def _format_message(project: config.Project, folder: dict, date_name: str) -> str:
    return project.read_message().format(
        project=project.name,
        video=folder["name"],
        path=folder["path"],
        date=date_name,
        link=Drive.folder_link(folder["id"]),
    )


def project_status(project: config.Project, drive: Drive, timezone: str, date_format: str,
                    date_override: str | None = None) -> dict:
    """So LEITURA: devolve as pastas encontradas e o status de cada uma. Nao envia nada."""
    out = {"name": project.name, "configured": project.is_configured(),
           "active": project.window.is_active(), "window": project.window.describe(),
           "date": None, "date_found": False, "folders": [], "error": None}
    if not project.is_configured():
        out["error"] = "Projeto incompleto (falta pasta, canal ou índices)."
        return out
    try:
        if date_override:
            date_name = date_override
            date_folder = drive._find_child_folder_by_name(project.midias_folder_id, date_name)
        else:
            date_folder, date_name = drive.get_today_folder(project.midias_folder_id, timezone, date_format)
        out["date"] = date_name
        if not date_folder:
            return out
        out["date_found"] = True
        for f in drive.walk_recording_folders(date_folder["id"]):
            complete = drive.is_complete(f["numbers"], project.required_indices)
            out["folders"].append({
                "id": f["id"],
                "path": f["path"],
                "numbers": sorted(f["numbers"]),
                "missing": sorted(project.required_indices - f["numbers"]),
                "complete": complete,
                "notified": db.is_notified(f["id"]),
                "link": Drive.folder_link(f["id"]),
            })
        out["folders"].sort(key=lambda x: x["path"])
    except Exception as e:  # noqa
        out["error"] = str(e)
    return out


def run_project(project: config.Project, drive: Drive, discord: Discord, timezone: str,
                 date_format: str, ignore_window: bool = False) -> dict:
    """Verifica e ENVIA mensagem para as pastas completas ainda nao avisadas."""
    result = {"name": project.name, "sent": [], "skipped_window": False, "error": None}
    if not project.is_configured():
        result["error"] = "não configurado"
        return result
    if not ignore_window and not project.window.is_active():
        result["skipped_window"] = True
        return result
    try:
        date_folder, date_name = drive.get_today_folder(project.midias_folder_id, timezone, date_format)
        if not date_folder:
            return result
        for folder in drive.walk_recording_folders(date_folder["id"]):
            if db.is_notified(folder["id"]):
                continue
            if drive.is_complete(folder["numbers"], project.required_indices):
                msg = _format_message(project, folder, date_name)
                discord.send_message(project.channel_id, msg)
                db.mark_notified(folder["id"], project.id, project.name, folder["path"],
                                  date_name, project.channel_id)
                result["sent"].append(folder["path"])
    except Exception as e:  # noqa
        result["error"] = str(e)
    return result


def run_all(ignore_window: bool = False) -> list[dict]:
    settings = db.get_settings()
    if settings.get("monitoring_enabled", "true") != "true" and not ignore_window:
        return [{"name": "(global)", "sent": [], "skipped_window": True,
                 "error": None, "note": "monitoramento desligado nas configurações"}]
    timezone = settings.get("timezone", "America/Sao_Paulo")
    date_format = settings.get("date_format", "%Y%m%d")
    drive = Drive(config.google_credentials())
    discord = Discord(config.DISCORD_TOKEN)
    projects = config.load_projects(timezone)
    return [run_project(p, drive, discord, timezone, date_format, ignore_window) for p in projects]
