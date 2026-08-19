"""
Configuração central da aplicação.

Todo valor que vem do ambiente (.env) passa por aqui.
Nenhum outro módulo deve chamar os.getenv diretamente - assim, se
amanhã precisar trocar de variável, mudar um default, ou validar algo,
existe um único lugar para mexer.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    glpi_url: str
    app_token: str
    user_token: str | None = None

    def validar(self) -> list[str]:
        """Retorna a lista de problemas de configuração (vazia se estiver tudo ok)."""
        problemas = []

        if not self.glpi_url:
            problemas.append("GLPI_URL não definida no .env")

        if not self.app_token:
            problemas.append("APP_TOKEN não definida no .env")

        return problemas


def carregar_settings() -> Settings:
    return Settings(
        glpi_url=(os.getenv("GLPI_URL") or "").rstrip("/"),
        app_token=os.getenv("APP_TOKEN", ""),
        user_token=os.getenv("USER_TOKEN") or None,
    )


settings = carregar_settings()
