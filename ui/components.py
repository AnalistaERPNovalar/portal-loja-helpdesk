"""
Componentes de UI reutilizáveis.

Cada função aqui renderiza um pedaço visual usado em mais de uma página
(cabeçalho, card de indicador, card de chamado...). Isso evita copiar e
colar blocos de st.markdown(f'<div>...') repetidos entre as páginas,
como acontecia no projeto antigo.
"""
from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st

from domain.models import Chamado

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


@st.cache_data(show_spinner=False)
def _imagem_base64(caminho: Path) -> str:
    if not caminho.exists():
        return ""
    return base64.b64encode(caminho.read_bytes()).decode()


def logo_base64() -> str:
    return _imagem_base64(ASSETS_DIR / "logo.png")


def background_login_base64() -> str:
    return _imagem_base64(ASSETS_DIR / "background_login.png")


def cabecalho(titulo: str, subtitulo: str = "Portal Loja e Abertura de Chamados") -> None:
    st.markdown('<div class="brand-bar"></div>', unsafe_allow_html=True)
    st.markdown(f"## {titulo}")
    st.caption(subtitulo)
    st.markdown("---")


def card_metrica(icone: str, titulo: str, valor, descricao: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="icone">{icone}</div>
            <div class="titulo">{html.escape(titulo)}</div>
            <div class="valor">{valor}</div>
            <div class="desc">{html.escape(descricao)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge_status(chamado: Chamado) -> str:
    return f'<span class="badge" style="background:{chamado.status_cor};">{chamado.status_nome.upper()}</span>'


def card_chamado(chamado: Chamado, previa_max_chars: int = 220) -> None:
    from services.ticket_service import limpar_html

    descricao = limpar_html(chamado.descricao_html)
    previa = descricao[:previa_max_chars] + "..." if len(descricao) > previa_max_chars else descricao
    previa = previa or "Clique para visualizar os detalhes completos."

    st.markdown(
        f"""
        <div class="ticket-card">
            <div class="titulo">
                <span>#{chamado.id} &nbsp; {html.escape(chamado.titulo)}</span>
                {badge_status(chamado)}
            </div>
            <div class="meta">📅 Aberto em: {chamado.data_abertura or "Não informado"}</div>
            <div style="margin-top:8px;color:#334155;font-size:14px;">{html.escape(previa)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def callout(mensagem: str, tipo: str = "info") -> None:
    st.markdown(f'<div class="callout callout-{tipo}">{mensagem}</div>', unsafe_allow_html=True)


ICONE_POR_TIPO_EQUIPAMENTO = {
    "Computer": "💻",
    "Monitor": "🖥️",
    "Printer": "🖨️",
    "PDU": "🔌",
}


def card_equipamento(equipamento) -> None:
    icone = ICONE_POR_TIPO_EQUIPAMENTO.get(equipamento.tipo, "🖥️")
    serie = html.escape(equipamento.numero_serie) if equipamento.numero_serie else "Não informado"

    st.markdown(
        f"""
        <div class="equip-card">
            <div class="equip-icone">{icone}</div>
            <div>
                <div class="equip-nome">{html.escape(equipamento.nome) or f"#{equipamento.id}"}</div>
                <div class="equip-serie">Nº de série: {serie}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def bloco_campos_descricao(campos: list[tuple[str, str]]) -> None:
    """Renderiza pares (rótulo, valor) da descrição do chamado como campos
    organizados. Rótulos sem valor (ex.: "Respostas do formulário") viram
    um subtítulo separador em vez de um campo vazio."""
    linhas_html = []
    for rotulo, valor in campos:
        if valor:
            linhas_html.append(
                f'<div class="campo-linha"><div class="campo-rotulo">{html.escape(rotulo)}</div>'
                f'<div class="campo-valor">{html.escape(valor)}</div></div>'
            )
        else:
            linhas_html.append(
                f'<div class="campo-linha campo-secao"><div class="campo-rotulo">{html.escape(rotulo)}</div></div>'
            )

    st.markdown(f'<div class="campos-descricao">{"".join(linhas_html)}</div>', unsafe_allow_html=True)