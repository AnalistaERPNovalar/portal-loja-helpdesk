"""Acesso ao plugin Formcreator do GLPI (formulários estruturados de solicitação)."""
from __future__ import annotations

from domain.models import Formulario, PerguntaFormulario, SecaoFormulario
from glpi.client import GLPIClient


def listar_formularios_ativos(client: GLPIClient) -> list[Formulario]:
    dados = client.list_all("PluginFormcreatorForm")
    return [
        Formulario.from_glpi(item)
        for item in dados
        if item.get("is_active") == 1 and item.get("is_deleted") == 0
    ]


def listar_secoes(client: GLPIClient, formulario_id: int) -> list[SecaoFormulario]:
    dados = client.list_all("PluginFormcreatorSection")
    secoes = [
        SecaoFormulario.from_glpi(item)
        for item in dados
        if item.get("plugin_formcreator_forms_id") == int(formulario_id)
    ]
    return sorted(secoes, key=lambda s: s.ordem)


def listar_perguntas(client: GLPIClient, secao_id: int) -> list[PerguntaFormulario]:
    dados = client.list_all("PluginFormcreatorQuestion")
    perguntas = [
        PerguntaFormulario.from_glpi(item)
        for item in dados
        if item.get("plugin_formcreator_sections_id") == int(secao_id)
    ]
    return sorted(perguntas, key=lambda p: p.id)
