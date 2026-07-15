"""Endpoint chamado periodicamente (pelo GitHub Actions) para fazer UMA verificacao
do Drive e enviar mensagens no Discord. Protegido por um segredo (CRON_SECRET) —
sem ele, ninguem mais consegue disparar isso."""
from __future__ import annotations

import sys
from datetime import datetime, timezone as tz
from pathlib import Path

from flask import Flask, jsonify, request

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import config  # noqa: E402
import db  # noqa: E402
import checker  # noqa: E402

app = Flask(__name__)


@app.route("/api/cron", methods=["GET", "POST"])
def cron():
    secret = request.headers.get("X-Cron-Secret") or request.args.get("secret", "")
    if not config.CRON_SECRET or secret != config.CRON_SECRET:
        return jsonify({"error": "não autorizado"}), 401

    results = checker.run_all()

    db.set_setting("last_run_at", datetime.now(tz.utc).isoformat())
    errors = [f"{r['name']}: {r['error']}" for r in results if r.get("error")]
    db.set_setting("last_run_error", "; ".join(errors))

    return jsonify({"ok": True, "results": results})


if __name__ == "__main__":
    app.run(port=5002)
