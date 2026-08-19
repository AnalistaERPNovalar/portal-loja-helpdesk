"""Serviço de equipamentos (inventário) da filial."""
from __future__ import annotations

from domain.models import InventarioFilial
from glpi.client import GLPIClient
from glpi.inventory_repo import buscar_inventario_localizacao


def buscar_inventario(client: GLPIClient, localizacao_id: int) -> InventarioFilial:
    return buscar_inventario_localizacao(client, localizacao_id)
