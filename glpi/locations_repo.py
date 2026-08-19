"""Acesso ao recurso Location/ITILCategory do GLPI."""
from __future__ import annotations

from domain.models import Categoria, Localizacao
from glpi.client import GLPIClient


def listar_localizacoes(client: GLPIClient) -> list[Localizacao]:
    dados = client.list_all("Location")
    localizacoes = [Localizacao.from_glpi(item) for item in dados if item.get("name")]
    return sorted(localizacoes, key=lambda loc: loc.nome)


def buscar_localizacao(client: GLPIClient, localizacao_id: int) -> Localizacao:
    return Localizacao.from_glpi(client.get_item("Location", localizacao_id))


def listar_categorias_ativas(client: GLPIClient) -> list[Categoria]:
    dados = client.list_all("ITILCategory")
    categorias = [Categoria.from_glpi(item) for item in dados if item.get("is_active", 1) == 1]
    return sorted(categorias, key=lambda cat: cat.nome)


def filtrar_por_localizacao(itens: list[dict], localizacao_id: int) -> list[dict]:
    return [item for item in itens if str(item.get("locations_id")) == str(localizacao_id)]
