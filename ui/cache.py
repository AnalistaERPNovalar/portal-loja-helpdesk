"""
Cache das consultas de leitura.

Por que isso não fica dentro de services/: os serviços são testados sem
precisar do Streamlit rodando (veja tests/test_ticket_service.py), e
`st.cache_data` é uma ferramenta do Streamlit. Colocar o cache aqui, na
camada de UI, mantém `services/` puro e coloca toda decisão de "por
quanto tempo cachear o quê" num lugar só - se um dado começar a parecer
"desatualizado" pro usuário, é aqui que se mexe no TTL.

Todas as funções usam `_client` (com underscore) porque é a convenção do
Streamlit para dizer "não tente calcular hash deste argumento" - o
GLPIClient guarda estado (token de sessão) e não é hasheável de forma
estável.
"""
from __future__ import annotations

import streamlit as st

from domain.models import Categoria, Chamado, Formulario, InventarioFilial, Localizacao
from services import dashboard_service, equipment_service, ticket_service
from services.dashboard_service import ResumoFilial
from services.ticket_service import DetalheChamado

# TTL curto: dado muda o dia inteiro (chamado novo, status mudando).
TTL_DADO_OPERACIONAL = 30

# TTL longo: cadastro que quase não muda (localização, categoria, formulário).
TTL_DADO_CADASTRAL = 300


@st.cache_data(ttl=TTL_DADO_OPERACIONAL, show_spinner=False)
def resumo_filial(_client, localizacao_id: int) -> ResumoFilial:
    return dashboard_service.montar_resumo_filial(_client, localizacao_id)


@st.cache_data(ttl=TTL_DADO_OPERACIONAL, show_spinner=False)
def meus_chamados(_client, localizacao_id: int, usuario_id: int) -> list[Chamado]:
    return ticket_service.listar_meus_chamados(_client, localizacao_id, usuario_id)


@st.cache_data(ttl=TTL_DADO_OPERACIONAL, show_spinner=False)
def detalhe_chamado(_client, ticket_id: int) -> DetalheChamado:
    return ticket_service.buscar_detalhe_chamado(_client, ticket_id)


@st.cache_data(ttl=TTL_DADO_OPERACIONAL, show_spinner=False)
def inventario_filial(_client, localizacao_id: int) -> InventarioFilial:
    return equipment_service.buscar_inventario(_client, localizacao_id)


@st.cache_data(ttl=TTL_DADO_CADASTRAL, show_spinner=False)
def categorias(_client) -> list[Categoria]:
    return ticket_service.listar_categorias(_client)


@st.cache_data(ttl=TTL_DADO_CADASTRAL, show_spinner=False)
def formularios_ativos(_client) -> list[Formulario]:
    return ticket_service.listar_formularios_ativos(_client)


@st.cache_data(ttl=TTL_DADO_CADASTRAL, show_spinner=False)
def secoes_formulario(_client, formulario_id: int):
    return ticket_service.listar_secoes_formulario(_client, formulario_id)


@st.cache_data(ttl=TTL_DADO_CADASTRAL, show_spinner=False)
def perguntas_secao(_client, secao_id: int):
    return ticket_service.listar_perguntas_secao(_client, secao_id)


def invalidar_dados_operacionais() -> None:
    """
    Chame depois de qualquer escrita (abrir chamado, enviar mensagem, excluir)
    para a próxima leitura não vir do cache antigo.
    """
    resumo_filial.clear()
    meus_chamados.clear()
    detalhe_chamado.clear()


def invalidar_inventario() -> None:
    inventario_filial.clear()
