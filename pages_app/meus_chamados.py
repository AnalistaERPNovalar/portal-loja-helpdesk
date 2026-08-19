"""Página meus chamados: lista com filtros/busca e detalhe de um chamado."""
from __future__ import annotations

import streamlit as st

from core.exceptions import PortalError
from core.logging_config import obter_logger
from services import ticket_service
from ui import cache, state
from ui.components import badge_status, bloco_campos_descricao, card_chamado, card_metrica

logger = obter_logger(__name__)

FILTROS = {
    "Todos": None,
    "Novo": [1],
    "Em atendimento": [2, 3, 4],
    "Solucionado": [5],
    "Fechado": [6],
}


def _filtrar(chamados, nome_filtro: str):
    status_aceitos = FILTROS[nome_filtro]
    if status_aceitos is None:
        return chamados
    return [c for c in chamados if c.status in status_aceitos]


def _barra_de_filtros(chamados) -> str:
    filtro_atual = st.session_state.get("_filtro_status_chamados", "Todos")
    colunas = st.columns(len(FILTROS))

    for coluna, nome_filtro in zip(colunas, FILTROS.keys()):
        quantidade = len(_filtrar(chamados, nome_filtro))
        if coluna.button(f"{nome_filtro}\n\n{quantidade}", use_container_width=True):
            st.session_state["_filtro_status_chamados"] = nome_filtro
            st.session_state["_chamado_selecionado_id"] = None
            st.rerun()

    return filtro_atual


def _lista_de_chamados(client, sessao) -> None:
    chamados = cache.meus_chamados(client, sessao.localizacao.id, sessao.usuario.id)

    if not chamados:
        st.info("Nenhum chamado encontrado para este usuário.")
        return

    filtro_atual = _barra_de_filtros(chamados)
    st.markdown(f"**Filtro atual:** {filtro_atual}")

    chamados_filtrados = _filtrar(chamados, filtro_atual)

    pesquisa = st.text_input(
        "🔎 Pesquisar chamado",
        placeholder="Digite número, título ou qualquer palavra do chamado...",
    )

    if pesquisa:
        chamados_filtrados = [
            c for c in chamados_filtrados if ticket_service.chamado_corresponde_pesquisa(pesquisa, c)
        ]

    st.markdown(f"**{len(chamados_filtrados)} chamado(s) encontrado(s)**")

    if not chamados_filtrados:
        st.warning("Nenhum chamado encontrado com este filtro.")
        return

    for chamado in chamados_filtrados:
        card_chamado(chamado)
        if st.button(f"👁️ Abrir chamado #{chamado.id}", key=f"abrir_{chamado.id}", use_container_width=True):
            st.session_state["_chamado_selecionado_id"] = chamado.id
            st.rerun()


def _aba_detalhes(detalhe) -> None:
    chamado = detalhe.chamado
    c1, c2, c3 = st.columns(3)
    with c1:
        card_metrica("🏷️", "Status", chamado.status_nome, "")
    with c2:
        card_metrica("📅", "Abertura", chamado.data_abertura or "Não informado", "")
    with c3:
        card_metrica("✅", "Fechamento", chamado.data_fechamento or "Em aberto", "")

    st.markdown(f"#### {chamado.titulo}")

    if detalhe.tecnicos:
        st.write(f"**Técnico(s) responsável(is):** {', '.join(detalhe.tecnicos)}")

    st.markdown("### 📝 Descrição do chamado")

    descricao_limpa = ticket_service.limpar_html(chamado.descricao_html)
    campos = ticket_service.estruturar_descricao(descricao_limpa)

    if campos:
        bloco_campos_descricao(campos)
    else:
        descricao_segura = ticket_service.texto_para_html_seguro(descricao_limpa)
        st.markdown(
            f'<div style="background:#f8fafc;border-left:6px solid #2563eb;border-radius:14px;'
            f'padding:18px;white-space:pre-wrap;">{descricao_segura}</div>',
            unsafe_allow_html=True,
        )


