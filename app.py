"""
Ponto de entrada do Portal Loja.

Este arquivo só faz roteamento: decide se mostra o login ou uma página
interna, e chama o menu lateral. Nenhuma regra de negócio, nenhuma
chamada ao GLPI e nenhum CSS deveria aparecer aqui - isso vive em
services/, glpi/ e ui/.
"""
import streamlit as st

from config import settings
from core.logging_config import configurar_logging, obter_logger
from pages_app import abrir_chamado, home, login, meus_chamados, meus_equipamentos
from ui import state
from ui.navigation import menu_lateral
from ui.theme import aplicar_tema

configurar_logging()
logger = obter_logger(__name__)

st.set_page_config(
    page_title="Portal Loja e Abertura de Chamados",
    page_icon="🏪",
    layout="wide",
)

PAGINAS = {
    "home": home.render,
    "abrir_chamado": abrir_chamado.render,
    "meus_chamados": meus_chamados.render,
    "meus_equipamentos": meus_equipamentos.render,
}


def main() -> None:
    problemas_config = settings.validar()
    if problemas_config:
        logger.error("Configuração inválida: %s", "; ".join(problemas_config))
        st.error(
            "Configuração incompleta. Ajuste o arquivo .env:\n\n"
            + "\n".join(f"- {p}" for p in problemas_config)
        )
        return

    if not state.usuario_autenticado():
        login.render()
        return

    aplicar_tema()
    menu_lateral()

    pagina = state.pagina_atual()
    renderizar = PAGINAS.get(pagina, home.render)

    try:
        renderizar()
    except Exception:
        # Qualquer erro não previsto (bug, GLPI fora do ar de um jeito
        # inesperado, etc.) fica registrado no log com o traceback
        # completo, mesmo que a tela mostre só uma mensagem genérica.
        logger.exception("Erro não tratado ao renderizar a página '%s'", pagina)
        st.error(
            "Ocorreu um erro inesperado ao carregar esta página. "
            "Tente novamente ou avise o TI se o problema continuar."
        )


if __name__ == "__main__":
    main()
