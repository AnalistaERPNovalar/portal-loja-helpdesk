"""Acesso ao recurso User do GLPI."""
from __future__ import annotations

from domain.models import Usuario
from glpi.client import GLPIClient


def buscar_usuario(client: GLPIClient, user_id: int, login_fallback: str = "") -> Usuario:
    dados = client.get_item("User", user_id)
    return Usuario.from_glpi(dados, login_fallback=login_fallback)


def nome_usuario(client: GLPIClient, user_id: int) -> str:
    usuario = buscar_usuario(client, user_id)
    return usuario.nome or f"Usuário ID {user_id}"
