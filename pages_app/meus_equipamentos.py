"""Página meus equipamentos: inventário de TI vinculado à filial."""
from __future__ import annotations

import streamlit as st

from ui import cache, state
from ui.components import cabecalho, card_equipamento


def _secao(titulo: str, equipamentos, colunas: int = 3) -> None:
    st.markdown(f"### {titulo}")

    if not equipamentos:
        st.info("Nenhum item encontrado.")
        return

    for inicio in range(0, len(equipamentos), colunas):
        grade = st.columns(colunas)
        lote = equipamentos[inicio: inicio + colunas]
        for coluna, equipamento in zip(grade, lote):
            with coluna:
                card_equipamento(equipamento)


def render() -> None:
    sessao = state.obter_sessao()
    client = state.obter_client()

    cabecalho("💻 Meus equipamentos")

    if st.button("🔄 Atualizar equipamentos"):
        cache.invalidar_inventario()
        st.rerun()

    st.markdown(f"**Filial:** {sessao.localizacao.nome}")

    with st.spinner("Carregando inventário..."):
        inventario = cache.inventario_filial(client, sessao.localizacao.id)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💻 Computadores", len(inventario.computadores))
    col2.metric("🖥️ Monitores", len(inventario.monitores))
    col3.metric("🖨️ Impressoras", len(inventario.impressoras))
    col4.metric("🔌 PDUs/Nobreaks", len(inventario.pdus))

    st.markdown("---")
    _secao("💻 Computadores", inventario.computadores)
    _secao("🖥️ Monitores", inventario.monitores)
    _secao("🖨️ Impressoras", inventario.impressoras)
    _secao("🔌 PDUs/Nobreaks", inventario.pdus)