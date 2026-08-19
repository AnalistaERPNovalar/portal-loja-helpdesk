"""Página de abertura de chamado: chamado rápido ou solicitação via formulário."""
from __future__ import annotations

import streamlit as st

from core.exceptions import PortalError
from core.logging_config import obter_logger
from services import ticket_service
from ui import cache, state
from ui.components import cabecalho

logger = obter_logger(__name__)


def _renderizar_campo_formulario(pergunta):
    label = f"{pergunta.nome} {'*' if pergunta.obrigatoria else ''}"
    key = f"form_q_{pergunta.id}"

    if pergunta.tipo_campo == "textarea":
        return st.text_area(label, key=key, height=130)
    if pergunta.tipo_campo in ("dropdown", "select"):
        if pergunta.opcoes:
            return st.selectbox(label, [""] + pergunta.opcoes, key=key)
        st.caption(
            f"⚠️ {pergunta.nome}: não foi possível carregar as opções configuradas no GLPI para "
            "este campo. Preencha manualmente abaixo."
        )
        return st.text_input(label, key=key)
    if pergunta.tipo_campo == "checkbox":
        return st.checkbox(label, key=key)
    if pergunta.tipo_campo == "date":
        return str(st.date_input(label, key=key))
    if pergunta.tipo_campo == "file":
        # Este portal não envia anexos para o GLPI. Em vez de fingir que
        # anexou (o que enganaria quem está abrindo o chamado), avisamos
        # e não incluímos esta pergunta na resposta enviada.
        st.caption(f"📎 {pergunta.nome}: anexos não são aceitos por este portal. Descreva o problema em detalhes no campo de texto.")
        return None

    return st.text_input(label, key=key)


def _abrir_chamado_rapido(client, sessao) -> None:
    st.info("Use esta opção para problemas simples e urgentes.")

    solicitante = st.text_input("Nome do Solicitante *")

    categorias = cache.categorias(client)
    if not categorias:
        st.error("Nenhuma categoria de chamado encontrada no GLPI.")
        return

    categoria = st.selectbox("Tipo do problema *", categorias, format_func=lambda c: c.nome)
    acesso_remoto = st.text_input("Informe o ID do acesso remoto *", placeholder="Anydesk ou HoptoDesk")
    descricao = st.text_area("Descrição do problema *", height=180)

    if st.button("📨 Abrir chamado rápido", use_container_width=True):
        if not solicitante or not acesso_remoto or not descricao:
            st.error("Preencha todos os campos obrigatórios.")
            return

        try:
            with st.spinner("Enviando chamado..."):
                ticket_service.abrir_chamado_rapido(
                    client,
                    solicitante=solicitante,
                    localizacao_id=sessao.localizacao.id,
                    localizacao_nome=sessao.localizacao.nome,
                    usuario_id=sessao.usuario.id,
                    categoria=categoria,
                    acesso_remoto=acesso_remoto,
                    descricao=descricao,
                )
        except PortalError as erro:
            logger.warning("Falha ao abrir chamado rápido (filial id=%s): %s", sessao.localizacao.id, erro)
            st.error(str(erro))
            return

        cache.invalidar_dados_operacionais()
        state.flash_sucesso("Chamado criado com sucesso.")
        state.ir_para_pagina("meus_chamados")
        st.rerun()


def _abrir_chamado_formulario(client, sessao) -> None:
    formularios = cache.formularios_ativos(client)

    if not formularios:
        st.error("Nenhum formulário ativo encontrado no GLPI.")
        return

    formulario_id = st.session_state.get("_formulario_selecionado_id")

    if formulario_id is None:
        st.info("Escolha abaixo o tipo de solicitação que deseja abrir.")
        cols = st.columns(2)

        for i, formulario in enumerate(formularios):
            with cols[i % 2]:
                st.markdown(f"**📋 {formulario.nome}**")
                if st.button("Abrir solicitação", key=f"abrir_form_{formulario.id}", use_container_width=True):
                    st.session_state["_formulario_selecionado_id"] = formulario.id
                    st.rerun()
        return

    formulario = next((f for f in formularios if f.id == formulario_id), None)

    if formulario is None:
        st.session_state["_formulario_selecionado_id"] = None
        st.rerun()
        return

    if st.button("⬅️ Voltar para lista de formulários"):
        st.session_state["_formulario_selecionado_id"] = None
        st.rerun()

    st.markdown(f"## 📋 {formulario.nome}")
    solicitante = st.text_input("Nome da pessoa solicitante *")

    respostas = {}
    for secao in cache.secoes_formulario(client, formulario.id):
        st.markdown(f"### {secao.nome}")
        for pergunta in cache.perguntas_secao(client, secao.id):
            valor = _renderizar_campo_formulario(pergunta)
            if valor is None:
                continue  # pergunta do tipo arquivo: não coletada por este portal
            respostas[pergunta.id] = {
                "pergunta": pergunta.nome,
                "valor": valor,
                "obrigatorio": pergunta.obrigatoria,
            }

    if st.button("📨 Enviar solicitação estruturada", use_container_width=True):
        if not solicitante:
            st.error("Informe o nome da pessoa solicitante.")
            return

        faltando = ticket_service.campos_obrigatorios_faltando(respostas)
        if faltando:
            st.error("Preencha os campos obrigatórios: " + ", ".join(faltando))
            return

        try:
            with st.spinner("Enviando solicitação..."):
                ticket_service.abrir_chamado_via_formulario(
                    client,
                    solicitante=solicitante,
                    localizacao_id=sessao.localizacao.id,
                    localizacao_nome=sessao.localizacao.nome,
                    usuario_id=sessao.usuario.id,
                    formulario=formulario,
                    respostas=respostas,
                )
        except PortalError as erro:
            logger.warning("Falha ao abrir chamado via formulário (filial id=%s): %s", sessao.localizacao.id, erro)
            st.error(str(erro))
            return

        st.session_state["_formulario_selecionado_id"] = None
        cache.invalidar_dados_operacionais()
        state.flash_sucesso("Solicitação criada com sucesso.")
        state.ir_para_pagina("meus_chamados")
        st.rerun()


def render() -> None:
    sessao = state.obter_sessao()
    client = state.obter_client()

    cabecalho("🎫 Abrir chamado")
    st.markdown(f"**Filial:** {sessao.localizacao.nome}")

    opcao = st.radio("Como deseja abrir o chamado?", ["⚡ Chamado rápido", "📋 Solicitação via Formulários"])
    st.markdown("---")

    if opcao == "⚡ Chamado rápido":
        _abrir_chamado_rapido(client, sessao)
    else:
        _abrir_chamado_formulario(client, sessao)