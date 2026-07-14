"""Bot em modo linha de comando: fica em loop verificando o Drive e enviando no
Discord. (O painel web faz o mesmo com um botao Ligar/Desligar.)"""
from __future__ import annotations

import logging
import time

import config
import checker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("multicorder-bot")


def main():
    interval = config.poll_interval()
    log.info("Iniciando. Checando a cada %ss. Projetos: %d",
             interval, len(config.load_projects()))
    while True:
        try:
            for r in checker.run_all():
                if r["sent"]:
                    log.info("[%s] enviados: %s", r["name"], ", ".join(r["sent"]))
                elif r["error"]:
                    log.error("[%s] erro: %s", r["name"], r["error"])
        except Exception:
            log.exception("Erro no ciclo de verificacao")
        time.sleep(interval)


if __name__ == "__main__":
    main()
