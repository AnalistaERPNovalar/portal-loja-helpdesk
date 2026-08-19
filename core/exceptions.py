"""Exceções específicas da aplicação.

Usar exceções nomeadas (em vez de tuplas (bool, str) espalhadas pelo código)
deixa claro, em cada camada, o que pode dar errado e por quê - e permite
tratar cada caso no lugar certo (a UI decide como mostrar a mensagem).
"""


class PortalError(Exception):
    """Erro base de qualquer falha conhecida da aplicação."""


class GLPIConnectionError(PortalError):
    """Falha de rede/timeout ao falar com o GLPI."""


class GLPIAuthError(PortalError):
    """Usuário/senha inválidos ou sessão do GLPI expirada."""


class GLPIRequestError(PortalError):
    """O GLPI respondeu, mas com um erro (status >= 400)."""

    def __init__(self, mensagem: str, status_code: int | None = None):
        super().__init__(mensagem)
        self.status_code = status_code


class UsuarioSemLocalizacaoError(PortalError):
    """Usuário logado não tem filial (Location) vinculada no GLPI."""
