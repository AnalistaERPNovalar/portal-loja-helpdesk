"""
Testes de performance/comportamento do glpi/tickets_repo.py.

O objetivo principal aqui não é só "a resposta está certa", mas
"o número de requisições HTTP não volta a crescer com o tamanho da
filial" - é fácil reintroduzir um N+1 sem perceber ao mexer nessa
função no futuro.
"""
from unittest.mock import MagicMock, patch

from glpi.client import GLPIClient
from glpi import tickets_repo


def _client_autenticado():
    client = GLPIClient("https://fake.example.com/apirest.php", "app-token")
    client._session_token = "tok"
    return client


def test_buscar_chamados_do_usuario_faz_no_maximo_duas_requisicoes():
    client = _client_autenticado()

    chamados_filial = [
        {"id": 100, "name": "A", "content": "", "status": 1, "date": "2026-01-01",
         "closedate": None, "locations_id": 12, "users_id_recipient": 5},
        {"id": 101, "name": "B", "content": "", "status": 2, "date": "2026-01-02",
         "closedate": None, "locations_id": 12, "users_id_recipient": 9},
        {"id": 102, "name": "C", "content": "", "status": 1, "date": "2026-01-03",
         "closedate": None, "locations_id": 12, "users_id_recipient": 20},
    ]
    vinculos_usuario_5 = [
        {"tickets_id": 101, "users_id": 5, "type": 1},  # requerente do 101
        {"tickets_id": 999, "users_id": 5, "type": 2},  # técnico em outro chamado (ignorar)
    ]

    chamadas = []

    def fake_get(url, params=None, **kwargs):
        caminho = url.rsplit("apirest.php/", 1)[-1]
        chamadas.append(caminho)
        if caminho == "Ticket":
            return MagicMock(status_code=200, json=lambda: chamados_filial)
        if caminho == "Ticket_User":
            return MagicMock(status_code=200, json=lambda: vinculos_usuario_5)
        raise AssertionError(f"chamada HTTP inesperada em teste: {caminho}")

    with patch.object(client._http, "get", side_effect=fake_get):
        resultado = tickets_repo.buscar_chamados_do_usuario(client, localizacao_id=12, usuario_id=5)

    ids = sorted(c.id for c in resultado)
    assert ids == [100, 101]  # 100: é recipient / 101: é requerente vinculado / 102: não é dele

    # O ponto central: sempre 2 chamadas, nunca 1 + (uma por chamado da filial)
    assert chamadas.count("Ticket") == 1
    assert chamadas.count("Ticket_User") == 1
    assert len(chamadas) == 2


def test_glpi_client_reaproveita_a_mesma_sessao_http():
    import requests

    client = _client_autenticado()
    assert isinstance(client._http, requests.Session)
