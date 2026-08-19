"""Acesso aos recursos de inventário do GLPI (Computer, Monitor, Printer, PDU)."""
from __future__ import annotations

from domain.models import Equipamento, InventarioFilial
from glpi.client import GLPIClient
from glpi.locations_repo import filtrar_por_localizacao

TIPOS_INVENTARIO = {
    "computadores": "Computer",
    "monitores": "Monitor",
    "impressoras": "Printer",
    "pdus": "PDU",
}


def buscar_inventario_localizacao(client: GLPIClient, localizacao_id: int) -> InventarioFilial:
    inventario = InventarioFilial()

    for campo, itemtype in TIPOS_INVENTARIO.items():
        # Pede pro GLPI já filtrar por locations_id no servidor. O filtro do
        # GLPI é "contém", então ainda cruzamos com filtrar_por_localizacao
        # para garantir o resultado exato - mas o volume trafegado já vem
        # bem menor do que a tabela inteira.
        itens_brutos = client.list_all(itemtype, filtros={"locations_id": localizacao_id})
        itens_brutos = filtrar_por_localizacao(itens_brutos, localizacao_id)
        equipamentos = [Equipamento.from_glpi(item, itemtype) for item in itens_brutos]
        setattr(inventario, campo, equipamentos)

    return inventario
