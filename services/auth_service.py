"""
Serviço de autenticação.

Concentra tudo que envolve "logar a loja no GLPI" em um único lugar:
abrir sessão, descobrir o usuário, descobrir a filial dele. A UI só
chama `autenticar(...)` e recebe uma SessaoUsuario pronta ou uma
exceção com uma mensagem clara.
"""
from __future__ import annotations

from config import settings
from core.exceptions import GLPIAuthError, PortalError, UsuarioSemLocalizacaoError
from core.logging_config import obter_logger
from domain.models import SessaoUsuario
from glpi.client import GLPIClient
from glpi.locations_repo import buscar_localizacao
from glpi.users_repo import buscar_usuario

logger = obter_logger(__name__)


def autenticar(usuario_login: str, senha: str) -> tuple[GLPIClient, SessaoUsuario]:
    """
    Autentica no GLPI e monta a sessão do usuário.

    Retorna o client já autenticado (para ser guardado em st.session_state
    e reaproveitado nas próximas chamadas) e os dados da sessão.
    """
    client = GLPIClient(settings.glpi_url, settings.app_token)

    try:
        client.iniciar_sessao_usuario(usuario_login, senha)

        full_session = client.get("getFullSession")
        sessao_glpi = full_session.get("session", {}) if isinstance(full_session, dict) else {}

        user_id = (
            sessao_glpi.get("glpiID")
            or sessao_glpi.get("glpi_currenttime_user_id")
            or (full_session.get("glpiID") if isinstance(full_session, dict) else None)
        )

        if not user_id:
            raise GLPIAuthError("Não foi possível identificar o usuário logado.")

        usuario = buscar_usuario(client, user_id, login_fallback=usuario_login)

        if not usuario.localizacao_id:
            raise UsuarioSemLocalizacaoError(
                "Usuário sem localização vinculada no GLPI. "
                "Procure o TI para configurar a filial do usuário."
            )

        localizacao = buscar_localizacao(client, usuario.localizacao_id)
    except PortalError as erro:
        # Nunca logar a senha - só o login (nome de usuário) e o motivo da falha.
        logger.warning("Falha de login para o usuário '%s': %s", usuario_login, erro)
        raise

    logger.info(
        "Login bem-sucedido: usuário '%s' (id=%s) - filial '%s' (id=%s)",
        usuario.login, usuario.id, localizacao.nome, localizacao.id,
    )
    return client, SessaoUsuario(usuario=usuario, localizacao=localizacao)
