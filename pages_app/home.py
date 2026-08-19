"""Página inicial: dashboard resumido da filial."""
from __future__ import annotations

import streamlit as st

from ui import cache, state
from ui.components import cabecalho, callout, card_chamado, card_metrica


def render() -> None:
    sessao = state.obter_sessao()
    client = state.obter_client()

    cabecalho(f"🏪 {sessao.localizacao.nome}")

    if st.button("🔄 Atualizar"):
        cache.invalidar_dados_operacionais()
        cache.invalidar_inventario()
        st.rerun()

    with st.spinner("Carregando resumo da filial..."):
        resumo = cache.resumo_filial(client, sessao.localizacao.id)

    st.markdown("### Resumo da filial")
    col1, col2, col3 = st.columns(3)

    with col1:
        card_metrica("🎫", "Chamados abertos", len(resumo.chamados_abertos), "Chamados ainda em andamento")
    with col2:
        card_metrica("🔵", "Em atendimento", len(resumo.chamados_em_atendimento), "Chamados com o TI ou pendentes")
    with col3:
        card_metrica("💻", "Equipamentos", resumo.inventario.total, "Itens vinculados à filial")

    st.markdown("### Ações rápidas")
    acao1, acao2, acao3 = st.columns(3)

    with acao1:
        if st.button("🎫 Abrir chamado", use_container_width=True):
            state.ir_para_pagina("abrir_chamado")
            st.rerun()
    with acao2:
        if st.button("📋 Meus chamados", use_container_width=True):
            state.ir_para_pagina("meus_chamados")
            st.rerun()
    with acao3:
        if st.button("💻 Meus equipamentos", use_container_width=True):
            state.ir_para_pagina("meus_equipamentos")
            st.rerun()

    st.markdown("### Últimos chamados da filial")
    ultimos = resumo.ultimos_chamados()

    if not ultimos:
        st.info("Nenhum chamado encontrado para esta filial.")
    else:
        for chamado in ultimos:
            card_chamado(chamado)

    callout(
        "⚠️ Para problemas críticos, como caixa parado, internet fora ou sistema sem abrir, "
        "abra o chamado com o máximo de detalhes possível e informe o TI imediatamente.",
        tipo="warning",
    )
