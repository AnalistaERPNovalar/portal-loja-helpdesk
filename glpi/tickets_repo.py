"""Acesso ao recurso Ticket do GLPI e seus sub-itens (followups, tarefas, soluções)."""
from __future__ import annotations

from domain.models import Chamado, Mensagem
from glpi.client import GLPIClient
from glpi.locations_repo import filtrar_por_localizacao

TYPE_REQUERENTE = 1
TYPE_TECNICO = 2


def listar_chamados_localizacao(client: GLPIClient, localizacao_id: int) -> list[dict]:
    """Retorna os dicts crus (uso interno dos repositórios)."""
    # Filtra no servidor (searchText faz "contém", por isso ainda cruzamos
    # com o filtro exato em Python) - evita baixar TODOS os chamados do GLPI
    # a cada carregamento de página.
    brutos = client.list_all("Ticket", filtros={"locations_id": localizacao_id})
    return filtrar_por_localizacao(brutos, localizacao_id)


def buscar_chamados_localizacao(client: GLPIClient, localizacao_id: int) -> list[Chamado]:
    return [Chamado.from_glpi(item) for item in listar_chamados_localizacao(client, localizacao_id)]


def buscar_vinculos_usuarios(client: GLPIClient, ticket_id: int) -> list[dict]:
    return client.get_sub_items("Ticket", ticket_id, "Ticket_User")


def buscar_chamados_do_usuario(
    client: GLPIClient, localizacao_id: int, usuario_id: int
) -> list[Chamado]:
    """
    Chamados da filial em que o usuário é o recipient OU um requerente vinculado.

    Antes, isso fazia 1 chamada por chamado da filial para descobrir os
    vínculos (N+1: uma filial com 200 chamados = até 200 requisições HTTP
    só para montar esta lista). Agora são sempre 2 chamadas no total: os
    chamados da filial, e os vínculos do usuário em todo o GLPI.
    """
    chamados_brutos = listar_chamados_localizacao(client, localizacao_id)

    vinculos_usuario = client.list_all("Ticket_User", filtros={"users_id": usuario_id})
    tickets_como_requerente = {
        int(v.get("tickets_id"))
        for v in vinculos_usuario
        if str(v.get("users_id")) == str(usuario_id) and int(v.get("type", 0)) == TYPE_REQUERENTE
    }

    resultado = [
        chamado
        for chamado in chamados_brutos
        if str(chamado.get("users_id_recipient")) == str(usuario_id)
        or int(chamado.get("id")) in tickets_como_requerente
    ]

    return [Chamado.from_glpi(item) for item in resultado]


def buscar_tecnicos_do_chamado(client: GLPIClient, ticket_id: int) -> list[str]:
    from glpi.users_repo import nome_usuario

    vinculos = buscar_vinculos_usuarios(client, ticket_id)
    return [
        nome_usuario(client, v.get("users_id"))
        for v in vinculos
        if v.get("type") == TYPE_TECNICO
    ]


def buscar_mensagens_do_chamado(client: GLPIClient, ticket_id: int) -> list[Mensagem]:
    dados = client.get_sub_items("Ticket", ticket_id, "TicketFollowup")
    mensagens = [Mensagem.from_glpi_followup(item) for item in dados]
    return sorted(mensagens, key=lambda m: m.data)


def buscar_solucoes_do_chamado(client: GLPIClient, ticket_id: int) -> list[str]:
    dados = client.get_sub_items("Ticket", ticket_id, "ITILSolution")
    return [item.get("content", "") for item in dados]


def buscar_chamado(client: GLPIClient, ticket_id: int) -> Chamado:
    return Chamado.from_glpi(client.get_item("Ticket", ticket_id))


def criar_chamado(
    client: GLPIClient,
    titulo: str,
    descricao: str,
    localizacao_id: int,
    usuario_id: int,
    categoria_id: int | None = None,
) -> Chamado:
    payload = {
        "input": {
            "name": titulo,
            "content": descricao,
            "status": 1,
            "locations_id": int(localizacao_id),
            "users_id_recipient": int(usuario_id),
            "_users_id_requester": int(usuario_id),
        }
    }

    if categoria_id:
        payload["input"]["itilcategories_id"] = int(categoria_id)

    resposta = client.post("Ticket", payload)
    ticket_id = resposta.get("id")

    return buscar_chamado(client, ticket_id)


def enviar_followup(client: GLPIClient, ticket_id: int, mensagem: str) -> None:
    payload = {
        "input": {
            "itemtype": "Ticket",
            "items_id": int(ticket_id),
            "content": mensagem,
            "is_private": 0,
        }
    }
    client.post("TicketFollowup", payload)


def excluir_chamado(client: GLPIClient, ticket_id: int) -> None:
    client.delete(f"Ticket/{ticket_id}")