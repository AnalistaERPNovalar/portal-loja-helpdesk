"""
Cliente da API REST do GLPI.

Esta é a ÚNICA classe que sabe falar HTTP com o GLPI. Ela não conhece
Streamlit, não conhece "loja" nem "chamado" - só sabe abrir sessão e
fazer GET/POST/DELETE genéricos. Isso é o que a torna fácil de testar
(dá pra simular respostas sem precisar rodar o Streamlit) e fácil de
reaproveitar (amanhã pode virar uma API, um bot, um script de migração).

Cada instância representa UMA sessão de usuário logado no GLPI.

Dois cuidados de performance vivem aqui, e só aqui:
1. Usamos uma única `requests.Session()` por cliente, então a conexão
   TCP/TLS com o GLPI é reaproveitada entre chamadas, em vez de ser
   reaberta a cada requisição.
2. `list_all` aceita `filtros`, que vira `searchText[campo]=valor` na
   query - isso pede pro GLPI já devolver só os itens que interessam,
   em vez de trazer a tabela inteira e filtrar em Python.
"""
from __future__ import annotations

import requests

from core.exceptions import GLPIAuthError, GLPIConnectionError, GLPIRequestError
from core.logging_config import obter_logger

logger = obter_logger(__name__)

TIMEOUT_PADRAO = 30


class GLPIClient:
    def __init__(self, glpi_url: str, app_token: str):
        self._glpi_url = glpi_url.rstrip("/")
        self._app_token = app_token
        self._session_token: str | None = None
        self._http = requests.Session()

    # ------------------------------------------------------------------
    # Sessão
    # ------------------------------------------------------------------
    @property
    def autenticado(self) -> bool:
        return self._session_token is not None

    def iniciar_sessao_usuario(self, usuario: str, senha: str) -> None:
        """Abre sessão autenticando com login/senha (usado no login da loja)."""
        headers = {"App-Token": self._app_token}

        try:
            resposta = self._http.get(
                f"{self._glpi_url}/initSession",
                headers=headers,
                auth=(usuario, senha),
                timeout=TIMEOUT_PADRAO,
            )
        except requests.RequestException as erro:
            raise GLPIConnectionError(f"Erro ao conectar no GLPI: {erro}") from erro

        if resposta.status_code != 200:
            raise GLPIAuthError("Usuário ou senha inválidos.")

        self._session_token = resposta.json().get("session_token")

        if not self._session_token:
            raise GLPIAuthError("GLPI não retornou um token de sessão válido.")

    def iniciar_sessao_user_token(self, user_token: str) -> None:
        """Abre sessão autenticando com um User-Token fixo (uso de serviço/robô)."""
        headers = {
            "App-Token": self._app_token,
            "Authorization": f"user_token {user_token}",
        }

        try:
            resposta = self._http.get(
                f"{self._glpi_url}/initSession", headers=headers, timeout=TIMEOUT_PADRAO
            )
        except requests.RequestException as erro:
            raise GLPIConnectionError(f"Erro ao conectar no GLPI: {erro}") from erro

        if resposta.status_code != 200:
            raise GLPIAuthError("Não foi possível autenticar com o User-Token configurado.")

        self._session_token = resposta.json().get("session_token")

    def encerrar_sessao(self) -> None:
        if not self._session_token:
            return
        try:
            self._http.get(f"{self._glpi_url}/killSession", headers=self._headers(), timeout=TIMEOUT_PADRAO)
        except requests.RequestException:
            pass  # best-effort: não bloqueia o logout do portal se o GLPI não responder
        finally:
            self._session_token = None

    def _headers(self) -> dict:
        if not self._session_token:
            raise GLPIAuthError("Nenhuma sessão ativa. Faça login novamente.")

        return {
            "App-Token": self._app_token,
            "Session-Token": self._session_token,
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Operações genéricas de item
    # ------------------------------------------------------------------
    def get(self, caminho: str, params: dict | None = None) -> dict | list:
        """GET genérico. `caminho` é relativo, ex: 'Ticket', 'User/12'."""
        try:
            resposta = self._http.get(
                f"{self._glpi_url}/{caminho}",
                headers=self._headers(),
                params=params or {},
                timeout=TIMEOUT_PADRAO,
            )
        except requests.RequestException as erro:
            logger.error("Falha de conexão ao buscar '%s': %s", caminho, erro)
            raise GLPIConnectionError(f"Erro ao buscar '{caminho}': {erro}") from erro

        if resposta.status_code != 200:
            logger.warning(
                "GLPI retornou status %s ao buscar '%s': %s",
                resposta.status_code, caminho, resposta.text[:300],
            )
            raise GLPIRequestError(
                f"GLPI retornou erro ao buscar '{caminho}': {resposta.text}",
                status_code=resposta.status_code,
            )

        return resposta.json()

    def list_all(self, itemtype: str, filtros: dict | None = None) -> list[dict]:
        """
        Lista itens de um tipo (ex: 'Ticket', 'Computer', 'Location').

        `filtros`, quando informado, filtra NO SERVIDOR usando o parâmetro
        `searchText` da API do GLPI (ex: {"locations_id": 12}) - o GLPI só
        devolve os itens que já batem com o filtro, em vez da tabela inteira.
        Use isso sempre que o campo existir no itemtype consultado.
        """
        params: dict = {"range": "0-9999"}

        if filtros:
            for campo, valor in filtros.items():
                params[f"searchText[{campo}]"] = valor

        dados = self.get(itemtype, params=params)
        return dados if isinstance(dados, list) else []

    def get_item(self, itemtype: str, item_id: int | str) -> dict:
        dados = self.get(f"{itemtype}/{item_id}")
        return dados if isinstance(dados, dict) else {}

    def get_sub_items(self, itemtype: str, item_id: int | str, sub_itemtype: str) -> list[dict]:
        dados = self.get(f"{itemtype}/{item_id}/{sub_itemtype}", params={"range": "0-9999"})
        return dados if isinstance(dados, list) else []

    def post(self, caminho: str, payload: dict) -> dict:
        try:
            resposta = self._http.post(
                f"{self._glpi_url}/{caminho}",
                headers=self._headers(),
                json=payload,
                timeout=TIMEOUT_PADRAO,
            )
        except requests.RequestException as erro:
            logger.error("Falha de conexão ao enviar dados para '%s': %s", caminho, erro)
            raise GLPIConnectionError(f"Erro ao enviar dados para '{caminho}': {erro}") from erro

        if resposta.status_code not in (200, 201):
            logger.warning(
                "GLPI recusou operação em '%s' (status %s): %s",
                caminho, resposta.status_code, resposta.text[:300],
            )
            raise GLPIRequestError(
                f"GLPI recusou a operação em '{caminho}': {resposta.text}",
                status_code=resposta.status_code,
            )

        return resposta.json()

    def delete(self, caminho: str) -> None:
        try:
            resposta = self._http.delete(
                f"{self._glpi_url}/{caminho}", headers=self._headers(), timeout=TIMEOUT_PADRAO
            )
        except requests.RequestException as erro:
            logger.error("Falha de conexão ao excluir '%s': %s", caminho, erro)
            raise GLPIConnectionError(f"Erro ao excluir '{caminho}': {erro}") from erro

        if resposta.status_code not in (200, 204):
            logger.warning(
                "GLPI recusou exclusão de '%s' (status %s): %s",
                caminho, resposta.status_code, resposta.text[:300],
            )
            raise GLPIRequestError(
                f"GLPI recusou a exclusão de '{caminho}': {resposta.text}",
                status_code=resposta.status_code,
            )
