"""Painel web local (Flask) para administrar o bot Multicorder."""
from __future__ import annotations

import re
import sys
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

# permite importar os modulos do projeto (pasta pai)
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import config  # noqa: E402
import checker  # noqa: E402
from drive import Drive  # noqa: E402
from notifier import Discord, DiscordError  # noqa: E402
from state import State  # noqa: E402

app = Flask(__name__, static_folder=None)


# ===================== Runner (Ligar/Desligar monitoramento) =====================
class Runner:
    def __init__(self):
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.last_run = None
        self.last_summary = None
        self.last_error = None

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def _loop(self):
        while not self.stop_event.is_set():
            try:
                results = checker.run_all()
                self.last_summary = results
                self.last_error = None
                self.last_run = time.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:  # noqa
                self.last_error = str(e)
            # dorme em passos curtos para poder parar rapido
            for _ in range(max(1, config.poll_interval())):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

    def start(self):
        if self.running:
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()


runner = Runner()


# ===================== Helpers =====================
def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "projeto"


def _discord() -> Discord:
    return Discord(config.discord_token())


def _valid_index(i: int) -> bool:
    return 0 <= i < len(config.load_projects_raw())


def _projects_out(projects: list[dict]) -> list[dict]:
    """IDs do Discord (snowflakes) sao grandes demais para o Number do JS.
    Envia-os como STRING para nao perder precisao no navegador."""
    out = []
    for p in projects:
        q = dict(p)
        q["discord_channel_id"] = str(p.get("discord_channel_id", 0) or 0)
        out.append(q)
    return out


# ===================== Rotas de pagina =====================
@app.route("/")
def index():
    return send_from_directory(Path(__file__).parent / "templates", "index.html")


# ===================== Config global =====================
@app.get("/api/config")
def get_config():
    token = config.discord_token()
    return jsonify({
        "token_set": bool(token),
        "token_preview": (token[:8] + "..." + token[-4:]) if token else "",
        "poll_interval": config.poll_interval(),
        "timezone": config.timezone(),
        "date_format": config.date_format(),
        "credentials_ok": config.credentials_ok(),
    })


@app.post("/api/config")
def set_config():
    data = request.get_json(force=True)
    if "poll_interval" in data:
        config.set_env("POLL_INTERVAL_SECONDS", str(int(data["poll_interval"])))
    if "timezone" in data and data["timezone"]:
        config.set_env("TIMEZONE", str(data["timezone"]))
    if "date_format" in data and data["date_format"]:
        config.set_env("DATE_FORMAT", str(data["date_format"]))
    if data.get("token"):  # so troca se veio um token novo
        config.set_env("DISCORD_TOKEN", str(data["token"]).strip())
    return get_config()


# ===================== E-mail do robô (conta de serviço) =====================
@app.get("/api/bot-email")
def bot_email():
    import json as _json
    try:
        data = _json.loads(Path(config.google_credentials_file()).read_text(encoding="utf-8"))
        return jsonify({"email": data.get("client_email", "")})
    except Exception as e:  # noqa
        return jsonify({"email": "", "error": str(e)})


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
    return jsonify({"projects": _projects_out(config.load_projects_raw())})


@app.post("/api/projects")
def add_project():
    data = request.get_json(force=True)
    projects = config.load_projects_raw()
    name = data.get("name") or f"Projeto {len(projects) + 1}"
    msg_rel = f"messages/{_slug(name)}.txt"
    msg_path = config.BASE_DIR / msg_rel
    config.MESSAGES_DIR.mkdir(exist_ok=True)
    if not msg_path.exists():
        msg_path.write_text(
            "🎬 **Gravação finalizada!**\n\n"
            "A pasta **{path}** (data {date}) já está com todos os arquivos no Drive.\n\n"
            "📁 {link}\n",
            encoding="utf-8",
        )
    projects.append({
        "name": name,
        "midias_folder_id": data.get("midias_folder_id", ""),
        "required_indices": data.get("required_indices", [1, 2, 3, 5, 6]),
        "discord_channel_id": int(data.get("discord_channel_id", 0) or 0),
        "message_file": msg_rel,
        "active_days": data.get("active_days", ""),
        "active_start": data.get("active_start", ""),
        "active_end": data.get("active_end", ""),
    })
    config.save_projects_raw(projects)
    return jsonify({"projects": _projects_out(projects)})