def _aba_conversa(client, sessao, detalhe) -> None:
    if not detalhe.mensagens:
        st.info("Nenhuma mensagem ainda.")
    else:
        for mensagem in detalhe.mensagens:
            classe = "mensagem-loja" if mensagem.da_loja else "mensagem-ti"
            autor = "Loja" if mensagem.da_loja else "TI"
            conteudo_seguro = ticket_service.texto_para_html_seguro(
                ticket_service.limpar_html(mensagem.conteudo_html)
            )
            st.markdown(
                f"""
                <div class="mensagem-bolha {classe}">
                    {conteudo_seguro}
                    <div class="mensagem-meta">{autor} • {mensagem.data}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("### ✍️ Enviar nova mensagem")
    ticket_id = detalhe.chamado.id
    nova_mensagem = st.text_area("Mensagem para o TI", height=120, key=f"nova_msg_{ticket_id}")

    col_enviar, col_atualizar = st.columns([3, 1])

    with col_enviar:
        if st.button("📨 Enviar mensagem", use_container_width=True, key=f"enviar_{ticket_id}"):
            if not nova_mensagem.strip():
                st.warning("Digite uma mensagem antes de enviar.")
            else:
                try:
                    ticket_service.enviar_mensagem_da_loja(
                        client, ticket_id, sessao.localizacao.nome, nova_mensagem
                    )
                except PortalError as erro:
                    logger.warning("Falha ao enviar mensagem no chamado #%s: %s", ticket_id, erro)
                    st.error(str(erro))
                else:
                    cache.invalidar_dados_operacionais()
                    state.flash_sucesso("Mensagem enviada com sucesso.")
                    st.rerun()

    with col_atualizar:
        if st.button("🔄 Atualizar", use_container_width=True, key=f"atualizar_{ticket_id}"):
            cache.invalidar_dados_operacionais()
            st.rerun()


def _aba_solucao(detalhe) -> None:
    if not detalhe.solucoes:
        st.info("Ainda sem solução registrada.")
        return
    for solucao in detalhe.solucoes:
        st.success(ticket_service.limpar_html(solucao))


def _aba_excluir(client, detalhe) -> None:
    chamado = detalhe.chamado

    if not chamado.pode_ser_excluido_pelo_solicitante:
        st.info(
            "Este chamado não pode ser excluído pelo portal, pois já está em "
            "atendimento, pendente, solucionado ou fechado."
        )
        return

    st.warning(
        "Atenção: esta ação irá excluir o chamado selecionado. "
        "Use somente se o chamado foi aberto por engano."
    )
    confirmar = st.checkbox(f"Confirmo que desejo excluir o chamado #{chamado.id}", key=f"confirmar_{chamado.id}")

    if st.button("🗑️ Excluir este chamado", use_container_width=True, key=f"excluir_{chamado.id}"):
        if not confirmar:
            st.warning("Marque a confirmação antes de excluir.")
            return

        try:
            ticket_service.excluir_chamado(client, chamado)
        except PortalError as erro:
            logger.warning("Falha ao excluir chamado #%s: %s", chamado.id, erro)
            state.flash_erro(str(erro))
        else:
            cache.invalidar_dados_operacionais()
            state.flash_sucesso("Chamado excluído com sucesso.")
            st.session_state["_chamado_selecionado_id"] = None

        st.rerun()


def _detalhe_do_chamado(client, sessao, ticket_id: int) -> None:
    with st.spinner("Carregando detalhes do chamado..."):
        detalhe = cache.detalhe_chamado(client, ticket_id)

    st.markdown(
        f'<div style="margin:8px 0 18px;">'
        f'<span style="font-size:22px;font-weight:900;color:#003b73;">Chamado #{ticket_id}</span> '
        f'{badge_status(detalhe.chamado)}</div>',
        unsafe_allow_html=True,
    )

    aba_detalhes, aba_conversa, aba_solucao, aba_excluir = st.tabs(
        ["📄 Detalhes", f"💬 Conversa ({len(detalhe.mensagens)})", "✅ Solução", "🗑️ Excluir"]
    )

    with aba_detalhes:
        _aba_detalhes(detalhe)
    with aba_conversa:
        _aba_conversa(client, sessao, detalhe)
    with aba_solucao:
        _aba_solucao(detalhe)
    with aba_excluir:
        _aba_excluir(client, detalhe)


def render() -> None:
    sessao = state.obter_sessao()
    client = state.obter_client()

    st.markdown("## 📋 Meus chamados")
    st.caption("Acompanhe seus chamados e interaja com o TI")

    if st.button("🔄 Atualizar"):
        cache.invalidar_dados_operacionais()
        st.rerun()

    state.consumir_flashes()
    st.markdown(f"**Filial:** {sessao.localizacao.nome}")

    _lista_de_chamados(client, sessao)

    ticket_id = st.session_state.get("_chamado_selecionado_id")
    if ticket_id:
        _detalhe_do_chamado(client, sessao, ticket_id)