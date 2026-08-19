"""
Configuração central de logging.

Sem isso, quando uma loja liga dizendo "não consegui abrir chamado
ontem às 15h", a única forma de investigar era perguntar pra ela o que
apareceu na tela. Com logging, existe um arquivo (`logs/portal.log`)
com data/hora, o que aconteceu e qual erro o GLPI devolveu.

Uso em qualquer módulo do projeto:

    from core.logging_config import obter_logger
    logger = obter_logger(__name__)
    logger.info("Chamado #%s criado para a filial %s", chamado.id, localizacao.nome)

Nunca logar senha, token de sessão ou App-Token - só o necessário para
investigar um problema depois.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

NOME_LOGGER_RAIZ = "portal_loja"
PASTA_LOGS = Path(__file__).resolve().parent.parent / "logs"
ARQUIVO_LOG = PASTA_LOGS / "portal.log"

_JA_CONFIGURADO = False


def configurar_logging() -> None:
    """
    Configura o logger raiz da aplicação. Chame uma vez, no início do
    `app.py`. É seguro chamar de novo (ex: a cada rerun do Streamlit) -
    a segunda chamada não duplica os handlers.
    """
    global _JA_CONFIGURADO

    if _JA_CONFIGURADO:
        return

    nivel = os.getenv("LOG_LEVEL", "INFO").upper()
    logger_raiz = logging.getLogger(NOME_LOGGER_RAIZ)
    logger_raiz.setLevel(nivel)

    formato = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(formato)
    logger_raiz.addHandler(console)

    try:
        PASTA_LOGS.mkdir(exist_ok=True)
        arquivo = RotatingFileHandler(
            ARQUIVO_LOG, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
        )
        arquivo.setFormatter(formato)
        logger_raiz.addHandler(arquivo)
    except OSError:
        # Se o disco for somente-leitura (alguns ambientes de container),
        # a aplicação continua funcionando só com log no console/stdout,
        # que o `docker logs` já captura.
        logger_raiz.warning("Não foi possível criar logs/portal.log - logando só no console.")

    logger_raiz.propagate = False
    _JA_CONFIGURADO = True


def obter_logger(nome_modulo: str) -> logging.Logger:
    """Use sempre `obter_logger(__name__)` no topo do módulo."""
    return logging.getLogger(f"{NOME_LOGGER_RAIZ}.{nome_modulo}")
