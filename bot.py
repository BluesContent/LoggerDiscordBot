"""Modo linha de comando (opcional, para testar localmente): fica em loop
verificando o Drive e enviando no Discord. Na nuvem, quem faz esse papel é o
endpoint api/cron.py, chamado periodicamente pelo GitHub Actions."""
from __future__ import annotations

import logging
import time

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("multicorder-bot")


def main():
    import checker
    while True:
        interval = int(db.get_settings().get("poll_interval_seconds", 300))
        try:
            for r in checker.run_all():
                if r.get("sent"):
                    log.info("[%s] enviados: %s", r["name"], ", ".join(r["sent"]))
                elif r.get("error"):
                    log.error("[%s] erro: %s", r["name"], r["error"])
        except Exception:
            log.exception("Erro no ciclo de verificação")
        time.sleep(interval)


if __name__ == "__main__":
    main()