@app.put("/api/projects/<int:i>")
def update_project(i):
    if not _valid_index(i):
        return jsonify({"error": "projeto inexistente"}), 404
    data = request.get_json(force=True)
    projects = config.load_projects_raw()
    p = projects[i]
    for key in ("name", "midias_folder_id", "active_days", "active_start", "active_end"):
        if key in data:
            p[key] = data[key]
    if "required_indices" in data:
        p["required_indices"] = [int(n) for n in data["required_indices"]]
    if "discord_channel_id" in data:
        p["discord_channel_id"] = int(data["discord_channel_id"] or 0)
    projects[i] = p
    config.save_projects_raw(projects)
    return jsonify({"projects": _projects_out(projects)})


@app.delete("/api/projects/<int:i>")
def delete_project(i):
    if not _valid_index(i):
        return jsonify({"error": "projeto inexistente"}), 404
    projects = config.load_projects_raw()
    projects.pop(i)
    config.save_projects_raw(projects)
    return jsonify({"projects": _projects_out(projects)})


@app.get("/api/projects/<int:i>/message")
def get_message(i):
    if not _valid_index(i):
        return jsonify({"error": "projeto inexistente"}), 404
    return jsonify({"text": config.load_projects()[i].read_message()})


@app.put("/api/projects/<int:i>/message")
def set_message(i):
    if not _valid_index(i):
        return jsonify({"error": "projeto inexistente"}), 404
    text = request.get_json(force=True).get("text", "")
    proj = config.load_projects()[i]
    proj.message_file.parent.mkdir(exist_ok=True)
    proj.message_file.write_text(text, encoding="utf-8")
    return jsonify({"ok": True})


@app.get("/api/projects/<int:i>/status")
def project_status(i):
    if not _valid_index(i):
        return jsonify({"error": "projeto inexistente"}), 404
    if not config.credentials_ok():
        return jsonify({"error": "credencial do Google nao encontrada"}), 400
    drive = Drive(config.google_credentials_file())
    state = State(config.STATE_FILE, config.timezone())
    date = request.args.get("date") or None
    return jsonify(checker.project_status(config.load_projects()[i], drive, state, date))


@app.post("/api/projects/<int:i>/test")
def test_send(i):
    if not _valid_index(i):
        return jsonify({"error": "projeto inexistente"}), 404
    proj = config.load_projects()[i]
    if proj.channel_id <= 0:
        return jsonify({"error": "defina o canal do Discord primeiro"}), 400
    sample = proj.read_message().format(
        project=proj.name, video="EXEMPLO", path="VIRAL / EXEMPLO",
        date=Drive(config.google_credentials_file()).today_folder_name(
            config.timezone(), config.date_format()) if config.credentials_ok() else "20260714",
        link="https://drive.google.com/drive/folders/EXEMPLO",
    )
    try:
        _discord().send_message(proj.channel_id, "🧪 **[TESTE]**\n" + sample)
        return jsonify({"ok": True})
    except DiscordError as e:
        return jsonify({"error": str(e)}), 400


# ===================== Historico =====================
@app.get("/api/history")
def history():
    return jsonify({"history": State(config.STATE_FILE, config.timezone()).history()})


@app.post("/api/history/forget")
def forget():
    fid = request.get_json(force=True).get("folder_id", "")
    ok = State(config.STATE_FILE, config.timezone()).forget(fid)
    return jsonify({"ok": ok})


# ===================== Runner =====================
@app.get("/api/runner")
def runner_status():
    return jsonify({
        "running": runner.running,
        "last_run": runner.last_run,
        "last_error": runner.last_error,
        "poll_interval": config.poll_interval(),
    })


@app.post("/api/runner/start")
def runner_start():
    runner.start()
    return runner_status()


@app.post("/api/runner/stop")
def runner_stop():
    runner.stop()
    return jsonify({"running": False})


if __name__ == "__main__":
    print("Painel Multicorder em http://127.0.0.1:5001")
    app.run(host="127.0.0.1", port=5001, threaded=True)
