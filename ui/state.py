"""
Acesso ao st.session_state centralizado.

No projeto antigo, chaves como "localizacao_id", "usuario_id", "pagina"
apareciam soltas, digitadas à mão, em uns 10 arquivos diferentes - um
typo em qualquer um deles quebra silenciosamente. Aqui existe uma função
por informação; se o nome da chave interna mudar, muda só aqui.
"""
from __future__ import annotations

import streamlit as st

from domain.models import SessaoUsuario
from glpi.client import GLPIClient

_CHAVE_CLIENT = "_glpi_client"
_CHAVE_SESSAO = "_sessao_usuario"
_CHAVE_PAGINA = "_pagina_atual"
_CHAVE_NAV_PENDENTE = "_navegacao_pendente"

PAGINA_PADRAO = "home"


def usuario_autenticado() -> bool:
    return _CHAVE_SESSAO in st.session_state


def salvar_login(client: GLPIClient, sessao: SessaoUsuario) -> None:
    st.session_state[_CHAVE_CLIENT] = client
    st.session_state[_CHAVE_SESSAO] = sessao
    st.session_state[_CHAVE_PAGINA] = PAGINA_PADRAO


def encerrar_sessao() -> None:
    st.session_state.clear()


def obter_client() -> GLPIClient:
    return st.session_state[_CHAVE_CLIENT]


def obter_sessao() -> SessaoUsuario:
    return st.session_state[_CHAVE_SESSAO]


def pagina_atual() -> str:
    return st.session_state.get(_CHAVE_PAGINA, PAGINA_PADRAO)


def ir_para_pagina(pagina: str) -> None:
    """Navegação disparada de fora do menu lateral (ex.: botões de "Ações
    rápidas" na Home). Marca a navegação como pendente para o menu
    lateral sincronizar o próprio widget no próximo render."""
    st.session_state[_CHAVE_PAGINA] = pagina
    st.session_state[_CHAVE_NAV_PENDENTE] = True


def sincronizar_pagina_do_menu(pagina: str) -> None:
    """Uso exclusivo do menu lateral: atualiza a página a partir da
    seleção feita no próprio rádio, sem marcar navegação pendente - senão
    o menu ficaria sobrescrevendo a própria seleção do usuário a cada
    clique."""
    st.session_state[_CHAVE_PAGINA] = pagina


def consumir_navegacao_pendente() -> bool:
    """Retorna True (e limpa a marca) se a última mudança de página veio
    de fora do menu lateral e ainda precisa ser refletida no widget."""
    return st.session_state.pop(_CHAVE_NAV_PENDENTE, False)


def flash_sucesso(mensagem: str) -> None:
    st.session_state["_flash_sucesso"] = mensagem


def flash_erro(mensagem: str) -> None:
    st.session_state["_flash_erro"] = mensagem


def consumir_flashes() -> None:
    """Mostra e limpa qualquer mensagem de sucesso/erro pendente de uma ação anterior."""
    if "_flash_sucesso" in st.session_state:
        st.success(st.session_state.pop("_flash_sucesso"))

    if "_flash_erro" in st.session_state:
        st.error(st.session_state.pop("_flash_erro"))