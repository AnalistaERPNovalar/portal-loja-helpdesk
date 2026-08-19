"""
Exemplos de teste da camada de serviços.

Como glpi/client.py é a única coisa que fala HTTP e ela não depende do
Streamlit, dá pra testar as regras de negócio sem precisar de um GLPI
de verdade no ar - basta simular (mock) os métodos do client.

Rodar com:  pytest
"""
from unittest.mock import MagicMock

from domain.models import Chamado
from services import ticket_service


def _chamado(id=1, titulo="Impressora não liga", conteudo="<p>Detalhe do problema</p>"):
    return Chamado(
        id=id,
        titulo=titulo,
        descricao_html=conteudo,
        status=1,
        data_abertura="2026-01-01 10:00:00",
        data_fechamento=None,
        localizacao_id=10,
        usuario_recipient_id=5,
    )


def test_limpar_html_remove_tags_e_normaliza_quebras_de_linha():
    resultado = ticket_service.limpar_html("<p>Olá</p><br>Mundo")
    assert resultado == "Olá\nMundo"


def test_limpar_html_com_vazio_retorna_vazio():
    assert ticket_service.limpar_html(None) == ""
    assert ticket_service.limpar_html("") == ""


def test_texto_para_html_seguro_neutraliza_tags_reveladas_por_entidades_numericas():
    """
    Regressão: entidades numéricas (&#60;script&#62;) só viram '<script>' de
    verdade DEPOIS que limpar_html decodifica o HTML - se a saída fosse
    inserida crua num st.markdown(unsafe_allow_html=True), um chamado ou
    mensagem malicioso executaria JavaScript no navegador de quem o visse
    (XSS armazenado). texto_para_html_seguro tem que neutralizar isso.
    """
    malicioso = "Olá &#60;script&#62;alert(document.cookie)&#60;/script&#62;"
    limpo = ticket_service.limpar_html(malicioso)
    seguro = ticket_service.texto_para_html_seguro(limpo)

    assert "<script>" not in seguro
    assert "&lt;script&gt;" in seguro


def test_chamado_corresponde_pesquisa_por_substring():
    chamado = _chamado(titulo="Impressora não liga")
    assert ticket_service.chamado_corresponde_pesquisa("impressora", chamado)
    assert ticket_service.chamado_corresponde_pesquisa("IMPRESSORA", chamado)
    assert not ticket_service.chamado_corresponde_pesquisa("nobreak", chamado)


def test_chamado_corresponde_pesquisa_tolera_acento_e_pequeno_erro_digitacao():
    chamado = _chamado(titulo="Não consigo emitir boleto")
    assert ticket_service.chamado_corresponde_pesquisa("nao emitir boleto", chamado)
    assert ticket_service.chamado_corresponde_pesquisa("boleeto", chamado)  # erro de digitação


def test_campos_obrigatorios_faltando_detecta_vazio():
    respostas = {
        1: {"pergunta": "Nome", "valor": "", "obrigatorio": True},
        2: {"pergunta": "Telefone", "valor": "11999999999", "obrigatorio": True},
        3: {"pergunta": "Observação", "valor": "", "obrigatorio": False},
    }
    faltando = ticket_service.campos_obrigatorios_faltando(respostas)
    assert faltando == ["Nome"]


def test_excluir_chamado_bloqueia_quando_status_nao_e_novo():
    client = MagicMock()
    chamado_em_atendimento = _chamado()
    chamado_em_atendimento.status = 2

    try:
        ticket_service.excluir_chamado(client, chamado_em_atendimento)
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass

    client.delete.assert_not_called()


def test_excluir_chamado_permite_quando_status_novo():
    client = MagicMock()
    chamado_novo = _chamado()  # status=1 por padrão

    ticket_service.excluir_chamado(client, chamado_novo)

    client.delete.assert_called_once()
