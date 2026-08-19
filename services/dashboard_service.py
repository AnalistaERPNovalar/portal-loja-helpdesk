"""Serviço do dashboard: resumo consolidado da filial (chamados + equipamentos)."""
from __future__ import annotations

from dataclasses import dataclass

from domain.models import Chamado, InventarioFilial
from glpi.client import GLPIClient
from glpi.inventory_repo import buscar_inventario_localizacao
from glpi.tickets_repo import buscar_chamados_localizacao


@dataclass
class ResumoFilial:
    chamados: list[Chamado]
    inventario: InventarioFilial

    @property
    def chamados_novos(self) -> list[Chamado]:
        return [c for c in self.chamados if c.status == 1]

    @property
    def chamados_em_atendimento(self) -> list[Chamado]:
        return [c for c in self.chamados if c.status in (2, 3, 4)]

    @property
    def chamados_abertos(self) -> list[Chamado]:
        return [c for c in self.chamados if c.esta_aberto]

    @property
    def chamados_solucionados(self) -> list[Chamado]:
        return [c for c in self.chamados if c.status == 5]

    def ultimos_chamados(self, limite: int = 5) -> list[Chamado]:
        return sorted(self.chamados, key=lambda c: c.id, reverse=True)[:limite]


def montar_resumo_filial(client: GLPIClient, localizacao_id: int) -> ResumoFilial:
    return ResumoFilial(
        chamados=buscar_chamados_localizacao(client, localizacao_id),
        inventario=buscar_inventario_localizacao(client, localizacao_id),
    )
