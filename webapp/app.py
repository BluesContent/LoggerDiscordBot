"""Painel web (Flask) para administrar o bot Multicorder. Roda tanto localmente
quanto na Vercel (api/index.py importa `app` daqui). Toda a config de projetos e
o estado (quem ja foi avisado) vivem no Supabase — nao ha mais arquivos locais."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, session, redirect, make_response

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import config  # noqa: E402
import checker  # noqa: E402
import db  # noqa: E402
from drive import Drive  # noqa: E402
from notifier import Discord, DiscordError  # noqa: E402

app = Flask(__name__, static_folder=None)
app.secret_key = config.env("FLASK_SECRET_KEY", "") or "dev-only-insecure-key-troque-no-.env"

LOGIN_HTML = """<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<title>Login — Painel Multicorder</title>
<style>
body{{font-family:-apple-system,Segoe UI,sans-serif;background:#0f1117;color:#e6e8ee;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
.box{{background:#1a1d27;border:1px solid #2e3446;border-radius:14px;padding:36px;width:320px}}
h1{{font-size:20px;margin:0 0 18px}}
input{{width:100%;padding:10px 12px;border-radius:8px;border:1px solid #2e3446;background:#0f1117;
color:#e6e8ee;font-size:14px;box-sizing:border-box;margin-bottom:12px}}
button{{width:100%;padding:10px;border:none;border-radius:8px;background:#5865F2;color:#fff;
font-size:14px;cursor:pointer}}
.err{{color:#f6a3a3;font-size:13px;margin-bottom:10px}}
</style></head><body>
<form class="box" method="POST">
  <h1>🎬 Painel Multicorder</h1>
  {error}
  <input type="password" name="password" placeholder="Senha" autofocus>
  <button type="submit">Entrar</button>
</form>
</body></html>"""


def _auth_required() -> bool:
    return bool(config.PANEL_PASSWORD)


@app.before_request
def require_login():
    if not _auth_required():
        return None
    if request.path == "/login" or request.path.startswith("/static"):
        return None
    if session.get("authed"):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "não autenticado"}), 401
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if not _auth_required():
        return redirect("/")
    error = ""
    if request.method == "POST":
        if request.form.get("password", "") == config.PANEL_PASSWORD:
            session["authed"] = True
            return redirect("/")
        error = '<div class="err">Senha incorreta.</div>'
    return LOGIN_HTML.format(error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ===================== Helpers =====================
def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "projeto"


def _discord() -> Discord:
    return Discord(config.DISCORD_TOKEN)


def _project_out(row: dict) -> dict:
    """discord_channel_id como STRING — snowflakes do Discord estouram o Number do JS."""
    q = dict(row)
    q["discord_channel_id"] = str(row.get("discord_channel_id", 0) or 0)
    return q


# ===================== Página =====================
@app.route("/")
def index():
    return send_from_directory(Path(__file__).parent / "templates", "index.html")


# ===================== Config global =====================
@app.get("/api/config")
def get_config():
    settings = db.get_settings()
    return jsonify({
        "token_set": bool(config.DISCORD_TOKEN),
        "poll_interval": int(settings.get("poll_interval_seconds", 300)),
        "timezone": settings.get("timezone", "America/Sao_Paulo"),
        "date_format": settings.get("date_format", "%Y%m%d"),
        "credentials_ok": config.credentials_ok(),
        "monitoring_enabled": settings.get("monitoring_enabled", "true") == "true",
    })


@app.post("/api/config")
def set_config():
    data = request.get_json(force=True)
    if "poll_interval" in data:
        db.set_setting("poll_interval_seconds", str(int(data["poll_interval"])))
    if data.get("timezone"):
        db.set_setting("timezone", str(data["timezone"]))
    if data.get("date_format"):
        db.set_setting("date_format", str(data["date_format"]))
    return get_config()


# ===================== Discord (consultas) =====================
@app.get("/api/discord/guilds")
def discord_guilds():
    try:
        return jsonify({"guilds": _discord().list_guilds()})
    except DiscordError as e:
        return jsonify({"error": str(e)}), 400


@app.get("/api/discord/<guild_id>/channels")
def discord_channels(guild_id):
    try:
        return jsonify({"channels": _discord().list_text_channels(guild_id)})
    except DiscordError as e:
        return jsonify({"error": str(e)}), 400


@app.get("/api/discord/<guild_id>/roles")
def discord_roles(guild_id):
    try:
        return jsonify({"roles": _discord().list_roles(guild_id)})
    except DiscordError as e:
        return jsonify({"error": str(e)}), 400


@app.get("/api/discord/guild-of-channel/<channel_id>")
def guild_of_channel(channel_id):
    try:
        return jsonify({"guild_id": _discord().guild_of_channel(channel_id)})
    except DiscordError as e:
        return jsonify({"error": str(e)}), 400


# ===================== Projetos =====================
@app.get("/api/projects")
def list_projects():
    return jsonify({"projects": [_project_out(r) for r in db.list_projects()]})


@app.post("/api/projects")
def add_project():
    data = request.get_json(force=True)
    name = data.get("name") or "Novo projeto"
    row = db.create_project({
        "name": name,
        "midias_folder_id": data.get("midias_folder_id", ""),
        "required_indices": data.get("required_indices", [1, 2, 3, 4, 5, 6]),
        "discord_channel_id": int(data.get("discord_channel_id", 0) or 0),
        "message_text": data.get("message_text",
            "🎬 **Gravação finalizada!**\n\nA pasta **{path}** (data {date}) já está com todos os arquivos no Drive.\n\n📁 {link}"),
        "active_days": data.get("active_days", ""),
        "active_start": data.get("active_start", ""),
        "active_end": data.get("active_end", ""),
    })
    return jsonify({"projects": [_project_out(r) for r in db.list_projects()], "created_id": row["id"]})


@app.put("/api/projects/<project_id>")
def update_project(project_id):
    data = request.get_json(force=True)
    patch = {}
    for key in ("name", "midias_folder_id", "active_days", "active_start", "active_end"):
        if key in data:
            patch[key] = data[key]
    if "required_indices" in data:
        patch["required_indices"] = [int(n) for n in data["required_indices"]]
    if "discord_channel_id" in data:
        patch["discord_channel_id"] = int(data["discord_channel_id"] or 0)
    if "message" in data:
        patch["message_text"] = data["message"]
    try:
        db.update_project(project_id, patch)
    except db.DBError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"projects": [_project_out(r) for r in db.list_projects()]})


@app.delete("/api/projects/<project_id>")
def delete_project(project_id):
    db.delete_project(project_id)
    return jsonify({"projects": [_project_out(r) for r in db.list_projects()]})


@app.get("/api/projects/<project_id>/message")
def get_message(project_id):
    row = db.get_project(project_id)
    if not row:
        return jsonify({"error": "projeto inexistente"}), 404
    return jsonify({"text": row.get("message_text", "")})


@app.put("/api/projects/<project_id>/message")
def set_message(project_id):
    text = request.get_json(force=True).get("text", "")
    try:
        db.update_project(project_id, {"message_text": text})
    except db.DBError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"ok": True})


def _settings():
    s = db.get_settings()
    return s.get("timezone", "America/Sao_Paulo"), s.get("date_format", "%Y%m%d")


@app.get("/api/projects/<project_id>/status")
def project_status(project_id):
    row = db.get_project(project_id)
    if not row:
        return jsonify({"error": "projeto inexistente"}), 404
    if not config.credentials_ok():
        return jsonify({"error": "credencial do Google não encontrada"}), 400
    timezone, date_format = _settings()
    project = config.Project(row, timezone)
    drive = Drive(config.google_credentials())
    date = request.args.get("date") or None
    return jsonify(checker.project_status(project, drive, timezone, date_format, date))


@app.post("/api/projects/<project_id>/test")
def test_send(project_id):
    row = db.get_project(project_id)
    if not row:
        return jsonify({"error": "projeto inexistente"}), 404
    timezone, date_format = _settings()
    project = config.Project(row, timezone)
    if project.channel_id <= 0:
        return jsonify({"error": "defina o canal do Discord primeiro"}), 400
    date_name = date_format
    try:
        if config.credentials_ok():
            date_name = Drive(config.google_credentials()).today_folder_name(timezone, date_format)
    except Exception:
        pass
    sample = project.read_message().format(
        project=project.name, video="EXEMPLO", path="VIRAL / EXEMPLO",
        date=date_name, link="https://drive.google.com/drive/folders/EXEMPLO",
    )
    try:
        _discord().send_message(project.channel_id, "🧪 **[TESTE]**\n" + sample)
        return jsonify({"ok": True})
    except DiscordError as e:
        return jsonify({"error": str(e)}), 400


# ===================== Bot / e-mail do robô =====================
@app.get("/api/bot-email")
def bot_email():
    try:
        creds = config.google_credentials()
        if isinstance(creds, dict):
            return jsonify({"email": creds.get("client_email", "")})
        import json as _json
        data = _json.loads(Path(creds).read_text(encoding="utf-8"))
        return jsonify({"email": data.get("client_email", "")})
    except Exception as e:  # noqa
        return jsonify({"email": "", "error": str(e)})


# ===================== Histórico =====================
@app.get("/api/history")
def history():
    return jsonify({"history": db.history()})


@app.post("/api/history/forget")
def forget():
    fid = request.get_json(force=True).get("folder_id", "")
    return jsonify({"ok": db.forget_notified(fid)})


# ===================== "Monitoramento" (liga/desliga o flag global) =====================
@app.get("/api/runner")
def runner_status():
    s = db.get_settings()
    return jsonify({
        "running": s.get("monitoring_enabled", "true") == "true",
        "last_run": s.get("last_run_at"),
        "last_error": s.get("last_run_error") or None,
        "poll_interval": int(s.get("poll_interval_seconds", 300)),
    })


@app.post("/api/runner/start")
def runner_start():
    db.set_setting("monitoring_enabled", "true")
    return runner_status()


@app.post("/api/runner/stop")
def runner_stop():
    db.set_setting("monitoring_enabled", "false")
    return jsonify({"running": False})


if __name__ == "__main__":
    print("Painel Multicorder em http://127.0.0.1:5001")
    app.run(host="127.0.0.1", port=5001, threaded=True)
