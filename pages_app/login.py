"""Página de login (autenticação com usuário/senha do GLPI)."""
from __future__ import annotations

import streamlit as st

from core.exceptions import PortalError
from services import auth_service
from ui import state
from ui.components import background_login_base64, logo_base64
from ui.theme import aplicar_tema_login


def render() -> None:
    aplicar_tema_login()

    fundo = background_login_base64()
    logo = logo_base64()

    lado_esquerdo, lado_direito = st.columns([1.5, 1])

    with lado_esquerdo:
        if fundo:
            st.markdown(
                f"""
                <div style="min-height:100vh;background-image:url('data:image/png;base64,{fundo}');
                            background-size:cover;background-position:left center;"></div>
                """,
                unsafe_allow_html=True,
            )

    with lado_direito:
        if logo:
            st.markdown(
                f'<div style="text-align:center;margin-bottom:14px;">'
                f'<img src="data:image/png;base64,{logo}" style="width:150px;"></div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="login-titulo">Central de Chamados TI</div>', unsafe_allow_html=True)

        with st.form("form_login"):
            usuario = st.text_input("Usuário GLPI", placeholder="Digite seu usuário")
            senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            entrar = st.form_submit_button("ACESSAR PORTAL", use_container_width=True)

        st.markdown(
            '<div class="login-rodape">🔒 Conexão segura • Portal interno</div>',
            unsafe_allow_html=True,
        )

        if entrar:
            if not usuario or not senha:
                st.error("Informe usuário e senha.")
                return

            try:
                with st.spinner("Autenticando..."):
                    client, sessao = auth_service.autenticar(usuario, senha)
            except PortalError as erro:
                st.error(str(erro))
                return

            state.salvar_login(client, sessao)
            st.rerun()