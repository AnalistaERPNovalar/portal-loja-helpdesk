"""Menu lateral e navegação entre páginas."""
from __future__ import annotations

import streamlit as st

from ui import state
from ui.components import logo_base64

PAGINAS = {
    "home": "🏠 Início",
    "abrir_chamado": "🎫 Abrir chamado",
    "meus_chamados": "📋 Meus chamados",
    "meus_equipamentos": "💻 Meus equipamentos",
}


def menu_lateral() -> None:
    sessao = state.obter_sessao()

    logo = logo_base64()
    if logo:
        st.sidebar.markdown(
            f'<img src="data:image/png;base64,{logo}" style="width:100%;border-radius:14px;margin-bottom:16px;">',
            unsafe_allow_html=True,
        )

    st.sidebar.markdown("## Portal Loja")
    st.sidebar.success(f"Filial: {sessao.localizacao.nome}")

    nomes = list(PAGINAS.values())
    pagina_atual = state.pagina_atual()

    # O rádio abaixo tem `key`, e quando um widget com `key` já existe em
    # st.session_state o Streamlit ignora o `index` e mantém o valor
    # antigo do widget. Isso é útil quando o próprio usuário clica no
    # rádio (o valor novo já está em session_state e deve prevalecer),
    # mas atrapalha quando a navegação veio de fora (botões de "Ações
    # rápidas" na Home) - nesse caso o widget precisa ser atualizado à
    # força. Por isso só sobrescrevemos o valor do widget quando há uma
    # navegação externa pendente; do contrário, o clique do próprio
    # usuário no menu seria desfeito a cada rerun.
    if state.consumir_navegacao_pendente():
        st.session_state["menu_lateral_radio"] = PAGINAS.get(pagina_atual, nomes[0])

    escolha = st.sidebar.radio("Menu", nomes, key="menu_lateral_radio")

    for chave, nome in PAGINAS.items():
        if escolha == nome:
            state.sincronizar_pagina_do_menu(chave)
            break

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair do sistema", use_container_width=True):
        state.obter_client().encerrar_sessao()
        state.encerrar_sessao()
        st.rerun()