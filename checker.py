"""Nucleo sincrono de verificacao: olha o Drive e (opcionalmente) envia no Discord.
Usado pelo painel web, pelo bot.py (loop) e, futuramente, pela funcao da Vercel."""
from __future__ import annotations

import config
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


def project_status(project: config.Project, drive: Drive, state, date_override: str | None = None) -> dict:
    """So LEITURA: devolve as pastas encontradas e o status de cada uma.
    Nao envia nada."""
    out = {"name": project.name, "configured": project.is_configured(),
           "active": project.window.is_active(), "window": project.window.describe(),
           "date": None, "date_found": False, "folders": [], "error": None}
    if not project.is_configured():
        out["error"] = "Projeto incompleto (falta pasta, canal ou indices)."
        return out
    try:
        if date_override:
            date_name = date_override
            date_folder = drive._find_child_folder_by_name(project.midias_folder_id, date_name)
        else:
            date_folder, date_name = drive.get_today_folder(
                project.midias_folder_id, config.timezone(), config.date_format())
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
                "notified": state.already_notified(f["id"]),
                "link": Drive.folder_link(f["id"]),
            })
        out["folders"].sort(key=lambda x: x["path"])
    except Exception as e:  # noqa
        out["error"] = str(e)
    return out


def run_project(project: config.Project, drive: Drive, state, discord: Discord,
                ignore_window: bool = False) -> dict:
    """Verifica e ENVIA mensagem para as pastas completas ainda nao avisadas."""
    result = {"name": project.name, "sent": [], "skipped_window": False, "error": None}
    if not project.is_configured():
        result["error"] = "nao configurado"
        return result
    if not ignore_window and not project.window.is_active():
        result["skipped_window"] = True
        return result
    try:
        date_folder, date_name = drive.get_today_folder(
            project.midias_folder_id, config.timezone(), config.date_format())
        if not date_folder:
            return result
        for folder in drive.walk_recording_folders(date_folder["id"]):
            if state.already_notified(folder["id"]):
                continue
            if drive.is_complete(folder["numbers"], project.required_indices):
                msg = _format_message(project, folder, date_name)
                discord.send_message(project.channel_id, msg)
                state.mark_notified(folder["id"], {
                    "project": project.name, "path": folder["path"],
                    "date": date_name, "channel_id": project.channel_id,
                })
                result["sent"].append(folder["path"])
    except Exception as e:  # noqa
        result["error"] = str(e)
    return result


def run_all(ignore_window: bool = False) -> list[dict]:
    drive = Drive(config.google_credentials_file())
    from state import State
    state = State(config.STATE_FILE, config.timezone())
    discord = Discord(config.discord_token())
    return [run_project(p, drive, state, discord, ignore_window) for p in config.load_projects()]
